# Copyright 2017 Battelle Energy Alliance, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
  Module where the base class of optimizer is. Adapted from Sampler.py.

  Created on Jan. 15, 2019
  @author: wangc, mandd
"""
#for future compatibility with Python 3--------------------------------------------------------------
from __future__ import division, print_function, unicode_literals, absolute_import
import warnings
warnings.simplefilter('default',DeprecationWarning)
#End compatibility block for Python 3----------------------------------------------------------------

#External Modules------------------------------------------------------------------------------------
import sys
import copy
import abc
import numpy as np
from collections import deque
#External Modules End--------------------------------------------------------------------------------

#Internal Modules------------------------------------------------------------------------------------
from utils import utils, randomUtils, InputData
from Assembler import Assembler
from Samplers import Sampler
#Internal Modules End--------------------------------------------------------------------------------

class OptimizerBase(Sampler):
  """
    This is the base class for optimizers
    Optimizer is a special type of "samplers" that own the optimization strategy (Type) and they generate the input values to optimize a loss function.
    The most significant deviation from the Samplers is that they do not use distributions.
  """
  @classmethod
  def getInputSpecification(cls):
    """
      Method to get a reference to a class that specifies the input data for class cls.
      @ In, cls, the class for which we are retrieving the specification
      @ Out, inputSpecification, InputData.ParameterInput, class to use for specifying input of cls.
    """
    inputSpecification = super(OptimizerBase, cls).getInputSpecification()
    # assembled objects
    # TargetEvaluation represents the container where the model evaluations are stored
    targEval = InputData.parameterInputFactory('TargetEvaluation', contentType=InputData.StringType, strictMode=True)
    targEval.addParam('type', InputData.StringType, True)
    targEval.addParam('class', InputData.StringType, True)
    inputSpecification.addSub(targEval)
    # Sampler can be used to initialize the starting points for some of the variables
    sampler = InputData.parameterInputFactory('Sampler', contentType=InputData.StringType, strictMode=True)
    sampler.addParam('type', InputData.StringType, True)
    sampler.addParam('class', InputData.StringType, True)
    inputSpecification.addSub(sampler)
    # Function indicateds the external function where the constraints are stored
    function = InputData.parameterInputFactory('Function', contentType=InputData.StringType, strictMode=True)
    function.addParam('type', InputData.StringType, True)
    function.addParam('class', InputData.StringType, True)
    inputSpecification.addSub(function)
    # variable
    ## was also part of Sampler, but we need to rewrite variable, so remove it first
    inputSpecification.removeSub('variable')
    variable = InputData.parameterInputFactory('variable', strictMode=True)
    variable.addParam("name", InputData.StringType, True)
    variable.addParam("shape", InputData.IntegerListType, required=False)
    upperBound = InputData.parameterInputFactory('upperBound', contentType=InputData.FloatType, strictMode=True)
    lowerBound = InputData.parameterInputFactory('lowerBound', contentType=InputData.FloatType, strictMode=True)
    initial = InputData.parameterInputFactory('initial',contentType=InputData.StringListType)
    variable.addSub(upperBound)
    variable.addSub(lowerBound)
    variable.addSub(initial)
    inputSpecification.addSub(variable)

    # objectVar
    objectVar = InputData.parameterInputFactory('objectVar', contentType=InputData.StringType, strictMode=True)
    inputSpecification.addSub(objectVar)

    # initialization
    init = InputData.parameterInputFactory('initialization', strictMode=True)
    limit      = InputData.parameterInputFactory('limit', contentType=InputData.IntegerType)
    minmax     = InputData.parameterInputFactory('type', contentType=minmaxEnum)
    init.addSub(limit)
    init.addSub(minmax)
    inputSpecification.addSub(init)

    return inputSpecification

  def __init__(self):
    """
      Default Constructor that will initialize member variables with reasonable
      defaults or empty lists/dictionaries where applicable.
      @ In, None
      @ Out, None
    """
    Sampler.__init__(self)
    #counters
    ## while "counter" is scalar in Sampler, it's more complicated in Optimizer
    self.counter                        = {}                        # Dict containing counters used for based and derived class
    self.counter['mdlEval']             = 0                         # Counter of the model evaluation performed (better the input generated!!!). It is reset by calling the function self.initialize
    self.counter['varsUpdate']          = 0                         # Counter of the optimization iteration.
    self.counter['recentOptHist']       = {}                        # as {traj: [pt0, pt1]} where each pt is {'inputs':{var:val}, 'output':val}, the two most recently-accepted points by value
    self.counter['prefixHistory']       = {}                        # as {traj: [prefix1, prefix2]} where each prefix is the job identifier for each trajectory
    self.objVar                         = None                      # Objective variable to be optimized
    self.optVars                        = {}                        # By trajectory, current decision variables for optimization
    self.optType                        = None                      # Either max or min
    self.fullOptVars                    = None                      # Decision variables for optimization, full space
    self.optTraj                        = None                      # Identifiers of parallel optimization trajectories
    self.optVarsInitialized             = {}                        # Dict {var1:<initial> present?,var2:<initial> present?}
    #initialization parameters
    self.optVarsInit                    = {}                        # Dict containing upper/lower bounds and initial of each decision variables
    self.optVarsInit['upperBound']      = {}                        # Dict containing upper bounds of each decision variables
    self.optVarsInit['lowerBound']      = {}                        # Dict containing lower bounds of each decision variables
    self.optVarsInit['initial']         = {}                        # Dict containing initial values of each decision variables
    self.optVarsInit['ranges']          = {}                        # Dict of the ranges (min and max) of each variable's domain
    self.optVarsHist                    = {}                        # History of decision variables for each iteration
    #limits
    ## while "limit" is scalar in Sampler, it's more complicated in Optimizer
    self.limit                          = {}                        # Dict containing limits for each counter
    self.limit['mdlEval']               = 2000                      # Maximum number of the loss function evaluation
    self.limit['varsUpdate']            = 650                       # Maximum number of the optimization iteration.
    self.writeSolnExportOn              = None                      # Determines when we write to solution export (every step or final solution)
    self.paramDict                      = {}                        # Dict containing additional parameters for derived class
    #sampler-step communication
    self.submissionQueue                = {}                        # by traj, a place (deque) to store points that should be submitted some time after they are discovered
    self.constraintFunction             = None                      # External constraint function, could be not present
    self.solutionExport                 = None                      # This is the data used to export the solution
    self.nextActionNeeded               = (None,None)               # tool for localStillReady to inform localGenerateInput on the next action needed
    self.mdlEvalHist                    = None                      # Containing information of all model evaluation

    self.addAssemblerObject('TargetEvaluation','1')
    self.addAssemblerObject('Function','-1')

  def _readMoreXMLbase(self,xmlNode):
    """
      Function to read the portion of the xml input that belongs to the base optimizer only
      and initialize some stuff based on the inputs got
      @ In, xmlNode, xml.etree.ElementTree.Element, Xml element node1
      @ Out, None
    """
    paramInput = self.getInputSpecification()()
    paramInput.parseNode(xmlNode)

    # TODO some merging with base sampler XML reading might be possible, but in general requires different entries
    # first read all XML nodes
    for child in paramInput.subparts:
      #FIXME: the common variable reading should be wrapped up in a method to reduce the code redundancy
      if child.getName() == "variable":
        if self.fullOptVars is None:
          self.fullOptVars = []
        # store variable name
        varName = child.parameterValues['name']
        self.optVarsInitialized[varName] = False
        # store variable requested shape, if any
        if 'shape' in child.parameterValues:
          self.variableShapes[varName] = child.parameterValues['shape']
        self.fullOptVars.append(varName)
        self.optVarsInit['initial'][varName] = {}
        for childChild in child.subparts:
          if childChild.getName() == "upperBound":
            self.optVarsInit['upperBound'][varName] = childChild.value
          elif childChild.getName() == "lowerBound":
            self.optVarsInit['lowerBound'][varName] = childChild.value
          elif childChild.getName() == "initial":
            # for consistent with multi trajectory, we initialize with only one trajectory with index '0'
            self.optVarsInit['initial'][varName][0] = childChild.value
            self.optVarsInitialized[varName] = True
            initPoints = childChild.value
      elif child.getName() == "constant":
        name,value = self._readInConstant(child)
        self.constants[child.parameterValues['name']] = value
      elif child.getName() == "objectVar":
        self.objVar = child.value.strip()
      elif child.getName() == "restartTolerance":
        self.restartTolerance = child.value
      elif child.getName() == "initialization":
        for childChild in child.subparts:
          if childChild.getName() == "limit":
            self.limit['mdlEval'] = childChild.value
            #the manual once claimed that "A" defaults to iterationLimit/10, but it's actually this number/10.
          elif childChild.getName() == "type":
            self.optType = childChild.value
            if self.optType not in ['min', 'max']:
              self.raiseAnError(IOError, 'Unknown optimization type "{}". Available: "min" or "max"'.format(childChild.value))
          elif childChild.getName() == 'writeSteps':
            whenToWrite = childChild.value.strip().lower()
            if whenToWrite == 'every':
              self.writeSolnExportOn = 'every'
            elif whenToWrite == 'final':
              self.writeSolnExportOn = 'final'
            else:
              self.raiseAnError(IOError,'Unexpected frequency for <writeSteps>: "{}". Expected "every" or "final".'.format(whenToWrite))
          else:
            self.raiseAnError(IOError,'Unknown tag: '+childChild.getName())

    # now that XML is read, do some checks and defaults
    # set defaults
    if self.writeSolnExportOn is None:
      self.writeSolnExportOn = 'every'
    self.raiseAMessage('Writing to solution export on "{}" optimizer iteration.'.format(self.writeSolnExportOn))
    if self.optType is None:
      self.optType = 'min'

    # NOTE: optTraj can be changed in "initialize" if the user provides a sampler for seeding
    if self.optTraj is None:
      self.optTraj = [0]

    # check required settings TODO this can probably be removed thanks to the input checking!
    if self.objVar is None:
      self.raiseAnError(IOError, 'Object variable is not specified for optimizer!')
    if self.fullOptVars is None:
      self.raiseAnError(IOError, 'Decision variable(s) not specified for optimizer!')

    for var in self.getOptVars():
      if var not in self.variableShapes:
        self.variableShapes[var] = (1,)
      else:
        if len(self.variableShapes[var]) > 1:
          self.raiseAnError(NotImplementedError,'Matrices as inputs are not yet supported in the Optimizer. For variable "{}" received shape "{}"!'.format(var,self.variableShapes[var]))

    for varName in self.fullOptVars:
      if varName not in self.optVarsInit['upperBound'].keys():
        self.raiseAnError(IOError, 'Upper bound for '+varName+' is not provided' )
      if varName not in self.optVarsInit['lowerBound'].keys():
        self.raiseAnError(IOError, 'Lower bound for '+varName+' is not provided' )
      #store ranges of variables
      self.optVarsInit['ranges'][varName] = self.optVarsInit['upperBound'][varName] - self.optVarsInit['lowerBound'][varName]
      if len(self.optVarsInit['initial'][varName]) == 0:
        for traj in self.optTraj:
          self.optVarsInit['initial'][varName][traj] = None

  def checkConstraint(self, optVars):
    """
      Method to check whether a set of decision variables satisfy the constraint or not in UNNORMALIZED input space
      @ In, optVars, dict, dictionary containing the value of decision variables to be checked, in form of
        {varName: varValue}
      @ Out, violatedConstrains, dict, variable indicating the satisfaction of constraints at the point optVars,
        masks for the under/over violations
    """
    violatedConstrains = {'internal':[],'external':[]}
    if self.constraintFunction == None:
      satisfied = True
    else:
      satisfied = True if self.constraintFunction.evaluate("constrain",optVars) == 1 else False
      if not satisfied:
        violatedConstrains['external'].append(self.constraintFunction.name)
    for var in optVars:
      varSatisfy=True
      # this should work whether optVars is an array or a single value
      check = np.atleast_1d(optVars[var])
      overMask = check > self.optVarsInit['upperBound'][var]
      underMask = check < self.optVarsInit['lowerBound'][var]
      if np.sum(overMask)+np.sum(underMask) > 0:
        self.raiseAWarning('A variable violated boundary constraints! Details below (enable DEBUG printing)')
        self.raiseADebug('Violating values: "{}"={}'.format(var,optVars[var]))
        satisfied = False
        violatedConstrains['internal'].append( (var,underMask,overMask) )
    return violatedConstrains

  def checkIfBetter(self,a,b):
    """
      Checks if a is preferable to b for this optimization problem.  Helps mitigate needing to keep
      track of whether a minimization or maximation problem is being run.
      @ In, a, float, value to be compared
      @ In, b, float, value to be compared against
      @ Out, checkIfBetter, bool, True if a is preferable to b for this optimization
    """
    if self.optType == 'min':
      return a <= b
    elif self.optType == 'max':
      return a >= b

  def denormalizeData(self, optVars):
    """
      Method to normalize the data
      @ In, optVars, dict, dictionary containing the value of decision variables to be deormalized, in form of {varName: varValue}
      @ Out, optVarsDenorm, dict, dictionary containing the value of denormalized decision variables, in form of {varName: varValue}
    """
    pass

  def normalizeData(self, optVars):
    """
      Method to normalize the data
      @ In, optVars, dict, dictionary containing the value of decision variables to be normalized, in form of {varName: varValue}
      @ Out, optVarsNorm, dict, dictionary containing the value of normalized decision variables, in form of {varName: varValue}
    """
    pass

  def getOptVars(self, traj=0, full=False):
    """
      Returns the variables in the active optimization space
      @ In, traj, int, optional, if provided then only return variables in current trajectory
      @ In, full, bool, optional, if True will always give ALL the opt variables
      @ Out, optVars, list(string), variables in the current optimization space
    """
    if full:
      return self.fullOptVars
    else:
      return self.optVars[traj]

  def getQueuedPoint(self, traj=0, denorm=False):
    """
      Pops the first point off the submission queue (or errors if empty).
      @ In, traj, int, the trajectory from whose queue we should obtain an entry
      @ In, denorm, bool, optional, if True the input data will be denormalized before returning
      @ Out, prefix, str, #_#_#
      @ Out, point, dict, {var:val}
    """
    try:
      entry = self.submissionQueue[traj].popleft()
    except IndexError:
      self.raiseAnError(RuntimeError,'Tried to get a point from submission queue of trajectory "{}" but it is empty!'.format(traj))
    prefix = entry['prefix']
    point = entry['inputs']
    if denorm:
      point = self.denormalizeData(point)
    return prefix,point

  def getInitParams(self):
    """
      This function is called from the base class to print some of the information inside the class.
      Whatever is permanent in the class and not inherited from the parent class should be mentioned here
      The information is passed back in the dictionary. No information about values that change during the simulation are allowed
      @ In, None
      @ Out, paramDict, dict, dictionary containing the parameter names as keys
                              and each parameter's initial value as the dictionary values
    """
    paramDict = {}
    for variable in self.getOptVars():
      paramDict[variable] = 'is sampled as a decision variable'
    paramDict['limit_mdlEval' ]        = self.limit['mdlEval']
    paramDict['limit_optIter']         = self.limit['varsUpdate']
    paramDict.update(self.localGetInitParams())
    return paramDict

  def getCurrentSetting(self):
    """
      This function is called from the base class to print some of the information inside the class.
      Whatever is a temporary value in the class and not inherited from the parent class should be mentioned here
      The information is passed back in the dictionary
      @ In, None
      @ Out, paramDict, dict, dictionary containing the parameter names as keys
                              and each parameter's initial value as the dictionary values
    """
    paramDict = Sampler.getCurrentSetting()
    paramDict.pop('counter', None)
    paramDict['counter_mdlEval'       ] = self.counter['mdlEval']
    paramDict['counter_varsUpdate'    ] = self.counter['varsUpdate']
    paramDict.update(self.localGetCurrentSetting())
    return paramDict

  def initialize(self,externalSeeding=None,solutionExport=None):
    """
      This function should be called every time a clean optimizer is needed. Called before takeAstep in <Step>
      @ In, externalSeeding, int, optional, external seed
      @ In, solutionExport, DataObject, optional, a PointSet to hold the solution
      @ Out, None
    """
    # NOTE: counter['varsUpdate'] needs to be set AFTER self.optTraj length is set by the sampler (if used exclusively)
    self.counter['mdlEval'] = 0
    self.counter['varsUpdate'] = [0]*len(self.optTraj)
    self.optTrajLive = copy.deepcopy(self.optTraj)
    # TODO: We should use retrieveObjectFromAssemblerDict to get the Instance
    self.mdlEvalHist = self.assemblerDict['TargetEvaluation'][0][3]
    # check if the TargetEvaluation feature and target spaces are consistent
    ins  = self.mdlEvalHist.getVars("input")
    outs = self.mdlEvalHist.getVars("output")
    for varName in self.fullOptVars:
      if varName not in ins:
        self.raiseAnError(RuntimeError,"the optimization variable "+varName+" is not contained in the TargetEvaluation object "+self.mdlEvalHist.name)
    if self.objVar not in outs:
      self.raiseAnError(RuntimeError,"the optimization objective variable "+self.objVar+" is not contained in the TargetEvaluation object "+self.mdlEvalHist.name)
    self.solutionExport = solutionExport
    if self.solutionExport is None:
      self.raiseAnError(IOError,'The results of optimization cannot be obtained without a SolutionExport defined in the Step!')

    if type(solutionExport).__name__ not in ["PointSet","DataSet"]:
      self.raiseAnError(IOError,'solutionExport type must be a PointSet or DataSet. Got '+\
                                 type(solutionExport).__name__+ '!')
    # TODO: We should use retrieveObjectFromAssemblerDict to get the Instance
    if 'Function' in self.assemblerDict.keys():
      self.constraintFunction = self.assemblerDict['Function'][0][3]
      if 'constrain' not in self.constraintFunction.availableMethods():
        self.raiseAnError(IOError,'the function provided to define the constraints must have an implemented method called "constrain"')

    # TODO a bunch of the gradient-level trajectory initializations should be moved here.
    for traj in self.optTraj:
      self.optVars[traj]            = self.getOptVars() #initial as full space
      self.submissionQueue[traj]    = deque()

    #check initial point array consistency
    rightLen = len(self.optTraj) #the hypothetical correct length
    for var in self.getOptVars(full=True):
      haveLen = len(self.optVarsInit['initial'][var])
      if haveLen != rightLen:
        self.raiseAnError(RuntimeError,'The number of trajectories for variable "{}" is incorrect!  Got {} but expected {}!  Check the <initial> block.'.format(var,haveLen,rightLen))

    # check the constraint here to check if the initial values violate it
    varK = {}
    for trajInd in self.optTraj:
      for varName in self.getOptVars():
        varK[varName] = self.optVarsInit['initial'][varName][trajInd]
        self.checkConstraint(varK)

    # extend multivalue variables (aka vector variables, or variables with "shape")
    ## TODO someday take array of initial values from a DataSet
    for var,shape in self.variableShapes.items():
      if np.prod(shape) > 1:
        for traj in self.optTraj:
          baseVal = self.optVarsInit['initial'][var][traj]
          newVal = np.ones(shape)*baseVal
          self.optVarsInit['initial'][var][traj] = newVal

    self.localInitialize(solutionExport=solutionExport)

  def amIreadyToProvideAnInput(self):
    """
      This is a method that should be called from any user of the optimizer before requiring the generation of a new input.
      This method act as a "traffic light" for generating a new input.
      Reason for not being ready could be for example: exceeding number of model evaluation, convergence criteria met, etc.
      @ In, None
      @ Out, ready, bool, indicating the readiness of the optimizer to generate a new input.
    """
    ready = True if self.counter['mdlEval'] < self.limit['mdlEval'] else False
    if not ready:
      self.raiseAMessage('Reached limit for number of model evaluations!')
    ready = self.localStillReady(ready)
    return ready

  def _incrementCounter(self):
    """
      Increments counter and sets up prefix.
      @ In, None
      @ Out, None
    """
    self.counter['mdlEval'] +=1 #since we are creating the input for the next run we increase the counter and global counter
    self.inputInfo['prefix'] = str(self.counter['mdlEval'])

  def updateVariableHistory(self,data,traj=0):
    """
      Stores new historical points into the optimization history.
      @ In, data, dict, new input space entries as {var:#, var:#}
      @ In, traj, int, integer label of the current trajectory of interest
      @ Out, None
    """
    self.optVarsHist[traj][self.counter['varsUpdate'][traj]] = copy.deepcopy(data)

  @abc.abstractmethod
  def checkConvergence(self):
    """
      Method to check whether the convergence criteria has been met.
      @ In, none,
      @ Out, convergence, bool, variable indicating whether the convergence criteria has been met.
    """

  @abc.abstractmethod
  def clearCurrentOptimizationEffort(self):
    """
      Used to inform the subclass optimization effor that it needs to forget whatever opt data it is using
      for the current point (for example, gradient determination points) so that we can start new.
      @ In, None
      @ Out, None
    """
    # README: this method is necessary because the base class optimizer doesn't know what needs to be reset in the
    #         subclass, but the subclass doesn't know when it needs to call this method.
    pass

  def writeToSolutionExport(self, traj=0):
    """
      Standardizes how the solution export is written to.
      Uses data from "recentOptHist" and other counters to fill in values.
      @ In, traj, int, the trajectory for which an entry is being written
      @ Out, None
    """
    pass

  def _checkModelFinish(self, traj=0, updateKey, evalID):
    """
      Determines if the Model has finished running an input and returned the output
      @ In, traj, int, traj on which the input is being checked
      @ In, updateKey, int, the id of variable update on which the input is being checked
      @ In, evalID, int or string, indicating the id of the perturbation (int) or its a variable update (string 'v')
      @ Out, _checkModelFinish, tuple(bool, int), indicating whether the Model has finished the evaluation over input
             identified by traj+updateKey+evalID, the index of the location of the input in dataobject
    """
    if len(self.mdlEvalHist) == 0:
      return (False,-1)
    lookFor = '{}_{}_{}'.format(traj,updateKey,evalID)
    index,match = self.mdlEvalHist.realization(matchDict = {'prefix':lookFor})
    # if no match, return False
    if match is None:
      return False,-1
    # otherwise, return index of match
    return True, index

  def _createEvaluationIdentifier(self, trajID=0, iterID=0, evalType='v'):
    """
      Create evaluation identifier
      @ In, trajID, integer, trajectory identifier
      @ In, iterID, integer, iteration number (identifier)
      @ In, evalType, integer or string, evaluation type (v for variable update; otherwise id for gradient evaluation)
      @ Out, identifier, string, the evaluation identifier
    """
    identifier = str(trajID) + '_' + str(iterID) + '_' + str(evalType)
    return identifier

  def _expandVectorVariables(self):
    """
      Normally used to extend variables; in the Optimizer, we do that in localGenerateInput
      @ In, None
      @ Out, None
    """
    pass

  @abc.abstractmethod
  def _getJobsByID(self):
    """
      Overwritten by the base class; obtains new solution export values
      @ In, None
      @ Out, None
    """
    pass
