#!/bin/bash

################################################################################
# TSC Tuber Segmentation Pipeline - Installation Validator
# 
# Description:
#   Validates that the pipeline is correctly installed and ready to run.
#   Checks Docker, input data, and script permissions.
#
# Usage:
#   ./validate_installation.sh
#
# Author: Tuber Pipeline Development Team
# Date: 2026-01-27
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASS=0
FAIL=0
WARN=0

# ============================================================================
# Utility Functions
# ============================================================================

print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARN++))
}

# ============================================================================
# Validation Checks
# ============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

print_header "TSC Pipeline Installation Validator"
echo "Project root: ${PROJECT_ROOT}"

# Check 1: Directory Structure
print_header "1. Directory Structure"

dirs=(
    "TSC_MRI_SUB"
    "scripts"
    "preprocessing"
    "logs"
    "results"
)

for dir in "${dirs[@]}"; do
    if [[ -d "${PROJECT_ROOT}/${dir}" ]]; then
        check_pass "Directory exists: ${dir}/"
    else
        check_fail "Directory missing: ${dir}/"
    fi
done

# Check 2: Pipeline Scripts
print_header "2. Pipeline Scripts"

scripts=(
    "scripts/run_pipeline.sh"
    "scripts/submit_gpu_job.sh"
    "scripts/0_prepare_data.sh"
    "scripts/1_skull_strip.sh"
    "scripts/2_combine_t2.sh"
    "scripts/3_register_to_mni.sh"
    "scripts/4_segment_tubers.sh"
)

for script in "${scripts[@]}"; do
    script_path="${PROJECT_ROOT}/${script}"
    if [[ -f "$script_path" ]]; then
        if [[ -x "$script_path" ]]; then
            check_pass "Script executable: ${script}"
        else
            check_warn "Script not executable: ${script} (run: chmod +x ${script_path})"
        fi
    else
        check_fail "Script missing: ${script}"
    fi
done

# Check 3: Docker
print_header "3. Docker Environment"

if command -v docker &> /dev/null; then
    check_pass "Docker command available"
    
    if docker ps &> /dev/null; then
        check_pass "Docker daemon running"
        
        # Check Docker version
        docker_version=$(docker --version | grep -oP '\d+\.\d+' | head -1)
        check_pass "Docker version: ${docker_version}"
    else
        check_fail "Docker daemon not running or permission denied"
        echo "  Try: sudo systemctl start docker"
        echo "  Or add user to docker group: sudo usermod -aG docker \$USER"
    fi
else
    check_fail "Docker not installed"
    echo "  Install Docker: https://docs.docker.com/get-docker/"
fi

# Check 4: SLURM (optional)
print_header "4. SLURM Environment (Optional)"

if command -v sbatch &> /dev/null; then
    check_pass "SLURM available (sbatch found)"
    
    if command -v squeue &> /dev/null; then
        check_pass "SLURM monitoring available (squeue found)"
    fi
    
    # Check for GPU partitions
    if sinfo -o "%P %G" 2>/dev/null | grep -q "gpu:"; then
        check_pass "GPU partitions detected"
        gpu_info=$(sinfo -o "%P %G" | grep "gpu:" | head -3)
        echo "  Available GPU resources:"
        echo "$gpu_info" | sed 's/^/    /'
    else
        check_warn "No GPU partitions found (CPU-only mode available)"
    fi
else
    check_warn "SLURM not available (use run_pipeline.sh for local execution)"
fi

# Check 5: GPU Support (optional)
print_header "5. GPU Support (Optional)"

if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi &> /dev/null; then
        check_pass "NVIDIA GPU detected"
        gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
        gpu_mem=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -1)
        echo "  GPU: ${gpu_name}"
        echo "  Memory: ${gpu_mem}"
    else
        check_warn "nvidia-smi command failed (GPU may not be accessible)"
    fi
else
    check_warn "nvidia-smi not found (CPU-only mode will be used)"
fi

# Check 6: Input Data
print_header "6. Input Data"

if [[ -d "${PROJECT_ROOT}/TSC_MRI_SUB" ]]; then
    subject_count=$(find "${PROJECT_ROOT}/TSC_MRI_SUB" -mindepth 1 -maxdepth 1 -type d | wc -l)
    
    if [[ $subject_count -gt 0 ]]; then
        check_pass "Found ${subject_count} subject(s)"
        
        # Check a few subjects for proper file naming
        subjects=$(find "${PROJECT_ROOT}/TSC_MRI_SUB" -mindepth 1 -maxdepth 1 -type d | head -3)
        
        for subject_dir in $subjects; do
            subject=$(basename "$subject_dir")
            
            # Count sequences
            t1_count=$(find "$subject_dir" -name "*_T1_*" \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null | wc -l)
            t2_count=$(find "$subject_dir" -name "*_T2_*" \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null | wc -l)
            flair_count=$(find "$subject_dir" -name "*_FLAIR_*" \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null | wc -l)
            
            if [[ $t1_count -gt 0 ]] && [[ $t2_count -gt 0 ]] && [[ $flair_count -gt 0 ]]; then
                check_pass "  ${subject}: T1=${t1_count}, T2=${t2_count}, FLAIR=${flair_count}"
            else
                check_warn "  ${subject}: Missing sequences (T1=${t1_count}, T2=${t2_count}, FLAIR=${flair_count})"
            fi
        done
    else
        check_warn "No subjects found in TSC_MRI_SUB/"
        echo "  Add your subject data to: ${PROJECT_ROOT}/TSC_MRI_SUB/"
    fi
else
    check_fail "TSC_MRI_SUB directory not found"
fi

# Check 7: Disk Space
print_header "7. Disk Space"

available_space=$(df -BG "${PROJECT_ROOT}" | tail -1 | awk '{print $4}' | sed 's/G//')
if [[ $available_space -gt 100 ]]; then
    check_pass "Sufficient disk space: ${available_space}GB available"
elif [[ $available_space -gt 50 ]]; then
    check_warn "Limited disk space: ${available_space}GB available (recommend 100GB+)"
else
    check_fail "Insufficient disk space: ${available_space}GB available (need 100GB+)"
fi

# Check 8: Documentation
print_header "8. Documentation"

docs=(
    "README.md"
    "implementation.md"
    "scripts/README.md"
)

for doc in "${docs[@]}"; do
    if [[ -f "${PROJECT_ROOT}/${doc}" ]]; then
        check_pass "Documentation: ${doc}"
    else
        check_warn "Documentation missing: ${doc}"
    fi
done

# ============================================================================
# Summary
# ============================================================================

print_header "Validation Summary"

echo -e "${GREEN}Passed: ${PASS}${NC}"
echo -e "${YELLOW}Warnings: ${WARN}${NC}"
echo -e "${RED}Failed: ${FAIL}${NC}"
echo ""

if [[ $FAIL -eq 0 ]]; then
    echo -e "${GREEN}✓ Pipeline is ready to run!${NC}"
    echo ""
    echo "Quick start:"
    echo "  CPU mode:  ./scripts/run_pipeline.sh"
    echo "  GPU mode:  ./scripts/submit_gpu_job.sh"
    echo ""
    echo "For help:    ./scripts/run_pipeline.sh --help"
    exit 0
else
    echo -e "${RED}✗ Pipeline has critical issues. Please fix failures above.${NC}"
    exit 1
fi



