#!/bin/bash

################################################################################
# TSC Tuber Segmentation Pipeline - Main Orchestrator
# 
# Description:
#   Main pipeline script that orchestrates all preprocessing and segmentation
#   steps. Runs on CPU (use submit_gpu_job.sh for GPU acceleration).
#
# Usage:
#   ./run_pipeline.sh [options]
#
# Options:
#   --force          Force re-run of all steps (ignore existing outputs)
#   --start-from N   Start from step N (0-4)
#   --help           Show this help message
#
# Steps:
#   0. Prepare data (organize into per-subject folders)
#   1. Skull strip with SynthStrip
#   2. Combine T2 sequences with NiftyMIC
#   3. Register to MNI with ANTs
#   4. Segment tubers with TSCCNN3D
#
# Author: Tuber Pipeline Development Team
# Date: 2026-01-27
################################################################################

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
LOG_DIR="${PROJECT_ROOT}/logs"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
PIPELINE_LOG="${LOG_DIR}/pipeline_${TIMESTAMP}.log"

# Parse command line arguments
FORCE_RERUN=false
START_FROM=0

# ============================================================================
# Utility Functions
# ============================================================================

log() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" | tee -a "$PIPELINE_LOG"
}

error_exit() {
    log "ERROR: $*"
    log "Pipeline failed. Check log: ${PIPELINE_LOG}"
    exit 1
}

show_help() {
    cat << EOF
TSC Tuber Segmentation Pipeline

Usage: $(basename "$0") [options]

Options:
  --force          Force re-run of all steps (ignore existing outputs)
  --start-from N   Start from step N (0-4, default: 0)
  --help           Show this help message

Steps:
  0. Prepare data
  1. Skull stripping
  2. T2 combination
  3. MNI registration
  4. Tuber segmentation

Examples:
  ./run_pipeline.sh                    # Run full pipeline
  ./run_pipeline.sh --start-from 2     # Resume from step 2
  ./run_pipeline.sh --force            # Force re-run all steps

For GPU-accelerated execution, use: ./submit_gpu_job.sh

EOF
    exit 0
}

# Check if a step's output directory has content
step_has_output() {
    local step_dir="$1"
    [[ -d "$step_dir" ]] && [[ -n "$(find "$step_dir" -mindepth 1 -maxdepth 1 2>/dev/null)" ]]
}

# Run a pipeline step
run_step() {
    local step_num="$1"
    local step_name="$2"
    local step_script="$3"
    local output_dir="$4"
    
    log ""
    log "=========================================="
    log "STEP ${step_num}: ${step_name}"
    log "=========================================="
    
    # Check if step should be skipped
    if [[ "$FORCE_RERUN" == "false" ]] && [[ $step_num -ge 1 ]] && step_has_output "$output_dir"; then
        log "Output directory exists and contains data: ${output_dir}"
        log "⏭  Skipping step ${step_num} (use --force to re-run)"
        return 0
    fi
    
    # Check if script exists
    if [[ ! -f "$step_script" ]]; then
        error_exit "Step script not found: ${step_script}"
    fi
    
    # Make script executable
    chmod +x "$step_script"
    
    # Run the step
    log "Executing: ${step_script}"
    local step_start=$(date +%s)
    
    if ! bash "$step_script"; then
        error_exit "Step ${step_num} failed: ${step_name}"
    fi
    
    local step_end=$(date +%s)
    local duration=$((step_end - step_start))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    log "✓ Step ${step_num} completed successfully in ${minutes}m ${seconds}s"
}

# ============================================================================
# Argument Parsing
# ============================================================================

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force)
            FORCE_RERUN=true
            shift
            ;;
        --start-from)
            START_FROM="$2"
            if ! [[ "$START_FROM" =~ ^[0-4]$ ]]; then
                echo "Error: --start-from must be 0-4"
                exit 1
            fi
            shift 2
            ;;
        --help|-h)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
done

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log "=========================================="
    log "TSC Tuber Segmentation Pipeline"
    log "=========================================="
    log "Project root: ${PROJECT_ROOT}"
    log "Pipeline log: ${PIPELINE_LOG}"
    log "Start time: $(date)"
    log ""
    
    if [[ "$FORCE_RERUN" == "true" ]]; then
        log "⚠ Force mode: Will re-run all steps"
    fi
    
    if [[ $START_FROM -gt 0 ]]; then
        log "⚠ Starting from step: ${START_FROM}"
    fi
    
    log ""
    
    # Record overall start time
    local pipeline_start=$(date +%s)
    
    # Step 0: Prepare Data
    if [[ $START_FROM -le 0 ]]; then
        run_step 0 "Data Preparation" \
            "${SCRIPTS_DIR}/0_prepare_data.sh" \
            "${PROJECT_ROOT}/preprocessing/MRI_files"
    fi
    
    # Step 1: Skull Stripping
    if [[ $START_FROM -le 1 ]]; then
        run_step 1 "Skull Stripping" \
            "${SCRIPTS_DIR}/1_skull_strip.sh" \
            "${PROJECT_ROOT}/preprocessing/skull_stripped_MRIs"
    fi
    
    # Step 2: T2 Combination
    if [[ $START_FROM -le 2 ]]; then
        run_step 2 "T2 Combination" \
            "${SCRIPTS_DIR}/2_combine_t2.sh" \
            "${PROJECT_ROOT}/preprocessing/combined_MRIs"
    fi
    
    # Step 3: MNI Registration
    if [[ $START_FROM -le 3 ]]; then
        run_step 3 "MNI Registration" \
            "${SCRIPTS_DIR}/3_register_to_mni.sh" \
            "${PROJECT_ROOT}/preprocessing/preprocessed_MRIs"
    fi
    
    # Step 4: Tuber Segmentation
    if [[ $START_FROM -le 4 ]]; then
        run_step 4 "Tuber Segmentation" \
            "${SCRIPTS_DIR}/4_segment_tubers.sh" \
            "${PROJECT_ROOT}/results"
    fi
    
    # Calculate total time
    local pipeline_end=$(date +%s)
    local total_duration=$((pipeline_end - pipeline_start))
    local total_hours=$((total_duration / 3600))
    local total_minutes=$(( (total_duration % 3600) / 60 ))
    local total_seconds=$((total_duration % 60))
    
    # Final summary
    log ""
    log "=========================================="
    log "PIPELINE COMPLETE"
    log "=========================================="
    log "Total time: ${total_hours}h ${total_minutes}m ${total_seconds}s"
    log "End time: $(date)"
    log ""
    log "Output locations:"
    log "  - Preprocessed MRIs: ${PROJECT_ROOT}/preprocessing/preprocessed_MRIs/"
    log "  - Segmentations: ${PROJECT_ROOT}/results/"
    log "  - Tuber burden: ${PROJECT_ROOT}/results/volume_results.txt"
    log "  - Pipeline log: ${PIPELINE_LOG}"
    log ""
    log "Next steps:"
    log "  1. Review volume_results.txt for tuber burden quantification"
    log "  2. Visualize segmentations using ITK-SNAP:"
    log "     itksnap -g results/Case001/Case001_T1_*.nii \\"
    log "             -s results/Case001/*seg*.nii"
    log ""
    log "=========================================="
    log "CITATION REMINDER"
    log "=========================================="
    log "Please cite these publications if you use this pipeline:"
    log "  - Sánchez Fernández et al., Epilepsia 2025 (main method)"
    log "  - Hoopes et al., Neuroimage 2022 (SynthStrip)"
    log "  - Ebner et al., Neuroimage 2020 (NiftyMIC)"
    log "  - Avants et al., Neuroimage 2011 (ANTs)"
    log "=========================================="
}

# Run main function
main "$@"



