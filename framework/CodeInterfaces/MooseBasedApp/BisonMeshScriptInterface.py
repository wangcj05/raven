"""
created on July 13, 2015

@author: tompjame
"""
from __future__ import division, print_function, unicode_literals, absolute_import
import warnings
warnings.simplefilter('default',DeprecationWarning)

import os
import copy
import sys
import re
import collections
from utils import toBytes, toStrish, compare
from CodeInterfaceBaseClass import CodeInterfaceBase

class BisonMeshScriptInterface(CodeInterfaceBase):
  """This class is used to couple raven to the Bison Mesh Generation Script using cubit (python syntax, NOT Cubit journal file)"""

  def generateCommand(self, inputFiles, executable, clargs=None, fargs=None):
    """Generate a command to run cubit using an input with sampled variables to output
       the perturbed mesh as an exodus file.
       @ In, inputFiles, the perturbed input files (list of Files) along with pass-through files from RAVEN.
       @ In, executable, the Cubit executable to run (string)
       @ In, clargs, command line arguments
       @ In, fargs, file-based arguments
       @Out, (string, string), execution command and output file name
    """
    found = False
    for index, inputFile in enumerate(inputFiles):
      if inputFile.getExt() in self.getInputExtension():
        found = True
        break
    if not found: raise IOError('None of the input files has one of the following extensions: ' + ' '.join(self.getInputExtension()))
    outputfile = 'mesh~'+inputFiles[index].getBase()
    executeCommand = ('python '+executable+ ' -i ' +inputFiles[index].getFilename()+' -o '+outputfile+'.e')
    return executeCommand,outputfile

  def createNewInput(self, currentInputFiles, oriInputFiles, samplerType, **Kwargs):
    """Generates new perturbed input files.
       @ In, currentInputFiles, list of Files objects, most recently perturbed files
       @ In, originInputFiles, the template input files originally shown
       @ In, samplerType, the sampler type used (not used in this algorithm)
       @ In, Kwargs, dictionary of key-val pairs
       @Out, list of perturbed files
    """
    import BISONMESHSCRIPTparser
    for index, inputFile in enumerate(oriInputFiles):
      if inputFile.getExt() == self.getInputExtension():
        break
    parser = BISONMESHSCRIPTparser.BISONMESHSCRIPTparser(currentInputFiles[index])
    # Copy dictionary of sampled vars sent to interface and change name of alias (if it exists)
    sampledDict = copy.deepcopy(Kwargs['SampledVars'])
    for alias,var in Kwargs['alias'].items():
      sampledDict[var] = Kwargs['SampledVars'][alias]
      del sampledDict[alias]
    parser.modifyInternalDictionary(**sampledDict)
    # Copy original mesh generation input file and write new input from sampled vars
    temp = str(oriInputFiles[index])[:]
    newInputFiles = copy.deepcopy(currentInputFiles)
    newInputFiles[index].close()
    newInputFiles[index].setBase(currentInputFiles[index].getBase()+'_'+Kwargs['prefix'])
    parser.writeNewInput(newInputFiles[index].getAbsFile())
    return newInputFiles

  def addDefaultExtension(self):
    """Adds the given extension to list of input file extensions."""
    self.addInputExtension(['py'])

  def finalizeCodeOutput(self, command, output, workingDir):
    """Cleans up files in the working directory that are not needed after the run
       @ In, command, (string), command used to run the just ended job
       @ In, output, (string), the Output name root
       @ In, workingDir, (string), the current working directory
    """
    # Append wildcard strings to workingDir for files wanted to be removed
    cubitjour_files = os.path.join(workingDir,'cubit*')
    pyc_files = os.path.join(workingDir,'*.pyc')
    # Inform user which files will be removed
    print('files being removed:\n'+cubitjour_files+'\n'+pyc_files)
    # Remove Cubit generated journal files
    self.rmUnwantedFiles(cubitjour_files)
    # Remove .pyc files created when running BMS python inputs
    self.rmUnwantedFiles(pyc_files)

  def rmUnwantedFiles(self, path_to_files):
    """Method to remove unwanted files after completing the run
       @ In, path_to_files, (string), path to the files to be removed
    """
    success = os.system('rm '+path_to_files)
    if success != 0:
      print(success,"Error removing ",path_to_files)