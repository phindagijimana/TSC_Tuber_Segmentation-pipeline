#!/usr/bin/env python3
"""
TSC Tuber Segmentation Pipeline - Step 3: MNI Registration

Performs bias-field correction, resampling to 1mm isotropic, and
registration to MNI152 2009c template space using ANTs.

Docker Image: ivansanchezfernandez/bias_correct_resample_and_register_to_MNI_with_ants
Citation: Avants et al., A reproducible evaluation of ANTs similarity metric
          performance in brain image registration. Neuroimage 2011. PMID: 20851191

Input:  preprocessing/combined_MRIs/{subject}/*.nii
Output: preprocessing/preprocessed_MRIs/{subject}/*.nii

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

DOCKER_IMAGE = "ivansanchezfernandez/bias_correct_resample_and_register_to_mni_with_ants"


# ============================================================================
# Core Functions
# ============================================================================

def process_subject(
    subject: str,
    input_dir: Path,
    output_dir: Path,
    docker_manager: DockerManager,
    logger
) -> Tuple[bool, int]:
    """
    Process MNI registration for a single subject.
    
    Args:
        subject: Subject ID
        input_dir: Subject's input directory
        output_dir: Subject's output directory
        docker_manager: Docker manager instance
        logger: Logger instance
    
    Returns:
        Tuple of (success: bool, duration: int in seconds)
    """
    logger.info(f"Processing subject: {subject}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Count input files
    input_files = FileValidator.find_nifti_files(input_dir)
    input_count = len(input_files)
    
    logger.info(f"  Input files: {input_count}")
    
    if input_count == 0:
        logger.warning("    WARNING: No input files found, skipping")
        return False, 0
    
    # Run Docker container
    logger.info("  Running ANTs registration container (this may take 10-30 minutes)...")
    
    timer = Timer()
    timer.start()
    
    try:
        # ANTs container uses /iterative_loop.sh as entrypoint
        # It creates temp directories (./bias_corrected, ./resampled, ./output2)
        # relative to workdir, so we need --writable-tmpfs overlay
        result = docker_manager.run_container(
            image=DOCKER_IMAGE,
            volumes={
                input_dir: "/input:ro",
                output_dir: "/output",
            },
            use_gpu=False,
            capture_output=True,
            workdir="/",  # Run from root where iterative_loop.sh and MNI_template are
            scratch=True  # Enable writable overlay so script can create temp directories
        )
        
        # Log container output for debugging
        if result.stdout:
            logger.info(f"Container stdout: {result.stdout[:500]}")
        if result.stderr:
            logger.info(f"Container stderr: {result.stderr[:500]}")
        
        timer.stop()
        hours, minutes, seconds = timer.elapsed()
        duration_sec = hours * 3600 + minutes * 60 + seconds
        
        # Validate outputs
        output_files = FileValidator.find_nifti_files(output_dir)
        output_count = len(output_files)
        
        logger.info(f"    Completed in {timer.elapsed_str()}")
        logger.info(f"  Output files: {output_count}")
        
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
        description="TSC Pipeline - Step 3: MNI Registration"
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
    log_manager = PipelineLogger("3_register_to_mni", config.logs_dir)
    logger = log_manager.get_logger()
    
    logger.info("=" * 50)
    logger.info("Step 3: Registration to MNI with ANTs")
    logger.info("=" * 50)
    logger.info(f"Project root: {config.project_root}")
    logger.info(f"Input directory: {config.preprocessing_dir / 'combined_MRIs'}")
    logger.info(f"Output directory: {config.preprocessing_dir / 'preprocessed_MRIs'}")
    logger.info("")
    
    try:
        # Initialize Docker manager
        docker_manager = DockerManager(logger)
        
        # Pull Docker image
        docker_manager.pull_image(DOCKER_IMAGE)
        logger.info("")
        
        # Discover subjects
        input_base = config.preprocessing_dir / "combined_MRIs"
        subjects = discover_subjects(input_base, logger)
        logger.info("")
        
        logger.info("  NOTE: This step is computationally intensive.")
        logger.info(f"   Expected time per subject: 10-30 minutes")
        logger.info(f"   Total estimated time: {len(subjects) * 15} - {len(subjects) * 30} minutes")
        logger.info("")
        
        # Process each subject
        output_base = config.preprocessing_dir / "preprocessed_MRIs"
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
        logger.info("MNI Registration Complete")
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
        logger.info(f"Log file: {log_manager.get_log_file()}")
        logger.info("=" * 50)
        
        sys.exit(1 if failed_subjects else 0)
        
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

