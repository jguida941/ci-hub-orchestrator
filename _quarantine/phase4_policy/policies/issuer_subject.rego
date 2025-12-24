package supplychain.issuer_subject

import future.keywords.if

default allow := false

allow if {
	issuer_regex := sprintf("^(?:%s)$", [input.policy.allowed_issuer_regex])
	subject_regex := sprintf("^(?:%s)$", [input.policy.allowed_subject_regex])
	regex.match(issuer_regex, input.issuer)
	regex.match(subject_regex, input.subject)
}

reason := msg if {
	not allow
	msg := sprintf("issuer %s or subject %s failed allowlist", [input.issuer, input.subject])
}
