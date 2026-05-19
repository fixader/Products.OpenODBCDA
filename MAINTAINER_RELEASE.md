# Maintainer Release Notes

This document is for maintainers who publish Products.OpenODBCDA releases.
It describes the release plumbing around GitHub Actions, TestPyPI, PyPI, and
GitHub Release assets.

Products.OpenODBCDA uses PyPI Trusted Publishing through GitHub Actions. This
avoids storing long-lived PyPI API tokens in GitHub secrets or on a developer
workstation.

## Package Name

The package name is:

```text
Products.OpenODBCDA
```

The version is read from:

```text
src/Products/OpenODBCDA/_version.py
```

## GitHub Environments

Create these GitHub environments before publishing:

- `testpypi`
- `pypi`

The `pypi` environment should require manual approval before deployment. This
keeps accidental releases from being published just because a release or tag was
created.

## One-Time TestPyPI Setup

1. Create or log in to a TestPyPI account at `https://test.pypi.org/`.
2. Go to account publishing settings.
3. Add a pending Trusted Publisher:

```text
Project name: Products.OpenODBCDA
Owner: fixader
Repository name: Products.OpenODBCDA
Workflow name: publish-testpypi.yml
Environment name: testpypi
```

4. In GitHub Actions, run `Publish to TestPyPI` manually.
5. Test installation from TestPyPI:

```bash
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  Products.OpenODBCDA
```

The extra PyPI index is needed because dependencies such as Zope packages and
pyodbc are normally resolved from the real PyPI.

## One-Time PyPI Setup

1. Create or log in to a PyPI account at `https://pypi.org/`.
2. Go to account publishing settings.
3. Add a pending Trusted Publisher:

```text
Project name: Products.OpenODBCDA
Owner: fixader
Repository name: Products.OpenODBCDA
Workflow name: publish-pypi.yml
Environment name: pypi
```

4. In GitHub Actions, run `Publish to PyPI` manually for the first release.

Future releases can be published by creating a GitHub Release, because
`publish-pypi.yml` also runs when a release is published.

## PyPI Release Contents

PyPI receives the normal Python packaging artifacts built by `python -m build`:

- source distribution: `.tar.gz`
- wheel: `.whl`

The legacy Python 3.8 `.egg` is not uploaded to PyPI. It is attached to GitHub
Releases for old Zope 5/buildout installations that need it.

GitHub Releases may include additional compatibility artifacts:

- source distribution with the normalized Python filename
- source distribution with the historical `Products.OpenODBCDA` filename
- wheel
- optional Python-version-specific legacy egg

## Manual Local Build Checks

Before publishing, it is useful to run:

```bash
python -m unittest discover -s src/Products/OpenODBCDA/tests -v
python -m build
python -m twine check dist/products_openodbcda-<version>.tar.gz dist/products_openodbcda-<version>-py3-none-any.whl
```
