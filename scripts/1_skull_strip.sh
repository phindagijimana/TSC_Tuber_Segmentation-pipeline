#!/bin/bash

################################################################################
# TSC Tuber Segmentation Pipeline - Skull Stripping Step
# 
# Description:
#   Removes non-brain tissue (skull, CSF, etc.) using SynthStrip and generates
#   brain masks. Processes each subject independently in a loop.
#
# Docker Image: ivansanchezfernandez/skull_strip_and_create_masks_with_synthstrip
# Citation: Hoopes et al., SynthStrip: Skull-Stripping for Any Brain Image.
#           Neuroimage 2022. PMID: 35842095
#
# Input:  preprocessing/MRI_files/{subject}/*.nii
# Output: preprocessing/skull_stripped_MRIs/{subject}/*.nii
#         preprocessing/masks/{subject}/*.nii
#
# Author: Tuber Pipeline Development Team
# Date: 2026-01-27
################################################################################

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

INPUT_DIR="${PROJECT_ROOT}/preprocessing/MRI_files"
OUTPUT_DIR="${PROJECT_ROOT}/preprocessing/skull_stripped_MRIs"
MASK_DIR="${PROJECT_ROOT}/preprocessing/masks"
LOG_DIR="${PROJECT_ROOT}/logs"

DOCKER_IMAGE="ivansanchezfernandez/skull_strip_and_create_masks_with_synthstrip"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/1_skull_strip_${TIMESTAMP}.log"

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

run_skull_strip_for_subject() {
    local subject="$1"
    local subject_input="${INPUT_DIR}/${subject}"
    local subject_output="${OUTPUT_DIR}/${subject}"
    local subject_masks="${MASK_DIR}/${subject}"
    
    # Create output directories
    mkdir -p "$subject_output" "$subject_masks"
    
    # Count input files
    local input_count=$(find "$subject_input" -type f \( -name "*.nii" -o -name "*.nii.gz" \) | wc -l)
    log "  Input files: ${input_count}"
    
    if [[ $input_count -eq 0 ]]; then
        log "  ⚠ WARNING: No input files found, skipping"
        return 1
    fi
    
    # Run Docker container
    log "  Running SynthStrip container..."
    local start_time=$(date +%s)
    
    if ! docker run --rm \
        -v "${subject_input}:/input:ro" \
        -v "${subject_output}:/output" \
        -v "${subject_masks}:/masks" \
        "$DOCKER_IMAGE" >> "$LOG_FILE" 2>&1; then
        log "  ✗ Container execution failed"
        return 1
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Validate outputs
    local output_count=$(find "$subject_output" -type f \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null | wc -l)
    local mask_count=$(find "$subject_masks" -type f \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null | wc -l)
    
    log "  ✓ Completed in ${duration}s"
    log "  Output files: ${output_count} skull-stripped, ${mask_count} masks"
    
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
    log "Step 1: Skull Stripping with SynthStrip"
    log "=========================================="
    log "Project root: ${PROJECT_ROOT}"
    log "Input directory: ${INPUT_DIR}"
    log "Output directory: ${OUTPUT_DIR}"
    log "Mask directory: ${MASK_DIR}"
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
    
    # Process each subject
    local total=${#subjects[@]}
    local current=0
    local success=0
    local failed=0
    local failed_list=()
    
    for subject in "${subjects[@]}"; do
        ((current++))
        log "=========================================="
        log "Processing subject ${current}/${total}: ${subject}"
        log "=========================================="
        
        if run_skull_strip_for_subject "$subject"; then
            ((success++))
            log "  ✓ ${subject} completed successfully"
        else
            ((failed++))
            failed_list+=("$subject")
            log "  ✗ ${subject} failed"
        fi
        log ""
    done
    
    # Summary
    log "=========================================="
    log "Skull Stripping Complete"
    log "=========================================="
    log "Total subjects: ${total}"
    log "Successful: ${success}"
    log "Failed: ${failed}"
    
    if [[ ${#failed_list[@]} -gt 0 ]]; then
        log ""
        log "Failed subjects:"
        for subj in "${failed_list[@]}"; do
            log "  - ${subj}"
        done
    fi
    
    log ""
    log "Output directory: ${OUTPUT_DIR}"
    log "Mask directory: ${MASK_DIR}"
    log "Log file: ${LOG_FILE}"
    log "=========================================="
    
    # Exit with error if any subjects failed
    if [[ $failed -gt 0 ]]; then
        exit 1
    fi
}

main "$@"



