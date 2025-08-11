#!/bin/bash
# Script to install all requirements files for the project
# Usage: bash install_all_requirements.sh

set -e

REQ_FILES=(
  "requirements.txt"
  "jobs-requirements.txt"
  "certificate_requirements.txt"
)

for req in "${REQ_FILES[@]}"; do
  if [ -f "$req" ]; then
    echo "Installing requirements from $req..."
    pip install -r "$req"
  else
    echo "Warning: $req not found, skipping."
  fi
done

echo "All requirements installed."
