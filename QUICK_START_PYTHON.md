# Quick Start Guide - Python Pipeline

## Prerequisites Check

```bash
# Check Python version (need 3.7+)
python3 --version

# Check Docker
docker --version
docker ps
```

## Basic Usage

### Run Full Pipeline (CPU)
```bash
cd /path/to/tuber_project
python3 scripts/run_pipeline.py
```

### Submit GPU Job (Recommended)
```bash
cd /path/to/tuber_project
./scripts/submit_gpu_job.sh
```

### Show Help
```bash
python3 scripts/run_pipeline.py --help
```

## Common Commands

### Resume from Step 3
```bash
python3 scripts/run_pipeline.py --start-from 3
```

### Force Re-run Everything
```bash
python3 scripts/run_pipeline.py --force
```

### Run Individual Step
```bash
python3 scripts/1_skull_strip.py
python3 scripts/4_segment_tubers.py
```

## File Structure

```
tuber_project/
├── TSC_MRI_SUB/              # Put your data here
│   ├── Case001/
│   │   ├── Case001_T1_.nii
│   │   ├── Case001_T2_axial.nii
│   │   └── Case001_FLAIR_axial.nii
│
├── scripts/
│   ├── pipeline_utils.py     # Shared utilities
│   ├── 0_prepare_data.py     # Step 0
│   ├── 1_skull_strip.py      # Step 1
│   ├── 2_combine_t2.py       # Step 2
│   ├── 3_register_to_mni.py  # Step 3
│   ├── 4_segment_tubers.py   # Step 4
│   └── run_pipeline.py       # Main orchestrator
│
├── results/                   # Results appear here
│   └── volume_results.txt    # Tuber burden
│
└── logs/                      # Logs appear here
```

## After Running

### Check Results
```bash
# View tuber burden
cat results/volume_results.txt

# List segmentation files
ls -lh results/Case001/
```

### Visualize with ITK-SNAP
```bash
itksnap -g results/Case001/Case001_T1_*.nii \
        -s results/Case001/*seg*.nii
```

### Check Logs
```bash
# View most recent pipeline log
ls -t logs/pipeline_*.log | head -1 | xargs less

# View step-specific log
ls -t logs/4_segment_tubers_*.log | head -1 | xargs less
```

## Troubleshooting

### Python Not Found
```bash
# Use python3 explicitly
python3 scripts/run_pipeline.py

# Or check PATH
which python3
```

### Docker Permission Denied
```bash
# Add user to docker group (requires admin)
sudo usermod -aG docker $USER
# Then log out and back in
```

### Step Failed
```bash
# Check the log file
ls -t logs/*.log | head -1 | xargs tail -50

# Resume from failed step (e.g., step 2)
python3 scripts/run_pipeline.py --start-from 2
```

## Monitoring SLURM Jobs

### Check Job Status
```bash
squeue -u $USER
```

### View Job Output
```bash
# Find your job ID
squeue -u $USER

# Watch output
tail -f logs/slurm-<JOB_ID>.out
```

### Cancel Job
```bash
scancel <JOB_ID>
```

## Key Differences from Bash Version

| Task | Bash (Old) | Python (New) |
|------|-----------|--------------|
| Run pipeline | `./scripts/run_pipeline.sh` | `python3 scripts/run_pipeline.py` |
| Help | `./scripts/run_pipeline.sh --help` | `python3 scripts/run_pipeline.py --help` |
| Individual step | `./scripts/1_skull_strip.sh` | `python3 scripts/1_skull_strip.py` |

> **Bash scripts are deprecated but still work for backward compatibility.**

## Next Steps

1. **Test**: `python3 scripts/run_pipeline.py --help`
2. **Run**: `python3 scripts/run_pipeline.py`
3. **Review**: Check `results/volume_results.txt`
4. **Visualize**: Use ITK-SNAP to view segmentations

## Documentation

- **Full README**: `README.md`
- **Migration Guide**: `PYTHON_MIGRATION.md`
- **Implementation Details**: `implementation.md`
- **Rewrite Summary**: `PYTHON_REWRITE_SUMMARY.md`

---

**Version**: 2.0 (Python)  
**Last Updated**: 2026-01-27



