#!/bin/bash
set -euo pipefail

# Delete the release and its tag to allow clean rebuild
RELEASE_TAG="pkg-2026.08.09-m15t07"

echo "Deleting release $RELEASE_TAG..."
gh release delete "$RELEASE_TAG" --cleanup-tag --yes

echo "Release $RELEASE_TAG deleted successfully"
