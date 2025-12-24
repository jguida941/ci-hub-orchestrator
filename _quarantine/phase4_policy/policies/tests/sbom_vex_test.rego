package supplychain.sbom_vex_test

import data.supplychain.sbom_vex
import future.keywords.if

default policy := {
	"cvss_threshold": 7.0,
	"epss_threshold": 0.8,
}

test_allows_when_vex_marks_not_affected if {
	test_input := {
		"vulnerabilities": [{"id": "CVE-1", "cvss": 9.1, "epss_percentile": 0.5}],
		"policy": policy,
		"vex": [{"id": "CVE-1", "status": "not_affected"}],
	}
	sbom_vex.allow with input as test_input
}

test_denies_when_high_cvss_without_vex if {
	test_input := {
		"vulnerabilities": [{"id": "CVE-2", "cvss": 9.5, "epss_percentile": 0.1}],
		"policy": policy,
		"vex": [],
	}
	not sbom_vex.allow with input as test_input
	sbom_vex.violations[_] == "CVE-2" with input as test_input
}
