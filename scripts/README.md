# TSC Tuber Segmentation Pipeline - Scripts

This directory contains the modular pipeline scripts for automated tuber segmentation in Tuberous Sclerosis Complex (TSC) patients.

## Quick Start

### Full Pipeline (CPU)
```bash
./run_pipeline.sh
```

### Full Pipeline (GPU - Recommended)
```bash
./submit_gpu_job.sh
```

---

## Scripts Overview

| Script | Purpose | Execution Mode |
|--------|---------|----------------|
| `run_pipeline.sh` | Main orchestrator (CPU) | Interactive |
| `submit_gpu_job.sh` | GPU job submission | SLURM batch |
| `0_prepare_data.sh` | Organize input data | Called by orchestrator |
| `1_skull_strip.sh` | Skull-stripping | Called by orchestrator |
| `2_combine_t2.sh` | T2 combination | Called by orchestrator |
| `3_register_to_mni.sh` | MNI registration | Called by orchestrator |
| `4_segment_tubers.sh` | Tuber segmentation | Called by orchestrator |

---

## Usage Examples

### 1. Run Full Pipeline on CPU
```bash
./run_pipeline.sh
```
- Runs all 5 steps (0-4)
- Takes ~2-3 hours for 3 subjects
- Good for testing

### 2. Submit GPU Job (Production)
```bash
./submit_gpu_job.sh
```
- Runs all 5 steps with GPU acceleration (Step 4 only)
- Takes ~1.5-2 hours for 3 subjects
- Recommended for production

### 3. Resume from a Specific Step
```bash
./run_pipeline.sh --start-from 3
```
- Skips steps 0-2, starts from step 3 (MNI registration)
- Useful when a step fails

### 4. Force Re-run All Steps
```bash
./run_pipeline.sh --force
```
- Ignores existing outputs
- Re-runs all steps from scratch

### 5. Custom GPU Resources
```bash
./submit_gpu_job.sh --gpu-mem 24 --mem 64 --cpus 16 --time 08:00:00
```
- Request 24GB GPU, 64GB RAM, 16 CPUs, 8-hour limit
- Use for larger datasets

### 6. Dry Run (Preview Job Script)
```bash
./submit_gpu_job.sh --dry-run
```
- Shows the SLURM batch script without submitting
- Good for debugging

---

## Pipeline Steps

### Step 0: Data Preparation
**Script**: `0_prepare_data.sh`  
**Input**: `TSC_MRI_SUB/{subject}/*.nii`  
**Output**: `preprocessing/MRI_files/{subject}/*.nii`  
**Purpose**: Organize raw data into per-subject folders with validation

### Step 1: Skull Stripping
**Script**: `1_skull_strip.sh`  
**Docker**: `ivansanchezfernandez/skull_strip_and_create_masks_with_synthstrip`  
**Input**: `preprocessing/MRI_files/{subject}/`  
**Output**: 
- `preprocessing/skull_stripped_MRIs/{subject}/` (brain-only)
- `preprocessing/masks/{subject}/` (brain masks)

**Time**: ~1-3 min/subject

### Step 2: T2 Combination
**Script**: `2_combine_t2.sh`  
**Docker**: `ivansanchezfernandez/combine_t2_files_with_niftymic`  
**Input**: 
- `preprocessing/skull_stripped_MRIs/{subject}/`
- `preprocessing/masks/{subject}/`

**Output**: `preprocessing/combined_MRIs/{subject}/`  
**Time**: ~10-30 min/subject (only for subjects with multiple T2s)

### Step 3: MNI Registration
**Script**: `3_register_to_mni.sh`  
**Docker**: `ivansanchezfernandez/bias_correct_resample_and_register_to_MNI_with_ants`  
**Input**: `preprocessing/combined_MRIs/{subject}/`  
**Output**: `preprocessing/preprocessed_MRIs/{subject}/`  
**Time**: ~10-30 min/subject

### Step 4: Tuber Segmentation
**Script**: `4_segment_tubers.sh`  
**Docker**: `ivansanchezfernandez/segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout`  
**Input**: `preprocessing/preprocessed_MRIs/{subject}/`  
**Output**: 
- `results/{subject}/` (segmentations)
- `results/volume_results.txt` (tuber burden)

**Time**: 
- CPU: ~5-15 min/subject
- GPU: ~1-2 min/subject

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

### Docker Not Running
```bash
# Check Docker status
docker ps

# If not running, start Docker daemon (requires admin)
sudo systemctl start docker
```

### Out of Memory
- Increase `--mem` in `submit_gpu_job.sh`
- Process subjects one at a time

### Step Failed
```bash
# Resume from failed step (e.g., step 2)
./run_pipeline.sh --start-from 2
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
- Linux (tested on CentOS/RHEL 9)
- Docker 5.0+
- SLURM (for GPU jobs)
- NVIDIA GPU + drivers (for GPU acceleration)

### Input Data
- NIfTI format (`.nii` or `.nii.gz`)
- Naming convention: `{SubjectID}_{T1|T2|FLAIR}_*.nii`
- Required sequences per subject:
  - 1× T1 (axial or MPRAGE)
  - 1× T2 (axial recommended, or axial + coronal)
  - 1× FLAIR (axial recommended)

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
2. Review `implementation.md` for detailed documentation
3. Verify input data naming conventions
4. Ensure Docker images are properly pulled

---

**Author**: Tuber Pipeline Development Team  
**Date**: 2026-01-27  
**Version**: 1.0



