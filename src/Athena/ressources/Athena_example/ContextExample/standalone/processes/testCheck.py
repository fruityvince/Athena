from Athena import AtCore, AtConstants, AtUtils, AtExceptions
import os

__author__ = 'Gregory Pijat'
__version__ = '0.1.0'
__released__ = '2020/07/14'
__edited__ = '2020/07/25'

__all__ = ('TestCheck',)


@AtCore.automatic
class TestCheck(AtCore.Process):

    NO_PROJECT_IN_WORKSPACE = AtCore.Thread(title='There is no projects in Workspace')

    def check(self):

        self.toFix = os.listdir(r'C:/Workspace')

        #FIXME: If exception occured another exception occur in the traceback module.
        # raise AtExceptions.AthenaException('Error occured during execution of the current process.')

        if self.toFix:
            self.NO_PROJECT_IN_WORKSPACE.setFail()
            self.setFeedback(
                    thread=self.NO_PROJECT_IN_WORKSPACE,
                    toDisplay=self.toFix,
                    toSelect=self.toFix,
                )

    def fix(self):

        feedback = self.getFeedback(self.NO_PROJECT_IN_WORKSPACE)
        if feedback is not None:
            print('fake fix', feedback)

    def tool(self):

        from Qt import QtWidgets

        return QtWidgets.QListWidget()
