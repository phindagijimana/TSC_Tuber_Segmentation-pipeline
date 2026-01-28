#!/bin/bash

################################################################################
# Test Docker on SLURM Compute Node
# 
# Description:
#   Submits a test job to verify Docker containers can be pulled on compute nodes.
#
# Usage:
#   ./test_docker_slurm.sh [--all]
#
# Options:
#   --all    Test all 4 containers (default: test first one only)
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

# Test mode
TEST_ALL=false

# SLURM settings for quick test
PARTITION="general"
TIME_LIMIT="00:30:00"  # 30 minutes should be plenty
MEMORY_GB="16"
CPUS="4"
GPU_MEM="12"

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
Test Docker Container Availability on SLURM Compute Nodes

Usage: $(basename "$0") [options]

Options:
  --all        Test all 4 containers (default: test first one only)
  --help       Show this help message

Examples:
  ./test_docker_slurm.sh           # Test first container only
  ./test_docker_slurm.sh --all     # Test all 4 containers

EOF
    exit 0
}

# ============================================================================
# Argument Parsing
# ============================================================================

while [[ $# -gt 0 ]]; do
    case "$1" in
        --all)
            TEST_ALL=true
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
# Generate Test Batch Script
# ============================================================================

generate_test_script() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local batch_file="${LOG_DIR}/test_docker_batch_${timestamp}.sh"
    
    cat > "$batch_file" << EOF
#!/bin/bash

#SBATCH --job-name=test_docker
#SBATCH --partition=${PARTITION}
#SBATCH --gres=gpu:l40s.${GPU_MEM}g:1
#SBATCH --cpus-per-task=${CPUS}
#SBATCH --mem=${MEMORY_GB}G
#SBATCH --time=${TIME_LIMIT}
#SBATCH --output=${LOG_DIR}/test_docker_slurm-%j.out
#SBATCH --error=${LOG_DIR}/test_docker_slurm-%j.err

################################################################################
# SLURM Test Job: Docker Container Availability
# Generated: $(date)
# Submitted by: \${USER}
################################################################################

echo "=========================================="
echo "Docker Container Test on Compute Node"
echo "=========================================="
echo "Job ID: \${SLURM_JOB_ID}"
echo "Node: \${SLURM_NODELIST}"
echo "Partition: \${SLURM_JOB_PARTITION}"
echo "CPUs: \${SLURM_CPUS_PER_TASK}"
echo "Memory: ${MEMORY_GB}GB"
echo "GPU: L40S ${GPU_MEM}GB"
echo "Start time: \$(date)"
echo "=========================================="
echo ""

# Check Docker/Singularity availability
echo "Checking container runtime..."
if command -v docker &> /dev/null; then
    echo "  Docker found: \$(docker --version)"
    RUNTIME="docker"
elif command -v singularity &> /dev/null; then
    echo "  Singularity found: \$(singularity --version)"
    RUNTIME="singularity"
elif command -v apptainer &> /dev/null; then
    echo "  Apptainer found: \$(apptainer --version)"
    RUNTIME="apptainer"
else
    echo "x No container runtime found (docker/singularity/apptainer)"
    exit 1
fi
echo ""

# Check GPU
if command -v nvidia-smi &> /dev/null; then
    echo "GPU Status:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    echo ""
fi

# Set environment
export PROJECT_ROOT="${PROJECT_ROOT}"

# Change to project directory
cd "${PROJECT_ROOT}"

# Run Python test script
echo "Running container test..."
echo ""

EOF

    # Add test command based on mode
    if [[ "$TEST_ALL" == "true" ]]; then
        echo "python3 ${SCRIPTS_DIR}/test_docker.py --all" >> "$batch_file"
    else
        echo "python3 ${SCRIPTS_DIR}/test_docker.py" >> "$batch_file"
    fi
    
    cat >> "$batch_file" << 'EOF'

TEST_EXIT=$?

echo ""
echo "=========================================="
if [ $TEST_EXIT -eq 0 ]; then
    echo "  Docker container test PASSED"
else
    echo "x Docker container test FAILED (exit code: $TEST_EXIT)"
fi
echo "End time: $(date)"
echo "=========================================="

exit $TEST_EXIT
EOF

    echo "$batch_file"
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log "=========================================="
    log "TSC Pipeline - Docker Test via SLURM"
    log "=========================================="
    log "Project root: ${PROJECT_ROOT}"
    
    # Validate SLURM is available
    if ! command -v sbatch &> /dev/null; then
        error_exit "sbatch command not found. Is SLURM installed?"
    fi
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    
    # Display configuration
    log ""
    log "Test Configuration:"
    log "  Partition: ${PARTITION}"
    log "  Time limit: ${TIME_LIMIT}"
    log "  Memory: ${MEMORY_GB}GB"
    log "  CPUs: ${CPUS}"
    log "  GPU: L40S ${GPU_MEM}GB"
    if [[ "$TEST_ALL" == "true" ]]; then
        log "  Mode: Test ALL 4 containers"
    else
        log "  Mode: Test FIRST container only"
    fi
    log ""
    
    # Generate batch script
    log "Generating test batch script..."
    local batch_script=$(generate_test_script)
    log "    Generated: ${batch_script}"
    log ""
    
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
    
    log "    Job submitted successfully"
    log "  Job ID: ${job_id}"
    log ""
    
    # Display monitoring commands
    log "=========================================="
    log "Job Monitoring"
    log "=========================================="
    log "Check job status:"
    log "  squeue -j ${job_id}"
    log ""
    log "View job output (after it starts):"
    log "  tail -f ${LOG_DIR}/test_docker_slurm-${job_id}.out"
    log ""
    log "Check job details:"
    log "  scontrol show job ${job_id}"
    log ""
    log "Cancel job (if needed):"
    log "  scancel ${job_id}"
    log ""
    log "Batch script: ${batch_script}"
    log "=========================================="
    log ""
    log "Waiting for job to start..."
    log "(This may take a few minutes depending on queue)"
    log ""
    
    # Wait for job to start and tail output
    local max_wait=300  # 5 minutes
    local elapsed=0
    local interval=5
    
    while [[ $elapsed -lt $max_wait ]]; do
        # Check if job is running or complete
        local job_state=$(squeue -j ${job_id} -h -o "%T" 2>/dev/null || echo "")
        
        if [[ -z "$job_state" ]]; then
            # Job finished or doesn't exist
            break
        elif [[ "$job_state" == "RUNNING" ]]; then
            log "Job is RUNNING on node: $(squeue -j ${job_id} -h -o "%N")"
            break
        elif [[ "$job_state" == "PENDING" ]]; then
            log "Job is PENDING (waiting for resources)... ${elapsed}s elapsed"
        else
            log "Job state: ${job_state}"
        fi
        
        sleep $interval
        elapsed=$((elapsed + interval))
    done
    
    if [[ $elapsed -ge $max_wait ]]; then
        log "  Timeout waiting for job to start"
        log "   Job is still in queue. Monitor manually with:"
        log "   squeue -j ${job_id}"
        log "   tail -f ${LOG_DIR}/test_docker_slurm-${job_id}.out"
        exit 0
    fi
    
    # Tail the output file if it exists
    log ""
    log "=========================================="
    log "Job Output (live tail, Ctrl+C to stop):"
    log "=========================================="
    log ""
    
    local output_file="${LOG_DIR}/test_docker_slurm-${job_id}.out"
    
    # Wait for file to be created
    sleep 2
    
    if [[ -f "$output_file" ]]; then
        tail -f "$output_file" &
        TAIL_PID=$!
        
        # Wait for job to complete
        while squeue -j ${job_id} -h &>/dev/null; do
            sleep 2
        done
        
        # Kill tail process
        kill $TAIL_PID 2>/dev/null || true
        
        log ""
        log "=========================================="
        log "Job Complete"
        log "=========================================="
        log "Output file: ${output_file}"
        log ""
        
        # Show final status
        local exit_code=$(sacct -j ${job_id} -o ExitCode -n | tail -1 | awk '{print $1}' | cut -d: -f1)
        
        if [[ "$exit_code" == "0" ]]; then
            log "  Test PASSED - Docker works on compute nodes!"
            log ""
            log "Next step: Run the full pipeline"
            log "  ./scripts/submit_gpu_job.sh"
        else
            log "x Test FAILED (exit code: ${exit_code})"
            log ""
            log "Review output file for details:"
            log "  less ${output_file}"
        fi
    else
        log "Output file not created yet. Check manually:"
        log "  tail -f ${output_file}"
    fi
}

main "$@"



