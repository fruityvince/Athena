from Athena import AtCore, AtConstants

from maya import cmds
from maya.api import OpenMaya as om

import random

from Qt import QtWidgets

__author__ = 'Gregory Pijat'
__version__ = '0.1.0'
__released__ = '2020/07/14'
__edited__ = '2020/07/25'

__all__ = ('TestCheck',)

CUSTOM_ERROR_LEVEL = AtCore.Status.FeedbackStatus('Custom Error', 4.7, (29, 20, 88), type=AtCore.Status.TYPE_FAIL, canBeDefault=True)


@AtCore.automatic
class TestCheck(AtCore.Process):
    """This documentation is only meant to be used as a documentation for the process.

    This value must be updated: {hello}

    """

    NODES_UNDER_WORLD = AtCore.Thread(
        title='These nodes are under world', 
        defaulFailLevel=CUSTOM_ERROR_LEVEL,
        documentation='Reparent you nodes using CTRL+G when selected, or select two nodes and CTRL+P'
    )
    NODES_AT_ORIGIN = AtCore.Thread(title='These nodes are in the center of the world')

    TEST_PERFORMANCES = AtCore.Thread(title='This trhead will generate a lot of error to test performances')

    def __init__(self):
        self._docFormat_['hello'] = random.uniform(0, 42)

    def check(self):

        self.toCheck = cmds.ls(dag=True, type='mesh', objectsOnly=True, long=True)

        self.toFix = ([], [])

        baseProgressValue = 100. / (len(self.toCheck) or 1)
        for i, shape in enumerate(self.toCheck):
            self.setProgressValue(baseProgressValue * i, text='Checking: {0}'.format(shape))
            node = next(iter(cmds.listRelatives(shape, parent=True)), None)


            if not cmds.listRelatives(node, parent=True):
                self.toFix[0].append(node)

            if all(axe == 0.0 for axe in cmds.getAttr('{}.translate'.format(node))[0]):
                self.toFix[1].append(node)

        self.addFeedback(
                thread=self.NODES_UNDER_WORLD,
                toDisplay=self.toFix[0],
                toSelect=self.toFix[0],
            )

        self.addFeedback(
                thread=self.NODES_AT_ORIGIN,
                toDisplay=self.toFix[1],
                toSelect=self.toFix[1],
            )

        errors = range(0, 1000)
        self.addFeedback(
                thread=self.TEST_PERFORMANCES,
                toDisplay=errors,
                toSelect=errors,
            )

    def fix(self):
        raise RuntimeError()

        feedback = self.feedback.get(self.NODES_UNDER_WORLD, None)
        if feedback is not None:
            cmds.group(feedback._toSelect)

    def tool(self):
        raise RuntimeError()

        tool = QtWidgets.QListWidget()

        return tool
