# Kyverno Policy Templates

Customizable templates for Kyverno policies. Copy and modify these templates for your organization.

## Available Templates

| Template | Purpose | Customization Required |
|----------|---------|----------------------|
| `verify-images-template.yaml` | Verify Cosign keyless signatures | GitHub org, registry pattern |

## Usage

```bash
# 1. Copy template to policies directory
cp templates/kyverno/verify-images-template.yaml policies/kyverno/verify-images.yaml

# 2. Edit with your values
# - Replace YOUR_ORG with your GitHub organization
# - Update registry patterns
# - Adjust namespace exclusions

# 3. Apply to cluster
kubectl apply -f policies/kyverno/verify-images.yaml
```

## See Also

- [docs/guides/KYVERNO.md](../../docs/guides/KYVERNO.md) - Full user guide
- [docs/adr/0012-kyverno-policies.md](../../docs/adr/0012-kyverno-policies.md) - Decision rationale
- [policies/kyverno/](../../policies/kyverno/) - Ready-to-use policies
