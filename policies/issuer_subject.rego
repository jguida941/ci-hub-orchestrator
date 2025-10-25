package supplychain.issuer_subject

default allow := false

allow if {
	input.issuer == regex.match(input.policy.allowed_issuer_regex, input.issuer)[0]
	input.subject == regex.match(input.policy.allowed_subject_regex, input.subject)[0]
}

reason := msg if {
	not allow
	msg := sprintf("issuer %s or subject %s failed allowlist", [input.issuer, input.subject])
}
