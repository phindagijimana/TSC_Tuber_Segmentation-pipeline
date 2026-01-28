# TSC Tuber Segmentation Pipeline

An automated pipeline for preprocessing MRI data and segmenting tubers in Tuberous Sclerosis Complex (TSC) patients using deep learning.

## Overview

This pipeline processes T1, T2, and FLAIR MRI sequences through multiple preprocessing steps and applies a convolutional neural network (TSCCNN3D_dropout) for automated tuber segmentation and burden quantification.

## Pipeline Steps

1. **Data Preparation**: Organize NIfTI files into per-subject folders
2. **Skull Stripping**: Remove non-brain tissue using SynthStrip
3. **T2 Combination**: Combine multiple T2 sequences using NiftyMIC (if applicable)
4. **MNI Registration**: Bias correction, resampling, and registration to MNI space using ANTs
5. **Tuber Segmentation**: CNN-based segmentation and regional quantification

## Features

- **Fully Automated**: End-to-end processing from raw NIfTI to segmentation results
- **GPU Accelerated**: Leverages NVIDIA GPUs for fast segmentation (~54s per subject)
- **HPC Ready**: SLURM job submission with resource management
- **Container-Based**: Uses Apptainer/Docker containers for reproducibility
- **Per-Subject Processing**: Organized output with detailed logging
- **Checkpointing**: Resume from any step if interrupted
- **Regional Quantification**: Detailed tuber burden by brain lobe

## Requirements

### System Requirements
- Linux operating system
- Apptainer (Singularity) or Docker
- Python 3.6+
- SLURM workload manager (for HPC execution)
- NVIDIA GPU (optional, but recommended for Step 4)

### Container Images
All preprocessing and segmentation tools run in containers:
- `ivansanchezfernandez/skull_strip_and_create_masks_with_synthstrip`
- `ivansanchezfernandez/combine_t2_files_with_niftymic`
- `ivansanchezfernandez/bias_correct_resample_and_register_to_mni_with_ants`
- `ivansanchezfernandez/segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout`

## Installation

```bash
# Clone the repository
git clone https://github.com/phindagijimana/TSC_Tuber_Segmentation-pipeline.git
cd TSC_Tuber_Segmentation-pipeline

# Create required directories
./scripts/setup_directories.sh

# No Python dependencies required (uses standard library only)
```

For detailed setup instructions, see [SETUP.md](SETUP.md).

## Quick Start

### 1. Prepare Your Data

Organize your NIfTI files in the following structure:

```
preprocessing/raw_data/
├── Case001/
│   ├── Case001_T1_*.nii
│   ├── Case001_T2_axial*.nii
│   ├── Case001_T2_coronal*.nii (optional)
│   └── Case001_FLAIR_axial*.nii
├── Case002/
│   └── ...
└── Case003/
    └── ...
```

### 2. Run the Pipeline

**On HPC with GPU (recommended):**
```bash
./scripts/submit_gpu_job.sh
```

**Local execution (CPU only):**
```bash
python3 scripts/run_pipeline.py
```

### 3. Resume from a Specific Step

```bash
# Resume from Step 3 (MNI registration)
./scripts/submit_gpu_job.sh --start-from 3

# Force re-run all steps
./scripts/submit_gpu_job.sh --force
```

## Output Structure

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

## Performance

- **Skull Stripping**: ~2-3 minutes per subject
- **T2 Combination**: ~10-30 minutes per subject (if multiple T2s)
- **MNI Registration**: ~1.5 hours per subject
- **Segmentation (GPU)**: ~54 seconds per subject
- **Segmentation (CPU)**: ~5-15 minutes per subject

**Total pipeline time**: ~2-3 hours per subject (with GPU)

## Advanced Usage

### Custom Resource Requests

```bash
# Request 24GB GPU and 64GB RAM
./scripts/submit_gpu_job.sh --gpu-mem 24 --mem 64

# Custom time limit
./scripts/submit_gpu_job.sh --time 08:00:00
```

### Testing Container Availability

```bash
# Test on compute node
sbatch scripts/test_docker_slurm.sh

# Test locally
python3 scripts/test_docker.py
```

## Documentation

- [Complete Setup Guide](SETUP.md) - Start here!
- [Quick Start Guide](QUICK_START_PYTHON.md)
- [Implementation Details](implementation.md)
- [Python Migration Notes](PYTHON_MIGRATION.md)
- [Container Fixes](CONTAINER_FIXES.md)

## File Naming Conventions

The pipeline expects NIfTI files to follow this naming convention:
- `{SubjectID}_T1_*.nii` or `{SubjectID}_T1_*.nii.gz`
- `{SubjectID}_T2_{orientation}*.nii` (e.g., `T2_axial`, `T2_coronal`)
- `{SubjectID}_FLAIR_{orientation}*.nii`

## Citation

If you use this pipeline in your research, please cite:

> Sánchez Fernández I, et al. *Convolutional neural networks for automatic tuber segmentation and quantification of tuber burden in patients with tuberous sclerosis complex*. Epilepsia. 2025. DOI: 10.1111/epi.70007

## License

This pipeline is provided as-is for research purposes. Please refer to individual container licenses for underlying tools.

## Authors

Developed by the Tuber Pipeline Development Team.

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Note**: This pipeline processes sensitive medical imaging data. Ensure compliance with your institution's data protection policies and obtain necessary approvals before use.
