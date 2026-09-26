# Contributing

Contributions to Safe Dependabot are welcome.

## Development setup

Safe Dependabot requires Python 3.12 or newer.

```bash
python -m pip install -e ".[dev,docs]"
```

Run the full local validation suite before opening a pull request:

```bash
ruff check .
mypy
pytest
mkdocs build --strict
```

## Pull requests

Keep pull requests focused on one concern. Changes to policy behavior should include tests that demonstrate both the accepted and rejected configuration.

When changing a supported ecosystem or manifest mapping:

1. update the detector in `src/validate.py`;
2. add or update tests;
3. update the MkDocs ecosystem documentation;
4. describe any compatibility impact in `CHANGELOG.md`.

## Commit style

Use short, descriptive conventional-style prefixes where useful, for example:

```text
feat: add ecosystem validation
fix: correct manifest detection
docs: clarify policy behavior
test: cover grouped updates
chore: maintain repository metadata
```

## Security

Do not disclose security vulnerabilities in public issues. Follow the process described in [SECURITY.md](SECURITY.md).
