"""Validate Dependabot configuration against a conservative policy."""

from __future__ import annotations

import argparse
import json
import os
import sys
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any, Final

import yaml

PATCH_UPDATE: Final[str] = "version-update:semver-patch"
MINOR_UPDATE: Final[str] = "version-update:semver-minor"
MAJOR_UPDATE: Final[str] = "version-update:semver-major"
ALLOWED_INTERVALS: Final[set[str]] = {
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "semiannually",
    "yearly",
    "cron",
}
IGNORED_DIRECTORIES: Final[set[str]] = {
    ".git",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "site",
    "target",
    "vendor",
    "venv",
}
NUGET_SUFFIXES: Final[set[str]] = {
    ".csproj",
    ".fsproj",
    ".nuspec",
    ".vbproj",
    ".vcxproj",
}


class PolicyError(ValueError):
    """Raised when a policy input is invalid."""


def parse_bool(value: str) -> bool:
    """Parse a GitHub Action boolean input."""

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise PolicyError(f"Invalid boolean value: {value!r}")


def annotate(level: str, message: str) -> None:
    """Write a GitHub workflow command annotation."""

    escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::{level}::{escaped}")


def repository_root() -> Path:
    """Return the checked-out repository root."""

    workspace = os.getenv("GITHUB_WORKSPACE")
    if workspace:
        return Path(workspace).resolve()
    return Path.cwd().resolve()


def current_checkout_branch() -> str | None:
    """Return the branch whose manifests are present in the checkout."""

    return os.getenv("GITHUB_BASE_REF") or os.getenv("GITHUB_REF_NAME") or None


def repository_default_branch() -> str | None:
    """Return the repository default branch from the GitHub event payload."""

    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        return None

    try:
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    repository = payload.get("repository")
    if not isinstance(repository, dict):
        return None

    default_branch = repository.get("default_branch")
    if isinstance(default_branch, str) and default_branch.strip():
        return default_branch.strip()
    return None


def load_config(path: Path) -> dict[str, Any]:
    """Load and type-check a Dependabot YAML file."""

    if not path.is_file():
        raise PolicyError(f"Dependabot configuration not found: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PolicyError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise PolicyError("Dependabot configuration must be a YAML mapping.")

    return raw


def manifest_ecosystem(path: Path) -> str | None:
    """Map a dependency manifest or lock file to a Dependabot ecosystem."""

    name = path.name
    suffix = path.suffix.lower()

    if name == "uv.lock":
        return "uv"
    if name in {"poetry.lock", "Pipfile", "Pipfile.lock", "setup.py", "setup.cfg"}:
        return "pip"
    if name == "pyproject.toml":
        return "uv" if (path.parent / "uv.lock").is_file() else "pip"
    if name.startswith("requirements") and suffix == ".txt":
        # uv projects often export a requirements.txt for environments that
        # cannot consume uv.lock directly. When both files live in the same
        # project directory, uv.lock is the authoritative dependency source
        # and Dependabot should manage the project through the uv ecosystem.
        return "uv" if (path.parent / "uv.lock").is_file() else "pip"

    if name == "Cargo.toml":
        return "cargo"

    if name == "package.json":
        has_bun_lock = any(
            (path.parent / lock_name).is_file()
            for lock_name in ("bun.lock", "bun.lockb")
        )
        return "bun" if has_bun_lock else "npm"

    if name in {"deno.json", "deno.jsonc", "deno.lock"}:
        return "deno"
    if name == "go.mod":
        return "gomod"
    if name == "Gemfile" or suffix == ".gemspec":
        return "bundler"
    if name == "composer.json":
        return "composer"
    if name == "pom.xml":
        return "maven"
    if name in {
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
    }:
        return "gradle"
    if name == "mix.exs":
        return "mix"
    if name == "pubspec.yaml":
        return "pub"
    if name == "Package.swift":
        return "swift"
    if name == "packages.config" or suffix in NUGET_SUFFIXES:
        return "nuget"
    if name == "global.json":
        return "dotnet-sdk"
    if name == "Manifest.toml":
        return "julia"
    if name == "Project.toml" and (path.parent / "Manifest.toml").is_file():
        return "julia"
    if name == ".terraform.lock.hcl":
        return "terraform"
    if name in {".pre-commit-config.yaml", ".pre-commit-config.yml"}:
        return "pre-commit"
    if name in {"MODULE.bazel", "WORKSPACE", "WORKSPACE.bazel"}:
        return "bazel"
    if name == "elm.json":
        return "elm"
    if name == "vcpkg.json":
        return "vcpkg"

    return None


def detect_ecosystems(root: Path) -> dict[str, list[str]]:
    """Detect Dependabot ecosystems represented by repository manifests."""

    detected: dict[str, list[str]] = {}

    for directory, dir_names, file_names in os.walk(root):
        dir_names[:] = sorted(
            name for name in dir_names if name not in IGNORED_DIRECTORIES
        )
        directory_path = Path(directory)

        for file_name in sorted(file_names):
            path = directory_path / file_name
            ecosystem = manifest_ecosystem(path)
            if ecosystem is None:
                continue

            relative_path = path.relative_to(root).as_posix()
            detected.setdefault(ecosystem, []).append(relative_path)

    return detected


def has_security_safe_major_guard(update: dict[str, Any]) -> bool:
    """Return whether routine major version updates are blocked without ignore."""

    allows = update.get("allow", [])
    if not isinstance(allows, list):
        return False

    for rule in allows:
        if not isinstance(rule, dict):
            continue
        update_types = rule.get("update-types", [])
        if not isinstance(update_types, list):
            continue

        allowed = set(update_types)
        if (
            rule.get("dependency-name") == "*"
            and MAJOR_UPDATE not in allowed
            and bool({PATCH_UPDATE, MINOR_UPDATE} & allowed)
        ):
            return True

    return False


def has_legacy_major_ignore(update: dict[str, Any]) -> bool:
    """Return whether an update block uses the legacy wildcard major ignore."""

    ignores = update.get("ignore", [])
    if not isinstance(ignores, list):
        return False

    for rule in ignores:
        if not isinstance(rule, dict):
            continue
        update_types = rule.get("update-types", [])
        if (
            rule.get("dependency-name") == "*"
            and isinstance(update_types, list)
            and MAJOR_UPDATE in update_types
        ):
            return True
    return False


def validate_schedule(
    schedule: Any,
    *,
    label: str,
) -> list[str]:
    """Validate a Dependabot schedule mapping."""

    errors: list[str] = []
    if not isinstance(schedule, dict):
        errors.append(f"{label} must define a schedule.")
        return errors

    interval = schedule.get("interval")
    if interval not in ALLOWED_INTERVALS:
        errors.append(
            f"{label} uses unsupported schedule interval {interval!r}."
        )

    return errors


def validate_multi_ecosystem_groups(
    config: dict[str, Any],
    updates: list[Any],
) -> tuple[list[str], set[str]]:
    """Validate top-level multi-ecosystem groups and grouped update references."""

    errors: list[str] = []
    raw_groups = config.get("multi-ecosystem-groups", {})

    if raw_groups is None:
        raw_groups = {}

    if not isinstance(raw_groups, dict):
        errors.append("multi-ecosystem-groups must be a mapping.")
        raw_groups = {}

    defined_groups: set[str] = set()

    for group_name, raw_group in raw_groups.items():
        label = f"multi-ecosystem-groups.{group_name}"
        if not isinstance(group_name, str) or not group_name.strip():
            errors.append("multi-ecosystem-groups keys must be non-empty strings.")
            continue

        defined_groups.add(group_name)

        if not isinstance(raw_group, dict):
            errors.append(f"{label} must be a mapping.")
            continue

        errors.extend(
            validate_schedule(
                raw_group.get("schedule"),
                label=label,
            )
        )

    referenced_groups: set[str] = set()

    for index, raw_update in enumerate(updates, start=1):
        if not isinstance(raw_update, dict):
            continue

        group_name = raw_update.get("multi-ecosystem-group")
        if group_name is None:
            continue

        label = f"updates[{index}]"
        if not isinstance(group_name, str) or not group_name.strip():
            errors.append(f"{label} multi-ecosystem-group must be a non-empty string.")
            continue

        referenced_groups.add(group_name)

        if group_name not in defined_groups:
            errors.append(
                f"{label} references undefined multi-ecosystem-group {group_name!r}."
            )

        patterns = raw_update.get("patterns")
        if (
            not isinstance(patterns, list)
            or not patterns
            or not all(isinstance(pattern, str) and pattern.strip() for pattern in patterns)
        ):
            errors.append(
                f"{label} ({group_name}) must define a non-empty patterns list."
            )

    return errors, referenced_groups


def broad_group_names(update: dict[str, Any]) -> list[str]:
    """Return dependency groups that match every dependency."""

    groups = update.get("groups", {})
    if not isinstance(groups, dict):
        return []

    broad: list[str] = []
    for name, definition in groups.items():
        if not isinstance(definition, dict):
            continue
        patterns = definition.get("patterns", [])
        if isinstance(patterns, list) and "*" in patterns:
            broad.append(str(name))
    return broad


def normalize_directory(value: str) -> str:
    """Normalize a Dependabot manifest directory or directory glob."""

    normalized = value.strip().replace("\\", "/")
    if normalized in {"", ".", "/"}:
        return "/"
    return f"/{normalized.strip('/')}"


def manifest_directory(manifest: str) -> str:
    """Return the normalized repository directory containing a manifest."""

    parent = PurePosixPath(manifest).parent.as_posix()
    if parent == ".":
        return "/"
    return normalize_directory(parent)


def _match_directory_segments(
    pattern_segments: tuple[str, ...],
    path_segments: tuple[str, ...],
) -> bool:
    """Match an anchored directory glob with support for globstar."""

    if not pattern_segments:
        return not path_segments

    head = pattern_segments[0]
    tail = pattern_segments[1:]

    if head == "**":
        return _match_directory_segments(tail, path_segments) or (
            bool(path_segments)
            and _match_directory_segments(pattern_segments, path_segments[1:])
        )

    if not path_segments or not fnmatchcase(path_segments[0], head):
        return False

    return _match_directory_segments(tail, path_segments[1:])


def directory_pattern_matches(pattern: str, directory: str) -> bool:
    """Return whether a Dependabot directories glob covers a directory."""

    normalized_pattern = normalize_directory(pattern).lstrip("/")
    normalized_directory = normalize_directory(directory).lstrip("/")

    # GitHub documents **/* as covering the current directory and recursive
    # subdirectories, so include the repository root as well.
    if normalized_pattern in {"**", "**/*"}:
        return True

    pattern_segments = tuple(
        segment for segment in normalized_pattern.split("/") if segment
    )
    path_segments = tuple(
        segment for segment in normalized_directory.split("/") if segment
    )
    return _match_directory_segments(pattern_segments, path_segments)


def path_pattern_matches(pattern: str, relative_path: str) -> bool:
    """Match an exclude-paths glob against a path relative to its update directory."""

    normalized_pattern = pattern.strip().replace("\\", "/").lstrip("/")
    normalized_path = relative_path.strip().replace("\\", "/").lstrip("/")

    if "/" not in normalized_pattern:
        return fnmatchcase(PurePosixPath(normalized_path).name, normalized_pattern)

    pattern_segments = tuple(
        segment for segment in normalized_pattern.split("/") if segment
    )
    path_segments = tuple(
        segment for segment in normalized_path.split("/") if segment
    )
    return _match_directory_segments(pattern_segments, path_segments)


def update_location_patterns(update: dict[str, Any]) -> list[tuple[str, bool]]:
    """Return configured locations as (pattern, supports_globbing) pairs."""

    locations: list[tuple[str, bool]] = []

    directory = update.get("directory")
    if isinstance(directory, str) and directory.strip():
        locations.append((normalize_directory(directory), False))

    directories = update.get("directories")
    if isinstance(directories, list):
        for value in directories:
            if isinstance(value, str) and value.strip():
                locations.append((normalize_directory(value), True))

    return locations


def update_covers_manifest(update: dict[str, Any], manifest: str) -> bool:
    """Return whether an update block covers one detected manifest."""

    directory = manifest_directory(manifest)

    matched = False
    for location, supports_globbing in update_location_patterns(update):
        if supports_globbing:
            if directory_pattern_matches(location, directory):
                matched = True
                break
        elif location == directory:
            matched = True
            break

    if not matched:
        return False

    excludes = update.get("exclude-paths", [])
    if not isinstance(excludes, list):
        return True

    # Directory coverage is exact at this point. For the detected manifest
    # itself, exclude-paths are evaluated relative to that concrete manifest
    # directory, so a filename pattern such as *.lock can exclude the file.
    relative_path = PurePosixPath(manifest).name
    for pattern in excludes:
        if isinstance(pattern, str) and path_pattern_matches(pattern, relative_path):
            return False

    return True


def effective_target_branch(
    update: dict[str, Any],
    default_branch: str | None,
) -> str | None:
    """Return the branch an update block targets for version updates."""

    target = update.get("target-branch")
    if isinstance(target, str) and target.strip():
        return target.strip()
    return default_branch


def update_applies_to_checkout(
    update: dict[str, Any],
    *,
    current_branch: str | None,
    default_branch: str | None,
) -> bool:
    """Return whether an update block applies to the checked-out manifests."""

    target = update.get("target-branch")
    if isinstance(target, str) and target.strip():
        return current_branch is not None and target.strip() == current_branch

    if current_branch is not None and default_branch is not None:
        return current_branch == default_branch

    # Outside GitHub Actions the default branch may be unknowable. Preserve
    # useful local validation by treating unscoped blocks as default coverage.
    return True


def validate_detected_ecosystems(
    updates: list[Any],
    detected_ecosystems: dict[str, list[str]],
    *,
    current_branch: str | None = None,
    default_branch: str | None = None,
) -> list[str]:
    """Return errors for detected manifests lacking directory-level coverage."""

    errors: list[str] = []
    blocks_by_ecosystem: dict[str, list[tuple[int, dict[str, Any]]]] = {}

    for index, raw_update in enumerate(updates, start=1):
        if not isinstance(raw_update, dict):
            continue
        ecosystem = raw_update.get("package-ecosystem")
        if isinstance(ecosystem, str) and ecosystem.strip():
            blocks_by_ecosystem.setdefault(ecosystem, []).append((index, raw_update))

    for ecosystem, manifests in sorted(detected_ecosystems.items()):
        blocks = blocks_by_ecosystem.get(ecosystem, [])
        if not blocks:
            examples = ", ".join(manifests[:3])
            if len(manifests) > 3:
                examples += f", +{len(manifests) - 3} more"
            errors.append(
                f"Detected {ecosystem} manifest(s) ({examples}) but no matching "
                "Dependabot update block is configured."
            )
            continue

        manifests_by_directory: dict[str, list[str]] = {}
        for manifest in manifests:
            manifests_by_directory.setdefault(manifest_directory(manifest), []).append(
                manifest
            )

        applicable_blocks = [
            (index, update)
            for index, update in blocks
            if update_applies_to_checkout(
                update,
                current_branch=current_branch,
                default_branch=default_branch,
            )
        ]

        for directory, directory_manifests in sorted(manifests_by_directory.items()):
            covered_by = [
                index
                for index, update in applicable_blocks
                if any(
                    update_covers_manifest(update, manifest)
                    for manifest in directory_manifests
                )
            ]

            if not covered_by:
                branch_detail = (
                    f" on branch {current_branch!r}" if current_branch else ""
                )
                examples = ", ".join(sorted(directory_manifests)[:3])
                errors.append(
                    f"Detected {ecosystem} manifest directory {directory} "
                    f"({examples}){branch_detail}, but no matching Dependabot "
                    "directory/directories entry covers it."
                )

        # GitHub requires multiple blocks for one ecosystem and target branch
        # to use unique, non-overlapping manifest locations. Evaluate overlap
        # against directories that actually contain detected manifests.
        scopes: dict[str | None, list[tuple[int, dict[str, Any]]]] = {}
        for index, update in blocks:
            scopes.setdefault(
                effective_target_branch(update, default_branch),
                [],
            ).append((index, update))

        for target_branch, scoped_blocks in scopes.items():
            if len(scoped_blocks) < 2:
                continue
            for directory, directory_manifests in sorted(
                manifests_by_directory.items()
            ):
                matching = [
                    index
                    for index, update in scoped_blocks
                    if any(
                        update_covers_manifest(update, manifest)
                        for manifest in directory_manifests
                    )
                ]
                if len(matching) <= 1:
                    continue

                scope = (
                    f"target branch {target_branch!r}"
                    if target_branch is not None
                    else "the default target branch"
                )
                labels = ", ".join(f"updates[{index}]" for index in matching)
                errors.append(
                    f"Detected overlapping {ecosystem} coverage for {directory} "
                    f"on {scope}: {labels}."
                )

    return errors


def validate(
    config: dict[str, Any],
    *,
    max_open_prs: int,
    require_major_ignore: bool,
    require_github_actions: bool,
    fail_on_broad_groups: bool,
    detected_ecosystems: dict[str, list[str]] | None = None,
    current_branch: str | None = None,
    default_branch: str | None = None,
) -> tuple[list[str], list[str], int]:
    """Validate configuration and return errors, warnings, and block count."""

    errors: list[str] = []
    warnings: list[str] = []

    if config.get("version") != 2:
        errors.append("Dependabot configuration must declare version: 2.")

    updates = config.get("updates")
    if not isinstance(updates, list) or not updates:
        errors.append("Dependabot configuration must contain a non-empty updates list.")
        return errors, warnings, 0

    configured_ecosystems: set[str] = set()
    group_errors, _ = validate_multi_ecosystem_groups(config, updates)
    errors.extend(group_errors)

    for index, raw_update in enumerate(updates, start=1):
        label = f"updates[{index}]"
        if not isinstance(raw_update, dict):
            errors.append(f"{label} must be a mapping.")
            continue

        ecosystem = raw_update.get("package-ecosystem")
        if not isinstance(ecosystem, str) or not ecosystem.strip():
            errors.append(f"{label} must define package-ecosystem.")
            ecosystem = "<unknown>"
        else:
            configured_ecosystems.add(ecosystem)

        has_location = "directory" in raw_update or "directories" in raw_update
        if not has_location:
            errors.append(
                f"{label} ({ecosystem}) must define directory or directories."
            )

        if "multi-ecosystem-group" not in raw_update:
            errors.extend(
                validate_schedule(
                    raw_update.get("schedule"),
                    label=f"{label} ({ecosystem})",
                )
            )

        limit = raw_update.get("open-pull-requests-limit")
        if limit is None and "multi-ecosystem-group" not in raw_update:
            warnings.append(
                f"{label} ({ecosystem}) does not set open-pull-requests-limit."
            )
        elif not isinstance(limit, int) or isinstance(limit, bool):
            errors.append(
                f"{label} ({ecosystem}) open-pull-requests-limit must be an integer."
            )
        elif limit > max_open_prs:
            errors.append(
                f"{label} ({ecosystem}) allows {limit} open PRs; policy maximum is "
                f"{max_open_prs}."
            )

        if require_major_ignore:
            has_safe_guard = has_security_safe_major_guard(raw_update)
            has_legacy_ignore = has_legacy_major_ignore(raw_update)

            if not has_safe_guard and not has_legacy_ignore:
                errors.append(
                    f"{label} ({ecosystem}) does not restrict routine semver-major "
                    "version updates."
                )
            elif has_legacy_ignore:
                warnings.append(
                    f"{label} ({ecosystem}) uses a wildcard semver-major ignore rule; "
                    "GitHub applies ignore rules to security updates too, so a major "
                    "security remediation can be suppressed. Prefer allow.update-types "
                    "with patch/minor version updates."
                )

        for group in broad_group_names(raw_update):
            message = (
                f"{label} ({ecosystem}) group {group!r} matches all dependencies; "
                "this can make failures harder to isolate."
            )
            if fail_on_broad_groups:
                errors.append(message)
            else:
                warnings.append(message)

    if require_github_actions and "github-actions" not in configured_ecosystems:
        errors.append("A github-actions update block is required by policy.")

    if detected_ecosystems is not None:
        errors.extend(
            validate_detected_ecosystems(
                updates,
                detected_ecosystems,
                current_branch=current_branch,
                default_branch=default_branch,
            )
        )

    return errors, warnings, len(updates)


def set_output(name: str, value: str) -> None:
    """Set a GitHub Action output when GITHUB_OUTPUT is available."""

    output_path = os.getenv("GITHUB_OUTPUT")
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=".github/dependabot.yml")
    parser.add_argument("--max-open-prs", type=int, default=5)
    parser.add_argument("--require-major-ignore", default="true")
    parser.add_argument("--require-github-actions", default="true")
    parser.add_argument("--fail-on-broad-groups", default="false")
    parser.add_argument("--detect-ecosystems", default="true")
    return parser


def main() -> int:
    """Run validation and return a process exit code."""

    args = build_parser().parse_args()

    try:
        if args.max_open_prs < 1:
            raise PolicyError("--max-open-prs must be at least 1.")

        root = repository_root()
        config_path = Path(args.config)
        if not config_path.is_absolute():
            config_path = root / config_path

        should_detect = parse_bool(args.detect_ecosystems)
        detected = detect_ecosystems(root) if should_detect else None

        config = load_config(config_path)
        errors, warnings, block_count = validate(
            config,
            max_open_prs=args.max_open_prs,
            require_major_ignore=parse_bool(args.require_major_ignore),
            require_github_actions=parse_bool(args.require_github_actions),
            fail_on_broad_groups=parse_bool(args.fail_on_broad_groups),
            detected_ecosystems=detected,
            current_branch=current_checkout_branch(),
            default_branch=repository_default_branch(),
        )
    except PolicyError as exc:
        annotate("error", str(exc))
        return 2

    for warning in warnings:
        annotate("warning", warning)
    for error in errors:
        annotate("error", error)

    detected_names = sorted(detected) if detected is not None else []
    set_output("update-blocks", str(block_count))
    set_output("detected-ecosystems", ",".join(detected_names))

    if errors:
        print(f"safe-dependabot: failed with {len(errors)} policy error(s).")
        return 1

    detected_summary = ", ".join(detected_names) if detected_names else "none"
    print(
        f"safe-dependabot: validated {block_count} update block(s) "
        f"with {len(warnings)} warning(s); detected ecosystems: "
        f"{detected_summary}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
