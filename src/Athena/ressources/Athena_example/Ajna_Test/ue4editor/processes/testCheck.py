from Athena import AtCore, AtConstants

import unreal

__author__ = 'Gregory Pijat'
__version__ = '0.1.0'
__released__ = '2020/07/14'
__edited__ = '2020/07/25'

__all__ = ('TestCheck',)


@AtCore.automatic
class TestCheck(AtCore.Process):

    NO_HIDDEN_ACTOR = AtCore.Thread(title='These nodes are in the center of the world')

    def check(self):

        for actor in unreal.EditorLevelLibrary.get_all_level_actors():
            if actor.hidden:
                self.toFix.append(actor)

        self.addFeedback(
                thread=self.NO_HIDDEN_ACTOR,
                toDisplay=self.toFix,
                toSelect=self.toFix,
                selectMethod=unreal.GlobalEditorUtilityBase.set_actor_selection_state
            )

    def fix(self):

        feedback = self.feedback.get(self.NO_HIDDEN_ACTOR, None)
        if feedback is not None:
            print('fake fix', feedback)

    def tool(self):

        from Qt import QtWidgets

        return QtWidgets.QListWidget()
