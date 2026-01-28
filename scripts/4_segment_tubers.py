#!/usr/bin/env python3
"""
TSC Tuber Segmentation Pipeline - Step 4: Tuber Segmentation

Automatically segments tubers and quantifies tuber burden using
TSCCNN3D_dropout deep learning model. Supports GPU acceleration.

Docker Image: ivansanchezfernandez/segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout
Citation: Sánchez Fernández et al., Convolutional neural networks for
          automatic tuber segmentation and quantification of tuber burden
          in tuberous sclerosis complex. Epilepsia 2025. DOI: 10.1111/epi.70007

Input:  preprocessing/preprocessed_MRIs/{subject}/*.nii
Output: results/{subject}/*.nii (segmentations)
        results/volume_results.txt (tuber burden quantification)

Author: Tuber Pipeline Development Team
Date: 2026-01-27
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from pipeline_utils import (
    PipelineConfig,
    PipelineLogger,
    DockerManager,
    FileValidator,
    discover_subjects,
    detect_gpu,
    Timer,
)


# ============================================================================
# Configuration
# ============================================================================

DOCKER_IMAGE = "ivansanchezfernandez/segment_tubers_and_quantify_tuber_burden_with_tsccnn3d_dropout"


# ============================================================================
# Core Functions
# ============================================================================

def process_subject(
    subject: str,
    input_dir: Path,
    output_dir: Path,
    docker_manager: DockerManager,
    use_gpu: bool,
    logger
) -> Tuple[bool, int]:
    """
    Process tuber segmentation for a single subject.
    
    Args:
        subject: Subject ID
        input_dir: Subject's input directory
        output_dir: Subject's output directory
        docker_manager: Docker manager instance
        use_gpu: Whether to use GPU acceleration
        logger: Logger instance
    
    Returns:
        Tuple of (success: bool, duration: int in seconds)
    """
    logger.info(f"Processing subject: {subject}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Count sequences and validate
    counts = FileValidator.count_sequences(input_dir)
    
    logger.info(f"  Sequences: T1={counts['T1']}, T2={counts['T2']}, FLAIR={counts['FLAIR']}")
    
    if counts["T1"] == 0 or counts["T2"] == 0 or counts["FLAIR"] == 0:
        logger.warning("  ⚠ WARNING: Missing required sequences, skipping")
        return False, 0
    
    # Run Docker container
    if use_gpu:
        logger.info("  Running with GPU acceleration...")
    else:
        logger.info("  Running on CPU...")
    
    timer = Timer()
    timer.start()
    
    try:
        docker_manager.run_container(
            image=DOCKER_IMAGE,
            volumes={
                input_dir: "/input:ro",
                output_dir: "/output",
            },
            workdir="/app",  # Container script (iterative_loop.py) is in /app
            use_gpu=use_gpu,
            capture_output=True
        )
        
        timer.stop()
        hours, minutes, seconds = timer.elapsed()
        duration_sec = hours * 3600 + minutes * 60 + seconds
        
        # Validate outputs - look for segmentation files
        output_files = [
            f for f in output_dir.iterdir()
            if f.is_file() and FileValidator.is_nifti_file(f) and "seg" in f.name.lower()
        ]
        seg_count = len(output_files)
        
        logger.info(f"  ✓ Completed in {timer.elapsed_str()}")
        logger.info(f"  Segmentation files: {seg_count}")
        
        if seg_count == 0:
            logger.warning("  ⚠ WARNING: No segmentation files generated")
            return False, duration_sec
        
        return True, duration_sec
        
    except Exception as e:
        logger.error(f"  ✗ Container execution failed: {e}")
        return False, 0


def aggregate_volume_results(results_dir: Path, logger) -> None:
    """
    Aggregate volume results from all subjects into a single file.
    
    Args:
        results_dir: Results directory
        logger: Logger instance
    """
    logger.info("Aggregating tuber burden results...")
    
    # Find all individual volume_results.txt files
    volume_files = list(results_dir.glob("*/volume_results.txt"))
    
    if not volume_files:
        logger.warning("  ⚠ No volume results found to aggregate")
        return
    
    # Create aggregated file
    aggregated_file = results_dir / "volume_results.txt"
    
    try:
        with open(aggregated_file, 'w') as outfile:
            # Write header
            outfile.write("Subject_ID\tT1_Volume_mm3\tT2_Volume_mm3\tFLAIR_Volume_mm3\tTotal_Volume_mm3\tGenerated_Timestamp\n")
            
            # Append contents from each subject
            for vol_file in sorted(volume_files):
                with open(vol_file, 'r') as infile:
                    lines = infile.readlines()
                    # Skip header if present
                    for line in lines:
                        if not line.startswith("Subject_ID"):
                            outfile.write(line)
        
        logger.info(f"  ✓ Aggregated results: {len(volume_files)} subject(s)")
        logger.info(f"  Output: {aggregated_file}")
        
    except Exception as e:
        logger.error(f"  Failed to aggregate results: {e}")


def main():
    """Main execution function."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="TSC Pipeline - Step 4: Tuber Segmentation"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root directory"
    )
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="Disable GPU even if available"
    )
    args = parser.parse_args()
    
    # Determine project root
    if args.project_root:
        project_root = args.project_root.resolve()
    else:
        project_root = Path(__file__).parent.parent.resolve()
    
    # Initialize configuration
    config = PipelineConfig.from_project_root(project_root)
    config.ensure_directories()
    
    # Setup logging
    log_manager = PipelineLogger("4_segment_tubers", config.logs_dir)
    logger = log_manager.get_logger()
    
    logger.info("=" * 50)
    logger.info("Step 4: Tuber Segmentation with TSCCNN3D")
    logger.info("=" * 50)
    logger.info(f"Project root: {config.project_root}")
    logger.info(f"Input directory: {config.preprocessing_dir / 'preprocessed_MRIs'}")
    logger.info(f"Output directory: {config.results_dir}")
    logger.info("")
    
    try:
        # Initialize Docker manager
        docker_manager = DockerManager(logger)
        
        # GPU detection
        gpu_available = detect_gpu() and not args.no_gpu
        if gpu_available:
            logger.info("GPU: Detected and enabled")
        else:
            logger.info("GPU: Not available, using CPU")
        logger.info("")
        
        # Pull Docker image
        docker_manager.pull_image(DOCKER_IMAGE)
        logger.info("")
        
        # Discover subjects
        input_base = config.preprocessing_dir / "preprocessed_MRIs"
        subjects = discover_subjects(input_base, logger)
        logger.info("")
        
        if gpu_available:
            logger.info("Expected time per subject: 1-2 minutes (GPU)")
            logger.info(f"Total estimated time: {len(subjects) * 2} - {len(subjects) * 3} minutes")
        else:
            logger.info("Expected time per subject: 5-15 minutes (CPU)")
            logger.info(f"Total estimated time: {len(subjects) * 10} - {len(subjects) * 15} minutes")
        logger.info("")
        
        # Process each subject
        success_count = 0
        failed_subjects: List[str] = []
        total_time = 0
        
        for i, subject in enumerate(subjects, 1):
            logger.info("=" * 50)
            logger.info(f"Processing subject {i}/{len(subjects)}: {subject}")
            logger.info("=" * 50)
            
            success, duration = process_subject(
                subject,
                input_base / subject,
                config.results_dir / subject,
                docker_manager,
                gpu_available,
                logger
            )
            
            if success:
                success_count += 1
                total_time += duration
                logger.info(f"  ✓ {subject} completed successfully")
            else:
                failed_subjects.append(subject)
                logger.info(f"  ✗ {subject} failed")
            
            logger.info("")
        
        # Aggregate volume results
        logger.info("=" * 50)
        aggregate_volume_results(config.results_dir, logger)
        logger.info("")
        
        # Calculate average time
        avg_time_min = 0
        avg_time_sec = 0
        if success_count > 0:
            avg_time_total = total_time // success_count
            avg_time_min = avg_time_total // 60
            avg_time_sec = avg_time_total % 60
        
        # Summary
        logger.info("=" * 50)
        logger.info("Tuber Segmentation Complete")
        logger.info("=" * 50)
        logger.info(f"Total subjects: {len(subjects)}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {len(failed_subjects)}")
        logger.info(f"Average time per subject: {avg_time_min}m {avg_time_sec}s")
        
        if failed_subjects:
            logger.info("")
            logger.info("Failed subjects:")
            for subj in failed_subjects:
                logger.info(f"  - {subj}")
        
        logger.info("")
        logger.info(f"Output directory: {config.results_dir}")
        logger.info(f"Volume results: {config.results_dir / 'volume_results.txt'}")
        logger.info(f"Log file: {log_manager.get_log_file()}")
        logger.info("")
        logger.info("=" * 50)
        logger.info("CITATION REMINDER")
        logger.info("=" * 50)
        logger.info("If you use these results in your research, please cite:")
        logger.info("Sánchez Fernández et al., Epilepsia 2025. DOI: 10.1111/epi.70007")
        logger.info("=" * 50)
        
        sys.exit(1 if failed_subjects else 0)
        
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

