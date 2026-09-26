# safe-dependabot

A GitHub Action that validates `.github/dependabot.yml` against a conservative dependency-update policy.

The default policy is intentionally simple:

- require Dependabot configuration version 2;
- require a GitHub Actions update block;
- require routine semantic-versioning major updates to be ignored;
- allow at most five open Dependabot pull requests per update block;
- detect dependency manifests and require matching Dependabot ecosystems;\n- warn when a dependency group matches every dependency, because broad groups can make CI failures harder to isolate.

## Usage

```yaml
name: Dependabot policy

on:
  pull_request:
    paths:
      - ".github/dependabot.yml"
  push:
    branches:
      - main
    paths:
      - ".github/dependabot.yml"

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: DiogoRibeiro7/safe-dependabot@v1
```

## Configuration

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  with:
    max-open-prs: 5
    require-major-ignore: true
    require-github-actions: true
    fail-on-broad-groups: false\n    detect-ecosystems: true
```

| Input | Default | Purpose |
| --- | --- | --- |
| `config-path` | `.github/dependabot.yml` | Dependabot configuration to validate |
| `max-open-prs` | `5` | Maximum permitted `open-pull-requests-limit` |
| `require-major-ignore` | `true` | Require a wildcard rule that ignores `version-update:semver-major` |
| `require-github-actions` | `true` | Require Dependabot coverage for GitHub Actions |
| `fail-on-broad-groups` | `false` | Turn wildcard dependency-group warnings into failures |\n| `detect-ecosystems` | `true` | Detect repository manifests and require matching Dependabot ecosystems |

The action exposes `update-blocks`, the number of Dependabot update blocks that were validated, and `detected-ecosystems`, a comma-separated list of ecosystems found from repository manifests.

## Ecosystem detection

Safe Dependabot detects common dependency manifests and checks that Dependabot covers the matching ecosystem. Examples include:

| Manifest | Dependabot ecosystem |
| --- | --- |
| `pyproject.toml`, `requirements*.txt`, `poetry.lock` | `pip` |
| `pyproject.toml` + `uv.lock` | `uv` |
| `Cargo.toml` | `cargo` |
| `package.json` | `npm` |
| `package.json` + Bun lockfile | `bun` |
| `go.mod` | `gomod` |
| `Gemfile`, `*.gemspec` | `bundler` |
| `composer.json` | `composer` |
| `pom.xml` | `maven` |
| Gradle build files | `gradle` |
| `mix.exs` | `mix` |
| `pubspec.yaml` | `pub` |
| `Package.swift` | `swift` |
| .NET project files | `nuget` |
| `global.json` | `dotnet-sdk` |
| `.terraform.lock.hcl` | `terraform` |
| `.pre-commit-config.yaml` | `pre-commit` |

Generated dependency directories such as `node_modules`, `vendor`, `target`, virtual environments, and build output are ignored.

## Recommended Dependabot baseline

```yaml
version: 2

updates:
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    ignore:
      - dependency-name: "*"
        update-types:
          - version-update:semver-major

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    ignore:
      - dependency-name: "*"
        update-types:
          - version-update:semver-major
```

Security updates remain a separate Dependabot capability. This action validates the repository configuration; it does not merge, approve, or modify dependency pull requests.

## Local development

Requires Python 3.12 or newer.

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy
pytest
```

## License

MIT.
