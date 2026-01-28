#!/bin/bash

################################################################################
# TSC Tuber Segmentation Pipeline - MNI Registration Step
# 
# Description:
#   Performs bias-field correction, resampling to 1mm isotropic, and
#   registration to MNI152 2009c template space using ANTs.
#
# Docker Image: ivansanchezfernandez/bias_correct_resample_and_register_to_MNI_with_ants
# Citation: Avants et al., A reproducible evaluation of ANTs similarity metric
#           performance in brain image registration. Neuroimage 2011. PMID: 20851191
#
# Input:  preprocessing/combined_MRIs/{subject}/*.nii
# Output: preprocessing/preprocessed_MRIs/{subject}/*.nii
#
# Author: Tuber Pipeline Development Team
# Date: 2026-01-27
################################################################################

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

INPUT_DIR="${PROJECT_ROOT}/preprocessing/combined_MRIs"
OUTPUT_DIR="${PROJECT_ROOT}/preprocessing/preprocessed_MRIs"
LOG_DIR="${PROJECT_ROOT}/logs"

DOCKER_IMAGE="ivansanchezfernandez/bias_correct_resample_and_register_to_mni_with_ants"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/3_register_to_mni_${TIMESTAMP}.log"

# ============================================================================
# Utility Functions
# ============================================================================

log() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $*"
    exit 1
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed or not in PATH"
    fi
    
    if ! docker ps &> /dev/null; then
        error_exit "Docker daemon is not running or permission denied"
    fi
}

pull_docker_image() {
    local image="$1"
    log "Checking Docker image: ${image}"
    
    if docker image inspect "$image" &> /dev/null; then
        log "  ✓ Image already available locally"
    else
        log "  Pulling Docker image (this may take a few minutes)..."
        if ! docker pull "$image"; then
            error_exit "Failed to pull Docker image: ${image}"
        fi
        log "  ✓ Image pulled successfully"
    fi
}

run_registration_for_subject() {
    local subject="$1"
    local subject_input="${INPUT_DIR}/${subject}"
    local subject_output="${OUTPUT_DIR}/${subject}"
    
    mkdir -p "$subject_output"
    
    # Count input files
    local input_count=$(find "$subject_input" -type f \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null | wc -l)
    log "  Input files: ${input_count}"
    
    if [[ $input_count -eq 0 ]]; then
        log "  ⚠ WARNING: No input files found, skipping"
        return 1
    fi
    
    log "  Running ANTs registration container (this may take 10-30 minutes)..."
    local start_time=$(date +%s)
    
    if ! docker run --rm \
        -v "${subject_input}:/input:ro" \
        -v "${subject_output}:/output" \
        "$DOCKER_IMAGE" >> "$LOG_FILE" 2>&1; then
        log "  ✗ Container execution failed"
        return 1
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    # Validate outputs
    local output_count=$(find "$subject_output" -type f \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null | wc -l)
    
    log "  ✓ Completed in ${minutes}m ${seconds}s"
    log "  Output files: ${output_count}"
    
    if [[ $output_count -eq 0 ]]; then
        log "  ⚠ WARNING: No output files generated"
        return 1
    fi
    
    return 0
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log "=========================================="
    log "Step 3: Registration to MNI with ANTs"
    log "=========================================="
    log "Project root: ${PROJECT_ROOT}"
    log "Input directory: ${INPUT_DIR}"
    log "Output directory: ${OUTPUT_DIR}"
    log ""
    
    # Pre-flight checks
    check_docker
    
    # Validate input directory
    if [[ ! -d "$INPUT_DIR" ]]; then
        error_exit "Input directory not found: ${INPUT_DIR}"
    fi
    
    # Pull Docker image
    pull_docker_image "$DOCKER_IMAGE"
    log ""
    
    # Discover subjects
    log "Discovering subjects..."
    subjects=()
    while IFS= read -r -d '' subject_dir; do
        subject=$(basename "$subject_dir")
        subjects+=("$subject")
        log "  Found: ${subject}"
    done < <(find "$INPUT_DIR" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
    
    if [[ ${#subjects[@]} -eq 0 ]]; then
        error_exit "No subjects found in ${INPUT_DIR}"
    fi
    
    log ""
    log "Total subjects: ${#subjects[@]}"
    log ""
    log "⚠ NOTE: This step is computationally intensive."
    log "   Expected time per subject: 10-30 minutes"
    log "   Total estimated time: $(( ${#subjects[@]} * 15 )) - $(( ${#subjects[@]} * 30 )) minutes"
    log ""
    
    # Process each subject
    local total=${#subjects[@]}
    local current=0
    local success=0
    local failed=0
    local failed_list=()
    local total_time=0
    
    for subject in "${subjects[@]}"; do
        ((current++))
        log "=========================================="
        log "Processing subject ${current}/${total}: ${subject}"
        log "=========================================="
        
        local subject_start=$(date +%s)
        
        if run_registration_for_subject "$subject"; then
            ((success++))
            local subject_end=$(date +%s)
            local subject_duration=$((subject_end - subject_start))
            total_time=$((total_time + subject_duration))
            log "  ✓ ${subject} completed successfully"
        else
            ((failed++))
            failed_list+=("$subject")
            log "  ✗ ${subject} failed"
        fi
        log ""
    done
    
    # Calculate average time
    local avg_time=0
    if [[ $success -gt 0 ]]; then
        avg_time=$((total_time / success))
    fi
    local avg_minutes=$((avg_time / 60))
    local avg_seconds=$((avg_time % 60))
    
    # Summary
    log "=========================================="
    log "MNI Registration Complete"
    log "=========================================="
    log "Total subjects: ${total}"
    log "Successful: ${success}"
    log "Failed: ${failed}"
    log "Average time per subject: ${avg_minutes}m ${avg_seconds}s"
    
    if [[ ${#failed_list[@]} -gt 0 ]]; then
        log ""
        log "Failed subjects:"
        for subj in "${failed_list[@]}"; do
            log "  - ${subj}"
        done
    fi
    
    log ""
    log "Output directory: ${OUTPUT_DIR}"
    log "Log file: ${LOG_FILE}"
    log "=========================================="
    
    if [[ $failed -gt 0 ]]; then
        exit 1
    fi
}

main "$@"

