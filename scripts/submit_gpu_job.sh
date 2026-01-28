#!/bin/bash

################################################################################
# TSC Tuber Segmentation Pipeline - GPU Job Submission Script
# 
# Description:
#   Submits the tuber segmentation pipeline as a SLURM batch job with GPU
#   resources. Automatically configures resource requests and monitors job.
#
# Usage:
#   ./submit_gpu_job.sh [options]
#
# Options:
#   --force          Force re-run of all steps
#   --start-from N   Start from step N (0-4)
#   --partition P    SLURM partition (default: general)
#   --time HH:MM:SS  Time limit (default: 04:00:00)
#   --mem GB         Memory in GB (default: 32)
#   --cpus N         CPU cores (default: 8)
#   --gpu-mem GB     GPU memory: 6, 12, or 24 (default: 12)
#   --dry-run        Show batch script without submitting
#   --help           Show this help message
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

# Default SLURM parameters
PARTITION="general"
TIME_LIMIT="04:00:00"
MEMORY_GB="32"
CPUS="8"
GPU_MEM="12"  # Options: 6, 12, 24 (GB)

# Pipeline parameters
FORCE_RERUN=false
START_FROM=0
DRY_RUN=false

# ============================================================================
# Utility Functions
# ============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error_exit() {
    log "ERROR: $*"
    exit 1
}

show_help() {
    cat << EOF
TSC Tuber Segmentation Pipeline - GPU Job Submission

Submits the pipeline as a SLURM batch job with GPU acceleration.

Usage: $(basename "$0") [options]

SLURM Resource Options:
  --partition P    SLURM partition (default: general)
                   Options: general (7-day limit), interactive (12-hour limit)
  --time HH:MM:SS  Time limit (default: 04:00:00)
  --mem GB         Memory in GB (default: 32)
  --cpus N         CPU cores (default: 8)
  --gpu-mem GB     GPU memory: 6, 12, or 24 GB (default: 12)

Pipeline Options:
  --force          Force re-run of all steps
  --start-from N   Start from step N (0-4, default: 0)
  --dry-run        Show batch script without submitting
  --help           Show this help message

Examples:
  ./submit_gpu_job.sh
      Submit full pipeline with default resources

  ./submit_gpu_job.sh --start-from 3 --time 02:00:00
      Resume from step 3 with 2-hour time limit

  ./submit_gpu_job.sh --gpu-mem 24 --mem 64
      Use 24GB GPU and 64GB RAM

  ./submit_gpu_job.sh --dry-run
      Preview the SLURM batch script

EOF
    exit 0
}

# Validate GPU memory option
validate_gpu_mem() {
    case "$GPU_MEM" in
        6|12|24)
            return 0
            ;;
        *)
            error_exit "Invalid --gpu-mem value: ${GPU_MEM}. Must be 6, 12, or 24."
            ;;
    esac
}

# Generate SLURM batch script
generate_batch_script() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local batch_file="${LOG_DIR}/slurm_batch_${timestamp}.sh"
    
    cat > "$batch_file" << EOF
#!/bin/bash

#SBATCH --job-name=tuber_pipeline
#SBATCH --partition=${PARTITION}
#SBATCH --gres=gpu:l40s.${GPU_MEM}g:1
#SBATCH --cpus-per-task=${CPUS}
#SBATCH --mem=${MEMORY_GB}G
#SBATCH --time=${TIME_LIMIT}
#SBATCH --output=${LOG_DIR}/slurm-%j.out
#SBATCH --error=${LOG_DIR}/slurm-%j.err

################################################################################
# SLURM Batch Job: TSC Tuber Segmentation Pipeline
# Generated: $(date)
# Submitted by: \${USER}
################################################################################

# Job information
echo "=========================================="
echo "SLURM Job Information"
echo "=========================================="
echo "Job ID: \${SLURM_JOB_ID}"
echo "Job name: \${SLURM_JOB_NAME}"
echo "Node: \${SLURM_NODELIST}"
echo "Partition: \${SLURM_JOB_PARTITION}"
echo "CPUs: \${SLURM_CPUS_PER_TASK}"
echo "Memory: ${MEMORY_GB}GB"
echo "GPU: L40S ${GPU_MEM}GB"
echo "Start time: \$(date)"
echo "=========================================="
echo ""

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    echo "GPU Status:"
    nvidia-smi
    echo ""
else
    echo "WARNING: nvidia-smi not found"
    echo ""
fi

# Set environment
export USE_GPU=true
export PROJECT_ROOT="${PROJECT_ROOT}"

# Change to project directory
cd "${PROJECT_ROOT}"

# Build pipeline command (Python version)
PIPELINE_CMD="python3 ${SCRIPTS_DIR}/run_pipeline.py"
EOF

    # Add pipeline flags
    if [[ "$FORCE_RERUN" == "true" ]]; then
        echo "PIPELINE_CMD=\"\${PIPELINE_CMD} --force\"" >> "$batch_file"
    fi
    
    if [[ $START_FROM -gt 0 ]]; then
        echo "PIPELINE_CMD=\"\${PIPELINE_CMD} --start-from ${START_FROM}\"" >> "$batch_file"
    fi
    
    cat >> "$batch_file" << 'EOF'

# Run the pipeline
echo "Executing pipeline..."
echo "Command: ${PIPELINE_CMD}"
echo ""

if eval "${PIPELINE_CMD}"; then
    EXIT_CODE=0
    echo ""
    echo "=========================================="
    echo "Job completed successfully"
else
    EXIT_CODE=$?
    echo ""
    echo "=========================================="
    echo "Job failed with exit code: ${EXIT_CODE}"
fi

echo "End time: $(date)"
echo "=========================================="

exit ${EXIT_CODE}
EOF

    echo "$batch_file"
}

# ============================================================================
# Argument Parsing
# ============================================================================

while [[ $# -gt 0 ]]; do
    case "$1" in
        --partition)
            PARTITION="$2"
            shift 2
            ;;
        --time)
            TIME_LIMIT="$2"
            shift 2
            ;;
        --mem)
            MEMORY_GB="$2"
            shift 2
            ;;
        --cpus)
            CPUS="$2"
            shift 2
            ;;
        --gpu-mem)
            GPU_MEM="$2"
            shift 2
            ;;
        --force)
            FORCE_RERUN=true
            shift
            ;;
        --start-from)
            START_FROM="$2"
            if ! [[ "$START_FROM" =~ ^[0-4]$ ]]; then
                error_exit "--start-from must be 0-4"
            fi
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log "=========================================="
    log "TSC Tuber Segmentation Pipeline"
    log "GPU Job Submission"
    log "=========================================="
    log "Project root: ${PROJECT_ROOT}"
    log ""
    
    # Validate SLURM is available
    if ! command -v sbatch &> /dev/null; then
        error_exit "sbatch command not found. Is SLURM installed?"
    fi
    
    # Validate GPU memory
    validate_gpu_mem
    
    # Display configuration
    log "SLURM Configuration:"
    log "  Partition: ${PARTITION}"
    log "  Time limit: ${TIME_LIMIT}"
    log "  Memory: ${MEMORY_GB}GB"
    log "  CPUs: ${CPUS}"
    log "  GPU: L40S ${GPU_MEM}GB"
    log ""
    
    log "Pipeline Configuration:"
    log "  Start from step: ${START_FROM}"
    log "  Force re-run: ${FORCE_RERUN}"
    log ""
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    
    # Generate batch script
    log "Generating SLURM batch script..."
    local batch_script=$(generate_batch_script)
    log "  ✓ Generated: ${batch_script}"
    log ""
    
    # Show batch script content if dry-run
    if [[ "$DRY_RUN" == "true" ]]; then
        log "=========================================="
        log "DRY RUN: Batch Script Content"
        log "=========================================="
        cat "$batch_script"
        log "=========================================="
        log "Dry run complete. Use without --dry-run to submit."
        exit 0
    fi
    
    # Submit job
    log "Submitting job to SLURM..."
    local submit_output
    if ! submit_output=$(sbatch "$batch_script" 2>&1); then
        error_exit "Job submission failed: ${submit_output}"
    fi
    
    # Extract job ID
    local job_id=$(echo "$submit_output" | grep -oP 'Submitted batch job \K\d+')
    
    if [[ -z "$job_id" ]]; then
        error_exit "Could not parse job ID from: ${submit_output}"
    fi
    
    log "  ✓ Job submitted successfully"
    log "  Job ID: ${job_id}"
    log ""
    
    # Display monitoring commands
    log "=========================================="
    log "Job Monitoring"
    log "=========================================="
    log "Check job status:"
    log "  squeue -j ${job_id}"
    log ""
    log "View job details:"
    log "  scontrol show job ${job_id}"
    log ""
    log "Monitor output (after job starts):"
    log "  tail -f ${LOG_DIR}/slurm-${job_id}.out"
    log ""
    log "Cancel job:"
    log "  scancel ${job_id}"
    log ""
    log "Batch script: ${batch_script}"
    log "=========================================="
    log ""
    log "Job submitted. Monitor progress using the commands above."
}

main "$@"

