#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gpus=1
#SBATCH --partition=gpu
#SBATCH --time=60:00:00
#SBATCH --output=train.out
#SBATCH --job-name=train

# Execute program located in $HOME
source activate marinedebrisdetector

srun python marinedebrisdetector/train.py
