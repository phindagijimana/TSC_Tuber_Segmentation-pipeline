#!/usr/bin/env python3
"""
TSC Tuber Segmentation Pipeline - Step 1: Skull Stripping

Removes non-brain tissue (skull, CSF, etc.) using SynthStrip and generates
brain masks. Processes each subject independently.

Docker Image: ivansanchezfernandez/skull_strip_and_create_masks_with_synthstrip
Citation: Hoopes et al., SynthStrip: Skull-Stripping for Any Brain Image.
          Neuroimage 2022. PMID: 35842095

Input:  preprocessing/MRI_files/{subject}/*.nii
Output: preprocessing/skull_stripped_MRIs/{subject}/*.nii
        preprocessing/masks/{subject}/*.nii

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
    Timer,
)


# ============================================================================
# Configuration
# ============================================================================

DOCKER_IMAGE = "ivansanchezfernandez/skull_strip_and_create_masks_with_synthstrip"


# ============================================================================
# Core Functions
# ============================================================================

def process_subject(
    subject: str,
    input_dir: Path,
    output_dir: Path,
    mask_dir: Path,
    docker_manager: DockerManager,
    logger
) -> Tuple[bool, int]:
    """
    Process skull stripping for a single subject.
    
    Args:
        subject: Subject ID
        input_dir: Subject's input directory
        output_dir: Subject's output directory for skull-stripped files
        mask_dir: Subject's output directory for brain masks
        docker_manager: Docker manager instance
        logger: Logger instance
    
    Returns:
        Tuple of (success: bool, duration: int in seconds)
    """
    logger.info(f"Processing subject: {subject}")
    
    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)
    
    # Count input files
    input_files = FileValidator.find_nifti_files(input_dir)
    input_count = len(input_files)
    
    logger.info(f"  Input files: {input_count}")
    
    if input_count == 0:
        logger.warning("    WARNING: No input files found, skipping")
        return False, 0
    
    # Run Docker container
    logger.info("  Running SynthStrip container...")
    
    timer = Timer()
    timer.start()
    
    try:
        docker_manager.run_container(
            image=DOCKER_IMAGE,
            volumes={
                input_dir: "/input:ro",
                output_dir: "/output",
                mask_dir: "/masks",
            },
            use_gpu=False,  # SynthStrip doesn't use GPU
            capture_output=True
        )
        
        timer.stop()
        duration_sec = timer.elapsed()[1] * 60 + timer.elapsed()[2]
        
        # Validate outputs
        output_files = FileValidator.find_nifti_files(output_dir)
        mask_files = FileValidator.find_nifti_files(mask_dir)
        
        output_count = len(output_files)
        mask_count = len(mask_files)
        
        logger.info(f"    Completed in {timer.elapsed_str()}")
        logger.info(f"  Output files: {output_count} skull-stripped, {mask_count} masks")
        
        if output_count == 0:
            logger.warning("    WARNING: No output files generated")
            return False, duration_sec
        
        return True, duration_sec
        
    except Exception as e:
        logger.error(f"  x Container execution failed: {e}")
        return False, 0


def main():
    """Main execution function."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="TSC Pipeline - Step 1: Skull Stripping"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root directory"
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
    log_manager = PipelineLogger("1_skull_strip", config.logs_dir)
    logger = log_manager.get_logger()
    
    logger.info("=" * 50)
    logger.info("Step 1: Skull Stripping with SynthStrip")
    logger.info("=" * 50)
    logger.info(f"Project root: {config.project_root}")
    logger.info(f"Input directory: {config.preprocessing_dir / 'MRI_files'}")
    logger.info(f"Output directory: {config.preprocessing_dir / 'skull_stripped_MRIs'}")
    logger.info(f"Mask directory: {config.preprocessing_dir / 'masks'}")
    logger.info("")
    
    try:
        # Initialize Docker manager
        docker_manager = DockerManager(logger)
        
        # Pull Docker image
        docker_manager.pull_image(DOCKER_IMAGE)
        logger.info("")
        
        # Discover subjects
        input_base = config.preprocessing_dir / "MRI_files"
        subjects = discover_subjects(input_base, logger)
        logger.info("")
        
        # Process each subject
        output_base = config.preprocessing_dir / "skull_stripped_MRIs"
        mask_base = config.preprocessing_dir / "masks"
        
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
                output_base / subject,
                mask_base / subject,
                docker_manager,
                logger
            )
            
            if success:
                success_count += 1
                total_time += duration
                logger.info(f"    {subject} completed successfully")
            else:
                failed_subjects.append(subject)
                logger.info(f"  x {subject} failed")
            
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
        logger.info("Skull Stripping Complete")
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
        logger.info(f"Output directory: {output_base}")
        logger.info(f"Mask directory: {mask_base}")
        logger.info(f"Log file: {log_manager.get_log_file()}")
        logger.info("=" * 50)
        
        sys.exit(1 if failed_subjects else 0)
        
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

