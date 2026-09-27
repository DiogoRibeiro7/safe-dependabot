# Ecosystem detection

Safe Dependabot scans the checked-out repository for dependency manifests and maps them to the ecosystem identifiers used by Dependabot.

## Detected manifests

| Manifest | Ecosystem |
| --- | --- |
| `pyproject.toml`, `requirements*.txt`, `poetry.lock`, `Pipfile` | `pip` |
| `pyproject.toml` with `uv.lock` | `uv` |
| `Cargo.toml` | `cargo` |
| `package.json` | `npm` |
| `package.json` with `bun.lock` or `bun.lockb` | `bun` |
| `deno.json`, `deno.jsonc`, `deno.lock` | `deno` |
| `go.mod` | `gomod` |
| `Gemfile`, `*.gemspec` | `bundler` |
| `composer.json` | `composer` |
| `pom.xml` | `maven` |
| Gradle build/settings files | `gradle` |
| `mix.exs` | `mix` |
| `pubspec.yaml` | `pub` |
| `Package.swift` | `swift` |
| .NET project files and `packages.config` | `nuget` |
| `global.json` | `dotnet-sdk` |
| Julia `Manifest.toml` / `Project.toml` | `julia` |
| `.terraform.lock.hcl` | `terraform` |
| `.pre-commit-config.yaml` | `pre-commit` |
| Bazel module/workspace files | `bazel` |
| `elm.json` | `elm` |
| `vcpkg.json` | `vcpkg` |

## Ignored directories

Generated or environment-specific directories are skipped during detection, including:

```text
.git
.venv
venv
node_modules
vendor
target
build
dist
site
.tox
.nox
```

This prevents vendored or generated dependency files from creating false policy failures.

## Monorepos

Detection is recursive. If a repository contains both `Cargo.toml` and `package.json`, Safe Dependabot expects both `cargo` and `npm` coverage in `.github/dependabot.yml`.

Coverage is validated at the **manifest-directory level**. A repository with `/apps/api/package.json` and `/apps/web/package.json` will therefore fail if Dependabot covers only `/apps/api`.

Use `directories` when one ecosystem appears in several locations:

```yaml
updates:
  - package-ecosystem: npm
    directories:
      - "/apps/*"
    schedule:
      interval: weekly
```

Safe Dependabot treats `directory` as one exact manifest location and supports globbing only for `directories`, matching GitHub's configuration semantics. It also scopes coverage by `target-branch` when the checked-out branch and repository default branch are available from the GitHub Actions event.

If multiple blocks for the same ecosystem and effective target branch cover the same detected manifest directory, validation fails because GitHub requires those locations to be unique and non-overlapping.
