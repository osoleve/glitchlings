"""Tests for GitHub Actions workflow configurations."""

import pathlib
import yaml
import pytest


@pytest.fixture
def workflows_dir():
    """Return path to GitHub workflows directory."""
    repo_root = pathlib.Path(__file__).parent.parent
    return repo_root / ".github" / "workflows"


@pytest.fixture
def publish_testpypi_workflow(workflows_dir):
    """Load the publish-testpypi workflow."""
    workflow_path = workflows_dir / "publish-testpypi.yml"
    with open(workflow_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def publish_workflow(workflows_dir):
    """Load the publish workflow."""
    workflow_path = workflows_dir / "publish.yml"
    with open(workflow_path) as f:
        return yaml.safe_load(f)


def test_publish_testpypi_workflow_valid_yaml(workflows_dir):
    """Verify publish-testpypi.yml is valid YAML."""
    workflow_path = workflows_dir / "publish-testpypi.yml"
    assert workflow_path.exists(), "publish-testpypi.yml not found"
    with open(workflow_path) as f:
        yaml.safe_load(f)  # Should not raise


def test_publish_workflow_valid_yaml(workflows_dir):
    """Verify publish.yml is valid YAML."""
    workflow_path = workflows_dir / "publish.yml"
    assert workflow_path.exists(), "publish.yml not found"
    with open(workflow_path) as f:
        yaml.safe_load(f)  # Should not raise


def test_publish_testpypi_has_multiplatform_build(publish_testpypi_workflow):
    """Verify TestPyPI workflow builds for multiple platforms."""
    build_job = publish_testpypi_workflow["jobs"]["build"]
    
    # Should have a matrix strategy
    assert "strategy" in build_job
    assert "matrix" in build_job["strategy"]
    
    # Should include both Windows and Linux
    matrix_include = build_job["strategy"]["matrix"]["include"]
    platforms = [item["platform"] for item in matrix_include]
    
    assert "windows" in platforms, "Windows build not found in matrix"
    assert "linux" in platforms, "Linux build not found in matrix"


def test_publish_has_multiplatform_build(publish_workflow):
    """Verify PyPI workflow builds for multiple platforms."""
    build_job = publish_workflow["jobs"]["build"]
    
    # Should have a matrix strategy
    assert "strategy" in build_job
    assert "matrix" in build_job["strategy"]
    
    # Should include both Windows and Linux
    matrix_include = build_job["strategy"]["matrix"]["include"]
    platforms = [item["platform"] for item in matrix_include]
    
    assert "windows" in platforms, "Windows build not found in matrix"
    assert "linux" in platforms, "Linux build not found in matrix"


def test_workflows_use_cibuildwheel(publish_testpypi_workflow, publish_workflow):
    """Verify workflows use cibuildwheel for building wheels."""
    for workflow_name, workflow in [
        ("publish-testpypi", publish_testpypi_workflow),
        ("publish", publish_workflow),
    ]:
        build_job = workflow["jobs"]["build"]
        
        # Find the build wheels step
        build_step = None
        for step in build_job["steps"]:
            if step.get("name") == "Build wheels":
                build_step = step
                break
        
        assert build_step is not None, f"{workflow_name}: Build wheels step not found"
        assert "cibuildwheel" in step["run"], f"{workflow_name}: Not using cibuildwheel"
        
        # Should have environment variables for cibuildwheel
        assert "env" in build_step, f"{workflow_name}: No env vars for cibuildwheel"
        env = build_step["env"]
        
        # Check key configuration
        assert "CIBW_BUILD" in env, f"{workflow_name}: CIBW_BUILD not set"
        assert "cp310-*" in env["CIBW_BUILD"], f"{workflow_name}: Python 3.10 not in build"
        assert "cp311-*" in env["CIBW_BUILD"], f"{workflow_name}: Python 3.11 not in build"
        assert "cp312-*" in env["CIBW_BUILD"], f"{workflow_name}: Python 3.12 not in build"


def test_workflows_build_source_distribution_on_linux(
    publish_testpypi_workflow, publish_workflow
):
    """Verify workflows build source distribution only on Linux."""
    for workflow_name, workflow in [
        ("publish-testpypi", publish_testpypi_workflow),
        ("publish", publish_workflow),
    ]:
        build_job = workflow["jobs"]["build"]
        
        # Find the build source distribution step
        sdist_step = None
        for step in build_job["steps"]:
            if step.get("name") == "Build source distribution":
                sdist_step = step
                break
        
        assert sdist_step is not None, f"{workflow_name}: sdist step not found"
        assert "if" in sdist_step, f"{workflow_name}: sdist step should be conditional"
        assert "linux" in sdist_step["if"], f"{workflow_name}: sdist should only run on linux"


def test_workflows_collect_all_artifacts(publish_testpypi_workflow, publish_workflow):
    """Verify workflows collect artifacts from all platforms."""
    for workflow_name, workflow in [
        ("publish-testpypi", publish_testpypi_workflow),
        ("publish", publish_workflow),
    ]:
        publish_job = workflow["jobs"]["publish"]
        
        # Should download all artifacts
        download_step = None
        for step in publish_job["steps"]:
            if step.get("name") == "Download all artifacts":
                download_step = step
                break
        
        assert download_step is not None, f"{workflow_name}: Download step not found"
        
        # Should prepare dist directory with all wheels
        prepare_step = None
        for step in publish_job["steps"]:
            if step.get("name") == "Prepare dist directory":
                prepare_step = step
                break
        
        assert prepare_step is not None, f"{workflow_name}: Prepare dist step not found"
        assert "find artifacts" in prepare_step["run"], (
            f"{workflow_name}: Should find artifacts from all platforms"
        )
