# Changelog

All notable changes to Safe Dependabot will be documented in this file.

The project follows semantic versioning.

## Unreleased

## 1.0.1 - 2026-09-27

### Fixed

- Treat exported `requirements*.txt` files beside `uv.lock` as part of the uv-managed project, avoiding false pip ecosystem failures.

## 1.0.0 - 2026-09-26

### Added

- Conservative Dependabot policy validation.
- Ecosystem-aware manifest detection.
- GitHub Actions, Python, Rust, Node, Go, Ruby, PHP, Java, .NET, Terraform and additional ecosystem coverage.
- Configurable policy inputs and action outputs.
- MkDocs documentation with GitHub Pages deployment.
- Self-validation against the repository's own Dependabot configuration.
- Repository governance files and contribution templates.
- Automated semantic release workflow with a moving stable major tag.

### Changed

- Repository documentation and action metadata describe ecosystem detection consistently.
