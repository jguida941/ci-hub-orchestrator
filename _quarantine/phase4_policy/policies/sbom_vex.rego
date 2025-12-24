package supplychain.sbom_vex

import future.keywords.contains
import future.keywords.if

default allow := false

allow if {
	not high_risk_without_vex
}

high_risk_without_vex if {
	vulner := input.vulnerabilities[_]
	vulner.cvss >= input.policy.cvss_threshold
	not rule_vex_not_affected(vulner.id)
}

high_risk_without_vex if {
	vulner := input.vulnerabilities[_]
	vulner.epss_percentile >= input.policy.epss_threshold
	not rule_vex_not_affected(vulner.id)
}

rule_vex_not_affected(id) if {
	record := input.vex[_]
	record.id == id
	record.status == "not_affected"
}

violations contains id if {
	vulner := input.vulnerabilities[_]
	vulner.cvss >= input.policy.cvss_threshold
	not rule_vex_not_affected(vulner.id)
	id := vulner.id
}

message := {id: "Requires VEX justification" | id := violations[_]}
