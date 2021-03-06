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
#***************************************
#* Simple analytic test ExternalModule *
#***************************************
#
# Simulates the attenuation of a beam through a purely-scattering medium with N distinct materials and unit length.
#     The uncertain inputs are the opacities.
#
import numpy as np

def evaluate(inp):
  if len(inp)>0:
    return np.exp(-sum(inp)/len(inp))
  else:
    return 1.0

def run(self,Input):
  self.ans  = evaluate(Input.values())

#
#  This model has analytic mean and variance documented in raven/docs/tests
#
