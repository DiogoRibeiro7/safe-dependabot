# safe-dependabot

A GitHub Action that validates `.github/dependabot.yml` against a conservative dependency-update policy.

The default policy is intentionally simple:

- require Dependabot configuration version 2;
- require a GitHub Actions update block;
- require routine semantic-versioning major updates to be ignored;
- allow at most five open Dependabot pull requests per update block;
- warn when a dependency group matches every dependency, because broad groups can make CI failures harder to isolate.

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
    fail-on-broad-groups: false
```

| Input | Default | Purpose |
| --- | --- | --- |
| `config-path` | `.github/dependabot.yml` | Dependabot configuration to validate |
| `max-open-prs` | `5` | Maximum permitted `open-pull-requests-limit` |
| `require-major-ignore` | `true` | Require a wildcard rule that ignores `version-update:semver-major` |
| `require-github-actions` | `true` | Require Dependabot coverage for GitHub Actions |
| `fail-on-broad-groups` | `false` | Turn wildcard dependency-group warnings into failures |

The action exposes `update-blocks`, the number of Dependabot update blocks that were validated.

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
