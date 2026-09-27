"""Validate Dependabot configuration against a conservative policy."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Final

import yaml

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


def has_major_ignore(update: dict[str, Any]) -> bool:
    """Return whether an update block ignores all semver-major updates."""

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


def validate_detected_ecosystems(
    configured_ecosystems: set[str],
    detected_ecosystems: dict[str, list[str]],
) -> list[str]:
    """Return errors for detected ecosystems missing from Dependabot."""

    errors: list[str] = []
    for ecosystem, manifests in sorted(detected_ecosystems.items()):
        if ecosystem in configured_ecosystems:
            continue

        examples = ", ".join(manifests[:3])
        if len(manifests) > 3:
            examples += f", +{len(manifests) - 3} more"

        errors.append(
            f"Detected {ecosystem} manifest(s) ({examples}) but no matching "
            "Dependabot update block is configured."
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

        schedule = raw_update.get("schedule")
        if isinstance(schedule, dict):
            interval = schedule.get("interval")
            if interval not in ALLOWED_INTERVALS:
                errors.append(
                    f"{label} ({ecosystem}) uses unsupported schedule "
                    f"interval {interval!r}."
                )
        elif "multi-ecosystem-group" not in raw_update:
            errors.append(f"{label} ({ecosystem}) must define a schedule.")

        limit = raw_update.get("open-pull-requests-limit")
        if limit is None:
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

        if require_major_ignore and not has_major_ignore(raw_update):
            errors.append(
                f"{label} ({ecosystem}) does not ignore routine semver-major updates."
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
                configured_ecosystems,
                detected_ecosystems,
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
