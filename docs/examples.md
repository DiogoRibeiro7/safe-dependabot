# Examples

## Python

```yaml
version: 2

updates:
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    allow:
      - dependency-name: "*"
        update-types:
          - version-update:semver-minor
          - version-update:semver-patch

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    allow:
      - dependency-name: "*"
        update-types:
          - version-update:semver-minor
          - version-update:semver-patch
```

## Rust

```yaml
version: 2

updates:
  - package-ecosystem: cargo
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    allow:
      - dependency-name: "*"
        update-types:
          - version-update:semver-minor
          - version-update:semver-patch

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    allow:
      - dependency-name: "*"
        update-types:
          - version-update:semver-minor
          - version-update:semver-patch
```

## Node

```yaml
version: 2

updates:
  - package-ecosystem: npm
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    allow:
      - dependency-name: "*"
        update-types:
          - version-update:semver-minor
          - version-update:semver-patch

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    allow:
      - dependency-name: "*"
        update-types:
          - version-update:semver-minor
          - version-update:semver-patch
```

## Mixed Python and Rust repository

```yaml
version: 2

updates:
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    allow:
      - dependency-name: "*"
        update-types:
          - version-update:semver-minor
          - version-update:semver-patch

  - package-ecosystem: cargo
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    allow:
      - dependency-name: "*"
        update-types:
          - version-update:semver-minor
          - version-update:semver-patch

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    allow:
      - dependency-name: "*"
        update-types:
          - version-update:semver-minor
          - version-update:semver-patch
```
