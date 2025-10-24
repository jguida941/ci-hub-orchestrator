package supplychain.oci_referrers

default allow = false

required := {"cyclonedx", "spdx", "provenance"}

missing := {item |
  item := required[_]
  not has(item)
}

allow {
  count(missing) == 0
}

has(item) {
  input[item] == true
}
