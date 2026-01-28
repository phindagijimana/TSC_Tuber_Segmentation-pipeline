#!/usr/bin/env python3
"""
Test Docker Container Availability

Tests if the pipeline can successfully pull and verify the required Docker containers.

Usage:
    python3 test_docker.py [--all]

Options:
    --all    Test all 4 containers (default: test first one only)
"""

import argparse
import sys
from pathlib import Path

# Add scripts directory to path to import utilities
sys.path.insert(0, str(Path(__file__).parent))

from pipeline_utils import PipelineLogger, DockerManager, detect_gpu


# Docker images used in the pipeline
DOCKER_IMAGES = {
    "Step 1 (Skull Strip)": "ivansanchezfernandez/skull_strip_and_create_masks_with_synthstrip",
    "Step 2 (T2 Combine)": "ivansanchezfernandez/combine_t2_files_with_niftymic",
    "Step 3 (MNI Register)": "ivansanchezfernandez/bias_correct_resample_and_register_to_mni_with_ants",
    "Step 4 (Segmentation)": "ivansanchezfernandez/segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout",
}


def test_docker_availability(logger):
    """Test if Docker is available and running."""
    logger.info("=" * 60)
    logger.info("Testing Docker Availability")
    logger.info("=" * 60)
    
    try:
        docker_manager = DockerManager(logger)
        logger.info("✓ Docker is available and running")
        return docker_manager
    except RuntimeError as e:
        logger.error(f"✗ Docker test failed: {e}")
        return None


def test_gpu_detection(logger):
    """Test GPU detection."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Testing GPU Detection")
    logger.info("=" * 60)
    
    gpu_available = detect_gpu()
    if gpu_available:
        logger.info("✓ GPU detected and available")
    else:
        logger.info("⚠ No GPU detected (will use CPU)")
    
    return gpu_available


def test_single_container(docker_manager, step_name, image_name, logger):
    """
    Test pulling a single container.
    
    Args:
        docker_manager: DockerManager instance
        step_name: Human-readable step name
        image_name: Docker image name
        logger: Logger instance
    
    Returns:
        True if successful, False otherwise
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Testing: {step_name}")
    logger.info("=" * 60)
    logger.info(f"Image: {image_name}")
    logger.info("")
    
    try:
        docker_manager.pull_image(image_name)
        logger.info(f"✓ Successfully pulled/verified: {step_name}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to pull {step_name}")
        logger.error(f"  Error: {e}")
        logger.info("")
        logger.info("Possible solutions:")
        logger.info("  1. Try running via SLURM job (compute nodes may have better Docker config)")
        logger.info("  2. Contact sysadmin about Docker/Podman UID/GID namespace mapping")
        logger.info("  3. Check if Singularity is available as alternative")
        return False


def main():
    """Main test function."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Test Docker container availability for TSC pipeline"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all 4 containers (default: test first one only)"
    )
    args = parser.parse_args()
    
    # Setup logging
    project_root = Path(__file__).parent.parent.resolve()
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    log_manager = PipelineLogger("test_docker", logs_dir)
    logger = log_manager.get_logger()
    
    logger.info("=" * 60)
    logger.info("TSC Pipeline - Docker Container Test")
    logger.info("=" * 60)
    logger.info(f"Project root: {project_root}")
    logger.info(f"Log file: {log_manager.get_log_file()}")
    logger.info("")
    
    # Test 1: Docker availability
    docker_manager = test_docker_availability(logger)
    if not docker_manager:
        logger.error("")
        logger.error("=" * 60)
        logger.error("TEST FAILED: Docker is not available")
        logger.error("=" * 60)
        logger.error("Cannot proceed with container tests.")
        sys.exit(1)
    
    # Test 2: GPU detection
    gpu_available = test_gpu_detection(logger)
    
    # Test 3: Container pulling
    logger.info("")
    logger.info("=" * 60)
    logger.info("Testing Container Availability")
    logger.info("=" * 60)
    
    if args.all:
        logger.info("Mode: Testing ALL 4 containers")
        containers_to_test = list(DOCKER_IMAGES.items())
    else:
        logger.info("Mode: Testing FIRST container only (use --all for all)")
        containers_to_test = [list(DOCKER_IMAGES.items())[0]]
    
    logger.info(f"Containers to test: {len(containers_to_test)}")
    
    # Test containers
    results = {}
    for step_name, image_name in containers_to_test:
        success = test_single_container(docker_manager, step_name, image_name, logger)
        results[step_name] = success
    
    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    failed = len(results) - passed
    
    logger.info(f"Docker available: ✓")
    logger.info(f"GPU available: {'✓' if gpu_available else '⚠ (CPU only)'}")
    logger.info(f"Containers tested: {len(results)}")
    logger.info(f"  Passed: {passed}")
    logger.info(f"  Failed: {failed}")
    logger.info("")
    
    if failed > 0:
        logger.error("=" * 60)
        logger.error("⚠ CONTAINER PULL FAILURES DETECTED")
        logger.error("=" * 60)
        logger.error("Failed containers:")
        for step_name, success in results.items():
            if not success:
                logger.error(f"  ✗ {step_name}")
        
        logger.info("")
        logger.info("Recommendations:")
        logger.info("  1. Run pipeline via SLURM job instead:")
        logger.info("     ./scripts/submit_gpu_job.sh")
        logger.info("")
        logger.info("  2. Compute nodes may have better Docker configuration")
        logger.info("")
        logger.info("  3. Contact system administrator if issue persists")
        logger.info("")
        logger.info(f"Log file: {log_manager.get_log_file()}")
        logger.info("=" * 60)
        
        sys.exit(1)
    
    else:
        logger.info("=" * 60)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 60)
        logger.info("The pipeline should be able to pull all required containers.")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  • Run full pipeline:")
        logger.info("    python3 scripts/run_pipeline.py")
        logger.info("")
        logger.info("  • Or submit GPU job:")
        logger.info("    ./scripts/submit_gpu_job.sh")
        logger.info("")
        logger.info(f"Log file: {log_manager.get_log_file()}")
        logger.info("=" * 60)
        
        sys.exit(0)


if __name__ == "__main__":
    main()

