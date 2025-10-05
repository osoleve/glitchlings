#!/usr/bin/env bash
# Synchronise the dev branch with trunk and recreate a release tag to retry the TestPyPI publish workflow.
#
# Usage:
#   scripts/retry_testpypi_release.sh <tag>
#
# The script assumes that:
#   * `trunk` is the canonical branch.
#   * `dev` is the branch that triggers the TestPyPI workflow.
#   * `origin` is the remote to update.
#
# Override the defaults by exporting REMOTE, TRUNK_BRANCH, or DEV_BRANCH.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <tag>" >&2
    exit 1
fi

tag="$1"
remote="${REMOTE:-origin}"
trunk_branch="${TRUNK_BRANCH:-trunk}"
dev_branch="${DEV_BRANCH:-dev}"

# Ensure we have the latest refs from the remote.
git fetch "${remote}" --prune

# Make sure the local trunk matches the remote state.
if git rev-parse --verify --quiet "refs/heads/${trunk_branch}" > /dev/null; then
    git checkout "${trunk_branch}"
else
    git checkout -b "${trunk_branch}" "${remote}/${trunk_branch}"
fi
git pull --ff-only "${remote}" "${trunk_branch}"

# Fast-forward dev to the refreshed trunk.
if git rev-parse --verify --quiet "refs/heads/${dev_branch}" > /dev/null; then
    git checkout "${dev_branch}"
else
    git checkout -b "${dev_branch}" "${remote}/${dev_branch}" 2>/dev/null || \
        git checkout -b "${dev_branch}" "${trunk_branch}"
fi
git merge --ff-only "${trunk_branch}"

git push "${remote}" "${dev_branch}"

# Delete the tag locally if it already exists.
if git rev-parse --verify --quiet "refs/tags/${tag}" > /dev/null; then
    git tag -d "${tag}"
fi

# Remove the tag from the remote. Ignore errors if the tag does not exist remotely.
git push "${remote}" ":refs/tags/${tag}" || true

# Recreate the tag from the trunk branch.
git checkout "${trunk_branch}"
git tag "${tag}"

git push "${remote}" "${tag}"
