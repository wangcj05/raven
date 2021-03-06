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
import sys, os, time
try:
  import autopy, pyscreenshot
  autopyAndPyscreenshotImported = True
except:
  autopyAndPyscreenshotImported = False

def run(self,Input):
  self.x1 = Input['x1']
  self.x2 = Input['x2']
  self.y = self.x1**2 + self.x2
  time.sleep(1)

  idxSet = str(int(Input['x1'][0])) + '_' + str(int(Input['x2'][0]))
  myFile = 'test_' + idxSet + '.png'

  ## Skip the first iteration, there is nothing to draw yet.
  if myFile == 'test_0_0.png':
    return

  testImageFile = os.path.join('..','gold','plot',myFile)
  if not autopyAndPyscreenshotImported:
    return
  testImage = autopy.bitmap.Bitmap.open(testImageFile)

  ## This didn't work, but everything else from the autopy library seems to:
  # screen = autopy.bitmap.capture_screen()

  ## Use pyscreenshot instead to get the screen image, save it to a file, and
  ## then load it using autopy, yes this is more cumbersome than necessary, but
  ## is one extra line that much work? The test harness will clean up these
  ## files, though the comparison against gold will be done in here, since the
  ## gold file represents a sub-image of the whole screenshot.
  pyscreenshot.grab().save(myFile)
  screenImage = autopy.bitmap.Bitmap.open(myFile)

  pos = screenImage.find_bitmap(testImage)
  if pos:
    pass
  else:
    print('Interactive plot not found on screen at step: ' + idxSet)
    sys.exit(1)
