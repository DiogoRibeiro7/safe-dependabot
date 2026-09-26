"""Tests for the safe-dependabot policy validator."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "validate.py"


def load_validator() -> ModuleType:
    """Load the validator module directly from source."""

    spec = spec_from_file_location("safe_dependabot_validate", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load validator module.")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_validator()


def safe_config() -> dict[str, Any]:
    """Return a valid conservative Dependabot configuration."""

    return {
        "version": 2,
        "updates": [
            {
                "package-ecosystem": "pip",
                "directory": "/",
                "schedule": {"interval": "weekly"},
                "open-pull-requests-limit": 5,
                "ignore": [
                    {
                        "dependency-name": "*",
                        "update-types": ["version-update:semver-major"],
                    }
                ],
            },
            {
                "package-ecosystem": "github-actions",
                "directory": "/",
                "schedule": {"interval": "weekly"},
                "open-pull-requests-limit": 5,
                "ignore": [
                    {
                        "dependency-name": "*",
                        "update-types": ["version-update:semver-major"],
                    }
                ],
            },
        ],
    }


def test_safe_configuration_passes() -> None:
    """A conservative configuration should pass without warnings."""

    errors, warnings, count = validator.validate(
        safe_config(),
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert warnings == []
    assert count == 2


def test_major_updates_are_rejected_when_not_ignored() -> None:
    """Missing semver-major ignore rules should fail policy validation."""

    config = safe_config()
    config["updates"][0]["ignore"] = []

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("semver-major" in error for error in errors)


def test_pull_request_limit_is_enforced() -> None:
    """Update blocks above the configured PR limit should fail."""

    config = safe_config()
    config["updates"][0]["open-pull-requests-limit"] = 10

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("policy maximum is 5" in error for error in errors)


def test_broad_groups_warn_by_default() -> None:
    """Groups matching all dependencies should warn by default."""

    config = safe_config()
    config["updates"][0]["groups"] = {
        "everything": {"patterns": ["*"]},
    }

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert any("matches all dependencies" in warning for warning in warnings)


def test_broad_groups_can_be_made_fatal() -> None:
    """Users may promote broad grouping warnings to policy errors."""

    config = safe_config()
    config["updates"][0]["groups"] = {
        "everything": {"patterns": ["*"]},
    }

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=True,
    )

    assert any("matches all dependencies" in error for error in errors)


def test_github_actions_block_can_be_required() -> None:
    """The policy should detect repositories missing action updates."""

    config = safe_config()
    config["updates"] = [config["updates"][0]]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert "A github-actions update block is required by policy." in errors
