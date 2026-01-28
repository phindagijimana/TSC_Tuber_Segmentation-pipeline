#!/usr/bin/env python3
"""
TSC Tuber Segmentation Pipeline - Step 2: T2 Combination

Combines axial and coronal T2 sequences for improved 3D resolution using
NiftyMIC. Only processes subjects with both T2 sequences; copies others.

Docker Image: ivansanchezfernandez/combine_t2_files_with_niftymic
Citation: Ebner et al., An automated framework for localization, segmentation
          and super-resolution reconstruction of fetal brain MRI.
          Neuroimage 2020. PMID: 31704293

Input:  preprocessing/skull_stripped_MRIs/{subject}/*.nii
        preprocessing/masks/{subject}/*.nii
Output: preprocessing/combined_MRIs/{subject}/*.nii

Author: Tuber Pipeline Development Team
Date: 2026-01-27
"""

import argparse
import shutil
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

DOCKER_IMAGE = "ivansanchezfernandez/combine_t2_files_with_niftymic"


# ============================================================================
# Core Functions
# ============================================================================

def needs_t2_combination(input_dir: Path) -> bool:
    """
    Check if subject needs T2 combination.
    
    Args:
        input_dir: Subject's input directory
    
    Returns:
        True if subject has multiple T2 files
    """
    counts = FileValidator.count_sequences(input_dir)
    return counts["T2"] > 1


def copy_subject_files(input_dir: Path, output_dir: Path, logger) -> bool:
    """
    Copy files directly without T2 combination.
    
    Args:
        input_dir: Source directory
        output_dir: Destination directory
        logger: Logger instance
    
    Returns:
        True if successful
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all NIfTI files
        input_files = FileValidator.find_nifti_files(input_dir)
        for file_path in input_files:
            shutil.copy2(file_path, output_dir / file_path.name)
        
        return len(input_files) > 0
        
    except Exception as e:
        logger.error(f"  Failed to copy files: {e}")
        return False


def run_t2_combination(
    subject: str,
    input_dir: Path,
    mask_dir: Path,
    output_dir: Path,
    docker_manager: DockerManager,
    logger
) -> Tuple[bool, int]:
    """
    Run T2 combination for a subject.
    
    Args:
        subject: Subject ID
        input_dir: Subject's input directory
        mask_dir: Subject's mask directory
        output_dir: Subject's output directory
        docker_manager: Docker manager instance
        logger: Logger instance
    
    Returns:
        Tuple of (success: bool, duration: int in seconds)
    """
    logger.info("  Running NiftyMIC container (this may take 10-30 minutes)...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timer = Timer()
    timer.start()
    
    try:
        docker_manager.run_container(
            image=DOCKER_IMAGE,
            volumes={
                input_dir: "/input:ro",
                mask_dir: "/masks:ro",
                output_dir: "/output",
            },
            use_gpu=False,
            capture_output=True,
            workdir="/app",  # NiftyMIC container needs to run from /app directory
            scratch=True  # Enable writable overlay for temp directories
        )
        
        timer.stop()
        hours, minutes, seconds = timer.elapsed()
        duration_sec = hours * 3600 + minutes * 60 + seconds
        
        # Validate outputs
        output_files = FileValidator.find_nifti_files(output_dir)
        output_count = len(output_files)
        
        logger.info(f"  ✓ Completed in {timer.elapsed_str()}")
        logger.info(f"  Output files: {output_count}")
        
        if output_count == 0:
            logger.warning("  ⚠ WARNING: No output files generated")
            return False, duration_sec
        
        return True, duration_sec
        
    except Exception as e:
        logger.error(f"  ✗ Container execution failed: {e}")
        return False, 0


def main():
    """Main execution function."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="TSC Pipeline - Step 2: T2 Combination"
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
    log_manager = PipelineLogger("2_combine_t2", config.logs_dir)
    logger = log_manager.get_logger()
    
    logger.info("=" * 50)
    logger.info("Step 2: T2 Combination with NiftyMIC")
    logger.info("=" * 50)
    logger.info(f"Project root: {config.project_root}")
    logger.info(f"Input directory: {config.preprocessing_dir / 'skull_stripped_MRIs'}")
    logger.info(f"Mask directory: {config.preprocessing_dir / 'masks'}")
    logger.info(f"Output directory: {config.preprocessing_dir / 'combined_MRIs'}")
    logger.info("")
    
    try:
        # Initialize Docker manager
        docker_manager = DockerManager(logger)
        
        # Discover subjects
        input_base = config.preprocessing_dir / "skull_stripped_MRIs"
        mask_base = config.preprocessing_dir / "masks"
        subjects = discover_subjects(input_base, logger)
        logger.info("")
        
        # Analyze which subjects need T2 combination
        logger.info("Analyzing T2 sequences...")
        subjects_needing_combination: List[str] = []
        subjects_for_copy: List[str] = []
        
        for subject in subjects:
            if needs_t2_combination(input_base / subject):
                subjects_needing_combination.append(subject)
                logger.info(f"  {subject}: Multiple T2 sequences → will combine")
            else:
                subjects_for_copy.append(subject)
                logger.info(f"  {subject}: Single T2 sequence → will copy")
        
        logger.info("")
        logger.info(f"Subjects needing combination: {len(subjects_needing_combination)}")
        logger.info(f"Subjects for direct copy: {len(subjects_for_copy)}")
        logger.info("")
        
        # Pull Docker image only if needed
        if subjects_needing_combination:
            docker_manager.pull_image(DOCKER_IMAGE)
            logger.info("")
        
        # Process subjects
        output_base = config.preprocessing_dir / "combined_MRIs"
        success_count = 0
        failed_subjects: List[str] = []
        total_time = 0
        current = 0
        total = len(subjects)
        
        # Copy subjects that don't need combination
        for subject in subjects_for_copy:
            current += 1
            logger.info("=" * 50)
            logger.info(f"Processing subject {current}/{total}: {subject} (copy)")
            logger.info("=" * 50)
            
            if copy_subject_files(
                input_base / subject,
                output_base / subject,
                logger
            ):
                success_count += 1
                logger.info("  ✓ Files copied successfully")
            else:
                failed_subjects.append(subject)
                logger.info("  ✗ Copy failed")
            
            logger.info("")
        
        # Combine T2 for subjects that need it
        for subject in subjects_needing_combination:
            current += 1
            logger.info("=" * 50)
            logger.info(f"Processing subject {current}/{total}: {subject} (combine)")
            logger.info("=" * 50)
            
            success, duration = run_t2_combination(
                subject,
                input_base / subject,
                mask_base / subject,
                output_base / subject,
                docker_manager,
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
        
        # Calculate average time for combined subjects
        avg_time_min = 0
        avg_time_sec = 0
        if subjects_needing_combination:
            combined_success = len(subjects_needing_combination) - sum(
                1 for s in failed_subjects if s in subjects_needing_combination
            )
            if combined_success > 0:
                avg_time_total = total_time // combined_success
                avg_time_min = avg_time_total // 60
                avg_time_sec = avg_time_total % 60
        
        # Summary
        logger.info("=" * 50)
        logger.info("T2 Combination Complete")
        logger.info("=" * 50)
        logger.info(f"Total subjects: {total}")
        logger.info(f"  Combined: {len(subjects_needing_combination)}")
        logger.info(f"  Copied: {len(subjects_for_copy)}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {len(failed_subjects)}")
        
        if subjects_needing_combination:
            logger.info(f"Average combination time: {avg_time_min}m {avg_time_sec}s")
        
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

