# Policy rules

Safe Dependabot separates routine dependency maintenance from deliberate breaking upgrades.

## Major-version updates

When `require-major-ignore` is enabled, the preferred policy is to allow routine minor and patch version updates explicitly:

```yaml
allow:
  - dependency-name: "*"
    update-types:
      - version-update:semver-minor
      - version-update:semver-patch
```

GitHub documents that `allow.update-types` affects version updates only, not security updates. This blocks routine major version-update pull requests while still allowing Dependabot to create a security update when remediation requires a major version.

Legacy wildcard `ignore` rules for `version-update:semver-major` remain accepted in v1 for compatibility, but Safe Dependabot emits a warning because GitHub applies `ignore` filtering to security updates as well.

The intention is not to avoid major upgrades permanently. It is to make routine major upgrades explicit engineering work with migration notes, dedicated tests, and focused review without weakening vulnerability remediation.

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
