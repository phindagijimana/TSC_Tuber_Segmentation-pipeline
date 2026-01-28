# TSC Tuber Segmentation Pipeline - Implementation Plan

## Overview
This document outlines the complete implementation of an automated pipeline for preprocessing MRI data and segmenting tubers in Tuberous Sclerosis Complex (TSC) patients.

**Input**: Raw NIfTI files in `TSC_MRI_SUB/`  
**Output**: Tuber segmentations + quantified tuber burden in `results/`

---

## Pipeline Architecture

The pipeline consists of **4 Docker-based steps** that run sequentially:

```
Input NIfTI (TSC_MRI_SUB/)
    ↓
[1] Skull-strip + Mask Creation (SynthStrip)
    ↓
[2] T2 Combination (NiftyMIC) [conditional]
    ↓
[3] Bias-correction + Resampling + MNI Registration (ANTs)
    ↓
[4] Tuber Segmentation + Burden Quantification (TSCCNN3D)
    ↓
Final Output (results/)
```

---

## Directory Structure

```
tuber_project/
├── TSC_MRI_SUB/                          # Input: Raw NIfTI files
│   ├── Case001/
│   │   ├── Case001_T1_.nii
│   │   ├── Case001_T2_axial.nii
│   │   ├── Case001_T2_coronal.nii
│   │   └── Case001_FLAIR_axial.nii
│   ├── Case002/
│   └── Case003/
├── scripts/                               # Pipeline scripts
│   ├── run_pipeline.sh                   # Main orchestrator (CPU)
│   ├── submit_gpu_job.sh                 # SLURM GPU job submission
│   ├── 0_prepare_data.sh                 # Data preparation
│   ├── 1_skull_strip.sh                  # Skull-stripping step
│   ├── 2_combine_t2.sh                   # T2 combination step
│   ├── 3_register_to_mni.sh              # Registration step
│   └── 4_segment_tubers.sh               # Segmentation step
├── preprocessing/                         # Working directories (per-subject)
│   ├── MRI_files/
│   │   ├── Case001/                      # Subject-specific input
│   │   ├── Case002/
│   │   └── Case003/
│   ├── skull_stripped_MRIs/              # Step 1 output
│   │   ├── Case001/
│   │   ├── Case002/
│   │   └── Case003/
│   ├── masks/                            # Step 1 output (brain masks)
│   │   ├── Case001/
│   │   ├── Case002/
│   │   └── Case003/
│   ├── combined_MRIs/                    # Step 2 output (T2 combined)
│   │   ├── Case001/
│   │   ├── Case002/
│   │   └── Case003/
│   └── preprocessed_MRIs/                # Step 3 output (final preprocessing)
│       ├── Case001/
│       ├── Case002/
│       └── Case003/
├── results/                               # Step 4 output (segmentations + burden)
│   ├── Case001/
│   ├── Case002/
│   ├── Case003/
│   └── volume_results.txt                # Aggregated tuber burden results
└── logs/                                  # Pipeline execution logs
```

---

## Step-by-Step Implementation

### Step 0: Data Preparation

**Goal**: Organize input data into per-subject preprocessing folders.

**Actions**:
1. Detect all subject directories in `TSC_MRI_SUB/`
2. For each subject:
   - Create `preprocessing/MRI_files/{subject}/`
   - Copy all `.nii` files from `TSC_MRI_SUB/{subject}/` → `preprocessing/MRI_files/{subject}/`
3. Verify file naming conventions for each subject:
   - Patient ID + underscore at start (e.g., `Case001_`)
   - Sequence token: `_T1_`, `_T2_`, `_FLAIR_`
4. Validate that each subject has at minimum:
   - One T1 sequence
   - One T2 sequence
   - One FLAIR sequence

**Output**:
```
preprocessing/MRI_files/
  Case001/
    Case001_T1_.nii
    Case001_T2_axial.nii
    Case001_T2_coronal.nii
    Case001_FLAIR_axial.nii
  Case002/
    Case002_T1_.nii
    Case002_T2_axial.nii
    Case002_FLAIR_axial.nii
    Case002_FLAIR_coronal.nii
  Case003/
    Case003_T1_.nii
    Case003_T2_axial.nii
    Case003_FLAIR_.nii
```

**Note**: Per-subject organization allows:
- Cleaner output tracking
- Easy identification of failed subjects
- Individual subject reprocessing
- Parallel processing (future enhancement)

---

### Step 1: Skull-Stripping + Mask Creation

**Tool**: SynthStrip (Freesurfer)  
**Docker Image**: `ivansanchezfernandez/skull_strip_and_create_masks_with_synthstrip`

**Goal**: Remove non-brain tissue (skull, CSF, etc.) and generate brain masks.

**Actions**:
1. Pull Docker image:
   ```bash
   docker pull ivansanchezfernandez/skull_strip_and_create_masks_with_synthstrip
   ```

2. Create output directories:
   ```bash
   mkdir -p preprocessing/skull_stripped_MRIs
   mkdir -p preprocessing/masks
   ```

3. Run container:
   ```bash
   docker run --rm \
     -v /full/path/to/preprocessing/MRI_files:/input \
     -v /full/path/to/preprocessing/skull_stripped_MRIs:/output \
     -v /full/path/to/preprocessing/masks:/masks \
     ivansanchezfernandez/skull_strip_and_create_masks_with_synthstrip
   ```

**Inputs**:
- `/input` → `preprocessing/MRI_files/`

**Outputs**:
- `/output` → `preprocessing/skull_stripped_MRIs/` (brain-only NIfTI)
- `/masks` → `preprocessing/masks/` (binary brain masks)

**Expected Output**:
- One skull-stripped NIfTI per input file
- One mask NIfTI per input file

**Citation**: Hoopes et al., *SynthStrip: Skull-Stripping for Any Brain Image.* Neuroimage 2022.

---

### Step 2: T2 Combination (Conditional)

**Tool**: NiftyMIC  
**Docker Image**: `ivansanchezfernandez/combine_t2_files_with_niftymic`

**Goal**: Combine axial + coronal T2 sequences for improved 3D resolution.

**Conditional Logic**:
- Run only for patients with **both** `_T2_axial` and `_T2_coronal` files.
- For patients with only one T2, copy files directly to output.
- In our dataset: Case001 has both; Case002 and Case003 have only axial.

**Actions**:
1. Pull Docker image:
   ```bash
   docker pull ivansanchezfernandez/combine_t2_files_with_niftymic
   ```

2. Create output directory:
   ```bash
   mkdir -p preprocessing/combined_MRIs
   ```

3. Run container:
   ```bash
   docker run --rm \
     -v /full/path/to/preprocessing/skull_stripped_MRIs:/input \
     -v /full/path/to/preprocessing/masks:/masks \
     -v /full/path/to/preprocessing/combined_MRIs:/output \
     ivansanchezfernandez/combine_t2_files_with_niftymic
   ```

**Inputs**:
- `/input` → `preprocessing/skull_stripped_MRIs/`
- `/masks` → `preprocessing/masks/`

**Outputs**:
- `/output` → `preprocessing/combined_MRIs/`
  - Combined T2 files (for patients with both axial/coronal)
  - Copies of T1/FLAIR files (unchanged)
  - Single T2 files (for patients with only one T2)

**Expected Output**:
- Each patient has exactly one T1, one T2, one FLAIR in output folder.

**Citation**: Ebner et al., *An automated framework for localization, segmentation and super-resolution reconstruction of fetal brain MRI.* Neuroimage 2020.

**Note**: This step is computationally intensive and may take significant time per patient.

---

### Step 3: Bias-Correction + Resampling + MNI Registration

**Tool**: ANTs (Advanced Normalization Tools)  
**Docker Image**: `ivansanchezfernandez/bias_correct_resample_and_register_to_MNI_with_ants`

**Goal**: 
- Correct magnetic field bias artifacts
- Resample all images to 1mm³ isotropic voxels
- Register to MNI152 2009c template space

**Actions**:
1. Pull Docker image:
   ```bash
   docker pull ivansanchezfernandez/bias_correct_resample_and_register_to_MNI_with_ants
   ```

2. Create output directory:
   ```bash
   mkdir -p preprocessing/preprocessed_MRIs
   ```

3. Run container:
   ```bash
   docker run --rm \
     -v /full/path/to/preprocessing/combined_MRIs:/input \
     -v /full/path/to/preprocessing/preprocessed_MRIs:/output \
     ivansanchezfernandez/bias_correct_resample_and_register_to_MNI_with_ants
   ```

**Inputs**:
- `/input` → `preprocessing/combined_MRIs/`

**Outputs**:
- `/output` → `preprocessing/preprocessed_MRIs/` (final preprocessed NIfTI files)

**Expected Output**:
- All images in MNI152 space
- Standardized 1mm³ resolution
- Bias-field corrected
- Ready for CNN segmentation

**Citation**: Avants et al., *A reproducible evaluation of ANTs similarity metric performance in brain image registration.* Neuroimage 2011.

**Note**: This step is computationally intensive and may take significant time per patient.

---

### Step 4: Tuber Segmentation + Burden Quantification

**Tool**: TSCCNN3D_dropout  
**Docker Image**: `ivansanchezfernandez/segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout`

**Goal**: Automatically segment tubers and quantify tuber burden (volume).

**Actions**:
1. Pull Docker image:
   ```bash
   docker pull ivansanchezfernandez/segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout
   ```

2. Create output directory:
   ```bash
   mkdir -p results
   ```

3. Run container:
   ```bash
   docker run --rm \
     -v /full/path/to/preprocessing/preprocessed_MRIs:/input \
     -v /full/path/to/results:/output \
     ivansanchezfernandez/segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout
   ```

**Inputs**:
- `/input` → `preprocessing/preprocessed_MRIs/`

**Outputs** (written to `results/`):
- Preprocessed MRIs resampled to 256×256×256
- Segmentation NIfTI files (tuber masks)
- `volume_results.txt` (tuber burden quantification per patient)

**Expected Output** (`volume_results.txt`):
```
Patient_ID    Total_Tuber_Volume_mm3    Tuber_Count
Case001       12345.67                  15
Case002       8901.23                   12
Case003       5432.10                   8
```

**Citation**: Sánchez Fernández et al., *Convolutional neural networks for automatic tuber segmentation and quantification of tuber burden in tuberous sclerosis complex.* Epilepsia 2025.

**Note**: This step is computationally intensive and may take significant time per patient.

---

## Implementation Strategy

### Script Structure: Hybrid Modular Approach (Recommended)

**Architecture**: Main orchestrator + modular step scripts

This combines the best of both worlds:
- **Modular scripts**: Each step is independently testable and reusable
- **Main orchestrator**: One-command execution for full pipeline
- **Separation of concerns**: Each script has a single responsibility
- **Easy debugging**: Run individual steps without re-executing the entire pipeline
- **Production-ready**: Standard pattern in bioinformatics workflows

### File Structure

```
tuber_project/
├── scripts/
│   ├── run_pipeline.sh              # Main orchestrator (what users run)
│   ├── submit_gpu_job.sh            # SLURM GPU job submission wrapper
│   ├── 0_prepare_data.sh            # Step 0: Flatten input data
│   ├── 1_skull_strip.sh             # Step 1: Skull-stripping
│   ├── 2_combine_t2.sh              # Step 2: T2 combination
│   ├── 3_register_to_mni.sh         # Step 3: Bias-correct + register
│   └── 4_segment_tubers.sh          # Step 4: Segmentation (GPU-accelerated)
└── logs/                             # Execution logs (timestamped)
```

### Usage

**Full pipeline on CPU (interactive mode)**:
```bash
./scripts/run_pipeline.sh
```

**Full pipeline with GPU (SLURM job submission)**:
```bash
./scripts/submit_gpu_job.sh
```

**Individual steps (for debugging/resuming)**:
```bash
./scripts/1_skull_strip.sh          # Run only skull-stripping
./scripts/3_register_to_mni.sh      # Resume from registration step
```

### Execution Modes

#### Mode 1: Interactive CPU Execution
- Run directly on login node or interactive session
- Uses CPU only for all steps
- Good for: small datasets (≤5 subjects), testing, debugging
- Runtime: ~2-3 hours for 3 subjects

#### Mode 2: GPU Job Submission (Recommended)
- Submit as SLURM batch job to GPU partition
- Steps 1-3 run on CPU, Step 4 uses GPU
- Good for: production runs, larger datasets (>5 subjects)
- Runtime: ~1.5-2 hours for 3 subjects (20-30% faster)
- Benefits:
  - Dedicated compute resources
  - No interference with login node
  - Can run overnight
  - Automatic logging

### SLURM GPU Configuration

**Available Resources** (URMC-SH cluster):
- GPU Type: NVIDIA L40S
- Memory options: 6GB, 12GB, 24GB
- Partitions: `general` (7-day limit), `interactive` (12-hour limit)

**Recommended GPU Request** for this pipeline:
- GPU: 1× L40S with 12GB VRAM
- CPUs: 4-8 cores
- RAM: 32GB
- Time: 4 hours (conservative for 3 subjects)
- Partition: `general`

### Main Orchestrator Features

The `run_pipeline.sh` script will:

1. **Path Configuration**
   - Define base directory at top
   - All paths derived from base directory
   - Export paths as environment variables for step scripts

2. **Pre-flight Checks**
   - Verify Docker is installed and running
   - Check input file naming conventions
   - Validate expected sequences per patient
   - Report any issues before starting

3. **Docker Image Pull Phase**
   - Pull all 4 images before starting
   - Check if images already exist (skip re-pull)
   - Display pull progress

4. **Sequential Step Execution**
   - Call each step script in order
   - Check exit codes after each step
   - Fail fast with clear error messages

5. **Checkpointing**
   - Skip steps if output directories already contain expected files
   - Allow `--force` flag to re-run steps
   - Display skip/run decisions

6. **Logging**
   - Timestamp all operations
   - Log to `logs/pipeline_YYYYMMDD_HHMMSS.log`
   - Capture both stdout and stderr
   - Display real-time progress to terminal

7. **Progress Reporting**
   - Display current step and elapsed time
   - Show which patient is being processed
   - Report completion status

8. **Cleanup Options**
   - `--clean-intermediate` flag to delete intermediate directories
   - Keep only `preprocessed_MRIs/` and `results/`

### Individual Step Script Features

Each step script (`1_skull_strip.sh`, `2_combine_t2.sh`, etc.) will:

1. **Standalone Execution**
   - Can be run independently
   - Validates own inputs exist
   - Creates own output directories

2. **Clear Input/Output**
   - Documents expected input directory
   - Documents output directory
   - Validates file counts

3. **Error Handling**
   - Exits with non-zero code on failure
   - Prints clear error messages
   - Validates Docker container execution

4. **Idempotent**
   - Safe to re-run (won't duplicate work)
   - Checks if outputs already exist

### Benefits of This Approach

1. **Development**: Easy to test one step at a time
2. **Debugging**: Identify which step fails without re-running everything
3. **Flexibility**: Users can run individual steps with custom parameters
4. **Maintenance**: Update one step without touching others
5. **Resume**: If pipeline fails at step 3, restart from step 3
6. **Reusability**: Use `1_skull_strip.sh` for other projects
7. **User-friendly**: Still provides one-command execution via orchestrator

---

### GPU Job Submission Script

The `submit_gpu_job.sh` script will:

1. **Generate SLURM batch script** with appropriate headers:
   ```bash
   #SBATCH --job-name=tuber_pipeline
   #SBATCH --partition=general
   #SBATCH --gres=gpu:l40s.12g:1
   #SBATCH --cpus-per-task=8
   #SBATCH --mem=32G
   #SBATCH --time=04:00:00
   #SBATCH --output=logs/slurm-%j.out
   #SBATCH --error=logs/slurm-%j.err
   ```

2. **Load required modules** (if needed):
   - Docker/Singularity
   - CUDA drivers

3. **Execute pipeline** with GPU passthrough:
   - Steps 1-3: Run on CPU (no GPU needed)
   - Step 4: Pass `--gpus all` flag to Docker
   ```bash
   docker run --rm --gpus all \
     -v /path/to/input:/input \
     -v /path/to/output:/output \
     ivansanchezfernandez/segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout
   ```

4. **Monitor and report**:
   - Track job ID
   - Display `squeue` status
   - Show log file paths

5. **Post-job validation**:
   - Check exit codes
   - Verify output files exist
   - Email notification (optional)

---

## Validation & Quality Control

### After Each Step

1. **File Count Check**: Expected output file count = input file count
2. **Visual Inspection**: Use ITK-SNAP to spot-check a few cases

### After Complete Pipeline

1. **Open `volume_results.txt`** and verify tuber burden for each case
2. **Visualize segmentations in ITK-SNAP**:
   ```bash
   # Load T1/T2/FLAIR + segmentation overlay
   itksnap -g results/Case001_T1_*.nii -o results/Case001_*segmentation*.nii
   ```

---

## Expected Runtime

### CPU-Only Execution

**Per Patient** (4-core CPU):
- Step 1 (Skull-strip): ~1-3 minutes
- Step 2 (T2 combine): ~10-30 minutes (if applicable)
- Step 3 (ANTs registration): ~10-30 minutes
- Step 4 (Segmentation): ~5-15 minutes

**Total for 3 patients**: ~2-3 hours

### GPU-Accelerated Execution

**Per Patient** (CPU + L40S GPU):
- Step 1 (Skull-strip): ~1-3 minutes (CPU)
- Step 2 (T2 combine): ~10-30 minutes (CPU, if applicable)
- Step 3 (ANTs registration): ~10-30 minutes (CPU)
- Step 4 (Segmentation): ~1-2 minutes (GPU)

**Total for 3 patients**: ~1.5-2 hours

**GPU Speedup**: 20-30% faster overall (Step 4 is 5-10× faster)

---

## Error Handling

### Common Issues

1. **Docker permission errors**
   - Solution: Add user to `docker` group or use `sudo`

2. **Out of memory**
   - Solution: Process one patient at a time, increase Docker memory limit

3. **Missing sequences**
   - Solution: Script should detect and report before starting

4. **File naming violations**
   - Solution: Pre-flight check in Step 0

---

## Citations

If you use this pipeline, cite:
1. Sánchez Fernández et al., *Epilepsia* 2025 (main method)
2. Hoopes et al., *Neuroimage* 2022 (SynthStrip)
3. Ebner et al., *Neuroimage* 2020 (NiftyMIC)
4. Avants et al., *Neuroimage* 2011 (ANTs)

---

## Next Steps

1. **Create modular pipeline scripts** based on this implementation plan:
   - Main orchestrator: `run_pipeline.sh`
   - GPU job submission: `submit_gpu_job.sh`
   - Step scripts: `0_prepare_data.sh`, `1_skull_strip.sh`, `2_combine_t2.sh`, `3_register_to_mni.sh`, `4_segment_tubers.sh`
2. **Test individual steps** on one patient (Case001) first on CPU
3. **Validate outputs** at each step using file counts and ITK-SNAP
4. **Run full pipeline** via `run_pipeline.sh` (CPU) after successful step tests
5. **Submit GPU job** via `submit_gpu_job.sh` for production runs
6. **Run full cohort** (all 3 cases) with GPU acceleration
7. **Archive intermediate outputs** for reproducibility

