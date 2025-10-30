# Runner Egress Allowlist

| Destination | Purpose                    | Notes |
|-------------|----------------------------|-------|
| dns.example.com:53 | DNS resolution | UDP and TCP; update with approved resolver |
| registry.example.com:443 | Push/pull container images | Auth via OIDC + short-lived token |
| artifacts.example.com:443 | Upload Evidence Bundle      | mTLS enforced |
| vault.example.com:8200    | Fetch short-lived credentials | Bound to runner identity |
| pool.ntp.org:123          | Time synchronization        | outbound UDP; pool rotates IPs—use hostname-based allow or internal NTP proxy |

No other outbound connections are permitted. Update this table when adding a new dependency and capture the approval in change-management records.

If you require strict IP-based allowlists, work with your network team to pin to fixed-IP NTP sources (ISP-provided or an internal relay) and document the rotation policy for the pool.
