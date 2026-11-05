#!/usr/bin/env bash
# Copy the lab files participants need into a shared workspace folder.
#   scripts/publish_to_workspace.sh <profile> [target_folder]
set -euo pipefail
PROFILE=${1:?usage: publish_to_workspace.sh <profile> [target_folder]}
TARGET=${2:-/Workspace/Shared/swa-ops-lakeflow-lab}
cd "$(dirname "$0")/.."

databricks workspace mkdirs "$TARGET" -p "$PROFILE"
for d in labs src app; do
  databricks workspace import-dir "$d" "$TARGET/$d" --overwrite -p "$PROFILE"
done
databricks workspace import "$TARGET/README.md" --file README.md --format AUTO --overwrite -p "$PROFILE"
echo "Published to $TARGET"
