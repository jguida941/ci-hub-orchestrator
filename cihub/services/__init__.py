"""Services layer for cihub - pure Python APIs returning dataclasses.

This module provides stable APIs for CLI, GUI, and programmatic access.
"""

from cihub.services.aggregation import (
    AggregationResult,
    aggregate_from_dispatch,
    aggregate_from_reports_dir,
)
from cihub.services.discovery import (
    DiscoveryFilters,
    DiscoveryResult,
    discover_repositories,
)
from cihub.services.report_validator import (
    ValidationResult,
    ValidationRules,
    validate_report,
    validate_report_file,
)
from cihub.services.types import RepoEntry, ServiceResult

__all__ = [
    # Types
    "ServiceResult",
    "RepoEntry",
    # Discovery
    "DiscoveryFilters",
    "DiscoveryResult",
    "discover_repositories",
    # Validation
    "ValidationRules",
    "ValidationResult",
    "validate_report",
    "validate_report_file",
    # Aggregation
    "AggregationResult",
    "aggregate_from_dispatch",
    "aggregate_from_reports_dir",
]
