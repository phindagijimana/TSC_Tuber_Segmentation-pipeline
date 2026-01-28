# Container Compatibility Fixes

## Issues Discovered and Resolved

### 1. Working Directory Issue with Apptainer

**Problem**: All Docker containers from `ivansanchezfernandez` have entrypoints that use relative paths (e.g., `./iterative_loop.sh`), expecting to run from the `/app` directory inside the container.

When Apptainer runs these containers, it automatically binds the current working directory from the host, changing the container's working directory. This causes the entrypoint scripts to fail with:
```
FATAL: stat /mnt/nfs/home/urmc-sh.rochester.edu/pndagiji/Documents/tuber_project/iterative_loop.sh: no such file or directory
```

**Solution**: Added `workdir="/app"` parameter to all `docker_manager.run_container()` calls. This sets the working directory inside the container to `/app` using:
- Docker: `-w /app` flag
- Apptainer: `--pwd /app` flag

**Files Modified**:
- `scripts/pipeline_utils.py` - Added `workdir` parameter to `DockerManager.run_container()` method
- `scripts/1_skull_strip.py` - Added `workdir="/app"` to container call
- `scripts/2_combine_t2.py` - Added `workdir="/app"` to container call
- `scripts/3_register_to_mni.py` - Added `workdir="/app"` to container call
- `scripts/4_segment_tubers.py` - Added `workdir="/app"` to container call

### 2. Docker Image Name Case Sensitivity

**Problem**: The preprocessing instructions PDF specifies the ANTs container as:
```
ivansanchezfernandez/bias_correct_resample_and_register_to_MNI_with_ants
```

However, Docker Hub repositories must be lowercase. Apptainer strictly enforces this when pulling from Docker Hub, causing:
```
FATAL: invalid reference format: repository name must be lowercase
```

**Solution**: Corrected the image name to lowercase:
```
ivansanchezfernandez/bias_correct_resample_and_register_to_mni_with_ants
```

**Files Modified**:
- `scripts/3_register_to_mni.py` - Changed `MNI` to `mni` in DOCKER_IMAGE constant
- `scripts/3_register_to_mni.sh` - Changed `MNI` to `mni` in DOCKER_IMAGE variable
- `scripts/test_docker.py` - Changed `MNI` to `mni` in DOCKER_IMAGES dictionary

## Container Details

Containers from `ivansanchezfernandez` have different directory structures:

### Verified Containers

| Step | Container | Workdir | Script Location | Status |
|------|-----------|---------|-----------------|--------|
| 1 | `skull_strip_and_create_masks_with_synthstrip` | (default) | N/A | ✅ Fixed |
| 2 | `combine_t2_files_with_niftymic` | `/app` | `/app/iterative_loop.sh` | ✅ Fixed |
| 3 | `bias_correct_resample_and_register_to_mni_with_ants` | `/` | `/iterative_loop.sh` | ✅ Fixed |
| 4 | `segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout` | (default) | N/A | ✅ Fixed |

**Notes**:
- Only containers with `iterative_loop.sh` entrypoints need explicit working directories
- Step 2 (NiftyMIC): Uses `/app` directory
- Step 3 (ANTs): Uses root `/` directory  
- Steps 1 & 4: Use default working directory (no change needed)

## Testing

To verify all containers work correctly:
```bash
./scripts/test_docker_slurm.sh --all
```

This will submit a SLURM job to test all 4 containers on a compute node with Apptainer.

## References

- **Apptainer Documentation**: https://apptainer.org/docs/
- **Docker Hub**: https://hub.docker.com/u/ivansanchezfernandez
- **Original Paper**: Epilepsia 2025 - Sánchez Fernández et al.

