package supplychain.issuer_subject_test

import data.supplychain.issuer_subject

allow_input := {
	"issuer": "https://issuer.example/sign",
	"subject": "https://github.com/jguida941/ci-intel-app/.github/workflows/release.yml@refs/tags/v1.0.0",
	"policy": {
		"allowed_issuer_regex": "https://issuer\\.example/sign",
		"allowed_subject_regex": "https://github\\.com/jguida941/.+",
	},
}

deny_input := {
	"issuer": allow_input.issuer,
	"subject": "https://github.com/other/repo/.github/workflows/release.yml@refs/tags/v1.0.0",
	"policy": allow_input.policy,
}

test_allowlist_passes_for_matching_issuer_subject if {
	issuer_subject.allow with input as allow_input
}

test_allowlist_blocks_unmatched_subject if {
	not issuer_subject.allow with input as deny_input
}
