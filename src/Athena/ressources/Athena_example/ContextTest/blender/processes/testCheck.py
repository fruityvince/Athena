from Athena import AtCore, AtConstants

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

        self.addFeedback(
                thread=self.NO_OBJECT_IN_SCENE,
                toDisplay=errors.keys(),
                toSelect=errors.values(),
            )

    def fix(self):

        feedback = self.feedback.get(self.NO_OBJECT_IN_SCENE, None)
        if feedback is not None:
            print('fake fix', feedback)

    def tool(self):

        from Qt import QtWidgets

        return QtWidgets.QListWidget()
