#!/bin/bash

################################################################################
# Setup Script - Create Pipeline Directory Structure
# 
# Description:
#   Creates all required directories for the TSC Tuber Segmentation Pipeline
#
# Usage:
#   ./scripts/setup_directories.sh
#
# Author: Tuber Pipeline Development Team
# Date: 2026-01-27
################################################################################

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "TSC Tuber Segmentation Pipeline Setup"
echo "=========================================="
echo ""

# Get project root (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo ""

# Create directories
echo "Creating directory structure..."
echo ""

dirs=(
    "preprocessing/raw_data"
    "preprocessing/skull_stripped_MRIs"
    "preprocessing/masks"
    "preprocessing/combined_MRIs"
    "preprocessing/preprocessed_MRIs"
    "results"
    "logs"
)

for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ${BLUE}EXISTS${NC}  $dir"
    else
        mkdir -p "$dir"
        echo -e "  ${GREEN}CREATED${NC} $dir"
    fi
done

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Place your NIfTI files in: preprocessing/raw_data/"
echo "     - Create one folder per subject (e.g., Case001, Case002)"
echo "     - Files should be named: SubjectID_T1_*.nii, SubjectID_T2_*.nii, etc."
echo ""
echo "  2. Run the pipeline:"
echo "     HPC with GPU:  ./scripts/submit_gpu_job.sh"
echo "     Local (CPU):   python3 scripts/run_pipeline.py"
echo ""
echo "  3. Check outputs in: results/"
echo ""
echo "For detailed instructions, see: SETUP.md"
echo "=========================================="

