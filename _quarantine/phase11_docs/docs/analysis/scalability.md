# Multi-Repository CI/CD Hub Scalability Design

## Current State vs Target State

### Current Implementation (Limited)
- **Hardcoded repositories** in `.github/workflows/release.yml:83-90`
- **Shared GITHUB_TOKEN** for all repos
- **No per-repo isolation** or resource limits
- **Global concurrency** controls only

### Target Architecture (Scalable Hub)

## 1. Dynamic Repository Registration

### Configuration-Driven Approach
```yaml
# config/repositories.yaml
repositories:
  - name: learn-caesar-cipher
    owner: jguida941
    settings:
      build_timeout: 30m
      resource_limit: 2GB
      allowed_egress:
        - github.com
        - registry.npmjs.org
      secret_scope: caesar-cipher
  - name: vector-space
    owner: jguida941
    settings:
      build_timeout: 45m
      resource_limit: 4GB
      allowed_egress:
        - github.com
        - pypi.org
      secret_scope: vector-space
```

### Implementation in Workflow
```yaml
strategy:
  matrix:
    repository: ${{ fromJson(needs.load-repos.outputs.repositories) }}
```

## 2. Per-Repository Isolation

### Secret Scoping
```yaml
- name: Load repo-specific secrets
  uses: actions/secrets@v2
  with:
    scope: ${{ matrix.repository.secret_scope }}
    vault_path: ci-cd-hub/repos/${{ matrix.repository.name }}
```

### Resource Limits
```yaml
- name: Apply resource limits
  run: |
    # Set memory limits
    ulimit -v ${{ matrix.repository.settings.resource_limit }}
    # Set CPU limits
    taskset -c 0-${{ matrix.repository.settings.cpu_cores }} $$
```

### Network Isolation
```yaml
- name: Configure egress for ${{ matrix.repository.name }}
  run: |
    # Apply repo-specific egress rules
    ./scripts/enforce_egress_control.sh \
      --allowed-hosts "${{ join(matrix.repository.settings.allowed_egress, ',') }}" \
      --repo "${{ matrix.repository.name }}"
```

## 3. Fair Scheduling & Rate Limiting

### Token Bucket Implementation
```python
# tools/rate_limiter.py
class RepoRateLimiter:
    def __init__(self, repo_name, tokens_per_hour=10):
        self.repo = repo_name
        self.bucket = TokenBucket(tokens_per_hour)

    def can_run(self):
        return self.bucket.consume(1)
```

### Concurrency Control
```yaml
concurrency:
  group: ci-cd-hub-${{ matrix.repository.name }}
  max-parallel: ${{ matrix.repository.settings.max_parallel || 2 }}
```

## 4. Observability Per Repository

### Metrics Collection
```yaml
- name: Record metrics for ${{ matrix.repository.name }}
  run: |
    python3 tools/record_metrics.py \
      --repo "${{ matrix.repository.name }}" \
      --duration "${{ steps.build.outputs.duration }}" \
      --status "${{ steps.build.outputs.status }}" \
      --cost "${{ steps.build.outputs.estimated_cost }}"
```

### Dashboard Generation
```sql
-- BigQuery view for per-repo metrics
CREATE VIEW repo_metrics AS
SELECT
  repository_name,
  DATE(timestamp) as date,
  AVG(build_duration) as avg_duration,
  SUM(estimated_cost) as daily_cost,
  COUNT(*) as build_count,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failures
FROM ci_hub.pipeline_runs
GROUP BY repository_name, date
```

## 5. GitHub Actions Network Controls

Since we're staying within GitHub Actions (no self-hosted runners), we need to implement network controls at the application level:

### Application-Level Egress Control
```bash
#!/bin/bash
# scripts/github_actions_egress.sh

# Use iptables in user namespace (no sudo required)
unshare --net --map-root-user bash -c '
  # Create new network namespace
  ip link add veth0 type veth peer name veth1

  # Apply egress rules
  iptables -A OUTPUT -d 10.0.0.0/8 -j REJECT
  iptables -A OUTPUT -d 192.168.0.0/16 -j REJECT

  # Allow only approved destinations
  for host in $ALLOWED_HOSTS; do
    ip=$(dig +short $host | head -1)
    iptables -A OUTPUT -d $ip -j ACCEPT
  done

  # Default deny
  iptables -P OUTPUT DROP

  # Run build in restricted namespace
  exec "$@"
' -- make build
```

### GitHub App for Per-Repo Tokens
```yaml
- name: Get repo-specific token
  id: token
  uses: tibdex/github-app-token@v2
  with:
    app_id: ${{ secrets.CI_HUB_APP_ID }}
    private_key: ${{ secrets.CI_HUB_APP_KEY }}
    repository: ${{ matrix.repository.owner }}/${{ matrix.repository.name }}
    permissions: |
      contents: read
      packages: write
```

## 6. Implementation Roadmap

### Phase 1: Dynamic Configuration (Week 1)
- [ ] Create `config/repositories.yaml`
- [ ] Add workflow job to load repository matrix
- [ ] Test with existing 2 repos

### Phase 2: Isolation (Week 2)
- [ ] Implement per-repo secret scoping
- [ ] Add resource limit enforcement
- [ ] Deploy application-level egress control

### Phase 3: Fair Scheduling (Week 3)
- [ ] Implement token bucket rate limiting
- [ ] Add per-repo concurrency controls
- [ ] Deploy queue management with Redis

### Phase 4: Observability (Week 4)
- [ ] Wire BigQuery pipeline
- [ ] Create per-repo dashboards
- [ ] Add cost allocation tracking

## 7. Scaling Limits

### GitHub Actions Constraints
- **Concurrent jobs**: 20 for free, 500 for enterprise
- **Job duration**: 6 hours max
- **Workflow duration**: 35 days max
- **API rate limits**: 1000 requests/hour authenticated

### Mitigation Strategies
1. **Job batching**: Group small repos into single jobs
2. **Caching**: Aggressive dependency and build caching
3. **Incremental builds**: Only rebuild changed components
4. **Queue management**: Priority queue for critical repos

## 8. Security Considerations

### Trust Boundaries
- Each repository runs in isolated context
- No shared state between repository builds
- Separate artifact namespaces
- Independent signing keys per repo

### Audit Trail
```json
{
  "repository": "learn-caesar-cipher",
  "build_id": "12345",
  "triggered_by": "push",
  "security_checks": {
    "secret_scan": "passed",
    "dependency_scan": "passed",
    "egress_validation": "passed"
  },
  "attestation": "sha256:abc123..."
}
```

## 9. Multi-Repo Governance

### Onboarding Process
1. Repository owner requests inclusion
2. Security review of repository
3. Resource allocation negotiation
4. Configuration addition to `repositories.yaml`
5. Test build in staging environment
6. Production enablement

### SLA per Repository Type
| Tier | Build Time | Frequency | Support |
|------|------------|-----------|---------|
| Critical | < 15 min | Unlimited | 24/7 |
| Standard | < 30 min | 100/day | Business hours |
| Community | < 60 min | 10/day | Best effort |

## 10. Future Enhancements

### GitOps Integration (Optional)
```yaml
# If ArgoCD/Flux is deployed
- name: Sync to GitOps
  run: |
    ./scripts/update_gitops_manifest.sh \
      --repo "${{ matrix.repository.name }}" \
      --image "${{ steps.build.outputs.image }}" \
      --digest "${{ steps.build.outputs.digest }}"
```

### Service Mesh (Optional)
```yaml
# If Istio/Linkerd is available
- name: Deploy to mesh
  run: |
    ./scripts/deploy_to_mesh.sh \
      --service "${{ matrix.repository.name }}" \
      --traffic-policy "canary" \
      --weight "10"
```

## Summary

This multi-repository CI/CD hub design provides:
- ✅ **Dynamic scaling** to hundreds of repositories
- ✅ **Per-repo isolation** for security
- ✅ **Fair resource allocation**
- ✅ **Complete observability**
- ✅ **GitHub Actions compatible** (no self-hosted runners needed)
- ✅ **Production-grade security** controls

The system can start with 2 repos and scale to 100+ without architectural changes.