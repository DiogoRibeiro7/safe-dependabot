"""Validate Dependabot configuration against a conservative policy."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
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


def validate(
    config: dict[str, Any],
    *,
    max_open_prs: int,
    require_major_ignore: bool,
    require_github_actions: bool,
    fail_on_broad_groups: bool,
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

    has_actions = False

    for index, raw_update in enumerate(updates, start=1):
        label = f"updates[{index}]"
        if not isinstance(raw_update, dict):
            errors.append(f"{label} must be a mapping.")
            continue

        ecosystem = raw_update.get("package-ecosystem")
        if not isinstance(ecosystem, str) or not ecosystem.strip():
            errors.append(f"{label} must define package-ecosystem.")
            ecosystem = "<unknown>"

        if ecosystem == "github-actions":
            has_actions = True

        has_location = "directory" in raw_update or "directories" in raw_update
        if not has_location:
            errors.append(f"{label} ({ecosystem}) must define directory or directories.")

        schedule = raw_update.get("schedule")
        if isinstance(schedule, dict):
            interval = schedule.get("interval")
            if interval not in ALLOWED_INTERVALS:
                errors.append(
                    f"{label} ({ecosystem}) uses unsupported schedule interval {interval!r}."
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

        broad_groups = broad_group_names(raw_update)
        for group in broad_groups:
            message = (
                f"{label} ({ecosystem}) group {group!r} matches all dependencies; "
                "this can make failures harder to isolate."
            )
            if fail_on_broad_groups:
                errors.append(message)
            else:
                warnings.append(message)

    if require_github_actions and not has_actions:
        errors.append("A github-actions update block is required by policy.")

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
    return parser


def main() -> int:
    """Run validation and return a process exit code."""

    args = build_parser().parse_args()

    try:
        if args.max_open_prs < 1:
            raise PolicyError("--max-open-prs must be at least 1.")

        config = load_config(Path(args.config))
        errors, warnings, block_count = validate(
            config,
            max_open_prs=args.max_open_prs,
            require_major_ignore=parse_bool(args.require_major_ignore),
            require_github_actions=parse_bool(args.require_github_actions),
            fail_on_broad_groups=parse_bool(args.fail_on_broad_groups),
        )
    except PolicyError as exc:
        annotate("error", str(exc))
        return 2

    for warning in warnings:
        annotate("warning", warning)
    for error in errors:
        annotate("error", error)

    set_output("update-blocks", str(block_count))

    if errors:
        print(f"safe-dependabot: failed with {len(errors)} policy error(s).")
        return 1

    print(
        f"safe-dependabot: validated {block_count} update block(s) "
        f"with {len(warnings)} warning(s)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
