package supplychain.oci_referrers_test

import data.supplychain.oci_referrers
import future.keywords.if

allow_input := {"cyclonedx": true, "spdx": true, "provenance": true}
missing_input := {"cyclonedx": true, "spdx": true}

test_allow_when_all_referrers_present if {
	oci_referrers.allow with input as allow_input
}

test_missing_referrers_detected if {
	not oci_referrers.allow with input as missing_input
	oci_referrers.missing[_] == "provenance" with input as missing_input
}
