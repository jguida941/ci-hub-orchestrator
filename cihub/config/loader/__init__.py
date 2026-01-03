"""
CI/CD Hub - Configuration Loader Package

Facade module that re-exports from submodules for backward compatibility.
Existing imports like `from cihub.config.loader import load_config` continue to work.
"""

from __future__ import annotations

from cihub.config.io import load_yaml_file
from cihub.config.loader.core import (
    ConfigValidationError,
    _load_yaml,
    _main,
    get_tool_config,
    get_tool_enabled,
    load_config,
)
from cihub.config.loader.inputs import generate_workflow_inputs
from cihub.config.merge import deep_merge

__all__ = [
    # Core loading
    "ConfigValidationError",
    "load_config",
    "_load_yaml",
    # Tool helpers
    "get_tool_enabled",
    "get_tool_config",
    # Workflow inputs
    "generate_workflow_inputs",
    # CLI
    "_main",
    # Re-exports from sibling modules for backward compatibility
    "deep_merge",
    "load_yaml_file",
]