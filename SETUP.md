# Complete Setup Guide

## Prerequisites

### System Requirements
- **Operating System**: Linux (tested on RHEL 8/9, Ubuntu 20.04+)
- **Container Runtime**: Apptainer/Singularity OR Docker
- **Python**: 3.7+ (no additional packages needed)
- **SLURM**: Required for HPC/GPU execution (optional for local CPU runs)
- **Storage**: ~50 GB free space per subject
- **GPU**: NVIDIA GPU recommended for Step 4 (optional but 30x faster)

### Check Your System

```bash
# Check Python version
python3 --version  # Should be 3.7 or higher

# Check for Apptainer
apptainer --version
# OR
singularity --version

# Check for Docker (alternative)
docker --version

# Check for SLURM (if using HPC)
squeue --version

# Check for GPU (optional)
nvidia-smi
```

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/phindagijimana/TSC_Tuber_Segmentation-pipeline.git
cd TSC_Tuber_Segmentation-pipeline
```

### Step 2: Create Directory Structure

```bash
# Create required directories
mkdir -p preprocessing/raw_data
mkdir -p preprocessing/skull_stripped_MRIs
mkdir -p preprocessing/masks
mkdir -p preprocessing/combined_MRIs
mkdir -p preprocessing/preprocessed_MRIs
mkdir -p results
mkdir -p logs
```

Or use the provided script:
```bash
./scripts/setup_directories.sh
```

### Step 3: Prepare Your Data

#### Expected File Naming Convention

Your NIfTI files must follow this pattern:
- `{SubjectID}_T1_{descriptor}.nii` or `.nii.gz`
- `{SubjectID}_T2_{orientation}_{descriptor}.nii` (e.g., `T2_axial`, `T2_coronal`)
- `{SubjectID}_FLAIR_{orientation}_{descriptor}.nii`

**Examples:**
- `Case001_T1_mprage.nii.gz`
- `Case001_T2_axial_tse.nii`
- `Case001_T2_coronal_tse.nii`
- `Case001_FLAIR_axial_flair.nii.gz`

#### Organize Your Files

Place your NIfTI files in per-subject folders:

```
preprocessing/raw_data/
├── Case001/
│   ├── Case001_T1_mprage.nii.gz
│   ├── Case001_T2_axial_tse.nii
│   ├── Case001_T2_coronal_tse.nii (optional if you have multiple T2s)
│   └── Case001_FLAIR_axial_flair.nii.gz
├── Case002/
│   ├── Case002_T1_mprage.nii.gz
│   ├── Case002_T2_axial_tse.nii
│   └── Case002_FLAIR_axial_flair.nii.gz
└── Case003/
    └── ...
```

**Important Notes:**
- At minimum, you need: T1, T2, and FLAIR for each subject
- Multiple T2 sequences (axial + coronal) will be combined automatically
- Single T2 sequences will be used directly
- File extensions can be `.nii` or `.nii.gz`

### Step 4: Validate Setup (Optional but Recommended)

```bash
# Check directory structure
./scripts/validate_installation.sh

# Test container availability (on compute node if using SLURM)
sbatch scripts/test_docker_slurm.sh
# OR locally:
python3 scripts/test_docker.py
```

## Running the Pipeline

### Option 1: Full Pipeline with One Command (HPC + GPU)

```bash
./scripts/submit_gpu_job.sh
```

This will:
1. Submit a SLURM job requesting GPU resources
2. Run all 5 steps automatically (Step 0-4)
3. Process all subjects in `preprocessing/raw_data/`
4. Generate segmentations and volume quantifications

**Expected Runtime:**
- ~2-3 hours per subject (with GPU)
- ~4-6 hours per subject (CPU only)

### Option 2: Local Execution (No SLURM)

```bash
python3 scripts/run_pipeline.py
```

**Note:** This will use CPU only unless you manually configure GPU support.

### Option 3: Step-by-Step Execution

```bash
# Run only Step 1 (Skull stripping)
python3 scripts/run_pipeline.py --start-from 1

# Resume from Step 3 (MNI registration)
python3 scripts/run_pipeline.py --start-from 3

# Force re-run all steps
python3 scripts/run_pipeline.py --force
```

## Monitoring Progress

### Check Job Status (SLURM)

```bash
# Check if job is running
squeue -u $USER

# View job details
scontrol show job <JOB_ID>

# Monitor output in real-time
tail -f logs/slurm-<JOB_ID>.out

# Check for errors
tail -f logs/slurm-<JOB_ID>.err
```

### Check Outputs

```bash
# Check preprocessing outputs
ls -lh preprocessing/preprocessed_MRIs/Case001/

# Check segmentation results
ls -lh results/Case001/

# View tuber burden quantification
cat results/volume_results.txt
```

## Output Structure

After successful completion:

```
results/
├── Case001/
│   ├── Case001_CNN_predicted_segmentation_in_MNI_space_256x256x256.nii.gz
│   ├── Case001_T1_MRI_in_MNI_space_256x256x256.nii.gz
│   ├── Case001_T2_MRI_in_MNI_space_256x256x256.nii.gz
│   ├── Case001_FLAIR_MRI_in_MNI_space_256x256x256.nii.gz
│   └── volume_results.txt
├── Case002/
│   └── ...
└── volume_results.txt  # Aggregated results for all subjects
```

## Troubleshooting

### Container Issues

**Problem:** "Container not found" or "Permission denied"

**Solutions:**
```bash
# If using Apptainer, ensure you're on a compute node (not login node)
srun --pty bash

# Test container availability
apptainer exec docker://ivansanchezfernandez/skull_strip_and_create_masks_with_synthstrip echo "Container works"

# Clear container cache if needed
rm -rf ~/.apptainer/cache
```

### File Naming Issues

**Problem:** "No valid files found for subject"

**Solutions:**
```bash
# Check your file naming
ls preprocessing/raw_data/Case001/

# Files must contain: SubjectID_T1_, SubjectID_T2_, SubjectID_FLAIR_
# Examples:
#   Case001_T1_anything.nii  ← Good
#   case001_t1_anything.nii  ← Bad (case sensitive)
#   T1_Case001.nii           ← Bad (wrong order)
```

### Memory Issues

**Problem:** "No space left on device" during T2 combination

**Solution:**
The pipeline includes a workaround that uses the first T2 file instead of combining multiple T2s. This is automatically applied when NiftyMIC fails.

### GPU Issues

**Problem:** "GPU not detected" or "CUDA not available"

**Solutions:**
```bash
# Check GPU availability
nvidia-smi

# Verify SLURM GPU request
scontrol show job <JOB_ID> | grep GRES

# Run without GPU (slower but works)
python3 scripts/run_pipeline.py --no-gpu
```

## Advanced Configuration

### Custom Resource Requests

```bash
# Request specific GPU memory
./scripts/submit_gpu_job.sh --gpu-mem 24  # 24GB GPU

# Custom time limit
./scripts/submit_gpu_job.sh --time 08:00:00  # 8 hours

# More RAM
./scripts/submit_gpu_job.sh --mem 64  # 64GB RAM

# Different partition
./scripts/submit_gpu_job.sh --partition interactive
```

### Processing Specific Subjects

Currently, the pipeline processes all subjects in `preprocessing/raw_data/`. To process specific subjects:

```bash
# Method 1: Temporarily move other subjects out
mv preprocessing/raw_data/Case002 /tmp/
mv preprocessing/raw_data/Case003 /tmp/

# Run pipeline (will only process Case001)
./scripts/submit_gpu_job.sh

# Move subjects back
mv /tmp/Case002 preprocessing/raw_data/
mv /tmp/Case003 preprocessing/raw_data/
```

## Getting Help

### Check Logs

All steps produce detailed logs in the `logs/` directory:
- `logs/pipeline_YYYYMMDD_HHMMSS.log` - Main pipeline log
- `logs/1_skull_strip_YYYYMMDD_HHMMSS.log` - Step 1 log
- `logs/2_combine_t2_YYYYMMDD_HHMMSS.log` - Step 2 log
- `logs/3_register_to_mni_YYYYMMDD_HHMMSS.log` - Step 3 log
- `logs/4_segment_tubers_YYYYMMDD_HHMMSS.log` - Step 4 log

### Report Issues

When reporting issues, please include:
1. Your system information (`uname -a`)
2. Python version (`python3 --version`)
3. Container runtime (`apptainer --version` or `docker --version`)
4. Error message and full log file
5. Command you ran

Submit issues at: https://github.com/phindagijimana/TSC_Tuber_Segmentation-pipeline/issues

## Citation

If you use this pipeline, please cite:

> Sánchez Fernández I, et al. Convolutional neural networks for automatic tuber segmentation and quantification of tuber burden in patients with tuberous sclerosis complex. Epilepsia. 2025. DOI: 10.1111/epi.70007

## Next Steps

After successful pipeline execution:
1. Review `results/volume_results.txt` for tuber burden quantification
2. Visualize segmentations using ITK-SNAP or similar tools
3. Perform statistical analysis on volume results
4. Compare with clinical assessments

---

**Need help?** Check the [main README](README.md) and [implementation details](implementation.md).

