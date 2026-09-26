# Development

Safe Dependabot is implemented as a Docker-based GitHub Action. The validator itself is Python 3.12 code.

## Local setup

```bash
python -m pip install -e ".[dev,docs]"
```

Run the quality checks:

```bash
ruff check .
mypy
pytest
mkdocs build --strict
```

## Documentation preview

Run the local MkDocs development server:

```bash
mkdocs serve
```

Then open the local address shown by MkDocs.

## Documentation deployment

Pull requests build the documentation in strict mode. Pushes to `main` build the same site, upload the generated `site/` directory as a Pages artifact, and deploy it through the `github-pages` environment.

The repository must use **GitHub Actions** as its Pages source in repository settings for deployment to succeed.
