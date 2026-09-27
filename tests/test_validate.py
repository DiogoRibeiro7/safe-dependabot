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
                "allow": [
                    {
                        "dependency-name": "*",
                        "update-types": [
                            "version-update:semver-minor",
                            "version-update:semver-patch",
                        ],
                    }
                ],
            },
            {
                "package-ecosystem": "github-actions",
                "directory": "/",
                "schedule": {"interval": "weekly"},
                "open-pull-requests-limit": 5,
                "allow": [
                    {
                        "dependency-name": "*",
                        "update-types": [
                            "version-update:semver-minor",
                            "version-update:semver-patch",
                        ],
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


def test_major_updates_are_rejected_without_version_guard() -> None:
    """Missing semver-major version guards should fail policy validation."""

    config = safe_config()
    config["updates"][0]["allow"] = []

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert any("semver-major" in error for error in errors)


def test_security_safe_allow_guard_passes_without_warning() -> None:
    """Minor/patch allow rules should guard majors without touching security updates."""

    errors, warnings, _ = validator.validate(
        safe_config(),
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert not any("security remediation" in warning for warning in warnings)


def test_legacy_major_ignore_is_accepted_with_security_warning() -> None:
    """Legacy wildcard major ignores remain compatible but should warn."""

    config = safe_config()
    config["updates"][0].pop("allow")
    config["updates"][0]["ignore"] = [
        {
            "dependency-name": "*",
            "update-types": ["version-update:semver-major"],
        }
    ]

    errors, warnings, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
    )

    assert errors == []
    assert any("security remediation" in warning for warning in warnings)


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


def test_detects_multiple_ecosystems(tmp_path: Path) -> None:
    """Repository manifests should map to the matching Dependabot ecosystems."""

    (tmp_path / "Cargo.toml").write_text(
        "[package]\nname='demo'\nversion='0.1.0'\n",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
    (tmp_path / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='demo'\n",
        encoding="utf-8",
    )

    detected = validator.detect_ecosystems(tmp_path)

    assert set(detected) == {"cargo", "gomod", "npm", "pip"}


def test_uv_lock_selects_uv_ecosystem(tmp_path: Path) -> None:
    """A pyproject with uv.lock should be treated as a uv project."""

    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='demo'\n",
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")

    detected = validator.detect_ecosystems(tmp_path)

    assert set(detected) == {"uv"}


def test_uv_lock_owns_exported_requirements_file(tmp_path: Path) -> None:
    """A requirements export beside uv.lock should not create a pip ecosystem."""

    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='demo'\n",
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text(
        "# Generated from uv.lock. Do not edit.\nexample==1.0\n",
        encoding="utf-8",
    )

    detected = validator.detect_ecosystems(tmp_path)

    assert set(detected) == {"uv"}
    assert sorted(detected["uv"]) == [
        "pyproject.toml",
        "requirements.txt",
        "uv.lock",
    ]




def test_uncovered_manifest_directory_fails_validation() -> None:
    """Every detected manifest directory must have matching coverage."""

    config = safe_config()
    config["updates"][0]["directory"] = "/apps/api"

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={
            "pip": [
                "apps/api/pyproject.toml",
                "apps/web/pyproject.toml",
            ]
        },
    )

    assert any("/apps/web" in error and "directory/directories" in error for error in errors)


def test_directories_glob_covers_monorepo_manifests() -> None:
    """The directories key should support anchored wildcard coverage."""

    config = safe_config()
    config["updates"][0].pop("directory")
    config["updates"][0]["directories"] = ["/apps/*"]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={
            "pip": [
                "apps/api/pyproject.toml",
                "apps/web/pyproject.toml",
            ]
        },
    )

    assert errors == []


def test_recursive_directories_glob_covers_root_and_nested_manifests() -> None:
    """GitHub's **/* directory glob should cover current and nested directories."""

    config = safe_config()
    config["updates"][0].pop("directory")
    config["updates"][0]["directories"] = ["**/*"]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={
            "pip": [
                "pyproject.toml",
                "apps/api/pyproject.toml",
                "apps/api/internal/requirements.txt",
            ]
        },
    )

    assert errors == []


def test_overlapping_blocks_for_same_target_branch_fail() -> None:
    """Two blocks must not cover the same manifest directory on one target branch."""

    config = safe_config()
    config["updates"][0]["directory"] = "/apps/api"
    config["updates"].insert(
        1,
        {
            "package-ecosystem": "pip",
            "directories": ["/apps/*"],
            "schedule": {"interval": "weekly"},
            "open-pull-requests-limit": 5,
            "allow": [
                {
                    "dependency-name": "*",
                    "update-types": [
                        "version-update:semver-minor",
                        "version-update:semver-patch",
                    ],
                }
            ],
        },
    )

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={"pip": ["apps/api/pyproject.toml"]},
        current_branch="main",
        default_branch="main",
    )

    assert any(
        "overlapping pip coverage" in error
        and "updates[1]" in error
        and "updates[2]" in error
        for error in errors
    )


def test_target_branch_block_does_not_cover_default_branch_checkout() -> None:
    """Coverage for another target branch must not satisfy the current checkout."""

    config = safe_config()
    config["updates"][0]["directory"] = "/apps/api"
    config["updates"][0]["target-branch"] = "develop"

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={"pip": ["apps/api/pyproject.toml"]},
        current_branch="main",
        default_branch="main",
    )

    assert any("branch 'main'" in error and "/apps/api" in error for error in errors)


def test_target_branch_block_covers_matching_checkout() -> None:
    """Explicit target-branch coverage should apply on that branch checkout."""

    config = safe_config()
    config["updates"][0]["directory"] = "/apps/api"
    config["updates"][0]["target-branch"] = "develop"

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={"pip": ["apps/api/pyproject.toml"]},
        current_branch="develop",
        default_branch="main",
    )

    assert errors == []


def test_excluded_manifest_does_not_count_as_covered() -> None:
    """An excluded detected manifest should not satisfy directory coverage."""

    config = safe_config()
    config["updates"][0]["exclude-paths"] = ["pyproject.toml"]

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={"pip": ["pyproject.toml"]},
    )

    assert any("no matching Dependabot" in error for error in errors)


def test_missing_detected_ecosystem_fails_validation() -> None:
    """Detected manifests must have corresponding Dependabot coverage."""

    config = safe_config()

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={"cargo": ["Cargo.toml"], "pip": ["pyproject.toml"]},
    )

    assert any("Detected cargo manifest" in error for error in errors)


def test_detected_ecosystems_pass_when_configured() -> None:
    """Detected manifests should pass when every ecosystem is configured."""

    config = safe_config()
    config["updates"].append(
        {
            "package-ecosystem": "cargo",
            "directory": "/",
            "schedule": {"interval": "weekly"},
            "open-pull-requests-limit": 5,
            "ignore": [
                {
                    "dependency-name": "*",
                    "update-types": ["version-update:semver-major"],
                }
            ],
        }
    )

    errors, _, _ = validator.validate(
        config,
        max_open_prs=5,
        require_major_ignore=True,
        require_github_actions=True,
        fail_on_broad_groups=False,
        detected_ecosystems={"cargo": ["Cargo.toml"], "pip": ["pyproject.toml"]},
    )

    assert errors == []
