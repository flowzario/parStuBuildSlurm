import parStuBuildSlurm as psb
import os

# instantiate a ParametricStudy object
myStudy = psb.ParametricStudy(
        studyName='trydemo',
        defaultInputFileName='input.dat',
        defaultSLURMFileName='run.slurm',
        lineMod=psb.lineMod,
        parametric_info={
            'a':[0,1,2,3],
            'b':[4,5,6,7],
            'c-d':[[8,9],[7,3]] # grouped parameters
            }
        )

# uncomment next two lines to test running multiple jobs per node
# myStudy.multipleJobsPerNode = True
# myStudy.executableName = 'sleep'

# build the study directory structure and populate with
# modified input files and job submission scripts
myStudy.build()

# submit jobs to the HPC cluster
jobs_to_run_concurrently = 5
myStudy.hpcExecute(jobs_to_run_concurrently)
