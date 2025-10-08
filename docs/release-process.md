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

## Build Process

Both the TestPyPI and PyPI workflows build wheels for multiple platforms to ensure compatibility across different operating systems and Python versions:

### Platforms

- **Windows**: Builds wheels for Windows (AMD64)
- **Linux**: Builds manylinux wheels for x86_64 architecture

### Python Versions

The workflows build wheels for Python 3.10, 3.11, and 3.12 using [cibuildwheel](https://cibuildwheel.readthedocs.io/).

### Wheel Types

- **Platform wheels**: Binary wheels optimized for each platform (e.g., `glitchlings-0.2.3-cp312-cp312-win_amd64.whl`, `glitchlings-0.2.3-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`)
- **Source distribution**: Built on Linux only (e.g., `glitchlings-0.2.3.tar.gz`)

The Linux builds use manylinux containers to ensure compatibility with a wide range of Linux distributions. The Rust extensions are compiled during the wheel build process using `setuptools-rust`.

### Artifact Collection

The workflows use a matrix strategy to build on multiple platforms in parallel. Each platform uploads its artifacts separately, and the publish job collects all artifacts before uploading to PyPI:

1. **Build job**: Runs in parallel for Windows and Linux, produces wheels
2. **Publish job**: Downloads all artifacts, merges them into a single `dist/` directory, and publishes to PyPI/TestPyPI

## Troubleshooting

### Build Failures

If the TestPyPI or PyPI workflow fails:

1. Check the [Actions tab](https://github.com/osoleve/glitchlings/actions) for detailed logs
2. Common issues:
   - **Rust compilation errors**: Ensure Rust toolchain is properly configured in the workflow. Check that `setuptools-rust` is installed in the cibuildwheel environment.
   - **Platform-specific build failures**: Check the matrix job logs for the specific platform. Windows and Linux builds run independently, so a failure on one platform doesn't affect the other.
   - **Artifact collection issues**: Verify that both build jobs completed successfully before the publish job runs. The publish job expects artifacts from all platforms.
   - **cibuildwheel configuration**: If wheel builds fail, check the `CIBW_*` environment variables in the workflow files. Ensure Python versions and architectures are correctly specified.
   - **Test failures**: Run tests locally first with `pytest`
   - **Version conflicts**: TestPyPI allows skipping existing versions with `skip-existing: true`

### Testing Before Release

Before publishing to PyPI:

1. Test the workflow configuration:
   ```bash
   pytest tests/test_workflows.py
   ```

2. Test the build locally (note: this builds for your current platform only):
   ```bash
   # Install build tools
   pip install cibuildwheel
   
   # Build wheels for your platform
   python -m cibuildwheel --output-dir dist
   ```

3. Test installation from TestPyPI:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ glitchlings
   ```

4. Verify the installed package works as expected:
   ```bash
   python -m glitchlings --help
   python -m glitchlings --list
   ```

5. Test platform-specific wheels:
   - Check that manylinux wheels are generated on Linux
   - Check that Windows wheels are generated on Windows
   - Verify wheels for all supported Python versions (3.10, 3.11, 3.12) are present
