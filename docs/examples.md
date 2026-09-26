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
    ignore:
      - dependency-name: "*"
        update-types: [version-update:semver-major]

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    ignore:
      - dependency-name: "*"
        update-types: [version-update:semver-major]
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
    ignore:
      - dependency-name: "*"
        update-types: [version-update:semver-major]

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    ignore:
      - dependency-name: "*"
        update-types: [version-update:semver-major]
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
    ignore:
      - dependency-name: "*"
        update-types: [version-update:semver-major]

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    ignore:
      - dependency-name: "*"
        update-types: [version-update:semver-major]
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
    ignore:
      - dependency-name: "*"
        update-types: [version-update:semver-major]

  - package-ecosystem: cargo
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    ignore:
      - dependency-name: "*"
        update-types: [version-update:semver-major]

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    ignore:
      - dependency-name: "*"
        update-types: [version-update:semver-major]
```
