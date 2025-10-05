# Release Process

This document describes how to publish glitchlings releases to PyPI and TestPyPI.

## TestPyPI Release

TestPyPI releases are used for testing the package distribution before publishing to the main PyPI repository.

### Method 1: Manual Workflow Trigger (Recommended)

The TestPyPI workflow can be triggered manually from the GitHub Actions tab:

1. Go to the [Actions tab](https://github.com/osoleve/glitchlings/actions/workflows/publish-testpypi.yml)
2. Click on "Build & Publish (TestPyPI)" workflow
3. Click "Run workflow" button
4. Select the branch to build from (usually `trunk`)
5. Click "Run workflow"

This will build and publish the current version specified in `pyproject.toml` to TestPyPI.

### Method 2: Using the Retry Script

For retrying a specific version release, use the `retry_testpypi_release.sh` script:

```bash
# From the repository root
./scripts/retry_testpypi_release.sh v0.2.1
```

This script will:
1. Sync the `dev` branch with `trunk`
2. Push the updated `dev` branch (triggers the TestPyPI workflow)
3. Create/recreate the specified tag on `trunk`
4. Push the tag to GitHub

### Method 3: Manual Branch Push

You can also trigger the TestPyPI workflow by pushing to the `dev` branch:

```bash
git fetch origin
git checkout trunk
git pull --ff-only origin trunk

# Fast-forward dev to trunk
git checkout dev
git merge --ff-only trunk
git push origin dev
```

This will trigger the workflow automatically.

## PyPI Release

PyPI releases are production releases triggered by pushing version tags:

```bash
# Tag the release on trunk
git checkout trunk
git tag v0.2.1
git push origin v0.2.1
```

The tag must match the pattern `v*.*.*` (e.g., `v0.2.1`, `v1.0.0`) to trigger the PyPI publish workflow.

## Version Management

The package version is defined in `pyproject.toml`:

```toml
[project]
version = "0.2.1"
```

Always ensure the version in `pyproject.toml` matches your intended release version before triggering a publish workflow.

## Troubleshooting

### Build Failures

If the TestPyPI or PyPI workflow fails:

1. Check the [Actions tab](https://github.com/osoleve/glitchlings/actions) for detailed logs
2. Common issues:
   - Rust compilation errors: Ensure Rust toolchain is properly configured
   - Test failures: Run tests locally first with `pytest`
   - Version conflicts: TestPyPI allows skipping existing versions with `skip-existing: true`

### Testing Before Release

Before publishing to PyPI:

1. Test the build locally:
   ```bash
   python -m build
   ```

2. Test installation from TestPyPI:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ glitchlings
   ```

3. Verify the installed package works as expected
