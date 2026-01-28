#!/bin/bash
#SBATCH --job-name=test_step3
#SBATCH --partition=general
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/mnt/nfs/home/urmc-sh.rochester.edu/pndagiji/Documents/tuber_project/logs/test_step3-%j.out

cd /mnt/nfs/home/urmc-sh.rochester.edu/pndagiji/Documents/tuber_project
python3 scripts/3_register_to_mni.py --project-root .



