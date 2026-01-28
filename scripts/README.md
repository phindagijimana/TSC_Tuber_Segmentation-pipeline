# TSC Tuber Segmentation Pipeline - Scripts

This directory contains the Python-based pipeline scripts for automated tuber segmentation in Tuberous Sclerosis Complex (TSC) patients.

## Quick Start

### Full Pipeline (CPU)
```bash
python3 scripts/run_pipeline.py
```

### Full Pipeline (GPU - Recommended)
```bash
./scripts/submit_gpu_job.sh
```

---

## Scripts Overview

### Python Pipeline Scripts

| Script | Purpose | Type |
|--------|---------|------|
| `run_pipeline.py` | Main orchestrator | Python |
| `pipeline_utils.py` | Shared utilities | Python module |
| `0_prepare_data.py` | Organize input data | Python |
| `1_skull_strip.py` | Skull-stripping | Python |
| `2_combine_t2.py` | T2 combination | Python |
| `3_register_to_mni.py` | MNI registration | Python |
| `4_segment_tubers.py` | Tuber segmentation | Python |
| `test_docker.py` | Container testing | Python |

### Bash Helper Scripts

| Script | Purpose | Type |
|--------|---------|------|
| `submit_gpu_job.sh` | SLURM GPU job submission | Bash |
| `setup_directories.sh` | Create directory structure | Bash |
| `test_docker_slurm.sh` | Test containers on compute nodes | Bash |
| `validate_installation.sh` | Validate installation | Bash |

---

## Usage Examples

### 1. Run Full Pipeline on CPU
```bash
python3 scripts/run_pipeline.py
```
- Runs all 5 steps (0-4)
- Takes ~4-6 hours for 3 subjects
- Good for testing

### 2. Submit GPU Job (Production)
```bash
./scripts/submit_gpu_job.sh
```
- Runs all 5 steps with GPU acceleration (Step 4 only)
- Takes ~1.5-2 hours for 3 subjects
- Recommended for production

### 3. Resume from a Specific Step
```bash
python3 scripts/run_pipeline.py --start-from 3
```
- Skips steps 0-2, starts from step 3 (MNI registration)
- Useful when a step fails

### 4. Force Re-run All Steps
```bash
python3 scripts/run_pipeline.py --force
```
- Ignores existing outputs
- Re-runs all steps from scratch

### 5. Custom GPU Resources
```bash
./scripts/submit_gpu_job.sh --gpu-mem 24 --mem 64 --cpus 16 --time 08:00:00
```
- Request 24GB GPU, 64GB RAM, 16 CPUs, 8-hour limit
- Use for larger datasets

### 6. Dry Run (Preview Job Script)
```bash
./scripts/submit_gpu_job.sh --dry-run
```
- Shows the SLURM batch script without submitting
- Good for debugging

### 7. Run Individual Steps
```bash
# Run only skull stripping
python3 scripts/1_skull_strip.py

# Run only segmentation
python3 scripts/4_segment_tubers.py
```

---

## Pipeline Steps

### Step 0: Data Preparation
**Script**: `0_prepare_data.py`  
**Input**: `preprocessing/raw_data/{subject}/*.nii`  
**Output**: Validates and organizes files  
**Purpose**: Ensure files follow naming conventions

### Step 1: Skull Stripping
**Script**: `1_skull_strip.py`  
**Container**: `ivansanchezfernandez/skull_strip_and_create_masks_with_synthstrip`  
**Input**: `preprocessing/raw_data/{subject}/`  
**Output**: 
- `preprocessing/skull_stripped_MRIs/{subject}/` (brain-only)
- `preprocessing/masks/{subject}/` (brain masks)

**Time**: ~1-3 min/subject

### Step 2: T2 Combination
**Script**: `2_combine_t2.py`  
**Container**: `ivansanchezfernandez/combine_t2_files_with_niftymic`  
**Input**: 
- `preprocessing/skull_stripped_MRIs/{subject}/`
- `preprocessing/masks/{subject}/`

**Output**: `preprocessing/combined_MRIs/{subject}/`  
**Time**: ~10-30 min/subject (only for subjects with multiple T2s)  
**Note**: Uses first T2 as workaround if combination fails

### Step 3: MNI Registration
**Script**: `3_register_to_mni.py`  
**Container**: `ivansanchezfernandez/bias_correct_resample_and_register_to_mni_with_ants`  
**Input**: `preprocessing/combined_MRIs/{subject}/`  
**Output**: `preprocessing/preprocessed_MRIs/{subject}/`  
**Time**: ~10-30 min/subject

### Step 4: Tuber Segmentation
**Script**: `4_segment_tubers.py`  
**Container**: `ivansanchezfernandez/segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout`  
**Input**: `preprocessing/preprocessed_MRIs/{subject}/`  
**Output**: 
- `results/{subject}/` (segmentations)
- `results/volume_results.txt` (tuber burden)

**Time**: 
- CPU: ~5-15 min/subject
- GPU: ~54 seconds/subject

---

## Monitoring Jobs

### Check SLURM Job Status
```bash
squeue -u $USER
```

### View Live Output
```bash
tail -f logs/slurm-<JOB_ID>.out
```

### Check GPU Usage (if in interactive job)
```bash
nvidia-smi
```

### Cancel a Job
```bash
scancel <JOB_ID>
```

---

## Troubleshooting

### Container Not Available
```bash
# Check Apptainer/Singularity
apptainer --version

# Test container access
python3 scripts/test_docker.py

# Test on compute node
sbatch scripts/test_docker_slurm.sh
```

### Out of Memory
- Increase `--mem` in `submit_gpu_job.sh`
- Process subjects one at a time
- Check available system resources

### Step Failed
```bash
# Resume from failed step (e.g., step 2)
python3 scripts/run_pipeline.py --start-from 2

# Force re-run with more verbose output
python3 scripts/run_pipeline.py --start-from 2 --force
```

### Check Logs
All steps generate timestamped logs in `logs/`:
- `0_prepare_data_YYYYMMDD_HHMMSS.log`
- `1_skull_strip_YYYYMMDD_HHMMSS.log`
- `2_combine_t2_YYYYMMDD_HHMMSS.log`
- `3_register_to_mni_YYYYMMDD_HHMMSS.log`
- `4_segment_tubers_YYYYMMDD_HHMMSS.log`
- `pipeline_YYYYMMDD_HHMMSS.log` (orchestrator)
- `slurm-<JOB_ID>.out` (SLURM jobs)

---

## Requirements

### System
- Linux (tested on RHEL 8/9, Ubuntu 20.04+)
- Python 3.7+ (no external packages needed)
- Apptainer/Singularity OR Docker
- SLURM (for GPU jobs, optional)
- NVIDIA GPU + drivers (optional, for GPU acceleration)

### Input Data
- NIfTI format (`.nii` or `.nii.gz`)
- Naming convention: `{SubjectID}_{T1|T2|FLAIR}_*.nii`
- Required sequences per subject:
  - 1× T1 (axial or MPRAGE)
  - 1× T2 (axial recommended, or axial + coronal)
  - 1× FLAIR (axial recommended)

---

## Python Module: `pipeline_utils.py`

### Classes

- **`PipelineConfig`**: Configuration and path management
- **`PipelineLogger`**: Centralized logging with file and console output
- **`DockerManager`**: Container operations (Docker/Apptainer/Singularity)
- **`FileValidator`**: NIfTI file validation and naming checks
- **`Timer`**: Execution timing and performance tracking

### Functions

- `detect_gpu()`: Check GPU availability
- `discover_subjects()`: Find all subject directories

---

## Citations

If you use this pipeline, please cite:

1. **Main method**:  
   Sánchez Fernández et al., *Convolutional neural networks for automatic tuber segmentation and quantification of tuber burden in tuberous sclerosis complex.* Epilepsia 2025. DOI: 10.1111/epi.70007

2. **SynthStrip**:  
   Hoopes et al., *SynthStrip: Skull-Stripping for Any Brain Image.* Neuroimage 2022. PMID: 35842095

3. **NiftyMIC**:  
   Ebner et al., *An automated framework for localization, segmentation and super-resolution reconstruction of fetal brain MRI.* Neuroimage 2020. PMID: 31704293

4. **ANTs**:  
   Avants et al., *A reproducible evaluation of ANTs similarity metric performance in brain image registration.* Neuroimage 2011. PMID: 20851191

---

## Support

For issues or questions:
1. Check log files in `logs/`
2. Review [SETUP.md](../SETUP.md) for detailed setup instructions
3. Review [implementation.md](../implementation.md) for architecture details
4. Verify input data naming conventions
5. Ensure containers are accessible

---

**Author**: Tuber Pipeline Development Team  
**Date**: 2026-01-27  
**Version**: 2.0 (Python)
