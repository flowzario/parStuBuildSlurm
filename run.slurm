#!/bin/bash
#SBATCH --job-name=jobName
#SBATCH --partition comp06
#SBATCH --output=test.slurm.out
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1
#SBATCH --time=00:00:30
cd $SLURM_SUBMIT_DIR
echo "running the executable" >> simTest.txt
sleep 5
