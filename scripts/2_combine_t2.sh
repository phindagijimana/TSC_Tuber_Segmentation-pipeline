#!/bin/bash

################################################################################
# TSC Tuber Segmentation Pipeline - T2 Combination Step
# 
# Description:
#   Combines axial and coronal T2 sequences for improved 3D resolution using
#   NiftyMIC. Only processes subjects with both T2 sequences; copies others.
#
# Docker Image: ivansanchezfernandez/combine_t2_files_with_niftymic
# Citation: Ebner et al., An automated framework for localization, segmentation
#           and super-resolution reconstruction of fetal brain MRI.
#           Neuroimage 2020. PMID: 31704293
#
# Input:  preprocessing/skull_stripped_MRIs/{subject}/*.nii
#         preprocessing/masks/{subject}/*.nii
# Output: preprocessing/combined_MRIs/{subject}/*.nii
#
# Author: Tuber Pipeline Development Team
# Date: 2026-01-27
################################################################################

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

INPUT_DIR="${PROJECT_ROOT}/preprocessing/skull_stripped_MRIs"
MASK_DIR="${PROJECT_ROOT}/preprocessing/masks"
OUTPUT_DIR="${PROJECT_ROOT}/preprocessing/combined_MRIs"
LOG_DIR="${PROJECT_ROOT}/logs"

DOCKER_IMAGE="ivansanchezfernandez/combine_t2_files_with_niftymic"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/2_combine_t2_${TIMESTAMP}.log"

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
        log "  Pulling Docker image (this may take several minutes, ~several GB)..."
        if ! docker pull "$image"; then
            error_exit "Failed to pull Docker image: ${image}"
        fi
        log "  ✓ Image pulled successfully"
    fi
}

# Check if subject needs T2 combination
needs_t2_combination() {
    local subject_dir="$1"
    local t2_count=0
    
    # Count T2 files (look for both axial and coronal patterns)
    while IFS= read -r file; do
        [[ -z "$file" ]] && continue
        if [[ "$file" =~ _T2_ ]]; then
            ((t2_count++))
        fi
    done < <(find "$subject_dir" -type f \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null)
    
    # Need combination if more than one T2
    [[ $t2_count -gt 1 ]]
}

# Copy files directly without T2 combination
copy_subject_files() {
    local subject="$1"
    local subject_input="${INPUT_DIR}/${subject}"
    local subject_output="${OUTPUT_DIR}/${subject}"
    
    mkdir -p "$subject_output"
    
    # Copy all files
    cp -r "${subject_input}"/* "${subject_output}/" 2>/dev/null || true
    
    local count=$(find "$subject_output" -type f \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null | wc -l)
    return $([ $count -gt 0 ] && echo 0 || echo 1)
}

# Run T2 combination for subject
run_t2_combination_for_subject() {
    local subject="$1"
    local subject_input="${INPUT_DIR}/${subject}"
    local subject_masks="${MASK_DIR}/${subject}"
    local subject_output="${OUTPUT_DIR}/${subject}"
    
    mkdir -p "$subject_output"
    
    log "  Running NiftyMIC container (this may take 10-30 minutes)..."
    local start_time=$(date +%s)
    
    if ! docker run --rm \
        -v "${subject_input}:/input:ro" \
        -v "${subject_masks}:/masks:ro" \
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
    log "Step 2: T2 Combination with NiftyMIC"
    log "=========================================="
    log "Project root: ${PROJECT_ROOT}"
    log "Input directory: ${INPUT_DIR}"
    log "Mask directory: ${MASK_DIR}"
    log "Output directory: ${OUTPUT_DIR}"
    log ""
    
    # Pre-flight checks
    check_docker
    
    # Validate input directories
    if [[ ! -d "$INPUT_DIR" ]]; then
        error_exit "Input directory not found: ${INPUT_DIR}"
    fi
    if [[ ! -d "$MASK_DIR" ]]; then
        error_exit "Mask directory not found: ${MASK_DIR}"
    fi
    
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
    
    # Analyze which subjects need T2 combination
    log "Analyzing T2 sequences..."
    subjects_needing_combination=()
    subjects_for_copy=()
    
    for subject in "${subjects[@]}"; do
        if needs_t2_combination "${INPUT_DIR}/${subject}"; then
            subjects_needing_combination+=("$subject")
            log "  ${subject}: Multiple T2 sequences → will combine"
        else
            subjects_for_copy+=("$subject")
            log "  ${subject}: Single T2 sequence → will copy"
        fi
    done
    
    log ""
    log "Subjects needing combination: ${#subjects_needing_combination[@]}"
    log "Subjects for direct copy: ${#subjects_for_copy[@]}"
    log ""
    
    # Pull Docker image only if needed
    if [[ ${#subjects_needing_combination[@]} -gt 0 ]]; then
        pull_docker_image "$DOCKER_IMAGE"
        log ""
    fi
    
    # Process subjects
    local total=${#subjects[@]}
    local current=0
    local success=0
    local failed=0
    local failed_list=()
    
    # Copy subjects that don't need combination
    for subject in "${subjects_for_copy[@]}"; do
        ((current++))
        log "=========================================="
        log "Processing subject ${current}/${total}: ${subject} (copy)"
        log "=========================================="
        
        if copy_subject_files "$subject"; then
            ((success++))
            log "  ✓ Files copied successfully"
        else
            ((failed++))
            failed_list+=("$subject")
            log "  ✗ Copy failed"
        fi
        log ""
    done
    
    # Combine T2 for subjects that need it
    for subject in "${subjects_needing_combination[@]}"; do
        ((current++))
        log "=========================================="
        log "Processing subject ${current}/${total}: ${subject} (combine)"
        log "=========================================="
        
        if run_t2_combination_for_subject "$subject"; then
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
    log "T2 Combination Complete"
    log "=========================================="
    log "Total subjects: ${total}"
    log "  Combined: ${#subjects_needing_combination[@]}"
    log "  Copied: ${#subjects_for_copy[@]}"
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
    log "Log file: ${LOG_FILE}"
    log "=========================================="
    
    if [[ $failed -gt 0 ]]; then
        exit 1
    fi
}

main "$@"



