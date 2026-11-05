#!/usr/bin/env bash
# Copy the lab files participants need into a shared workspace folder.
#   scripts/publish_to_workspace.sh <profile> [target_folder]
set -euo pipefail
PROFILE=${1:?usage: publish_to_workspace.sh <profile> [target_folder]}
TARGET=${2:-/Workspace/Shared/swa-ops-lakeflow-lab}
cd "$(dirname "$0")/.."

find labs src app -name __pycache__ -type d -prune -exec rm -rf {} +
databricks workspace mkdirs "$TARGET" -p "$PROFILE"
for d in labs src app; do
  databricks workspace import-dir "$d" "$TARGET/$d" --overwrite -p "$PROFILE"
done
for f in README.md AGENTS.md; do
  databricks workspace import "$TARGET/$f" --file "$f" --format AUTO --overwrite -p "$PROFILE"
done
echo "Published to $TARGET"
