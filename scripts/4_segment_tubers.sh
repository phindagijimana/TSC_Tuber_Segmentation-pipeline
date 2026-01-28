#!/bin/bash

################################################################################
# TSC Tuber Segmentation Pipeline - Tuber Segmentation Step
# 
# Description:
#   Automatically segments tubers and quantifies tuber burden using
#   TSCCNN3D_dropout deep learning model. Supports GPU acceleration.
#
# Docker Image: ivansanchezfernandez/segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout
# Citation: Sánchez Fernández et al., Convolutional neural networks for
#           automatic tuber segmentation and quantification of tuber burden
#           in tuberous sclerosis complex. Epilepsia 2025. DOI: 10.1111/epi.70007
#
# Input:  preprocessing/preprocessed_MRIs/{subject}/*.nii
# Output: results/{subject}/*.nii (segmentations)
#         results/volume_results.txt (tuber burden quantification)
#
# Author: Tuber Pipeline Development Team
# Date: 2026-01-27
################################################################################

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

INPUT_DIR="${PROJECT_ROOT}/preprocessing/preprocessed_MRIs"
OUTPUT_DIR="${PROJECT_ROOT}/results"
LOG_DIR="${PROJECT_ROOT}/logs"

DOCKER_IMAGE="ivansanchezfernandez/segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout"

# Check if GPU support should be enabled
USE_GPU="${USE_GPU:-auto}"  # Can be: auto, true, false

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/4_segment_tubers_${TIMESTAMP}.log"

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

# Detect if GPU is available
detect_gpu() {
    if [[ "$USE_GPU" == "false" ]]; then
        echo "false"
        return
    fi
    
    if [[ "$USE_GPU" == "true" ]]; then
        echo "true"
        return
    fi
    
    # Auto-detect GPU
    if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
        echo "true"
    else
        echo "false"
    fi
}

pull_docker_image() {
    local image="$1"
    log "Checking Docker image: ${image}"
    
    if docker image inspect "$image" &> /dev/null; then
        log "    Image already available locally"
    else
        log "  Pulling Docker image (this may take several minutes, ~several GB)..."
        if ! docker pull "$image"; then
            error_exit "Failed to pull Docker image: ${image}"
        fi
        log "    Image pulled successfully"
    fi
}

run_segmentation_for_subject() {
    local subject="$1"
    local use_gpu="$2"
    local subject_input="${INPUT_DIR}/${subject}"
    local subject_output="${OUTPUT_DIR}/${subject}"
    
    mkdir -p "$subject_output"
    
    # Count input files and validate we have T1, T2, FLAIR
    local t1_count=$(find "$subject_input" -type f -name "*_T1_*" \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null | wc -l)
    local t2_count=$(find "$subject_input" -type f -name "*_T2_*" \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null | wc -l)
    local flair_count=$(find "$subject_input" -type f -name "*_FLAIR_*" \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null | wc -l)
    
    log "  Sequences: T1=${t1_count}, T2=${t2_count}, FLAIR=${flair_count}"
    
    if [[ $t1_count -eq 0 ]] || [[ $t2_count -eq 0 ]] || [[ $flair_count -eq 0 ]]; then
        log "    WARNING: Missing required sequences, skipping"
        return 1
    fi
    
    # Build Docker command
    local docker_cmd="docker run --rm"
    
    # Add GPU support if available
    if [[ "$use_gpu" == "true" ]]; then
        docker_cmd="$docker_cmd --gpus all"
        log "  Running with GPU acceleration..."
    else
        log "  Running on CPU..."
    fi
    
    docker_cmd="$docker_cmd -v ${subject_input}:/input:ro -v ${subject_output}:/output ${DOCKER_IMAGE}"
    
    local start_time=$(date +%s)
    
    if ! eval "$docker_cmd" >> "$LOG_FILE" 2>&1; then
        log "  x Container execution failed"
        return 1
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    # Validate outputs
    local seg_count=$(find "$subject_output" -type f -name "*seg*" \( -name "*.nii" -o -name "*.nii.gz" \) 2>/dev/null | wc -l)
    
    log "    Completed in ${minutes}m ${seconds}s"
    log "  Segmentation files: ${seg_count}"
    
    if [[ $seg_count -eq 0 ]]; then
        log "    WARNING: No segmentation files generated"
        return 1
    fi
    
    return 0
}

# Aggregate volume results from all subjects
aggregate_volume_results() {
    log "Aggregating tuber burden results..."
    
    local results_file="${OUTPUT_DIR}/volume_results.txt"
    
    # Create header
    echo "Subject_ID	T1_Volume_mm3	T2_Volume_mm3	FLAIR_Volume_mm3	Total_Volume_mm3	Generated_Timestamp" > "$results_file"
    
    # Find all individual volume_results.txt files
    local found_results=false
    while IFS= read -r -d '' vol_file; do
        found_results=true
        # Skip the aggregated file itself
        [[ "$vol_file" == "$results_file" ]] && continue
        
        # Append contents (skip header if present)
        tail -n +2 "$vol_file" 2>/dev/null >> "$results_file" || cat "$vol_file" >> "$results_file"
    done < <(find "$OUTPUT_DIR" -mindepth 2 -name "volume_results.txt" -print0 2>/dev/null)
    
    if [[ "$found_results" == "true" ]]; then
        local line_count=$(wc -l < "$results_file")
        log "    Aggregated results: $((line_count - 1)) subject(s)"
        log "  Output: ${results_file}"
    else
        log "    No volume results found to aggregate"
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log "=========================================="
    log "Step 4: Tuber Segmentation with TSCCNN3D"
    log "=========================================="
    log "Project root: ${PROJECT_ROOT}"
    log "Input directory: ${INPUT_DIR}"
    log "Output directory: ${OUTPUT_DIR}"
    log ""
    
    # Pre-flight checks
    check_docker
    
    # GPU detection
    local gpu_available=$(detect_gpu)
    if [[ "$gpu_available" == "true" ]]; then
        log "GPU: Detected and enabled"
    else
        log "GPU: Not available, using CPU"
    fi
    log ""
    
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
    
    if [[ "$gpu_available" == "true" ]]; then
        log "Expected time per subject: 1-2 minutes (GPU)"
        log "Total estimated time: $(( ${#subjects[@]} * 2 )) - $(( ${#subjects[@]} * 3 )) minutes"
    else
        log "Expected time per subject: 5-15 minutes (CPU)"
        log "Total estimated time: $(( ${#subjects[@]} * 10 )) - $(( ${#subjects[@]} * 15 )) minutes"
    fi
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
        
        if run_segmentation_for_subject "$subject" "$gpu_available"; then
            ((success++))
            local subject_end=$(date +%s)
            local subject_duration=$((subject_end - subject_start))
            total_time=$((total_time + subject_duration))
            log "    ${subject} completed successfully"
        else
            ((failed++))
            failed_list+=("$subject")
            log "  x ${subject} failed"
        fi
        log ""
    done
    
    # Aggregate volume results
    log "=========================================="
    aggregate_volume_results
    log ""
    
    # Calculate average time
    local avg_time=0
    if [[ $success -gt 0 ]]; then
        avg_time=$((total_time / success))
    fi
    local avg_minutes=$((avg_time / 60))
    local avg_seconds=$((avg_time % 60))
    
    # Summary
    log "=========================================="
    log "Tuber Segmentation Complete"
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
    log "Volume results: ${OUTPUT_DIR}/volume_results.txt"
    log "Log file: ${LOG_FILE}"
    log ""
    log "=========================================="
    log "CITATION REMINDER"
    log "=========================================="
    log "If you use these results in your research, please cite:"
    log "Sánchez Fernández et al., Epilepsia 2025. DOI: 10.1111/epi.70007"
    log "=========================================="
    
    if [[ $failed -gt 0 ]]; then
        exit 1
    fi
}

main "$@"



