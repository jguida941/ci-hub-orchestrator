package supplychain.oci_referrers

import future.keywords.if

default allow := false

required := {"cyclonedx", "spdx", "provenance"}

missing := {item |
	item := required[_]
	not has(item)
}

allow if {
	count(missing) == 0
}

has(item) if {
	input[item] == true
}
