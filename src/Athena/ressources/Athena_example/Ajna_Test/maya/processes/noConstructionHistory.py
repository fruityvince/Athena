from Athena import AtCore, AtConstants

from maya import cmds
from maya.api import OpenMaya as om

__all__ = ('NoNGons',)


@AtCore.automatic
class NoConstructionHistory(AtCore.Process):

    NODES_WITH_HISTORY = AtCore.Thread(title='These nodes have construction history', failStatus=AtCore.Status.ERROR)

    def check(self):

        self.toCheck = cmds.ls(dag=True, type='transform', long=True)

        baseProgressValue = 100. / (len(self.toCheck) or 1)
        for i, each in enumerate(self.toCheck):
            self.setProgressValue(baseProgressValue * i, text='Checking: {0}'.format(each))

            history = cmds.listHistory(each, future=False, pruneDagObjects=True)

            if history:
                self.toFix.append(each)

        if self.toFix:
            self.setFail(self.NODES_WITH_HISTORY)
            self.setFeedback(
                    thread=self.NODES_WITH_HISTORY,
                    toDisplay=[cmds.ls(node, shortNames=True)[0] for node in self.toFix],
                    toSelect=self.toFix
                )
        else:
            self.setSuccess(self.NODES_WITH_HISTORY)

    def fix(self):

        if not self.isChecked:
            self.check()

        for each in self.toFix:
            cmds.delete(each, constructionHistory=True)
