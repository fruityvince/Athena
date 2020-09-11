from Athena import AtCore, AtConstants, AtUtils
import sys

import bpy

__author__ = 'Gregory Pijat'
__version__ = '0.1.0'
__released__ = '2020/07/14'
__edited__ = '2020/07/25'

__all__ = ('TestCheck',)


@AtCore.automatic
class TestCheck(AtCore.Process):

    NO_OBJECT_IN_SCENE = AtCore.Thread(title='These nodes are in the center of the world')

    def check(self):

        errors = {}

        for obj in bpy.context.scene.objects: 
            errors[obj.name] = obj

        if errors:
            self.NO_OBJECT_IN_SCENE.setFail()
            self.addFeedback(
                    thread=self.NO_OBJECT_IN_SCENE,
                    toDisplay=list(errors.keys()),
                    toSelect=list(errors.values()),
                )

    def fix(self):

        feedback = self.getFeedback(self.NO_OBJECT_IN_SCENE)
        if feedback is not None:
            print('fake fix', feedback)

    def tool(self):

        from Qt import QtWidgets

        return QtWidgets.QListWidget()


# Setup
'''
import sys
sys.path.append('C:\Python37\Lib\site-packages')
sys.path.append('C:\Workspace\Athena\src')

import Athena.ressources.Athena_example.ContextExample

import Athena
Athena._reload(__name__)

Athena.launch(dev=True)
'''

#FIXME: In python 3 (Or Blender only) when an exception occured I can't catch it and print it in the TracebackWidget.
"""
Traceback (most recent call last):
  File "C:/Workspace/Athena/src\Athena\AtGui\AtUi.py", line 1047, in execFix
    result, status = self._blueprint.fix()
  File "C:/Workspace/Athena/src\Athena\AtCore.py", line 619, in fix
    returnValue = self._fix(*args, **kwargs)
  File "C:/Workspace/Athena/src\Athena\AtCore.py", line 233, in fix
    result = fix_(self, *args, **kwargs)
  File "C:/Workspace/Athena/src\Athena\ressources\Athena_example\ContextExample\blender\processes\testCheck.py", line 39, in fix
    feedback = self.getFeedback(self.NO_OBJECT_IN_SCENE, None)
TypeError: getFeedback() takes 2 positional arguments but 3 were given

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:/Workspace/Athena/src\Athena\AtGui\AtUi.py", line 1059, in execFix
    self.setFeedback(exception)
  File "C:/Workspace/Athena/src\Athena\AtGui\AtUi.py", line 953, in setFeedback
    self._processDisplay.logTraceback(feedback)
  File "C:/Workspace/Athena/src\Athena\AtGui\AtUi.py", line 1473, in logTraceback
    self._tracebackWidget.logTraceback(traceback)
  File "C:/Workspace/Athena/src\Athena\AtGui\AtUi.py", line 1347, in logTraceback
    self.document().setPlainText(AtUtils.formatTraceback(traceback.format_exc(exception)))
  File "C:\Program Files\Blender Foundation\Blender 2.83\2.83\python\lib\traceback.py", line 167, in format_exc
    return "".join(format_exception(*sys.exc_info(), limit=limit, chain=chain))
  File "C:\Program Files\Blender Foundation\Blender 2.83\2.83\python\lib\traceback.py", line 121, in format_exception
    type(value), value, tb, limit=limit).format(chain=chain))
  File "C:\Program Files\Blender Foundation\Blender 2.83\2.83\python\lib\traceback.py", line 508, in __init__
    capture_locals=capture_locals)
  File "C:\Program Files\Blender Foundation\Blender 2.83\2.83\python\lib\traceback.py", line 337, in extract
    if limit >= 0:
TypeError: '>=' not supported between instances of 'TypeError' and 'int'
"""