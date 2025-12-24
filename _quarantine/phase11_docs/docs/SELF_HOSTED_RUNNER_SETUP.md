# Self-Hosted Runner Deployment Guide

This guide shows how to launch the production-grade runner profile referenced in
`config/runner-isolation.yaml`. It uses AWS EC2 + Firecracker as the isolation layer,
Vault for credentials, and hands out cache provenance signatures.

## 1. Networking & Security

| Resource                    | Example Value              | Notes                                             |
|-----------------------------|----------------------------|---------------------------------------------------|
| VPC CIDR                    | `10.42.0.0/16`             | Dedicated CI network                              |
| Runner subnet               | `10.42.10.0/24`            | Only runners live here                            |
| Security group ingress      | `0.0.0.0/0 -> tcp/22`      | Optional for maintenance; otherwise disable SSH   |
| Security group egress       | Allow HTTPS to registry, artifact store, Vault, NTP | Matches `policies/egress-allowlist.md` |
| IAM role                    | `ci-intel-runner-role`     | Grants SSM + CloudWatch + restricted ECR pull/push |

## 2. Vault Roles & Policies

Create a policy that issues short-lived GitHub tokens:

```hcl
# vault/policies/ci-runner.hcl
path "github/token" {
  capabilities = ["update"]
}

path "kv/data/ci/intel/*" {
  capabilities = ["read"]
}
```

Enable the role:

```bash
vault write auth/approle/role/ci-intel-runner \
  secret_id_ttl=15m \
  secret_id_num_uses=1 \
  token_ttl=15m \
  token_max_ttl=30m \
  policies=ci-runner
```

Record the `role_id` and ship it to the hosts via AWS SSM Parameter Store:

```bash
ROLE_ID=$(vault read -field=role_id auth/approle/role/ci-intel-runner/role-id)
aws ssm put-parameter --name "/ci-intel/runner/role-id" --value "$ROLE_ID" --type SecureString
```

## 3. Firecracker Runner Image

Bake an AMI with the following packages:

- `actions-runner` (self-hosted GitHub Actions runner)
- `firecracker`, `jailer`
- `cgroup-tools`, `bubblewrap` (gVisor optional)
- `cosign`, `oras`, `jq`
- `blake3`, Python 3.12, Docker CLI

Example Packer snippet:

```json
{
  "builders": [
    {
      "type": "amazon-ebs",
      "source_ami": "ami-0c55b159cbfafe1f0",
      "instance_type": "c5.large",
      "ssh_username": "ubuntu",
      "ami_name": "ci-intel-runner-{{timestamp}}"
    }
  ],
  "provisioners": [
    {"type": "shell", "script": "scripts/install-runner.sh"}
  ]
}
```

The `install-runner.sh` script should:

1. Install dependencies (Docker, cosign, blake3, python3).
2. Download and install the GitHub actions runner.
3. Configure Firecracker or gVisor to launch build sandboxes.
4. Register the runner with tags `self-hosted`, `build-fips`, `linux`.

## 4. Launch Template (Terraform)

```hcl
resource "aws_launch_template" "ci_runner" {
  name_prefix   = "ci-intel-runner-"
  image_id      = data.aws_ami.ci_runner.id
  instance_type = "c5.xlarge"

  iam_instance_profile {
    name = aws_iam_instance_profile.ci_runner.name
  }

  network_interfaces {
    subnet_id       = aws_subnet.runner.id
    security_groups = [aws_security_group.runner.id]
  }

  user_data = base64encode(templatefile("user-data.sh", {
    github_token_ssm = "/ci-intel/github/registration-token",
    vault_role_ssm   = "/ci-intel/runner/role-id"
  }))
}
```

`user-data.sh` retrieves the GitHub registration token from SSM, the Vault role ID, and
runs the bootstrap script that fetches credentials and registers the runner.

## 5. cache_provenance.sh Integration

Ensure the bootstrap script exports the cache directory (example `CACHE_DIR=/var/cache/pip`).
`cache_provenance.sh` is now callable by the release job (see `.github/workflows/release.yml`).
Captured manifests land in `artifacts/evidence/cache/`.

## 6. Monitoring & Alerts

- Install node exporter and ship metrics to Prometheus.
- Alert when queue latency > 15m or failure rate > 3%.
- Stream logs to Loki with the runner labels.

## 7. Periodic Maintenance

- Rotate the GitHub registration token weekly (`gh api --method POST repos/<org>/<repo>/actions/runners/registration-token`).
- Rotate the Vault AppRole secret daily (the workflow already expects single-use IDs).
- Patch the AMI monthly and rebuild.
- Keep `config/runner-isolation.yaml` aligned with any new labels or concurrency requirements.

Once this runner profile is online, the existing CI guardrails ensure every build job
uses the hardened environment and produces cache provenance evidence automatically.
