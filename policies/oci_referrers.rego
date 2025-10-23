package supplychain.oci_referrers

default allow = false

required = {"sbom-spdx", "sbom-cyclonedx", "slsa-provenance-v1"}

allow {
  refs := {r | r := input.referrers[_].annotation}
  required \u2286 refs
}

missing[item] {
  item := required[_]
  not allow
  not some annotation
  annotation := input.referrers[_].annotation
  annotation == item
}
