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

The action currently checks **ecosystem coverage**, not whether every manifest directory has a dedicated update block. Directory-level coverage can be added as a stricter future policy.
