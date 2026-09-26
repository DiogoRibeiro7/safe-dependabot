# Getting started

Safe Dependabot runs against the checked-out repository, so the workflow must check out the caller repository before invoking the action.

## 1. Configure Dependabot

Create `.github/dependabot.yml`:

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

Replace or extend the package ecosystem blocks to match the repository.

## 2. Add the policy workflow

Create `.github/workflows/dependabot-policy.yml`:

```yaml
name: Dependabot policy

on:
  pull_request:
    paths:
      - ".github/dependabot.yml"
      - "pyproject.toml"
      - "uv.lock"
      - "Cargo.toml"
      - "package.json"
      - "go.mod"
  push:
    branches:
      - main
    paths:
      - ".github/dependabot.yml"
      - "pyproject.toml"
      - "uv.lock"
      - "Cargo.toml"
      - "package.json"
      - "go.mod"

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: DiogoRibeiro7/safe-dependabot@v1
```

The manifest paths in the trigger are optional. Add the ones relevant to the repository if you want the policy check to rerun whenever dependency technology changes.

## 3. Review failures

Policy violations are emitted as GitHub Actions error annotations. Warnings are used for advisory findings, such as broad dependency groups when `fail-on-broad-groups` is disabled.

A successful run also reports how many update blocks were validated and which ecosystems were detected.
