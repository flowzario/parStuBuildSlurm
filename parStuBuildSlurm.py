import os
import shutil
import subprocess as sp
import time

class ParametricStudy:





    # -----------------------------------------------
    # "Special" methods (i.e. constructor etc)
    # -----------------------------------------------





    def __init__(self,**kwargs):
        """Initialize the parametric study with appropriate values."""
        # "public" members
        self.studyName = None
        self.defaultInputFileName = None
        self.defaultSLURMFileName = None
        self.lineMod = None
        self.parametric_info = None
        self.multipleJobsPerNode = False
        self.executableName = None
        self.coresPerNode = 16
        self.coresPerJob = 1
        # "private" members
        self._startDir = os.getcwd()+'/'
        self._numOfParamSets = None
        self._subDir = None
        self._subDirName = None
        self._listOfSets = None
        self._buildComplete = False
        self._allJobs = None
        self._execCommand = None
        self._jobsPerNode = None
        self._numNodes = None
        self._leftOverJobs = None

        validKwargs = {
                'studyName':self.studyName,
                'defaultInputFileName':self.defaultInputFileName,
                'defaultSLURMFileName':self.defaultSLURMFileName,
                'lineMod':self.lineMod,
                'parametric_info':self.parametric_info
                }

        # check for valid keyword arguments
        for key in kwargs:
            if key not in validKwargs:
                eflag = key
                print(str(eflag)+' is not a valid keyword! Valid keyword args:')
                for k in validKwargs:
                    print(k)
                raise ValueError('invalid keyword argument')

        # assign keyword args to respective class attributes
        for key in kwargs:
            validKwargs[key] = kwargs[key]
        self.studyName = validKwargs['studyName']
        self.defaultInputFileName = validKwargs['defaultInputFileName']
        self.defaultSLURMFileName = validKwargs['defaultSLURMFileName']
        self.lineMod = validKwargs['lineMod']
        self.parametric_info = validKwargs['parametric_info']






    # -----------------------------------------------
    # "PRIVATE" methods
    # -----------------------------------------------




    def _checkBuildInit(self):
        """ Check to make sure that the build method was initialized properly."""
        classMembers = {
                'studyName':self.studyName,
                'defaultInputFileName':self.defaultInputFileName,
                'defaultSLURMFileName':self.defaultSLURMFileName,
                'lineMod':self.lineMod,
                'parametric_info':self.parametric_info
                }
        goodInitialization = True
        # make sure essential class attributes have been initialized
        for mem in classMembers:
            if classMembers[mem] == None:
                goodInitialization = False
                print('Class member '+mem+' was not initialized to an')
                print('appropriate value or data structure.')
        if not goodInitialization:
            print('You must initialize all class members before attempting')
            print('to build a parametric study. Class members that must be')
            print('initialized include:')
            for mem in classMembers:
                print(mem)
        # if running more than 1 job per node check to make sure certain
        # attributes have been initialized
        if self.multipleJobsPerNode:
            if self.executableName == None:
                print('must define the executableName attribute with the')
                print('executable file\'s name (string type).')
                goodInitialization = False
        return goodInitialization





    def _calcNumUniqueParamSets(self):
        """Calculate the number of unique parameter sets in the parametric study."""
        # calculate the total number of unique parameter sets
        self._numOfParamSets = 1
        for k in sorted(self.parametric_info):
            # check for grouped parameters
            if type(self.parametric_info[k][0]) == list:
                self._numOfParamSets *= len(self.parametric_info[k][0])
            else:
                self._numOfParamSets *= len(self.parametric_info[k])

        # make a list that holds a dictionary for each unique parameter set
        container = self.parametric_info.copy()
        for k in container:
            container[k] = 0
        self._listOfSets = []
        for i in range(self._numOfParamSets):
            self._listOfSets.append(container.copy())

        # calculate each unique parameter set
        skip = 1
        # iterate over each parameter or group of parameters in parametric_info
        for p in sorted(self.parametric_info):
            # grouped parameter values are stored in parametric_info as a list of lists.
            # i.e. one list for each grouped parameter
            if type(self.parametric_info[p][0])==list:
                numParValues = len(self.parametric_info[p][0])
            else:
                numParValues = len(self.parametric_info[p])
            val_i =0
            for i, pSet in enumerate(self._listOfSets):
                if type(self.parametric_info[p][0])==list:
                    pSet[p] = []
                    for grpPar in self.parametric_info[p]:
                        pSet[p].append(grpPar[val_i])
                else:
                    pSet[p] = self.parametric_info[p][val_i]
                if i%skip == 0:
                    val_i += 1
                if val_i == numParValues:
                    val_i = 0
            skip *= numParValues

        # sort the list of parameter sets
        self._listOfSets.sort(key=self._specialSort)





    def _specialSort(self,dic):
        """special sort function for sorting _listOfSets."""
        crit = []
        mykeys = sorted(dic.keys())
        for key in mykeys:
            crit.append(dic[key])
        return tuple(crit)





    def _createDirStructure(self):
        """Create the main study directory and a sub-directory for each parameter set."""
        # make the main study directory
        os.makedirs(self._startDir + self.studyName)

        # create sub directory names
        self._subDir = []
        self._subDirName = []
        for s in self._listOfSets:
            name = ''
            for param in sorted(s):
                # check for grouped parameters
                if type(s[param]) == list:
                    name += str(param)
                    for val in s[param]:
                        name += '-'+str(val)
                else:
                    name += str(param)+str(s[param])
            # create path to sub-directory
            pathPlusSub = self._startDir+self.studyName+'/'+name
            # save sub-directory name and path for later use
            self._subDirName.append(name)
            self._subDir.append(pathPlusSub)
            # create the sub-directory
            os.makedirs(pathPlusSub)





    def _saveStudyInfo(self):
        """Write information about the study to a file named 'parStudyInfo.txt'."""
        path = self.studyName + '/parStudyInfo.txt'
        with open(path,'w') as fout:
            # write header
            fout.write('Parameters varied and their values:\n')
            # write parameter names and values
            for par in sorted(self.parametric_info):
                fout.write(par + ':\t'+str(self.parametric_info[par]))
                fout.write('\n')
            # write names of parameter set subdirectories
            fout.write('Unique parameter set directory names:\n')
            for parSet in sorted(self._subDirName):
                fout.write(parSet + '\n')
        fout.close()





    def _modInputFile(self,param,value,curInFi):
        """Uses lineMod function to modify input file parameters."""
        # create temporary copy of input file
        tempInFi = os.getcwd()+'/temp'
        shutil.copy(curInFi,tempInFi)
        # read from temp and write modified version to original
        with open(tempInFi,'r') as fin:
            with open(curInFi,'w') as fout:
                for line in fin:
                    items = line.split()
                    if len(items) > 0:
                        if param == items[0]:
                            modifiedLine = self.lineMod(line,param,value)
                            fout.write(modifiedLine)
                        else:
                            fout.write(line)
        fout.close()
        fin.close()
        os.remove(tempInFi)






    def _createInputFiles(self):
        """Copy default input file to sub-directories and modify each one accordingly."""
        for i, s in enumerate(self._listOfSets):
            # populate sub-directory with input file
            os.system('cp ' + self.defaultInputFileName + ' ' + self._subDir[i])
            # input file in current sub-directory
            inputFile = self._subDir[i]+'/'+self.defaultInputFileName
            
            # modify input file by looping over each parameter to be modified
            for par in sorted(s):
                # check for grouped parameters
                if type(s[par])==list:
                    paramNames = par.split('-')
                    # check that grouped parameters were grouped with assumed syntax
                    assert(len(paramNames)==len(s[par]))
                    # modify each of the grouped params in the input file
                    for n,val in enumerate(s[par]):
                        self._modInputFile(paramNames[n],val,inputFile)
                else:
                    # change input file for single non-grouped parameter
                    self._modInputFile(par,s[par],inputFile)





    def _setupJobScripts(self):
        """Create job scripts for jobs that use 1 or more node."""
        # create a job script for each unique parameter set
        for i, s in enumerate(self._listOfSets):
            # populate sub-directory with SLURM file
            os.system('cp ' + self.defaultSLURMFileName + ' ' + self._subDir[i])

            # modify SLURM file's job name
            # create temporary copy of SLURM file
            curSlurmFi = self._subDir[i]+'/'+self.defaultSLURMFileName
            tempSlurmFi = self._subDir[i]+'/temp'
            shutil.copy(curSlurmFi,tempSlurmFi)
            with open(tempSlurmFi,'r') as fin:
                with open(curSlurmFi,'w') as fout:
                    for line in fin:
                        if '#SBATCH --job-name=' in line:
                            fout.write('#SBATCH --job-name='+self._subDirName[i]+'\n')
                        else:
                            fout.write(line)
            fout.close()
            fin.close()
            os.remove(tempSlurmFi)





    def _findExecCommand(self):
        "Finds the executable command in the default SLURM script."""
        # get the executable command line from the default SLURM file
        with open(self.defaultSLURMFileName) as fin:
            for line in fin:
                if self.executableName in line:
                    self._execCommand = line
        fin.close
        # strip off new line character from executable command
        self._execCommand = self._execCommand.split('\n')[0]

        # check that the executable command was found in the SLURM file
        if self._execCommand == None:
            print('could not find executable command line in')
            print(self.defaultSLURMFileName +'. No instance of')
            print('"'+self.executableName+'" in '+self.defaultSLURMFileName+'.')
            return False
        else:
            return True





    def _calcNumNodesNeeded(self):
        """Calculate how many nodes are needed for the multiple jobs per case."""
        print('Proceeding with the assumption that each node has '+str(self.coresPerNode)+' cores')
        print('and each job will run on only '+str(self.coresPerJob)+' core(s). If this is not the')
        print('case, restart and define the ParametricStudy attributes')
        print('"coresPerNode" and "coresPerJob" with the appropriate values.')
        self._jobsPerNode = int(int(self.coresPerNode)/int(self.coresPerJob))
        if self._jobsPerNode < 1 or self._jobsPerNode > self.coresPerNode:
            print('invalid value for either "coresPerNode" attribute or "coresPerJob" attribute.')
            raise AssertionError
        self._numNodes = int(int(self._numOfParamSets)/int(self._jobsPerNode))
        self._leftOverJobs = int(int(self._numOfParamSets)%int(self._jobsPerNode))





    def _setupMultipleJobsPerNode(self):
        """Create job scripts that run more than one job per node."""
        # create directory for job scripts and populate with needed SLURM files
        os.makedirs(self._startDir+self.studyName+'/jobScripts')
        jobCounter = 0
        jstart = 0
        jend = 0
        for i in range(self._numNodes):
            jstart = i*self._jobsPerNode+1
            jend = (i+1)*self._jobsPerNode
            jnum = str(jstart)+'-'+str(jend)
            curSlurmFi = self._startDir+self.studyName+'/jobScripts/jobs'+jnum+'.slurm'
            os.system('cp '+self._startDir+self.defaultSLURMFileName+' '+curSlurmFi)

            # alter the SLURM script to run jobs assigned it
            with open(self.defaultSLURMFileName,'r') as fin:
                with open(curSlurmFi,'w') as fout:
                    for line in fin:
                        if '#SBATCH --job-name=' in line:
                            fout.write('#SBATCH --job-name=jobs'+jnum+'\n')
                        elif self.executableName in line:
                            fout.write('# go to job sub-directories and start jobs then wait\n')
                            writeStart = fout.tell()
                            break
                        else:
                            fout.write(line)

                    # write bash code to SLURM file that starts and waits for jobs assigned this file
                    for j in range(self._jobsPerNode):
                        fout.write('cd '+self._subDir[jobCounter]+'\n')
                        fout.write(self._execCommand+'&\n')
                        jobCounter += 1
                    fout.write('wait\n')
                    # write the rest of the lines from the default SLURM file
                    for line in fin:
                        fout.write(line)
            fin.close()
            fout.close()

        return jend,jobCounter




        
    def _handleLeftOverJobs(self,jend,jobCounter):
        """Handle setup last node when their are left over jobs that do not fill an entire node."""
        print('jend='+str(jend))
        jstart = jend + 1
        jend = jend + self._leftOverJobs
        jnum = str(jstart)+'-'+str(jend)
        curSlurmFi = self._startDir+self.studyName+'/jobScripts/jobs'+jnum+'.slurm'
        os.system('cp '+self._startDir+self.defaultSLURMFileName+' '+curSlurmFi)

        # alter the SLURM script to run jobs assigned it
        with open(self.defaultSLURMFileName,'r') as fin:
            with open(curSlurmFi,'w') as fout:
                for line in fin:
                    if '#SBATCH --job-name=' in line:
                        fout.write('#SBATCH --job-name=jobs'+jnum+'\n')
                    elif self.executableName in line:
                        fout.write('# go to job sub-directories and start jobs then wait\n')
                        writeStart = fout.tell()
                        break
                    else:
                        fout.write(line)

                # write bash code to SLURM file that starts and waits for jobs assigned this file
                for j in range(self._leftOverJobs):
                    fout.write('cd '+self._subDir[jobCounter]+'\n')
                    fout.write(self._execCommand+'&\n')
                    jobCounter += 1
                fout.write('wait\n')
                # write the rest of the lines from the default SLURM file
                for line in fin:
                    fout.write(line)
        fin.close()
        fout.close()





    def _checkHpcExecInit(self,numConcJobs):
        """Make sure study was initialized correctly for running the hpcExecute method."""
        # make sure build method has been called aready
        if not self._buildComplete:
            print('You must run the build method before running the hpcExecute method')
        assert self._buildComplete

        # check for correct input
        if numConcJobs < 1:
            print('numConcJobs < 0.')
        # convert numConcJobs to an integer if it is not already
        numConcJobs = int(numConcJobs)
        assert numConcJobs > 0





    def _launchJobs(self,numConcJobs):
        """Launches 1 or more jobs per node on the HPC using sbatch."""
        jobIDs = []
        # make sure numConcJobs is less than the number of parameter sets
        if numConcJobs > self._numOfParamSets:
            print('numConcJobs is more than needed. Adjusting to needed amount:')
            while numConcJobs > self._numOfParamSets:
                numConcJobs -= 1
            print('changed to numConcJobs='+str(numConcJobs))
        assert numConcJobs <= self._numOfParamSets and numConcJobs > 0

        # start the first batch of jobs to run simultaneously
        for i in range(numConcJobs):
            # change to the sub-directory to start the job
            os.chdir(self._subDir[i])
            # build the command to submit job to the HPC
            cmd = ['sbatch',self.defaultSLURMFileName]
            print('\t'+' '.join(cmd))
            # submit the job and get the job ID
            jID = sp.check_output(cmd)
            # store the job ID in a list
            jobIDs.append(jID.split('.')[0])
            # keep a running list of all job IDs
            self._allJobs.append(jID.split('.')[0])

        # start the rest of the jobs on hold until the first batch finishes
        for sd in self._subDir[numConcJobs:]:
            os.chdir(sd)
            jobStr = jobIDs[0]
            # build the command to submit job to the HPC
            cmd = ['sbatch','--dependency=afterany:'+jobStr.split()[3],self.defaultSLURMFileName]
            print('\t'+' '.join(cmd))
            # submit the job and get the job ID
            jID = sp.check_output(cmd)
            # store the job ID in a list
            jobIDs.append(jID.split('.')[0])
            # update running list of all job IDs
            self._allJobs.append(jID.split('.')[0])
            # make sure job list never grows beyond numConcJobs
            jobIDs.pop(0)





    def _launchMultiJobsPerNode(self,numConcJobs):
        """Launches multiple jobs per node on the HPC using sbatch."""
        jobIDs = []
        # make sure numConcJobs is in valid range
        if self._leftOverJobs > 0:
            self._numNodes += 1
        if numConcJobs > self._numNodes:
            print('numConcJobs is more than needed. Adjusting to needed amount:')
            while numConcJobs > self._numNodes:
                numConcJobs -= 1
            print('changed to numConcJobs='+str(numConcJobs))
        assert numConcJobs <= self._numNodes and numConcJobs > 0
        # get list of multi-job SLURM scripts
        jobScripts = os.listdir(self._startDir+self.studyName+'/jobScripts')
        os.chdir(self._startDir+self.studyName+'/jobScripts')
        # start the first batch of jobs to run simultaneously
        for i in range(numConcJobs):
            # build the command to submit job to the HPC
            cmd = ['sbatch',jobScripts[i]]
            print('\t'+' '.join(cmd))
            # submit the job and get the job ID
            jID = sp.check_output(cmd)
            # store the job ID in a list
            jobIDs.append(jID.split('.')[0])
            # keep a running list of all job IDs
            self._allJobs.append(jID.split('.')[0])

        # start the rest of the jobs on hold until the first batch finishes
        for js in jobScripts[numConcJobs:]:
            jobStr = jobIDs[0]
            # build the command to submit job to the HPC # added .split()[3]
            cmd = ['sbatch','dependency=afterany:'+jobStr.split()[3],js]
            print('\t'+' '.join(cmd))
            # submit the job and get the job ID
            jID = sp.check_output(cmd)
            # store the job ID in a list
            jobIDs.append(jID.split('.')[0])
            # update running list of all job IDs
            self._allJobs.append(jID.split('.')[0])
            # make sure job list never grows beyond numConcJobs
            jobIDs.pop(0)







    # -----------------------------------------------
    # "PUBLIC" METHODS
    # -----------------------------------------------





    def build(self):
        """Build the parametric study directories and files."""
        print('\n\nBuilding parametric study directory structure and populating with necessary files...')
        start = time.time()
        assert(self._checkBuildInit())
        self._calcNumUniqueParamSets()
        self._createDirStructure()
        self._saveStudyInfo()
        self._createInputFiles()
        if not self.multipleJobsPerNode:
            self._setupJobScripts()
        else:
            assert(self._findExecCommand())
            self._calcNumNodesNeeded()
            je,jc = self._setupMultipleJobsPerNode()
            if self._leftOverJobs > 0:
                self._handleLeftOverJobs(je,jc)
        self._buildComplete = True
        end = time.time()
        print('Setup the whole study in '+str(end-start)+' seconds!')





    def hpcExecute(self,numConcJobs):
        """Start parametric study jobs on the HPC using the "sbatch" command."""
        print('\n\nLaunching Jobs on the HPC using the following commands:\n')
        start = time.time()
        self._checkHpcExecInit(numConcJobs)
        self._allJobs = []
        if not self.multipleJobsPerNode:
            self._launchJobs(numConcJobs)
        else:
            self._launchMultiJobsPerNode(numConcJobs)

        # change back to the starting directory
        os.chdir(self._startDir+self.studyName)
        # write job IDs to a file in case they need to be deleted later
        print('\nWriting Job IDs file...')
        with open('jobIDs.txt','w') as fout:
            for jobID in self._allJobs:
                fout.write(jobID.split()[3]+'\n')
        fout.close()
        end = time.time()
        print('\nSubmitted all those jobs in '+str(end-start)+' seconds!')





    def batchDelete(self):
        """Delete all the jobs running on the HPC for a given parametric study."""
        start = time.time()
        # checking for jobID.txt file existence
        assert os.path.isfile(self._startDir+self.studyName+'/jobIDs.txt')

        # make sure studyName atribute is defined
        bad = self.studyName == None
        if bad:
            print('must define attribute "studyName" before calling this method.')
            print('It should be defined as a string that is the name of the parametric')
            print('study directory that contains the jobIDs.txt file.')
        assert not bad

        print('\n\nDeleting jobs stored in the parametric study\'s jobIds.txt file!')
        with open(self._startDir+self.studyName+'/jobIDs.txt') as fin:
            for line in fin:
                jobID = line.split('\n')[0]
                cmd = ['scancel',jobID]
                print('Deleting job with job ID: '+jobID)
                try:
                    cmdReturn = sp.check_output(cmd)
                except Exception as e:
                    print('exception caught: '+ type(e).__name__)
        fin.close()
        end = time.time()
        print('\nDeleted all those jobs in '+str(end-start)+' seconds!')






# -----------------------------------------------
# Functions that are not class methods
# -----------------------------------------------





def lineMod(line,par,par_value):
    """An input file line modifying function that works for input files with format 'parameterName = parameterValue'."""
    rep_value = str(par_value)+str('\n')
    if par in line:
        orig_value = str(line.split(' = ')[1])
        rep_line = line.replace(orig_value,rep_value)
        return rep_line
    else:
        return None
