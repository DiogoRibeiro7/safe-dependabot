# Configuration

Safe Dependabot exposes a small set of inputs so repositories can tighten or relax the default policy without forking the action.

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `config-path` | `.github/dependabot.yml` | Path to the Dependabot configuration file. |
| `max-open-prs` | `5` | Maximum permitted value of `open-pull-requests-limit`. |
| `require-major-ignore` | `true` | Require a wildcard rule ignoring `version-update:semver-major`. |
| `require-github-actions` | `true` | Require a `github-actions` update block. |
| `fail-on-broad-groups` | `false` | Treat groups matching every dependency as errors instead of warnings. |
| `detect-ecosystems` | `true` | Detect manifests and require matching Dependabot ecosystems. |

## Outputs

| Output | Description |
| --- | --- |
| `update-blocks` | Number of Dependabot update blocks validated. |
| `detected-ecosystems` | Comma-separated ecosystems detected from repository manifests. |

## Example

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  id: dependabot-policy
  with:
    max-open-prs: 3
    require-major-ignore: true
    require-github-actions: true
    fail-on-broad-groups: true
    detect-ecosystems: true

- name: Show detected ecosystems
  run: echo "${{ steps.dependabot-policy.outputs.detected-ecosystems }}"
```

## Disabling ecosystem detection

For unusual monorepos or generated manifests, automatic detection can be disabled:

```yaml
- uses: DiogoRibeiro7/safe-dependabot@v1
  with:
    detect-ecosystems: false
```

The rest of the Dependabot policy validation still runs.
