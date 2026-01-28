#!/usr/bin/env python3
"""
TSC Tuber Segmentation Pipeline - Main Orchestrator

Main pipeline script that orchestrates all preprocessing and segmentation
steps. Runs on CPU by default (use submit_gpu_job.sh for GPU acceleration).

Usage:
    python run_pipeline.py [options]

Options:
    --force          Force re-run of all steps (ignore existing outputs)
    --start-from N   Start from step N (0-4)
    --help           Show this help message

Steps:
    0. Prepare data (organize into per-subject folders)
    1. Skull strip with SynthStrip
    2. Combine T2 sequences with NiftyMIC
    3. Register to MNI with ANTs
    4. Segment tubers with TSCCNN3D

Author: Tuber Pipeline Development Team
Date: 2026-01-27
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from pipeline_utils import PipelineConfig, PipelineLogger, Timer


# ============================================================================
# Step Configuration
# ============================================================================

@dataclass
class PipelineStep:
    """Configuration for a pipeline step."""
    number: int
    name: str
    script: str
    output_dir: Path
    
    def should_skip(self, force: bool) -> bool:
        """
        Check if step should be skipped based on existing outputs.
        
        Args:
            force: If True, never skip
        
        Returns:
            True if step should be skipped
        """
        if force or self.number == 0:  # Step 0 always runs
            return False
        
        # Check if output directory exists and has content
        if not self.output_dir.exists():
            return False
        
        # Check if directory has at least one subdirectory with files
        try:
            subdirs = [d for d in self.output_dir.iterdir() if d.is_dir()]
            return len(subdirs) > 0 and any(
                list(subdir.iterdir())
                for subdir in subdirs
            )
        except Exception:
            return False


# ============================================================================
# Core Functions
# ============================================================================

def run_step(
    step: PipelineStep,
    config: PipelineConfig,
    force: bool,
    logger
) -> bool:
    """
    Run a single pipeline step.
    
    Args:
        step: Pipeline step configuration
        config: Pipeline configuration
        force: Force re-run even if outputs exist
        logger: Logger instance
    
    Returns:
        True if step succeeded, False otherwise
    """
    logger.info("")
    logger.info("=" * 50)
    logger.info(f"STEP {step.number}: {step.name}")
    logger.info("=" * 50)
    
    # Check if step should be skipped
    if step.should_skip(force):
        logger.info(f"Output directory exists and contains data: {step.output_dir}")
        logger.info(f"⏭  Skipping step {step.number} (use --force to re-run)")
        return True
    
    # Build command
    script_path = config.project_root / "scripts" / step.script
    
    if not script_path.exists():
        logger.error(f"Step script not found: {script_path}")
        return False
    
    cmd = [sys.executable, str(script_path), "--project-root", str(config.project_root)]
    
    # Run the step
    logger.info(f"Executing: {' '.join(cmd)}")
    
    timer = Timer()
    timer.start()
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,
            text=True
        )
        
        timer.stop()
        logger.info(f"  Step {step.number} completed successfully in {timer.elapsed_str()}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"x Step {step.number} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        logger.error(f"x Step {step.number} failed: {e}")
        return False


def main():
    """Main execution function."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="TSC Tuber Segmentation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Steps:
  0. Prepare data
  1. Skull stripping
  2. T2 combination
  3. MNI registration
  4. Tuber segmentation

Examples:
  python run_pipeline.py                    # Run full pipeline
  python run_pipeline.py --start-from 2     # Resume from step 2
  python run_pipeline.py --force            # Force re-run all steps

For GPU-accelerated execution, use: ./submit_gpu_job.sh
        """
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-run of all steps (ignore existing outputs)"
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        choices=[0, 1, 2, 3, 4],
        help="Start from step N (0-4, default: 0)"
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
        project_root = Path(__file__).parent.parent.resolve()
    
    # Initialize configuration
    config = PipelineConfig.from_project_root(project_root)
    config.ensure_directories()
    
    # Setup logging
    log_manager = PipelineLogger("pipeline", config.logs_dir)
    logger = log_manager.get_logger()
    
    logger.info("=" * 50)
    logger.info("TSC Tuber Segmentation Pipeline")
    logger.info("=" * 50)
    logger.info(f"Project root: {config.project_root}")
    logger.info(f"Pipeline log: {log_manager.get_log_file()}")
    logger.info(f"Start time: {Timer().start}")
    logger.info("")
    
    if args.force:
        logger.info("  Force mode: Will re-run all steps")
    
    if args.start_from > 0:
        logger.info(f"  Starting from step: {args.start_from}")
    
    logger.info("")
    
    # Define pipeline steps
    steps = [
        PipelineStep(
            number=0,
            name="Data Preparation",
            script="0_prepare_data.py",
            output_dir=config.preprocessing_dir / "MRI_files"
        ),
        PipelineStep(
            number=1,
            name="Skull Stripping",
            script="1_skull_strip.py",
            output_dir=config.preprocessing_dir / "skull_stripped_MRIs"
        ),
        PipelineStep(
            number=2,
            name="T2 Combination",
            script="2_combine_t2.py",
            output_dir=config.preprocessing_dir / "combined_MRIs"
        ),
        PipelineStep(
            number=3,
            name="MNI Registration",
            script="3_register_to_mni.py",
            output_dir=config.preprocessing_dir / "preprocessed_MRIs"
        ),
        PipelineStep(
            number=4,
            name="Tuber Segmentation",
            script="4_segment_tubers.py",
            output_dir=config.results_dir
        ),
    ]
    
    # Run pipeline
    pipeline_timer = Timer()
    pipeline_timer.start()
    
    try:
        for step in steps:
            # Skip steps before start_from
            if step.number < args.start_from:
                continue
            
            success = run_step(step, config, args.force, logger)
            
            if not success:
                logger.error(f"Pipeline failed at step {step.number}: {step.name}")
                logger.error(f"Check log: {log_manager.get_log_file()}")
                sys.exit(1)
        
        # Pipeline complete
        pipeline_timer.stop()
        hours, minutes, seconds = pipeline_timer.elapsed()
        
        logger.info("")
        logger.info("=" * 50)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 50)
        logger.info(f"Total time: {hours}h {minutes}m {seconds}s")
        logger.info("")
        logger.info("Output locations:")
        logger.info(f"  - Preprocessed MRIs: {config.preprocessing_dir / 'preprocessed_MRIs'}")
        logger.info(f"  - Segmentations: {config.results_dir}")
        logger.info(f"  - Tuber burden: {config.results_dir / 'volume_results.txt'}")
        logger.info(f"  - Pipeline log: {log_manager.get_log_file()}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Review volume_results.txt for tuber burden quantification")
        logger.info("  2. Visualize segmentations using ITK-SNAP:")
        logger.info("     itksnap -g results/Case001/Case001_T1_*.nii \\")
        logger.info("             -s results/Case001/*seg*.nii")
        logger.info("")
        logger.info("=" * 50)
        logger.info("CITATION REMINDER")
        logger.info("=" * 50)
        logger.info("Please cite these publications if you use this pipeline:")
        logger.info("  - Sánchez Fernández et al., Epilepsia 2025 (main method)")
        logger.info("  - Hoopes et al., Neuroimage 2022 (SynthStrip)")
        logger.info("  - Ebner et al., Neuroimage 2020 (NiftyMIC)")
        logger.info("  - Avants et al., Neuroimage 2011 (ANTs)")
        logger.info("=" * 50)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()



