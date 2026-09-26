# Safe Dependabot

**Safe Dependabot** is a GitHub Action that validates `.github/dependabot.yml` against a conservative dependency-update policy.

It is designed for repositories where dependency updates should remain easy to review, easy to diagnose, and explicit about potentially breaking upgrades.

## What it checks

By default, Safe Dependabot verifies that:

- the configuration uses Dependabot version 2;
- routine semantic-versioning major updates are ignored;
- no update block allows more than five open Dependabot pull requests;
- GitHub Actions updates are configured;
- repository manifests have matching Dependabot ecosystem coverage;
- broad dependency groups are reported because they can make CI failures harder to isolate.

!!! note
    Safe Dependabot is implemented in Python, but it is **not Python-specific**. It validates repositories using Rust, JavaScript, Go, Ruby, Java, .NET, Terraform, Swift, Dart, Elixir, PHP and other supported ecosystems.

## Minimal usage

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
      - uses: actions/checkout@v7
      - uses: DiogoRibeiro7/safe-dependabot@v1
```

See [Getting started](getting-started.md) for the complete setup.
