#!/usr/bin/env python3
"""
TSC Tuber Segmentation Pipeline - Utilities Module

Shared utilities for logging, Docker operations, file validation, and configuration.

Author: Tuber Pipeline Development Team
Date: 2026-01-27
"""

import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class PipelineConfig:
    """Pipeline configuration and paths."""
    
    project_root: Path
    input_dir: Path
    preprocessing_dir: Path
    results_dir: Path
    logs_dir: Path
    
    @classmethod
    def from_project_root(cls, project_root: Path) -> 'PipelineConfig':
        """Create configuration from project root directory."""
        project_root = project_root.resolve()
        preprocessing = project_root / "preprocessing"
        
        return cls(
            project_root=project_root,
            input_dir=project_root / "TSC_MRI_SUB",
            preprocessing_dir=preprocessing,
            results_dir=project_root / "results",
            logs_dir=project_root / "logs",
        )
    
    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        directories = [
            self.preprocessing_dir / "MRI_files",
            self.preprocessing_dir / "skull_stripped_MRIs",
            self.preprocessing_dir / "masks",
            self.preprocessing_dir / "combined_MRIs",
            self.preprocessing_dir / "preprocessed_MRIs",
            self.results_dir,
            self.logs_dir,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Logging
# ============================================================================

class PipelineLogger:
    """Enhanced logging with both file and console output."""
    
    def __init__(self, name: str, log_dir: Path, console_level: int = logging.INFO):
        """
        Initialize logger with file and console handlers.
        
        Args:
            name: Logger name (used for log filename)
            log_dir: Directory to store log files
            console_level: Logging level for console output
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{name}_{timestamp}.log"
        
        # File handler (DEBUG level)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler (INFO level by default)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.log_file = log_file
    
    def get_logger(self) -> logging.Logger:
        """Return the logger instance."""
        return self.logger
    
    def get_log_file(self) -> Path:
        """Return the log file path."""
        return self.log_file


# ============================================================================
# Docker Operations
# ============================================================================

class DockerManager:
    """Manage container operations for the pipeline (Docker or Apptainer/Singularity)."""
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize container manager.
        
        Args:
            logger: Logger instance for output
        """
        self.logger = logger
        self.runtime = self._detect_container_runtime()
        self.logger.info(f"Container runtime: {self.runtime}")
    
    def _detect_container_runtime(self) -> str:
        """
        Detect which container runtime is available.
        
        Returns:
            'docker', 'apptainer', or 'singularity'
        
        Raises:
            RuntimeError: If no container runtime is available
        """
        # Try Docker first
        if shutil.which("docker"):
            try:
                subprocess.run(
                    ["docker", "ps"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                return "docker"
            except subprocess.CalledProcessError:
                # Docker command exists but daemon not running
                pass
        
        # Try Apptainer (preferred Singularity successor)
        if shutil.which("apptainer"):
            try:
                subprocess.run(
                    ["apptainer", "--version"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                return "apptainer"
            except subprocess.CalledProcessError:
                pass
        
        # Try Singularity
        if shutil.which("singularity"):
            try:
                subprocess.run(
                    ["singularity", "--version"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                return "singularity"
            except subprocess.CalledProcessError:
                pass
        
        raise RuntimeError(
            "No container runtime found. Need Docker, Apptainer, or Singularity."
        )
    
    def pull_image(self, image: str) -> None:
        """
        Pull container image if not already available.
        
        Args:
            image: Container image name (without docker:// prefix for Docker)
        """
        self.logger.info(f"Checking container image: {image}")
        
        if self.runtime == "docker":
            # Check if Docker image exists locally
            result = subprocess.run(
                ["docker", "image", "inspect", image],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info("  ✓ Image already available locally")
            else:
                self.logger.info("  Pulling Docker image (this may take several minutes)...")
                try:
                    subprocess.run(
                        ["docker", "pull", image],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    self.logger.info("  ✓ Image pulled successfully")
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f"Failed to pull Docker image {image}: {e}")
        
        else:  # apptainer or singularity
            # Apptainer/Singularity pulls on first run if needed
            # We can optionally pre-pull to cache, but not required
            self.logger.info(f"  ✓ {self.runtime.capitalize()} will pull on first use if needed")
            self.logger.info(f"  Image: docker://{image}")
    
    def run_container(
        self,
        image: str,
        volumes: Dict[Path, str],
        use_gpu: bool = False,
        capture_output: bool = True,
        workdir: str = None,
        scratch: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Run container with specified volumes.
        
        Args:
            image: Container image name
            volumes: Dictionary mapping host paths to container paths
            use_gpu: Whether to enable GPU support
            capture_output: Whether to capture stdout/stderr
            workdir: Working directory inside container (for Apptainer/Singularity)
            scratch: Enable writable overlay for Apptainer (default: False)
        
        Returns:
            CompletedProcess instance
        
        Raises:
            RuntimeError: If container execution fails
        """
        if self.runtime == "docker":
            cmd = ["docker", "run", "--rm"]
            
            # Add GPU support if requested
            if use_gpu:
                cmd.extend(["--gpus", "all"])
            
            # Add volume mounts
            for host_path, container_path in volumes.items():
                cmd.extend(["-v", f"{host_path}:{container_path}"])
            
            # Add working directory if specified
            if workdir:
                cmd.extend(["-w", workdir])
            
            cmd.append(image)
        
        else:  # apptainer or singularity
            cmd = [self.runtime, "run"]
            
            # Add GPU support if requested
            if use_gpu:
                cmd.append("--nv")  # NVIDIA GPU support
            
            # Add writable overlay if requested
            if scratch:
                cmd.append("--writable-tmpfs")  # Create writable overlay in memory
            
            # Add working directory if specified (must come before --bind)
            if workdir:
                cmd.extend(["--pwd", workdir])
            
            # Add volume mounts (bind)
            for host_path, container_path in volumes.items():
                # Remove :ro suffix if present, Apptainer handles differently
                container_path_clean = container_path.replace(":ro", "")
                cmd.extend(["--bind", f"{host_path}:{container_path_clean}"])
            
            # Add docker:// prefix to image name
            cmd.append(f"docker://{image}")
        
        try:
            if capture_output:
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(cmd, check=True)
            
            return result
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Container execution failed ({self.runtime}):\n"
                f"Command: {' '.join(cmd)}\n"
                f"Exit code: {e.returncode}\n"
                f"Error: {e.stderr if capture_output else 'N/A'}"
            )


# ============================================================================
# File Validation
# ============================================================================

class FileValidator:
    """Validate NIfTI files and naming conventions."""
    
    NIFTI_EXTENSIONS = {".nii", ".nii.gz"}
    SEQUENCE_PATTERNS = {
        "T1": re.compile(r"_T1_"),
        "T2": re.compile(r"_T2_"),
        "FLAIR": re.compile(r"_FLAIR_"),
    }
    
    @classmethod
    def is_nifti_file(cls, file_path: Path) -> bool:
        """Check if file is a NIfTI file."""
        return any(str(file_path).endswith(ext) for ext in cls.NIFTI_EXTENSIONS)
    
    @classmethod
    def validate_filename(cls, filename: str, subject_id: str) -> bool:
        """
        Validate filename follows naming convention.
        
        Args:
            filename: Filename to validate
            subject_id: Expected subject ID
        
        Returns:
            True if filename is valid, False otherwise
        """
        # Check if filename starts with subject ID followed by underscore
        if not filename.startswith(f"{subject_id}_"):
            return False
        
        # Check if filename contains at least one sequence token
        has_sequence = any(
            pattern.search(filename) 
            for pattern in cls.SEQUENCE_PATTERNS.values()
        )
        
        return has_sequence
    
    @classmethod
    def get_sequence_type(cls, filename: str) -> Optional[str]:
        """
        Extract sequence type from filename.
        
        Args:
            filename: Filename to analyze
        
        Returns:
            Sequence type (T1, T2, FLAIR) or None if not found
        """
        for seq_type, pattern in cls.SEQUENCE_PATTERNS.items():
            if pattern.search(filename):
                return seq_type
        return None
    
    @classmethod
    def count_sequences(cls, directory: Path) -> Dict[str, int]:
        """
        Count sequences by type in directory.
        
        Args:
            directory: Directory to scan
        
        Returns:
            Dictionary with counts for each sequence type
        """
        counts = {"T1": 0, "T2": 0, "FLAIR": 0}
        
        if not directory.exists():
            return counts
        
        for file_path in directory.iterdir():
            if not file_path.is_file() or not cls.is_nifti_file(file_path):
                continue
            
            seq_type = cls.get_sequence_type(file_path.name)
            if seq_type:
                counts[seq_type] += 1
        
        return counts
    
    @classmethod
    def find_nifti_files(cls, directory: Path) -> List[Path]:
        """
        Find all NIfTI files in directory.
        
        Args:
            directory: Directory to scan
        
        Returns:
            List of NIfTI file paths
        """
        if not directory.exists():
            return []
        
        return sorted([
            f for f in directory.iterdir()
            if f.is_file() and cls.is_nifti_file(f)
        ])


# ============================================================================
# Subject Discovery
# ============================================================================

def discover_subjects(input_dir: Path, logger: logging.Logger) -> List[str]:
    """
    Discover subject directories in input directory.
    
    Args:
        input_dir: Input directory containing subject folders
        logger: Logger instance
    
    Returns:
        List of subject IDs
    
    Raises:
        ValueError: If no subjects found
    """
    if not input_dir.exists():
        raise ValueError(f"Input directory not found: {input_dir}")
    
    logger.info("Discovering subjects...")
    
    subjects = sorted([
        d.name for d in input_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])
    
    if not subjects:
        raise ValueError(f"No subject directories found in {input_dir}")
    
    for subject in subjects:
        logger.info(f"  Found: {subject}")
    
    logger.info(f"Total subjects found: {len(subjects)}")
    
    return subjects


# ============================================================================
# GPU Detection
# ============================================================================

def detect_gpu() -> bool:
    """
    Detect if GPU is available.
    
    Returns:
        True if GPU detected, False otherwise
    """
    # Check environment variable override
    use_gpu_env = os.environ.get("USE_GPU", "auto").lower()
    
    if use_gpu_env == "false":
        return False
    if use_gpu_env == "true":
        return True
    
    # Auto-detect
    if not shutil.which("nvidia-smi"):
        return False
    
    try:
        subprocess.run(
            ["nvidia-smi"],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# ============================================================================
# Timing Utilities
# ============================================================================

class Timer:
    """Simple timer for measuring execution time."""
    
    def __init__(self):
        """Initialize timer."""
        self.start_time = None
        self.end_time = None
    
    def start(self) -> None:
        """Start the timer."""
        self.start_time = datetime.now()
    
    def stop(self) -> None:
        """Stop the timer."""
        self.end_time = datetime.now()
    
    def elapsed(self) -> Tuple[int, int, int]:
        """
        Get elapsed time.
        
        Returns:
            Tuple of (hours, minutes, seconds)
        """
        if self.start_time is None:
            return (0, 0, 0)
        
        end = self.end_time if self.end_time else datetime.now()
        delta = end - self.start_time
        
        total_seconds = int(delta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return (hours, minutes, seconds)
    
    def elapsed_str(self) -> str:
        """
        Get elapsed time as formatted string.
        
        Returns:
            Formatted time string (e.g., "1h 23m 45s")
        """
        hours, minutes, seconds = self.elapsed()
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

