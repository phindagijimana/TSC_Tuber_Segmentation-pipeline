#!/bin/bash

################################################################################
# TSC Tuber Segmentation Pipeline - Data Preparation Step
# 
# Description:
#   Organizes raw NIfTI files from nested subject directories into per-subject
#   preprocessing folders with validation of file naming conventions.
#
# Input:  TSC_MRI_SUB/{subject}/*.nii
# Output: preprocessing/MRI_files/{subject}/*.nii
#
# Author: Tuber Pipeline Development Team
# Date: 2026-01-27
################################################################################

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# ============================================================================
# Configuration
# ============================================================================

# Get absolute path to project root (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Define key directories
INPUT_DIR="${PROJECT_ROOT}/TSC_MRI_SUB"
OUTPUT_DIR="${PROJECT_ROOT}/preprocessing/MRI_files"
LOG_DIR="${PROJECT_ROOT}/logs"

# Create log file with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/0_prepare_data_${TIMESTAMP}.log"

# ============================================================================
# Utility Functions
# ============================================================================

# Log message to both console and log file
log() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

# Log error and exit
error_exit() {
    log "ERROR: $*"
    exit 1
}

# Validate file naming convention
validate_filename() {
    local filename="$1"
    local subject="$2"
    
    # Check if filename starts with subject ID followed by underscore
    if [[ ! "$filename" =~ ^${subject}_ ]]; then
        return 1
    fi
    
    # Check if filename contains required sequence token
    if [[ ! "$filename" =~ _T1_ ]] && [[ ! "$filename" =~ _T2_ ]] && [[ ! "$filename" =~ _FLAIR_ ]]; then
        return 1
    fi
    
    return 0
}

# Count files by sequence type for a subject
count_sequences() {
    local subject_dir="$1"
    local t1_count=0
    local t2_count=0
    local flair_count=0
    
    while IFS= read -r file; do
        [[ -z "$file" ]] && continue
        if [[ "$file" =~ _T1_ ]]; then
            ((t1_count++))
        elif [[ "$file" =~ _T2_ ]]; then
            ((t2_count++))
        elif [[ "$file" =~ _FLAIR_ ]]; then
            ((flair_count++))
        fi
    done < <(find "$subject_dir" -maxdepth 1 -name "*.nii" -o -name "*.nii.gz" 2>/dev/null)
    
    echo "${t1_count} ${t2_count} ${flair_count}"
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log "=========================================="
    log "Step 0: Data Preparation"
    log "=========================================="
    log "Project root: ${PROJECT_ROOT}"
    log "Input directory: ${INPUT_DIR}"
    log "Output directory: ${OUTPUT_DIR}"
    log ""
    
    # Validate input directory exists
    if [[ ! -d "$INPUT_DIR" ]]; then
        error_exit "Input directory not found: ${INPUT_DIR}"
    fi
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Discover all subject directories
    log "Discovering subjects..."
    subjects=()
    while IFS= read -r -d '' subject_dir; do
        subject=$(basename "$subject_dir")
        subjects+=("$subject")
        log "  Found: ${subject}"
    done < <(find "$INPUT_DIR" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
    
    if [[ ${#subjects[@]} -eq 0 ]]; then
        error_exit "No subject directories found in ${INPUT_DIR}"
    fi
    
    log ""
    log "Total subjects found: ${#subjects[@]}"
    log ""
    
    # Process each subject
    local total_subjects=${#subjects[@]}
    local current=0
    local failed_subjects=()
    
    for subject in "${subjects[@]}"; do
        ((current++))
        log "----------------------------------------"
        log "Processing subject ${current}/${total_subjects}: ${subject}"
        log "----------------------------------------"
        
        local subject_input="${INPUT_DIR}/${subject}"
        local subject_output="${OUTPUT_DIR}/${subject}"
        
        # Create subject output directory
        mkdir -p "$subject_output"
        
        # Find all NIfTI files
        local nifti_files=()
        while IFS= read -r -d '' file; do
            nifti_files+=("$file")
        done < <(find "$subject_input" -maxdepth 1 \( -name "*.nii" -o -name "*.nii.gz" \) -print0 | sort -z)
        
        if [[ ${#nifti_files[@]} -eq 0 ]]; then
            log "  WARNING: No NIfTI files found for ${subject}"
            failed_subjects+=("${subject} (no NIfTI files)")
            continue
        fi
        
        log "  Found ${#nifti_files[@]} NIfTI file(s)"
        
        # Validate and copy files
        local valid_files=0
        local invalid_files=0
        
        for file in "${nifti_files[@]}"; do
            local filename=$(basename "$file")
            
            # Validate filename
            if validate_filename "$filename" "$subject"; then
                cp "$file" "${subject_output}/${filename}"
                log "      ${filename}"
                ((valid_files++))
            else
                log "    x ${filename} (invalid naming convention)"
                ((invalid_files++))
            fi
        done
        
        # Count sequences
        read -r t1_count t2_count flair_count <<< "$(count_sequences "$subject_output")"
        
        log "  Sequence summary:"
        log "    T1:    ${t1_count} file(s)"
        log "    T2:    ${t2_count} file(s)"
        log "    FLAIR: ${flair_count} file(s)"
        
        # Validate minimum requirements
        local has_error=false
        if [[ $t1_count -eq 0 ]]; then
            log "    WARNING: No T1 sequence found"
            has_error=true
        fi
        if [[ $t2_count -eq 0 ]]; then
            log "    WARNING: No T2 sequence found"
            has_error=true
        fi
        if [[ $flair_count -eq 0 ]]; then
            log "    WARNING: No FLAIR sequence found"
            has_error=true
        fi
        
        if [[ "$has_error" == "true" ]]; then
            failed_subjects+=("${subject} (missing required sequences)")
        else
            log "    Subject validation passed"
        fi
        
        log "  Copied: ${valid_files} valid file(s)"
        if [[ $invalid_files -gt 0 ]]; then
            log "  Skipped: ${invalid_files} invalid file(s)"
        fi
        log ""
    done
    
    # Summary
    log "=========================================="
    log "Data Preparation Complete"
    log "=========================================="
    log "Total subjects processed: ${total_subjects}"
    log "Successfully prepared: $((total_subjects - ${#failed_subjects[@]}))"
    
    if [[ ${#failed_subjects[@]} -gt 0 ]]; then
        log ""
        log "  Subjects with issues:"
        for failed in "${failed_subjects[@]}"; do
            log "  - ${failed}"
        done
        log ""
        log "WARNING: Some subjects may not process correctly in subsequent steps."
    else
        log "  All subjects validated successfully"
    fi
    
    log ""
    log "Output directory: ${OUTPUT_DIR}"
    log "Log file: ${LOG_FILE}"
    log "=========================================="
}

# Run main function
main "$@"



