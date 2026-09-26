# Policy rules

Safe Dependabot separates routine dependency maintenance from deliberate breaking upgrades.

## Major-version updates

When `require-major-ignore` is enabled, every update block must include:

```yaml
ignore:
  - dependency-name: "*"
    update-types:
      - version-update:semver-major
```

The intention is not to avoid major upgrades permanently. It is to make them explicit engineering work with migration notes, dedicated tests, and focused review.

!!! warning "Pre-1.0 dependencies"
    Semantic versioning allows breaking changes in minor releases before version 1.0. A `0.4 -> 0.5` update can therefore still be breaking even when it is not classified as semver-major.

## Pull-request limits

Dependabot can generate substantial PR churn in repositories with many dependency groups. The default policy limits `open-pull-requests-limit` to five.

Repositories can lower this:

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  with:
    max-open-prs: 3
```

## Broad groups

A group with:

```yaml
patterns:
  - "*"
```

can make a failed CI run harder to diagnose because several dependency changes arrive together.

By default this generates a warning. To fail the policy check instead:

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  with:
    fail-on-broad-groups: true
```

## GitHub Actions coverage

With `require-github-actions: true`, Safe Dependabot requires a `github-actions` update block. Workflow dependencies age like application dependencies and should be maintained deliberately.

## Security updates

Safe Dependabot validates configuration. It does not approve, merge, or suppress security updates, and it does not replace Dependabot alerts or dependency review.
