package supplychain.sbom_vex

default allow = false

allow {
  not high_risk_without_vex
}

high_risk_without_vex {
  vuln := input.vulnerabilities[_]
  vuln.cvss >= input.policy.cvss_threshold
  not vex_not_affected[vuln.id]
}

high_risk_without_vex {
  vuln := input.vulnerabilities[_]
  vuln.epss_percentile >= input.policy.epss_threshold
  not vex_not_affected[vuln.id]
}

vex_not_affected[id] {
  record := input.vex[_]
  record.id == id
  record.status == "not_affected"
}

violations[id] {
  high_risk_without_vex
  vuln := input.vulnerabilities[_]
  vuln.cvss >= input.policy.cvss_threshold
  not vex_not_affected[vuln.id]
  id := vuln.id
}

message := {id: "Requires VEX justification" | id := violations[_]}
