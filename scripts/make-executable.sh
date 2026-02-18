#!/bin/bash

# Make all shell scripts executable

chmod +x scripts/setup-aks.sh
chmod +x scripts/deploy.sh
chmod +x scripts/cleanup.sh
chmod +x scripts/test-inference.sh

echo "✓ All scripts made executable"
ls -la scripts/*.sh
