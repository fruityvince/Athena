from Athena import AtCore, AtConstants

from maya import cmds
from maya.api import OpenMaya as OpenMaya

import random

from Qt import QtWidgets

__author__ = 'Gregory Pijat'
__version__ = '0.1.0'
__released__ = '2020/07/14'
__edited__ = '2020/08/24'

__all__ = ('TestCheck',)

CUSTOM_ERROR_LEVEL = AtCore.Status.FailStatus('Custom Error', (29, 20, 88), 2.0)


@AtCore.automatic
class TestCheck(AtCore.Process):
    """This documentation is only meant to be used as a documentation for the process.

    This value must be updated: {hello}

    """

    NODES_UNDER_WORLD = AtCore.Thread(
        title='These nodes are under world',
        successStatus=AtCore.Status.CORRECT,
        failStatus=CUSTOM_ERROR_LEVEL,
        documentation='Reparent you nodes using CTRL+G when selected, or select two nodes and press CTRL+P'
    )

    NODES_AT_ORIGIN = AtCore.Thread(title='These nodes are in the center of the world')

    TEST_PERFORMANCES = AtCore.Thread(
        title='This thread will generate a lot of error to test performances',
        failStatus=AtCore.Status.WARNING
    )

    def __init__(self):
        self._docFormat_['hello'] = random.uniform(0, 42)

    def check(self):

        self.toCheck = cmds.ls(dag=True, type='mesh', objectsOnly=True, long=True)

        self.toFix = ([], [])

        self.NODES_AT_ORIGIN.setSuccess()
        baseProgressValue = 100. / (len(self.toCheck) or 1)
        for i, shape in enumerate(self.toCheck):
            self.setProgressValue(baseProgressValue * i, text='Checking: {0}'.format(shape))
            node = next(iter(cmds.listRelatives(shape, parent=True)), None)


            if not cmds.listRelatives(node, parent=True):
                self.toFix[0].append(node)

            if all(axe == 0.0 for axe in cmds.getAttr('{}.translate'.format(node))[0]):
                self.NODES_AT_ORIGIN.setFail()
                self.addFeedback(
                    thread=self.NODES_AT_ORIGIN,
                    toDisplay=node,
                    toSelect=node,
            )

        if self.toFix[0]:
            self.NODES_UNDER_WORLD.setFail()
            self.setFeedback(
                    thread=self.NODES_UNDER_WORLD,
                    toDisplay=self.toFix[0],
                    toSelect=self.toFix[0],
                )
        # else:
        #     self.NODES_UNDER_WORLD.setSuccess()
        #     self.setFeedback(
        #             thread=self.NODES_UNDER_WORLD,
        #             toDisplay=cmds.ls(),
        #             toSelect=cmds.ls(),
        #         )

        errors = range(0, 10000)
        if errors:
            self.TEST_PERFORMANCES.setFail()
            self.setFeedback(
                    thread=self.TEST_PERFORMANCES,
                    toDisplay=errors,
                    toSelect=errors,
                )
        else:
            self.TEST_PERFORMANCES.setSuccess()

        # self.NODES_UNDER_WORLD.failStatus = CUSTOM_ERROR_LEVEL

    def fix(self):

        feedback = self.getFeedback(self.NODES_UNDER_WORLD)
        if feedback is not None:
            cmds.group(feedback._toSelect)

    def tool(self):

        tool = QtWidgets.QListWidget()

        return tool
