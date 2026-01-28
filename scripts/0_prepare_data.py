#!/usr/bin/env python3
"""
TSC Tuber Segmentation Pipeline - Step 0: Data Preparation

Organizes raw NIfTI files from nested subject directories into per-subject
preprocessing folders with validation of file naming conventions.

Input:  TSC_MRI_SUB/{subject}/*.nii
Output: preprocessing/MRI_files/{subject}/*.nii

Author: Tuber Pipeline Development Team
Date: 2026-01-27
"""

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

from pipeline_utils import (
    PipelineConfig,
    PipelineLogger,
    FileValidator,
    discover_subjects,
)


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class ValidationResult:
    """Results of subject validation."""
    subject: str
    valid_files: int
    invalid_files: int
    t1_count: int
    t2_count: int
    flair_count: int
    has_error: bool
    error_messages: List[str]


# ============================================================================
# Core Functions
# ============================================================================

def process_subject(
    subject: str,
    input_dir: Path,
    output_dir: Path,
    logger
) -> ValidationResult:
    """
    Process a single subject: validate and copy files.
    
    Args:
        subject: Subject ID
        input_dir: Subject's input directory
        output_dir: Subject's output directory
        logger: Logger instance
    
    Returns:
        ValidationResult with processing summary
    """
    logger.info(f"Processing subject: {subject}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all NIfTI files
    nifti_files = FileValidator.find_nifti_files(input_dir)
    
    if not nifti_files:
        logger.warning(f"  No NIfTI files found for {subject}")
        return ValidationResult(
            subject=subject,
            valid_files=0,
            invalid_files=0,
            t1_count=0,
            t2_count=0,
            flair_count=0,
            has_error=True,
            error_messages=["No NIfTI files found"]
        )
    
    logger.info(f"  Found {len(nifti_files)} NIfTI file(s)")
    
    # Validate and copy files
    valid_files = 0
    invalid_files = 0
    
    for file_path in nifti_files:
        filename = file_path.name
        
        if FileValidator.validate_filename(filename, subject):
            shutil.copy2(file_path, output_dir / filename)
            logger.info(f"      {filename}")
            valid_files += 1
        else:
            logger.warning(f"    x {filename} (invalid naming convention)")
            invalid_files += 1
    
    # Count sequences
    counts = FileValidator.count_sequences(output_dir)
    
    logger.info("  Sequence summary:")
    logger.info(f"    T1:    {counts['T1']} file(s)")
    logger.info(f"    T2:    {counts['T2']} file(s)")
    logger.info(f"    FLAIR: {counts['FLAIR']} file(s)")
    
    # Validate minimum requirements
    error_messages = []
    has_error = False
    
    if counts["T1"] == 0:
        logger.warning("    WARNING: No T1 sequence found")
        error_messages.append("No T1 sequence")
        has_error = True
    
    if counts["T2"] == 0:
        logger.warning("    WARNING: No T2 sequence found")
        error_messages.append("No T2 sequence")
        has_error = True
    
    if counts["FLAIR"] == 0:
        logger.warning("    WARNING: No FLAIR sequence found")
        error_messages.append("No FLAIR sequence")
        has_error = True
    
    if not has_error:
        logger.info("    Subject validation passed")
    
    logger.info(f"  Copied: {valid_files} valid file(s)")
    if invalid_files > 0:
        logger.info(f"  Skipped: {invalid_files} invalid file(s)")
    
    return ValidationResult(
        subject=subject,
        valid_files=valid_files,
        invalid_files=invalid_files,
        t1_count=counts["T1"],
        t2_count=counts["T2"],
        flair_count=counts["FLAIR"],
        has_error=has_error,
        error_messages=error_messages
    )


def main():
    """Main execution function."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="TSC Pipeline - Step 0: Data Preparation"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root directory (default: parent of scripts directory)"
    )
    args = parser.parse_args()
    
    # Determine project root
    if args.project_root:
        project_root = args.project_root.resolve()
    else:
        # Assume script is in scripts/ directory
        project_root = Path(__file__).parent.parent.resolve()
    
    # Initialize configuration
    config = PipelineConfig.from_project_root(project_root)
    config.ensure_directories()
    
    # Setup logging
    log_manager = PipelineLogger(
        "0_prepare_data",
        config.logs_dir
    )
    logger = log_manager.get_logger()
    
    logger.info("=" * 50)
    logger.info("Step 0: Data Preparation")
    logger.info("=" * 50)
    logger.info(f"Project root: {config.project_root}")
    logger.info(f"Input directory: {config.input_dir}")
    logger.info(f"Output directory: {config.preprocessing_dir / 'MRI_files'}")
    logger.info("")
    
    try:
        # Discover subjects
        subjects = discover_subjects(config.input_dir, logger)
        logger.info("")
        
        # Process each subject
        output_base = config.preprocessing_dir / "MRI_files"
        results: List[ValidationResult] = []
        
        for i, subject in enumerate(subjects, 1):
            logger.info("-" * 50)
            logger.info(f"Processing subject {i}/{len(subjects)}: {subject}")
            logger.info("-" * 50)
            
            subject_input = config.input_dir / subject
            subject_output = output_base / subject
            
            result = process_subject(
                subject,
                subject_input,
                subject_output,
                logger
            )
            results.append(result)
            logger.info("")
        
        # Summary
        logger.info("=" * 50)
        logger.info("Data Preparation Complete")
        logger.info("=" * 50)
        
        successful = sum(1 for r in results if not r.has_error)
        failed = len(results) - successful
        
        logger.info(f"Total subjects processed: {len(results)}")
        logger.info(f"Successfully prepared: {successful}")
        
        if failed > 0:
            logger.info("")
            logger.info("  Subjects with issues:")
            for result in results:
                if result.has_error:
                    errors = ", ".join(result.error_messages)
                    logger.info(f"  - {result.subject}: {errors}")
            logger.info("")
            logger.info("WARNING: Some subjects may not process correctly in subsequent steps.")
        else:
            logger.info("  All subjects validated successfully")
        
        logger.info("")
        logger.info(f"Output directory: {output_base}")
        logger.info(f"Log file: {log_manager.get_log_file()}")
        logger.info("=" * 50)
        
        # Exit with error if any subjects failed
        sys.exit(1 if failed > 0 else 0)
        
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()



