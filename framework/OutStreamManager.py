'''
Created on Nov 14, 2013

@author: alfoa
'''
#for future compatibility with Python 3--------------------------------------------------------------
from __future__ import division, print_function, unicode_literals, absolute_import
import warnings
warnings.simplefilter('default',DeprecationWarning)
if not 'xrange' in dir(__builtins__):
  xrange = range
#End compatibility block for Python 3----------------------------------------------------------------

import numpy as np
from BaseType import BaseType
import copy
import ast
from scipy.interpolate import griddata


class OutStreamManager(BaseType):
  '''
  ********************************************************************
  *                          OUTSTREAM CLASS                         *
  ********************************************************************
  *  This class is a general base class for outstream action classes *
  *  For example, a matplotlib interface class or Print class, etc.  *
  ********************************************************************
  '''
  def __init__(self):
    '''
      Init of Base class 
    '''
    BaseType.__init__(self)
    # outstreaming options
    self.options = {}
    # we are in interactive mode?
    self.interactive = True
    #counter
    self.counter = 0
    #overwrite outstream?
    self.overwrite = True

  def initialize(self,inDict):
    '''
    Function to link the source object to the outstream object (i.e. the Data)
    '''
    raise NotYetImplemented('Li Mortacci!!!!!! Non implementataaaa!!!!')
    
    
  def readMoreXML(self,xmlNode):
    '''
    Function to read the portion of the xml input that belongs to this specialized class
    and initialize some stuff based on the got inputs 
    @ In, xmlNode    : Xml element node
    @ Out, None
    '''
    BaseType.readMoreXML(self,xmlNode)
    if 'interactive' in xmlNode.attrib.keys():
      if xmlNode.attrib['interactive'].lower() in ['t','true','on']: self.interactive = True
      else: self.interactive = False
    if 'overwrite' in xmlNode.attrib.keys():
      if xmlNode.attrib['overwrite'].lower() in ['t','true','on']: self.overwrite = True
      else: self.overwrite = False    

  def addInitParams(self,tempDict):
    '''
    Function adds the initial parameter in a temporary dictionary
    @ In, tempDict
    @ Out, tempDict 
    '''
    return tempDict

  def finalize(self):
    '''
    Function to finalize the outstream.Each outstream specialized class must implement it
    @ In, None
    @ Out, None 
    '''
    pass 

  def addOutput(self):
    '''
    Function to add a new output source (for example a CSV file or a HDF5 object)
    @ In, toLoadFrom, source object
    @ Out, None 
    '''
    # this function adds the file name/names to the
    # filename list
    
#  def getInpParametersValues(self):
#    return self.inpParametersValues  
#
#  def getOutParametersValues(self):
#    return self.outParametersValues 

  def retrieveHistories(self):
    '''
    Function to retrieve histories from th toLoadFromList object
    @ In, None
    @ Out, None 
    '''
    # Check type of source
    try:
      if self.toLoadFromList[0].type == "HDF5":
        # HDF5 database
        # Retrieve ending histories' names from the database
        endGroupNames = self.toLoadFromList[0].getEndingGroupNames()
        # Retrieve the histories
        for index in xrange(len(endGroupNames)):
          if not endGroupNames[index] in self.alreadyRead:
            self.histories[endGroupNames[index]] = self.toLoadFromList[0].returnHistory({'history':endGroupNames[index],'filter':'whole'})
            self.alreadyRead.append(endGroupNames[index])
    except AttributeError:
      # loading from file (csv) 
      # Retrieve histories from CSV files
      for index in xrange(len(self.toLoadFromList)):
        groupname = self.toLoadFromList[index].split('~')[1]
        if not groupname in self.alreadyRead:
          # open file
          myFile = open (self.toLoadFromList[index],'rb')
          # read the field names
          all_field_names = myFile.readline().split(b',')
          # load the table data (from the csv file) into a numpy nd array 
          data = np.loadtxt(myFile,dtype='float',delimiter=',',ndmin=2)
          # close file
          myFile.close()  
          self.histories[groupname] = (data,{'headers':all_field_names})
          self.alreadyRead.append(groupname)
    return

  def getParam(self,typeVar,keyword):
    '''
    Function to get a Parameter in this function
    @ In, typeVar : Variable type (string)
    @ In, keyword: Keyword to retrieve 
    @ Out,param  : Requested parameter
    '''
    pass

class OutStreamPlot(OutStreamManager):
  def __init__(self):
    self.availableOutStreamTypes = ['scatter','line','surface','histogram','stem','step','polar','pseudocolor']
    OutStreamManager.__init__(self)
    self.sourceName   = []
    self.sourceData   = None
    self.x_cordinates = None
    self.y_cordinates = None
    self.z_cordinates = None
    self.plotSettings = {}


  def initialize(self,inDict):
    '''
    Function called to initialize the OutStream linking it to the proper Data
    '''
    self.x_cordinates = []
    self.sourceName   = []
    self.sourceData   = []

    for pltindex in range(len(self.options['plot_settings']['plot'])):
      if 'y' in self.options['plot_settings']['plot'][pltindex].keys(): self.y_cordinates = [] 
      if 'z' in self.options['plot_settings']['plot'][pltindex].keys(): self.z_cordinates = [] 
    for pltindex in range(len(self.options['plot_settings']['plot'])): 
      self.x_cordinates.append(self.options['plot_settings']['plot'][pltindex]['x'].split(',')) 
      self.sourceName.append(self.x_cordinates[pltindex][0].split('|')[0].strip())
      if 'y' in self.options['plot_settings']['plot'][pltindex].keys(): 
        self.y_cordinates.append(self.options['plot_settings']['plot'][pltindex]['y'].split(',')) 
        if self.y_cordinates[pltindex][0].split('|')[0] != self.sourceName[pltindex]: raise IOError('STREAM MANAGER: ERROR -> Every plot can be linked to one Data only. x_cord source is ' + self.sourceName[pltindex] + '. Got y_cord source is' + self.y_cordinates[pltindex][0].split('|')[0])
      if 'z' in self.options['plot_settings']['plot'][pltindex].keys(): 
        self.z_cordinates.append(self.options['plot_settings']['plot'][pltindex]['z'].split(',')) 
        if self.z_cordinates[0][pltindex].split('|')[0] != self.sourceName[pltindex]: raise IOError('STREAM MANAGER: ERROR -> Every plot can be linked to one Data only. x_cord source is ' + self.sourceName[pltindex] + '. Got z_cord source is' + self.z_cordinates[pltindex][0].split('|')[0])
      
      foundData = False
      for output in inDict['Output']:
        if output.name.strip() == self.sourceName[pltindex]:
          self.sourceData.append(output)
          foundData = True
      if not foundData:
        for inp in inDict['Input']:
          if not isinstance(inp, basestring):
            if inp.name.strip() == self.sourceName[pltindex]:
              self.sourceData.append(inp)
              foundData = True  
      if not foundData and 'TargetEvaluation' in inDict.keys():
        if inDict['TargetEvaluation'].name.strip() == self.sourceName[pltindex]:
          self.sourceData.append(inDict['TargetEvaluation'])
          foundData = True 
      if not foundData and 'SolutionExport' in inDict.keys():
        if inDict['SolutionExport'].name.strip() == self.sourceName[pltindex]:
          self.sourceData.append(inDict['SolutionExport'])
          foundData = True 
      if not foundData: raise IOError('STREAM MANAGER: ERROR -> the Data named ' + self.sourceName[pltindex] + ' has not been found!!!!')
    # retrieve all the other plot settings (plot dependent) 
    for key in self.options['plot_settings'].keys():
      if key not in ['plot']: self.plotSettings[key] = self.options['plot_settings'][key]
    #execute actions
    #self.__executeActions() 
  
  def __splitVariableNames(self,what,where):
    ''' 
      Function to split the variable names
      input, what => x,y or z
      where, tuple => pos 0 = plotIndex, pos 1 = variable Index 
    '''
    if   what == 'x': var = self.x_cordinates[where[0]][where[1]]
    elif what == 'y': var = self.y_cordinates[where[0]][where[1]]
    elif what == 'z': var = self.z_cordinates[where[0]][where[1]]
    
    if var:
      if '(' in var and ')' in var:
        if var.count('(') > 1: raise IOError('Only a () is allowed in variable names (Outstream)!!!!!!')
        result = var.split('|(')[0].split('|')
        result.append(var.split('(')[1].replace(")", ""))
      else:  result = var.split('|')
    else: result = None
    if len(result) != 3: raise IOError('Only a three level variables are accepted in OutStreamPlot!!!!!!')
    
    return result
    
    
    
  def __readPlotActions(self,snode):
    #if snode.find('how') is not None: self.options[snode.tag]['how'] = snode.find('how').text.lower()
    #else: self.options[snode.tag]['how'] = 'screen'
    for node in snode:
      self.options[node.tag] = {}
      if len(node):
        for subnode in node: 
          if subnode.tag != 'kwargs': self.options[node.tag][subnode.tag] = subnode.text
          else:
            self.options[node.tag]['attributes'] = {} 
            for subsub in subnode: self.options[node.tag]['attributes'][subsub.tag] = subsub.text   
      elif node.text: 
        if node.text.strip(): self.options[node.tag][node.tag] = node.text
    if 'how' not in self.options.keys(): self.options['how']={'how':'screen'} 

  def __fillCoordinatesFromSource(self):
    self.x_values = []
    if self.y_cordinates: self.y_values = []
    if self.z_cordinates: self.z_values = []
    for pltindex in range(len(self.outStreamTypes)):
      self.x_values.append(None)
      if self.y_cordinates: self.y_values.append(None)
      if self.z_cordinates: self.z_values.append(None)
    for pltindex in range(len(self.outStreamTypes)):
      if len(self.sourceData[pltindex].getInpParametersValues().keys()) == 0 and len(self.sourceData[pltindex].getOutParametersValues().keys()) == 0: return False
      if self.sourceData[pltindex].type.strip() not in 'Histories': 
        self.x_values[pltindex] = {1:[]}
        if self.y_cordinates: self.y_values[pltindex] = {1:[]}
        if self.z_cordinates: self.z_values[pltindex] = {1:[]}
        for i in range(len(self.x_cordinates[pltindex])):
          xsplit = self.__splitVariableNames('x', (pltindex,i)) 
          self.x_values[pltindex][1].append(np.asarray(self.sourceData[pltindex].getParam(xsplit[1],xsplit[2])))
        if self.y_cordinates:
          ysplit = self.__splitVariableNames('y', (pltindex,i))
          for i in range(len(self.y_cordinates[pltindex])): self.y_values[pltindex][1].append(np.asarray(self.sourceData[pltindex].getParam(ysplit[1],ysplit[2])))
        if self.z_cordinates and self.dim>2:
          zsplit = self.__splitVariableNames('z', (pltindex,i))
          for i in range(len(self.z_cordinates[pltindex])): self.z_values[pltindex][1].append(np.asarray(self.sourceData[pltindex].getParam(zsplit[1],zsplit[2])))
      else:
        self.x_values[pltindex] = {}
        if self.y_cordinates: self.y_values[pltindex] = {}
        if self.z_cordinates  and self.dim>2: self.z_values[pltindex] = {}
        for key in self.sourceData[pltindex].getInpParametersValues().keys(): 
          self.x_values[pltindex][key] = []
          if self.y_cordinates: self.y_values[pltindex][key] = []
          if self.z_cordinates: self.z_values[pltindex][key] = []
          for i in range(len(self.x_cordinates[pltindex])): 
            xsplit = self.__splitVariableNames('x', (pltindex,i)) 
            self.x_values[pltindex][key].append(np.asarray(self.sourceData[pltindex].getParam(xsplit[1],key)[xsplit[2]]))
          if self.y_cordinates:
            for i in range(len(self.y_cordinates[pltindex])): 
              ysplit = self.__splitVariableNames('y', (pltindex,i))
              self.y_values[pltindex][key].append(np.asarray(self.sourceData[pltindex].getParam(ysplit[1],key)[ysplit[2]]))
          if self.z_cordinates and self.dim>2:
            for i in range(len(self.z_cordinates[pltindex])): 
              zsplit = self.__splitVariableNames('z', (pltindex,i))
              self.z_values[pltindex][key].append(np.asarray(self.sourceData[pltindex].getParam(zsplit[1],key)[zsplit[2]]))
      #check if something has been got
      if len(self.x_values[pltindex].keys()) == 0: return False
      else:
        for key in self.x_values[pltindex].keys():
          if len(self.x_values[pltindex][key]) == 0: return False
          else:
            for i in range(len(self.x_values[pltindex][key])):
              if self.x_values[pltindex][key][i].size == 0: return False 
      if self.z_cordinates and self.dim>2:
        if len(self.z_values[pltindex].keys()) == 0: return False
        else:
          for key in self.z_values[pltindex].keys():
            if len(self.z_values[pltindex][key]) == 0: return False      
            else:
              for i in range(len(self.z_values[pltindex][key])):
                if self.z_values[pltindex][key][i].size == 0: return False    
      if self.y_cordinates:
        if len(self.y_values[pltindex].keys()) == 0: return False    
        else:
          for key in self.y_values[pltindex].keys():
            if len(self.y_values[pltindex][key]) == 0: return False    
            else:
              for i in range(len(self.y_values[pltindex][key])):
                if self.y_values[pltindex][key][i].size == 0: return False           
    return True    
  def __executeActions(self):
    if self.dim < 3:
      self.plt.ticklabel_format(**{'style':'sci','scilimits':(0,0),'useOffset':True,'axis':'both'})
      if 'figure_properties' in self.options.keys():
        key = 'figure_properties'
        if 'figsize' not in self.options[key].keys():   self.options[key]['figsize'  ] = 'None' 
        if 'dpi' not in self.options[key].keys():       self.options[key]['dpi'      ] = 'None'
        if 'facecolor' not in self.options[key].keys(): self.options[key]['facecolor'] = 'None'
        if 'edgecolor' not in self.options[key].keys(): self.options[key]['edgecolor'] = 'None'
        if 'frameon' not in self.options[key].keys():   self.options[key]['frameon'  ] = 'True'
        elif self.options[key]['frameon'].lower() in ['t','true']: self.options[key]['frameon'] = 'True'
        elif self.options[key]['frameon'].lower() in ['f','false']: self.options[key]['frameon'] = 'False'           
        if 'attributes' in self.options[key].keys(): self.plt.figure(num=None, figsize=ast.literal_eval(self.options[key]['figsize']), dpi=ast.literal_eval(self.options[key]['dpi']), facecolor=self.options[key]['facecolor'],edgecolor=self.options[key]['edgecolor'],frameon=ast.literal_eval(self.options[key]['frameon']),**self.options[key]['attrobutes'])
        else: self.plt.figure(num=None, figsize=ast.literal_eval(self.options[key]['figsize']), dpi=ast.literal_eval(self.options[key]['dpi']), facecolor=self.options[key]['facecolor'],edgecolor=self.options[key]['edgecolor'],frameon=ast.literal_eval(self.options[key]['frameon']))
      if 'title' not in self.options.keys(): self.plt.title(self.name)
      for key in self.options.keys():
        if key == 'range': 
          if 'ymin' in self.options[key].keys(): self.plt.ylim(ymin = ast.literal_eval(self.options[key]['ymin']))
          if 'ymax' in self.options[key].keys(): self.plt.ylim(ymax = ast.literal_eval(self.options[key]['ymax']))
          if 'xmin' in self.options[key].keys(): self.plt.xlim(xmin = ast.literal_eval(self.options[key]['xmin']))
          if 'xmax' in self.options[key].keys(): self.plt.xlim(xmax = ast.literal_eval(self.options[key]['xmax']))
        elif key == 'title':
          if 'attributes' in self.options[key].keys(): self.plt.title(self.options[key]['text'],**self.options[key]['attributes'])
          else: self.plt.title(self.options[key]['text'])    
        elif key == 'figure_properties': pass
        elif key == 'add_text':
          if 'position' not in self.options[key].keys(): self.options[key]['position'] = str((min(self.x_values) + max(self.x_values))*0.5) + ',' + str((min(self.y_values) + max(self.y_values))*0.5)  
          if 'fontdict' not in self.options[key].keys(): self.options[key]['fontdict'] = None
          else: 
            try: self.options[key]['fontdict'] = ast.literal_eval(self.options[key]['fontdict'])
            except AttributeError: raise('STREAM MANAGER: ERROR -> In ' + key +' tag: can not convert the string "' + self.options[key]['fontdict'] + '" to a dictionary! Check syntax for python function ast.literal_eval')
          if 'attributes' in self.options[key].keys(): self.plt.text(float(self.options[key]['position'].split(',')[0]),float(self.options[key]['position'].split(',')[1]),self.options[key]['text'],fontdict=self.options[key]['fontdict'],**self.options[key]['attributes'])
          else: self.plt.text(ast.literal_eval(self.options[key]['position'].split(',')[0]),ast.literal_eval(self.options[key]['position'].split(',')[1]),self.options[key]['text'],fontdict=self.options[key]['fontdict'])    
        elif key == 'autoscale':
          if 'enable' not in self.options[key].keys(): self.options[key]['enable'] = 'True'
          elif self.options[key]['enable'].lower() in ['t','true']: self.options[key]['enable'] = 'True'
          elif self.options[key]['enable'].lower() in ['f','false']: self.options[key]['enable'] = 'False' 
          if 'axis' not in self.options[key].keys()  : self.options[key]['axis'] = 'both'
          if 'tight' not in self.options[key].keys() : self.options[key]['tight'] = 'None'
          self.plt.autoscale(enable = ast.literal_eval(self.options[key]['enable']), axis = self.options[key]['axis'], tight = ast.literal_eval(self.options[key]['tight']))
        elif key == 'horizontal_line':
          if 'y' not in self.options[key].keys(): self.options[key]['y'] = '0'
          if 'xmin' not in self.options[key].keys()  : self.options[key]['xmin'] = '0'
          if 'xmax' not in self.options[key].keys() : self.options[key]['xmax'] = '1'
          if 'hold' not in self.options[key].keys() : self.options[key]['hold'] = 'None'
          if 'attributes' in self.options[key].keys(): self.plt.axhline(y=ast.literal_eval(self.options[key]['y']), xmin=ast.literal_eval(self.options[key]['xmin']), xmax=ast.literal_eval(self.options[key]['xmax']), hold=ast.literal_eval(self.options[key]['hold']),**self.options[key]['attributes'])
          else: self.plt.axhline(y=ast.literal_eval(self.options[key]['y']), xmin=ast.literal_eval(self.options[key]['xmin']), xmax=ast.literal_eval(self.options[key]['xmax']), hold=ast.literal_eval(self.options[key]['hold']))
        elif key == 'vertical_line':
          if 'x' not in self.options[key].keys(): self.options[key]['x'] = '0'
          if 'ymin' not in self.options[key].keys()  : self.options[key]['ymin'] = '0'
          if 'ymax' not in self.options[key].keys() : self.options[key]['ymax'] = '1'
          if 'hold' not in self.options[key].keys() : self.options[key]['hold'] = 'None'
          if 'attributes' in self.options[key].keys(): self.plt.axhline(x=ast.literal_eval(self.options[key]['x']), ymin=ast.literal_eval(self.options[key]['ymin']), ymax=ast.literal_eval(self.options[key]['ymax']), hold=ast.literal_eval(self.options[key]['hold']),**self.options[key]['attributes'])
          else: self.plt.axvline(x=ast.literal_eval(self.options[key]['x']), ymin=ast.literal_eval(self.options[key]['ymin']), ymax=ast.literal_eval(self.options[key]['ymax']), hold=ast.literal_eval(self.options[key]['hold']))
        elif key == 'horizontal_rectangle':
          if 'ymin' not in self.options[key].keys(): raise('STREAM MANAGER: ERROR -> ymin parameter is needed for function horizontal_rectangle!!')
          if 'ymax' not in self.options[key].keys(): raise('STREAM MANAGER: ERROR -> ymax parameter is needed for function horizontal_rectangle!!')
          if 'xmin' not in self.options[key].keys()  : self.options[key]['xmin'] = '0'
          if 'xmax' not in self.options[key].keys() : self.options[key]['xmax'] = '1'
          if 'attributes' in self.options[key].keys(): self.plt.axhspan(ast.literal_eval(self.options[key]['ymin']),ast.literal_eval(self.options[key]['ymax']), ymin=ast.literal_eval(self.options[key]['xmin']), ymax=ast.literal_eval(self.options[key]['xmax']),**self.options[key]['attributes'])
          else:self.plt.axhspan(ast.literal_eval(self.options[key]['ymin']),ast.literal_eval(self.options[key]['ymax']), xmin=ast.literal_eval(self.options[key]['xmin']), xmax=ast.literal_eval(self.options[key]['xmax']))
        elif key == 'vertical_rectangle':
          if 'xmin' not in self.options[key].keys(): raise('STREAM MANAGER: ERROR -> xmin parameter is needed for function vertical_rectangle!!')
          if 'xmax' not in self.options[key].keys(): raise('STREAM MANAGER: ERROR -> xmax parameter is needed for function vertical_rectangle!!')
          if 'ymin' not in self.options[key].keys()  : self.options[key]['ymin'] = '0'
          if 'ymax' not in self.options[key].keys() : self.options[key]['ymax'] = '1'
          if 'attributes' in self.options[key].keys(): self.plt.axvspan(ast.literal_eval(self.options[key]['xmin']),ast.literal_eval(self.options[key]['xmax']), ymin=ast.literal_eval(self.options[key]['ymin']), ymax=ast.literal_eval(self.options[key]['ymax']),**self.options[key]['attributes'])
          else:self.plt.axvspan(ast.literal_eval(self.options[key]['xmin']),ast.literal_eval(self.options[key]['xmax']), ymin=ast.literal_eval(self.options[key]['ymin']), ymax=ast.literal_eval(self.options[key]['ymax']))
        elif key == 'axes_box': self.plt.box(self.options[key][key])
        elif key == 'axis_properties':
          try:self.plt.axis(ast.literal_eval(self.options[key][key]))
          except: self.plt.axis(self.options[key][key]) 
        elif key == 'grid':
          if 'b' not in self.options[key].keys()  : self.options[key]['b'] = None
          elif self.options[key]['b'].lower() in ['true','t']: self.options[key]['b'] = 'on'
          elif self.options[key]['b'].lower() in ['false','f']: self.options[key]['b'] = 'off'
          if 'which' not in self.options[key].keys() : self.options[key]['which'] = 'major'
          if 'axis' not in self.options[key].keys() : self.options[key]['axis'] = 'both'
          if 'attributes' in self.options[key].keys(): self.plt.grid(ast.literal_eval(b =self.options[key]['b']),which = ast.literal_eval(self.options[key]['which']), axis=ast.literal_eval(self.options[key]['axis']),**self.options[key]['attributes'])
          else:self.plt.grid(b=self.options[key]['b'],which = (self.options[key]['which']), axis=(self.options[key]['axis']))
        elif key in ['how','plot_settings']: pass
        else:
          command_args = ''
          for kk in self.options[key]:
            if kk != 'attributes' and kk != key:
              if command_args != '(': prefix = ','
              else: prefix = '' 
              try: command_args = prefix + command_args + kk + '=' + str(ast.literal_eval(self.options[key][kk]))
              except:command_args = prefix + command_args + kk + '="' + str(self.options[key][kk])+'"'  
          exec('self.plt.' + key + '(' + command_args + ')')
    else:
      self.plt3D.ticklabel_format(**{'style':'sci','scilimits':(0,0),'useOffset':True,'axis':'both'})
      if 'figure_properties' in self.options.keys():
        key = 'figure_properties'
        if 'figsize' not in self.options[key].keys():   self.options[key]['figsize'  ] = 'None' 
        if 'dpi' not in self.options[key].keys():       self.options[key]['dpi'      ] = 'None'
        if 'facecolor' not in self.options[key].keys(): self.options[key]['facecolor'] = 'None'
        if 'edgecolor' not in self.options[key].keys(): self.options[key]['edgecolor'] = 'None'
        if 'frameon' not in self.options[key].keys():   self.options[key]['frameon'  ] = 'True'
        elif self.options[key]['frameon'].lower() in ['t','true']: self.options[key]['frameon'] = 'True'
        elif self.options[key]['frameon'].lower() in ['f','false']: self.options[key]['frameon'] = 'False'           
        if 'attributes' in self.options[key].keys(): self.plt.figure(num=None, figsize=ast.literal_eval(self.options[key]['figsize']), dpi=ast.literal_eval(self.options[key]['dpi']), facecolor=self.options[key]['facecolor'],edgecolor=self.options[key]['edgecolor'],frameon=ast.literal_eval(self.options[key]['frameon']),**self.options[key]['attrobutes'])
        else: self.plt.figure(num=None, figsize=ast.literal_eval(self.options[key]['figsize']), dpi=ast.literal_eval(self.options[key]['dpi']), facecolor=self.options[key]['facecolor'],edgecolor=self.options[key]['edgecolor'],frameon=ast.literal_eval(self.options[key]['frameon']))
      if 'title' not in self.options.keys(): self.plt3D.set_title(self.name)
      for key in self.options.keys():
        if key == 'range': 
          if 'xmin' in self.options[key].keys(): self.plt3D.set_xlim3d(xmin = ast.literal_eval(self.options[key]['xmin']))
          if 'xmax' in self.options[key].keys(): self.plt3D.set_xlim3d(xmax = ast.literal_eval(self.options[key]['xmax']))
          if 'ymin' in self.options[key].keys(): self.plt3D.set_ylim3d(ymin = ast.literal_eval(self.options[key]['ymin']))
          if 'ymax' in self.options[key].keys(): self.plt3D.set_ylim3d(ymax = ast.literal_eval(self.options[key]['ymax']))
          if 'zmin' in self.options[key].keys(): 
            self.plt3D.set_zlim(ast.literal_eval(self.options[key]['zmin']),ast.literal_eval(self.options[key]['zmax']))
        elif key == 'camera':
          if 'elevation' in self.options[key].keys() and 'azimuth' in self.options[key].keys(): self.plt3D.view_init(elev = float(self.options[key]['elevation']),azim = float(self.options[key]['azimuth']))
          elif 'elevation' in self.options[key].keys() and 'azimuth' not in self.options[key].keys(): self.plt3D.view_init(elev = float(self.options[key]['elevation']),azim = None)
          elif 'elevation' not in self.options[key].keys() and 'azimuth' in self.options[key].keys(): self.plt3D.view_init(elev = None,azim = float(self.options[key]['azimuth']))
        elif key== 'scale':
          if 'xscale' in self.options[key].keys(): self.plt3D.set_xscale(self.options[key]['xscale'])
          if 'yscale' in self.options[key].keys(): self.plt3D.set_yscale(self.options[key]['yscale'])        
          if 'zscale' in self.options[key].keys(): self.plt3D.set_zscale(self.options[key]['zscale'])
        elif key == 'title':
          if 'attributes' in self.options[key].keys(): self.plt3D.set_title(self.options[key]['text'],**self.options[key]['attributes'])
          else: self.plt3D.set_title(self.options[key]['text'])    
        elif key == 'figure_properties': pass
        elif key == 'add_text':
          if 'position' not in self.options[key].keys(): self.options[key]['position'] = str((min(self.x_values) + max(self.x_values))*0.5) + ',' + str((min(self.y_values) + max(self.y_values))*0.5)  
          if 'fontdict' not in self.options[key].keys(): self.options[key]['fontdict'] = 'None'
          if 'withdash' not in self.options[key].keys(): self.options[key]['withdash'] = 'False' 
          if len(self.options[key]['position'].split(',')) < 3: raise('STREAM MANAGER: ERROR -> in 3D plot add_text needs an x,y,z coordinate input the position!!!')
          if 'attributes' in self.options[key].keys(): self.plt3D.text(float(self.options[key]['position'].split(',')[0]),float(self.options[key]['position'].split(',')[1]),float(self.options[key]['position'].split(',')[2]),self.options[key]['text'],fontdict=ast.literal_eval(self.options[key]['fontdict']),withdash=ast.literal_eval(self.options[key]['withdash']),**self.options[key]['attributes'])
          else: self.plt3D.text(float(self.options[key]['position'].split(',')[0]),float(self.options[key]['position'].split(',')[1]),float(self.options[key]['position'].split(',')[2]),self.options[key]['text'],fontdict=ast.literal_eval(self.options[key]['fontdict']),withdash=ast.literal_eval(self.options[key]['withdash']))
        elif key in ['vertical_rectangle','vertical_line','horizontal_rectangle','horizontal_line']:pass
        elif key == 'autoscale':
          if 'enable' not in self.options[key].keys(): self.options[key]['enable'] = 'True'
          elif self.options[key]['enable'].lower() in ['t','true']: self.options[key]['enable'] = 'True'
          elif self.options[key]['enable'].lower() in ['f','false']: self.options[key]['enable'] = 'False' 
          if 'axis' not in self.options[key].keys()  : self.options[key]['axis'] = 'both'
          if 'tight' not in self.options[key].keys() : self.options[key]['tight'] = 'None'
          self.plt3D.autoscale(enable = ast.literal_eval(self.options[key]['enable']), axis = self.options[key]['axis'], tight = ast.literal_eval(self.options[key]['tight']))
        elif key == 'grid':
          if 'b' not in self.options[key].keys()  : self.options[key]['b'] = 'True'
          if self.options[key]['b'].lower() in ['on','t','true']: self.options[key]['b'] = 'True'
          elif self.options[key]['b'].lower() in ['off','f','false']: self.options[key]['b'] = 'False'
          if 'attributes' in self.options[key].keys(): self.Ax.grid(b=ast.literal_eval(self.options[key]['b']),**self.options[key]['attributes'])
          else:self.plt3D.grid(b=ast.literal_eval(self.options[key]['b']))
        elif key in ['how','plot_settings']: pass
        else:
          command_args = ''
          for kk in self.options[key]:
            if kk != 'attributes' and kk != key:
              if command_args != '(': prefix = ','
              else: prefix = '' 
              try: command_args = prefix + command_args + kk + '=' + str(ast.literal_eval(self.options[key][kk]))
              except:command_args = prefix + command_args + kk + '="' + str(self.options[key][kk])+'"'  
          exec('self.plt3D.' + key + '(' + command_args + ')')

  def readMoreXML(self,xmlNode):
    OutStreamManager.readMoreXML(self,xmlNode)
    if not 'dim' in xmlNode.attrib.keys(): self.dim = 2
    else: self.dim = int(xmlNode.attrib['dim'])
    exec('import matplotlib as ' + 'mpl_' + self.name)
    exec('self.mpl = mpl_' + self.name)
    print('STREAM MANAGER: matplotlib version is ' + str(self.mpl.__version__))
    if self.dim not in [2,3]: raise('STREAM MANAGER: ERROR -> This Plot interface is able to handle 2D-3D plot only')
    exec('import matplotlib.pyplot as ' + 'plt_' + self.name)
    exec('self.plt = plt_' + self.name)
    if self.interactive:self.plt.ion()
    if self.dim == 3:
      exec('from mpl_toolkits.mplot3d import Axes3D as ' + 'Ax3D_' + self.name)
      #exec('self.Ax = Ax3D_' + self.name)
    self.fig = self.plt.figure()
    if self.dim == 3: self.plt3D = self.fig.add_subplot(111, projection='3d')

    foundPlot = False
    for subnode in xmlNode:
      if subnode.tag in ['actions']: self.__readPlotActions(subnode)
      if subnode.tag in ['plot_settings']:
        self.options[subnode.tag] = {}
        self.options[subnode.tag]['plot'] = []
        for subsub in subnode:
          if subsub.tag == 'plot':
            tempDict = {}
            foundPlot = True
            for subsubsub in subsub:
              if subsubsub.tag != 'kwargs': tempDict[subsubsub.tag] = subsubsub.text
              else:
                tempDict['attributes'] = {}
                for sss in subsubsub: tempDict['attributes'][sss.tag] = sss.text       
            self.options[subnode.tag][subsub.tag].append(copy.deepcopy(tempDict))
          else: self.options[subnode.tag][subsub.tag] = subsub.text 
      if subnode.tag in 'title':
        self.options[subnode.tag] = {}
        for subsub in subnode: self.options[subnode.tag][subsub.tag] = subsub.text
        if 'text'     not in self.options[subnode.tag].keys(): self.options[subnode.tag]['text'    ] = node.attrib['name']
        if 'location' not in self.options[subnode.tag].keys(): self.options[subnode.tag]['location'] = 'center'   
      if subnode.tag == 'figure_properties':
        self.options[subnode.tag] = {}
        for subsub in subnode: self.options[subnode.tag][subsub.tag] = subsub.text         
    self.type = 'OutStreamPlot'
    if not 'plot_settings' in self.options.keys(): raise IOError('STREAM MANAGER: ERROR -> For plot named ' + self.name + ' the plot_settings block IS REQUIRED!!')
    if not foundPlot: raise IOErrror('STREAM MANAGER: ERROR -> For plot named'+ self.name + ', No plot section has been found in the plot_settings block!')
    self.outStreamTypes = []
    for pltindex in range(len(self.options['plot_settings']['plot'])):
      if not 'type' in self.options['plot_settings']['plot'][pltindex].keys(): raise IOErrror('STREAM MANAGER: ERROR -> For plot named'+ self.name + ', No plot type keyword has been found in the plot_settings/plot block!')
      else: self.outStreamTypes.append(self.options['plot_settings']['plot'][pltindex]['type']) 
    return

  def addOutput(self):
    '''
    Function to add a new output source
    @ In, toLoadFrom, source object
    @ Out, None 
    ''' 
    if not self.__fillCoordinatesFromSource():
      print('STREAM MANAGER: WARNING -> Nothing to Plot Yet... Returning!!!!')
      return
    self.counter += 1
    if self.counter > 1:
      if self.dim == 2: self.fig.clear()
      else: self.actPlot.remove()
    self.__executeActions()
    for pltindex in range(len(self.outStreamTypes)):
      if self.dim == 2:
        if len(self.outStreamTypes) > 1: self.plt.hold(True)
        if 'xlabel' not in self.plotSettings.keys():
          self.plt.xlabel('x')
        else:
          self.plt.xlabel(self.plotSettings['xlabel'])
        if 'ylabel' not in self.plotSettings.keys():
          if self.y_cordinates:
            self.plt.ylabel('y')
            self.plt.legend(ast.literal_eval(y_label))
        else:
          if self.y_cordinates: self.plt.ylabel(self.plotSettings['ylabel'])
         
        if self.outStreamTypes[pltindex] == 'scatter':
          if 's' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['s'] = '20'
          if 'c' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['c'] = 'b'
          if 'marker' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['marker'] = 'o'   
          if 'alpha' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['alpha']='None'
          if 'linewidths' not in self.options['plot_settings']['plot'][pltindex].keys():  self.options['plot_settings']['plot'][pltindex]['linewidths'] = 'None'
          for key in self.x_values[pltindex].keys():
            for x_index in range(len(self.x_values[pltindex][key])):
              for y_index in range(len(self.y_values[pltindex][key])):
                if 'attributes' in self.options['plot_settings']['plot'][pltindex].keys(): self.actPlot = self.plt.scatter(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],s=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['s']),c=(self.options['plot_settings']['plot'][pltindex]['c']),marker=(self.options['plot_settings']['plot'][pltindex]['marker']),alpha=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['alpha']),linewidths=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['linewidths']),**self.options['plot_settings']['plot'][pltindex]['attributes'])
                else: self.actPlot = self.plt.scatter(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],s=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['s']),c=(self.options['plot_settings']['plot'][pltindex]['c']),marker=(self.options['plot_settings']['plot'][pltindex]['marker']),alpha=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['alpha']),linewidths=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['linewidths']))
        elif self.outStreamTypes[pltindex] == 'line':
          for key in self.x_values[pltindex].keys():
            for x_index in range(len(self.x_values[pltindex][key])):
              for y_index in range(len(self.y_values[pltindex][key])):
                if 'attributes' in self.options['plot_settings']['plot'][pltindex].keys(): self.actPlot = self.plt.plot(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],**self.options['plot_settings']['plot'][pltindex]['attributes'])
                else: self.actPlot = self.plt.plot(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index])
        elif self.outStreamTypes[pltindex] == 'histogram':
          if 'bins' in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['bins'] = ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['bins'])
          else: self.options['plot_settings']['plot'][pltindex]['bins'] = 10
          if 'normed' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['normed'] = False
          else: self.options['plot_settings']['plot'][pltindex]['normed'] = ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['normed'])
          if 'weights' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['weights'] = None
          else: self.options['plot_settings']['plot'][pltindex]['weights'] = ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['weights'])
          if 'cumulative' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['cumulative'] = False
          else: self.options['plot_settings']['plot'][pltindex]['cumulative'] = ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['cumulative'])
          if 'histtype' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['histtype'] = 'bar'
          if 'align' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['align'] = 'mid'
          if 'orientation' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['orientation'] = 'vertical'                        
          if 'rwidth' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['rwidth'] = None
          else: self.options['plot_settings']['plot'][pltindex]['rwidth'] = ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['rwidth'])
          if 'log' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['log'] = None
          else: self.options['plot_settings']['plot'][pltindex]['log'] = ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['log'])      
          if 'color' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['color'] = None
          else: self.options['plot_settings']['plot'][pltindex]['color'] = ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['color'])   
          if 'stacked' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['stacked'] = None
          else: self.options['plot_settings']['plot'][pltindex]['stacked'] = ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['stacked'])                 
          for key in self.x_values[pltindex].keys():
            for x_index in range(len(self.x_values[pltindex][key])):
              if 'attributes' in self.options['plot_settings']['plot'][pltindex].keys(): self.plt.hist(self.x_values[pltindex][key][x_index], bins=self.options['plot_settings']['plot'][pltindex]['bins'], normed=self.options['plot_settings']['plot'][pltindex]['normed'], weights=self.options['plot_settings']['plot'][pltindex]['weights'], 
                            cumulative=self.options['plot_settings']['plot'][pltindex]['cumulative'], histtype=self.options['plot_settings']['plot'][pltindex]['histtype'], align=self.options['plot_settings']['plot'][pltindex]['align'], 
                            orientation=self.options['plot_settings']['plot'][pltindex]['orientation'], rwidth=self.options['plot_settings']['plot'][pltindex]['rwidth'], log=self.options['plot_settings']['plot'][pltindex]['log'], 
                            color=self.options['plot_settings']['plot'][pltindex]['color'], stacked=self.options['plot_settings']['plot'][pltindex]['stacked'], **self.options['plot_settings']['plot'][pltindex]['attributes'])
              else: self.plt.hist(x, bins=self.options['plot_settings']['plot'][pltindex]['bins'], normed=self.options['plot_settings']['plot'][pltindex]['normed'], weights=self.options['plot_settings']['plot'][pltindex]['weights'], 
                            cumulative=self.options['plot_settings']['plot'][pltindex]['cumulative'], histtype=self.options['plot_settings']['plot'][pltindex]['histtype'], align=self.options['plot_settings']['plot'][pltindex]['align'], 
                            orientation=self.options['plot_settings']['plot'][pltindex]['orientation'], rwidth=self.options['plot_settings']['plot'][pltindex]['rwidth'], log=self.options['plot_settings']['plot'][pltindex]['log'], 
                            color=self.options['plot_settings']['plot'][pltindex]['color'], stacked=self.options['plot_settings']['plot'][pltindex]['stacked'])       
        elif self.outStreamTypes[pltindex] == 'stem':
          if 'linefmt' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['linefmt'] = 'b-'
          if 'markerfmt' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['markerfmt'] = 'bo'
          if 'basefmt' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['basefmt'] = 'r-'
          for key in self.x_values[pltindex].keys():
            for x_index in range(len(self.x_values[pltindex][key])):
              for y_index in range(len(self.y_values[pltindex][key])):
                if 'attributes' in self.options['plot_settings']['plot'][pltindex].keys(): self.actPlot = self.plt.stem(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],linefmt=self.options['plot_settings']['plot'][pltindex]['linefmt'], markerfmt=self.options['plot_settings']['plot'][pltindex]['markerfmt'], basefmt=self.options['plot_settings']['plot'][pltindex]['linefmt'],**self.options['plot_settings']['plot'][pltindex]['attributes'])
                else: self.actPlot = self.plt.stem(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],linefmt=self.options['plot_settings']['plot'][pltindex]['linefmt'], markerfmt=self.options['plot_settings']['plot'][pltindex]['markerfmt'], basefmt=self.options['plot_settings']['plot'][pltindex]['linefmt'])             
        elif self.outStreamTypes[pltindex] == 'step':
          if 'where' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['where'] = 'mid'
          for key in self.x_values[pltindex].keys():
            for x_index in range(len(self.x_values[pltindex][key])):
              for y_index in range(len(self.y_values[pltindex][key])):
                if 'attributes' in self.options['plot_settings']['plot'][pltindex].keys(): self.actPlot = self.plt.step(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],where=self.options['plot_settings']['plot'][pltindex]['where'],**self.options['plot_settings']['plot'][pltindex]['attributes'])
                else: self.actPlot = self.plt.step(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],where=self.options['plot_settings']['plot'][pltindex]['where'])
        elif self.outStreamTypes[pltindex] == 'polar':
          # in here we assume that the x_cordinates are the theta, and y_coordinates are the r(s)
          for key in self.x_values[pltindex].keys():
            for x_index in range(len(self.x_values[pltindex][key])):
              for y_index in range(len(self.y_values[pltindex][key])):
                if 'attributes' in self.options['plot_settings']['plot'][pltindex].keys(): self.actPlot = self.plt.polar(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],**self.options['plot_settings']['plot'][pltindex]['attributes'])
                else: self.actPlot = self.plt.polar(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index])      
        elif self.outStreamTypes[pltindex] == 'pseudocolor':
          pass
  #       if 'alpha' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['alpha'] = None
  #       else: self.options['plot_settings']['plot'][pltindex]['alpha'] = ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['alpha']) 
  #       if 'C' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['C'] = None
  #       else: self.options['plot_settings']['plot'][pltindex]['alpha'] = ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['alpha'])                   
  #       if 'edgecolors' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['edgecolors'] = None
  #       if 'shading' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['shading'] = 'flat'
  #       
  #       for key in self.x_values[pltindex].keys():
  #         for x_index in range(self.x_values[pltindex][key]):
  #           for y_index in range(self.y_values[pltindex][key]):
  #             if 'attributes' in self.options['plot_settings']['plot'][pltindex].keys(): self.actPlot = self.plt.pcolormesh(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],**self.options['plot_settings']['plot'][pltindex]['attributes'])
  #             else: self.actPlot = self.plt.pcolormesh(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index])      
      else:
        #3d
        if len(self.outStreamTypes) > 1: self.plt.hold(True)
        if 'xlabel' not in self.plotSettings.keys():
          x_label = ''
          for index in range(len(self.x_cordinates)) : x_label = x_label + str(self.x_cordinates[index]) + ';'
          self.plt3D.set_xlabel(x_label)
        else:
          self.plt3D.set_xlabel(self.plotSettings['xlabel'])
        if 'ylabel' not in self.plotSettings.keys():
          if self.y_cordinates:
            y_label = ''
            leg_y = ''
            for index in range(len(self.x_cordinates)) : 
              y_label = y_label + str(self.y_cordinates[index]) + ','
            self.plt3D.set_ylabel(y_label)
        else:
          if self.y_cordinates: self.plt3D.set_ylabel(self.plotSettings['ylabel'])
        if 'zlabel' not in self.plotSettings.keys():
          if self.z_cordinates:
            z_label = ''
            leg_z = ''
            for index in range(len(self.x_cordinates)) : 
              z_label = z_label + str(self.z_cordinates[index][-1]) + ','
            self.plt3D.set_zlabel(z_label)
        else:
          if self.z_cordinates: self.plt3D.set_zlabel(self.plotSettings['zlabel'])
   
        if self.outStreamTypes[pltindex] == 'scatter':
          if 's' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['s'] = '20'
          if 'c' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['c'] = 'b'
          if 'marker' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['marker'] = 'o'   
          if 'alpha' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['alpha']='None'
          if 'linewidths' not in self.options['plot_settings']['plot'][pltindex].keys():  self.options['plot_settings']['plot'][pltindex]['linewidths'] = 'None'
          for key in self.x_values[pltindex].keys():
            for x_index in range(len(self.x_values[pltindex][key])):
              for y_index in range(len(self.y_values[pltindex][key])):
                for z_index in range(len(self.z_values[pltindex][key])):
                  if 'attributes' in self.options['plot_settings']['plot'][pltindex].keys(): self.actPlot = self.plt3D.scatter(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],self.z_values[pltindex][key][z_index],rasterized= True,s=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['s']),c=(self.options['plot_settings']['plot'][pltindex]['c']),marker=(self.options['plot_settings']['plot'][pltindex]['marker']),alpha=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['alpha']),linewidths=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['linewidths']),**self.options['plot_settings']['plot'][pltindex]['attributes'])
                  else: self.actPlot = self.plt3D.scatter(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],self.z_values[pltindex][key][z_index],s=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['s']),rasterized= True,c=(self.options['plot_settings']['plot'][pltindex]['c']),marker=(self.options['plot_settings']['plot'][pltindex]['marker']),alpha=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['alpha']),linewidths=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['linewidths']))
        elif self.outStreamTypes[pltindex] == 'line':
          for key in self.x_values[pltindex].keys():
            for x_index in range(len(self.x_values[pltindex][key])):
              for y_index in range(len(self.y_values[pltindex][key])):
                for z_index in range(len(self.z_values[pltindex][key])):
                  if 'attributes' in self.options['plot_settings']['plot'][pltindex].keys(): self.actPlot = self.plt3D.plot(self.Ax,self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],self.z_values[pltindex][key][z_index],**self.options['plot_settings']['plot'][pltindex]['attributes'])
                  else: self.actPlot = self.plt3D.plot(self.Ax,self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index],self.z_values[pltindex][key][z_index])
        elif self.outStreamTypes[pltindex] == 'surface':
          if 'rstride' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['rstride'] = '1'
          if 'cstride' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['cstride'] = '1'
          if 'cmap' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['cmap'] = 'Accent'
          elif self.options['plot_settings']['plot'][pltindex]['cmap'] not in self.mpl.cm.datad.keys(): raise('ERROR. The colorMap you specified does not exist... Available are ' + str(self.mpl.cm.datad.keys()))    
          if 'antialiased' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['antialiased']='False'
          if 'linewidth' not in self.options['plot_settings']['plot'][pltindex].keys():  self.options['plot_settings']['plot'][pltindex]['linewidth'] = '0'
          if 'interpolation_type' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['interpolation_type'] = 'cubic'
          elif self.options['plot_settings']['plot'][pltindex]['interpolation_type'] not in ['nearest','linear','cubic']: raise('STREAM MANAGER: ERROR -> surface interpolation unknown. Available are :' + str(['nearest','linear','cubic']))  
          if 'interpPointsY' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['interpPointsY'] = '50'
          if 'interpPointsX' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['interpPointsX'] = '50'
          for key in self.x_values[pltindex].keys():
            for x_index in range(len(self.x_values[pltindex][key])):
              xi = np.linspace(self.x_values[pltindex][key][x_index].min(),self.x_values[pltindex][key][x_index].max(),ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['interpPointsX']))
              for y_index in range(len(self.y_values[pltindex][key])):
                yi = np.linspace(self.y_values[pltindex][key][y_index].min(),self.y_values[pltindex][key][y_index].max(),ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['interpPointsY']))
                xig, yig = np.meshgrid(xi, yi)
                for z_index in range(len(self.z_values[pltindex][key])):
                  if self.options['plot_settings']['plot'][pltindex]['interpolation_type'] != 'nearest' and self.z_values[pltindex][key][z_index].size > 3: zi = griddata((self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index]), self.z_values[pltindex][key][z_index], (xi[:], yi[:]), method=self.options['plot_settings']['plot'][pltindex]['interpolation_type'])
                  else: zi = griddata((self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index]), self.z_values[pltindex][key][z_index], (xi[:], yi[:]), method='nearest')
                  if 'attributes' in self.options['plot_settings']['plot'][pltindex].keys(): self.actPlot = self.plt3D.plot_surface(xig,yig,zi, rstride = ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['rstride']), cstride=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['cstride']),cmap=self.mpl.cm.get_cmap(name=self.options['plot_settings']['plot'][pltindex]['cmap']),linewidth= ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['linewidth']),antialiased=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['antialiased']),**self.options['plot_settings']['plot'][pltindex]['attributes'])    
                  else: self.actPlot = self.plt3D.plot_surface(xig,yig,zi,rstride=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['rstride']), cstride=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['cstride']),cmap=self.mpl.cm.get_cmap(name=self.options['plot_settings']['plot'][pltindex]['cmap']),linewidth= ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['linewidth']),antialiased=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['antialiased'])) 
        elif self.outStreamTypes[pltindex] == 'tri-surface':
          if 'color' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['color'] = 'b'
          if 'cmap' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['cmap'] = 'Accent'
          elif self.options['plot_settings']['plot'][pltindex]['cmap'] not in self.mpl.cm.datad.keys(): raise('ERROR. The colorMap you specified does not exist... Available are ' + str(self.mpl.cm.datad.keys()))    
          if 'shade' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['shade']='False'
          for key in self.x_values[pltindex].keys():
            for x_index in range(len(self.x_values[pltindex][key])):
              for y_index in range(len(self.y_values[pltindex][key])):
                 for z_index in range(len(self.z_values[pltindex][key])):
                   if 'attributes' in self.options['plot_settings']['plot'][pltindex].keys(): self.actPlot = self.plt3D.plot_trisurf(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][x_index],self.z_values[pltindex][key][x_index], color = self.options['plot_settings']['plot'][pltindex]['color'],cmap=self.mpl.cm.get_cmap(name=self.options['plot_settings']['plot'][pltindex]['cmap']),shade= ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['shade']),**self.options['plot_settings']['plot'][pltindex]['attributes'])    
                   else: self.actPlot = self.plt3D.plot_trisurf(self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][x_index],self.z_values[pltindex][key][x_index], color = self.options['plot_settings']['plot'][pltindex]['color'],cmap=self.mpl.cm.get_cmap(name=self.options['plot_settings']['plot'][pltindex]['cmap']),shade= ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['shade']))
        elif self.outStreamTypes[pltindex] == 'wireframe':
          if 'rstride' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['rstride'] = '1'
          if 'cstride' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['cstride'] = '1'
          if 'interpolation_type' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['interpolation_type'] = 'cubic'
          elif self.options['plot_settings']['plot'][pltindex]['interpolation_type'] not in ['nearest','linear','cubic']: raise('STREAM MANAGER: ERROR -> surface interpolation unknown. Available are :' + str(['nearest','linear','cubic']))  
          if 'interpPointsY' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['interpPointsY'] = '50'
          if 'interpPointsX' not in self.options['plot_settings']['plot'][pltindex].keys(): self.options['plot_settings']['plot'][pltindex]['interpPointsX'] = '50'
          for key in self.x_values[pltindex].keys():
            for x_index in range(len(self.x_values[pltindex][key])):
              xi = np.linspace(self.x_values[pltindex][key][x_index].min(),self.x_values[pltindex][key][x_index].max(),ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['interpPointsX']))
              for y_index in range(len(self.y_values[pltindex][key])):
                yi = np.linspace(self.y_values[pltindex][key][y_index].min(),self.y_values[pltindex][key][y_index].max(),ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['interpPointsY']))
                xig, yig = np.meshgrid(xi, yi)
                for z_index in range(len(self.z_values[pltindex][key])):
                  if self.options['plot_settings']['plot'][pltindex]['interpolation_type'] != 'nearest' and self.z_values[pltindex][key][z_index].size > 3: zi = griddata((self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index]), self.z_values[pltindex][key][z_index], (xi[:], yi[:]), method=self.options['plot_settings']['plot'][pltindex]['interpolation_type'])
                  else: zi = griddata((self.x_values[pltindex][key][x_index],self.y_values[pltindex][key][y_index]), self.z_values[pltindex][key][z_index], (xi[:], yi[:]), method='nearest')
                  if 'attributes' in self.options['plot_settings']['plot'][pltindex].keys(): self.actPlot = self.plt3D.plot_wireframe(xig,yig,zi, rstride = ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['rstride']), cstride=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['cstride']),**self.options['plot_settings']['plot'][pltindex]['attributes'])    
                  else: self.actPlot = self.plt3D.plot_wireframe(xig,yig,zi,rstride=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['rstride']), cstride=ast.literal_eval(self.options['plot_settings']['plot'][pltindex]['cstride'])) 
        elif self.outStreamTypes[pltindex] == 'contour' or self.outStreamTypes[pltindex] == 'contourf':
          pass
        elif self.outStreamTypes[pltindex] == 'histogram':
          pass
        elif self.outStreamTypes[pltindex] == 'pseudocolor':
          pass      
        else: raise IOError('STREAM MANAGER: ERROR -> plot named'+ self.name+ ': plot type '+ self.outStreamTypes[pltindex] + 'unknown!!!')
      #if self.interactive: self.plt.ion()
    if 'screen' in self.options['how']['how'].split(','): 
      if self.dim == 2: self.fig.canvas.draw()
      else: self.plt.draw()
      if not self.interactive:self.plt.show()
    for i in range(len(self.options['how']['how'].split(','))):
      if self.options['how']['how'].split(',')[i].lower() != 'screen':
        if not self.overwrite: prefix = str(self.counter) + '-'
        else: prefix = ''
        self.plt.savefig(prefix + self.name+'_' + str(self.outStreamTypes)+'.'+self.options['how']['how'].split(',')[i], format=self.options['how']['how'].split(',')[i])        
class OutStreamPrint(OutStreamManager):
  def __init(self):
    self.availableOutStreamTypes = ['csv']
  def readMoreXML(self,xmlNode):
    self.type = 'OutStreamPrint'

'''
 Interface Dictionary (factory) (private)
'''
__base                    = 'OutStreamManager'
__interFaceDict           = {}
__interFaceDict['Plot'  ] = OutStreamPlot
__interFaceDict['Print'  ] = OutStreamPrint
__knownTypes              = __interFaceDict.keys()

def knonwnTypes():
  return __knownTypes

def returnInstance(Type):
  '''
  function used to generate a OutStream class
  @ In, Type : OutStream type
  @ Out,Instance of the Specialized OutStream class
  '''
  try: return __interFaceDict[Type]()
  except KeyError: raise NameError('not known '+__base+' type '+Type)  
  



