package supplychain.oci_referrers

default allow = false

required = {"sbom-spdx", "sbom-cyclonedx", "slsa-provenance-v1"}

allow {
  not missing[_]
}

missing[item] {
  item := required[_]
  not has_referrer(item)
}

has_referrer(item) {
  ref := input.referrers[_]
  ref.annotation == item
}
