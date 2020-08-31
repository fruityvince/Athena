from Athena import AtCore

from maya import cmds
from maya.api import OpenMaya, OpenMayaAnim


__all__ = \
    (
        'NoStaticAnimKeys',
    )


class NoStaticAnimKeys(AtCore.Process):
    """This Process will iterate through all animCurve nodes of the scene and look for static keys.

    check:
        If all keys of a curve have the same value, the curve is static and will be deleted through the fix process.
        Otherwise, each keys of the curve will be checked to find if it should be kept or removed.
        For each key, the current key, `key-1` and `key+1` will be compared, if they have the same value and `key-1`
        have no out tangent, current key have no in or out tangent and `key+1` have no in tangent, the key is static and
        does not affect the animation.

    fix:
        Delete all static anim curves and remove the static keys from the curves that have static keys but are not
        completely static.

    notes:
        This process can take a lot of time if performed on a scene with a lot of animations. Remember that this process
        will check each key for each animCurve that are not static. (try mel command "size(`ls -type animCurve`)" to know
        how many curves there is in the current scene)

        Also, remember that this process will probably remove from 80% to 90% of the curves in the scenes, the process
        will force maya to recompute some of its UI and cause the process to be more than 10x longer. Close NodeEditor,
        Outliner, GraphEditor and Script Editor + Focus on the viewport (CTRL+MAJ) to optimize fix execution.

    """

    STATIC_CURVES = AtCore.Thread(title='All these animCurves nodes are static.')

    STATIC_KEYS = AtCore.Thread(title='All these animCurves nodes have static keys.')

    def __init__(self):
        """ Define all instance attributes """

        self.allAnimCurves = []

        self.staticCurves = []
        self.staticKeys = {}

        self.isChecked = False

    def check(self, deep=True, exclude=()):
        """ Iterate through all anim curves and their keys to find those who are static and should be deleted/removed

        :parameter deep: If True, will perform a deep inspection on curves by checking each keys to find static ones.
        :type deep: bool (default: True)

        :parameter exclude: Iterable containing lists of maya.api.OpenMaya.MObject() to ignore on check. Remember that
        the more item are excluded, the more the check will be longer.
        :type exclude: list(list(maya.api.OpenMaya.MObject()))

        :return: All nodes with errors (Some are statics and others only have static keys)
        :rtype: list
        """

        self.reset()

        staticCurves = []
        staticKeys = {}

        exclude = [node for excludeList in exclude for node in excludeList]

        # Iter through all animCurve nodes.
        self.allAnimCurves = cmds.ls(type='animCurve')
        iterator = OpenMaya.MItDependencyNodes(OpenMaya.MFn.kAnimCurve)
        iteratorIndex = 0
        baseValue = 100. / (len(self.allAnimCurves) or 1)
        while not iterator.isDone():
            iteratorIndex += 1
            self.setProgressValue(iteratorIndex * baseValue)

            thisNode = iterator.thisNode()

            if thisNode in exclude:
                iterator.next()
                continue

            animCurveMFn = OpenMayaAnim.MFnAnimCurve(thisNode)
            if animCurveMFn.isFromReferencedFile:
                iterator.next()
                continue

            # If the curve is static it should be deleted
            if animCurveMFn.isStatic:
                staticCurves.append(iterator.thisNode())
                iterator.next()
                continue

            if not deep:
                iterator.next()
                continue

            staticKeysIds = []
            numKeys = animCurveMFn.numKeys
            for iKey in range(numKeys):  # Iter through all key of the current animCurve node

                iKeyPrevious = 0 if iKey == 0 else iKey - 1
                iKeyNext = numKeys - 1 if iKey == numKeys - 1 else iKey + 1

                value = animCurveMFn.value(iKey)  # float
                # frame = animCurveMFn.input(iKey)  # maya.api.OpenMaya.MTime

                # True = inTangent, False = outTangent
                previousOutTangent = animCurveMFn.getTangentAngleWeight(iKeyPrevious, False)[0]
                inTangent = animCurveMFn.getTangentAngleWeight(iKey, True)[0]
                outTangent = animCurveMFn.getTangentAngleWeight(iKey, False)[0]
                nextInTangent = animCurveMFn.getTangentAngleWeight(iKeyNext, True)[0]

                # If the previous key out tangent, the current key in and out tangent and the next key inTangent have a value the current key should not be deleted.
                if previousOutTangent.value or inTangent.value or outTangent.value or nextInTangent.value:
                    continue

                # If the value of previous, the current and the next key are similar, the key should not be kept.
                if animCurveMFn.value(iKeyPrevious) == value == animCurveMFn.value(iKeyNext):
                    staticKeysIds.append(iKey)

            if staticKeysIds:
                staticKeys[animCurveMFn] = staticKeysIds

            iterator.next()

        self.staticCurves = staticCurves
        self.staticKeys = staticKeys

        if staticCurves:
            self.setFail(self.STATIC_CURVES)
            self.setFeedback(self.STATIC_CURVES, toDisplay=staticCurves, toSelect=staticCurves)
        # else:
        #     self.setSuccess(self.STATIC_CURVES)

        if staticKeys:
            self.setFail(self.STATIC_KEYS)
            self.setFeedback(thread=self.STATIC_KEYS, toDisplay=staticKeys, toSelect=staticKeys)
        # else:
            # self.setSuccess(self.STATIC_KEYS)

        self.isChecked = True
        return staticCurves, staticKeys

    def fix(self, deep=True, exclude=()):
        """ Iterate through all errors and delete static anim curves and remove static keys from their curves.

        :parameter deep: If True, will perform a deep inspection on curves by checking each keys to find static ones.
        :type deep: bool (default: True)

        :parameter exclude: Iterable containing lists of maya.api.OpenMaya.MObject() to ignore on check. Remember that
        the more item are excluded, the more the check will be longer.
        :type exclude: list(list(maya.api.OpenMaya.MObject()))
        """

        if not self.isChecked or len(self.allAnimCurves) != len(cmds.ls(type='animCurve')):
            self.check(deep=deep, exclude=exclude)

        #TODO: Disable the viewport to increase performances.

        # Save the method in a variable to reduce calls in loops.
        setProgressValue = self.setProgressValue

        # Store instance attributes in local variables.
        staticCurves = self.staticCurves
        staticKeys = self.staticKeys
        errorsCount = len(staticCurves) + len(staticKeys)

        # Calculate the max value in the progressBar that should be used for the staticCurves
        staticCurvesValue = (len(staticCurves)*100.) / (errorsCount or 1)

        deletionModifier = OpenMaya.MDGModifier()  # Define a DG modifier to delete static anim curves.
        baseValue = staticCurvesValue / (len(staticCurves) or 1)  # Define the base percentage for the static curves
        for i, animCurve in enumerate(staticCurves):
            setProgressValue(i * baseValue)

            dgNode = OpenMaya.MFnDependencyNode(animCurve)
            connectionModifier = OpenMaya.MDGModifier()  # Define a DG modifier to disconnect plugs.
            for sourcePlug in dgNode.getConnections():
                unlockedPlugs = []

                # Unlock source plug recursively to allow disconnection. We do not need to re-lock, the curve will be deleted.
                lockPlugRecursively(sourcePlug)

                destinationPlugs = sourcePlug.destinations()
                for destinationPlug in destinationPlugs:
                    # Unlock destination plug recursively to allow disconnection.
                    unlockedPlugs.extend(lockPlugRecursively(destinationPlug))
                    connectionModifier.disconnect(sourcePlug, destinationPlug)
                # Execute the Modifier queue to prevent issue when re-lock plugs.
                connectionModifier.doIt()

                # Ensure destinations plugs will keep source plugs values - Prevent unwanted behaviour like multiplyDivide auto reset to 0
                for destinationPlug in destinationPlugs:
                    try:
                        # This can fail, for instance, on children of compound attributes when the compound itself has a connection
                        destinationPlug.setFloat(sourcePlug.asFloat())
                    except RuntimeError:
                        pass

                for plug in unlockedPlugs:
                    plug.isLocked = True
            del connectionModifier

            deletionModifier.deleteNode(animCurve)
        deletionModifier.doIt()
        del deletionModifier

        if not deep:
            self.isChecked = False
            return

        # Remove all useless key in all animCurves
        baseValue = ((len(staticKeys)*100.) / (errorsCount or 1)) / (len(staticKeys) or 1)  # Define the base percentage for the staticKeys
        for i, (animCurveMFn, frameIndexes) in enumerate(staticKeys.iteritems()):
            setProgressValue(staticCurvesValue + (i * baseValue))

            # Retrieve `keyTimeValue` plug to unlock it and ensure curve key edit (e.g. When key are part of an animLayer)
            keyTimeValuePlug = animCurveMFn.findPlug('keyTimeValue', True)
            ktvLocked = keyTimeValuePlug.isLocked

            keyTimeValuePlug.isLocked = False
            for frameIndex in reversed(frameIndexes):  # Key index on curves are automatically reordered on each operation, starting from the end will prevent errors.
                animCurveMFn.remove(frameIndex)
            keyTimeValuePlug.isLocked = ktvLocked

        self.isChecked = False


# Utils
def lockPlugRecursively(plug, lock=False):
    """Lock or unlock the given plug recursively (the plugs and then its parents)

    :parameter plug: The plug to recursively change lock state.
    :type plug: maya.api.OpenMaya.MPlug or str
    :parameter lock: Lock state to set for the plug.
    :type lock: bool

    :return: Plugs that have been changed to the given state.
    :rtype: list(maya.api.OpenMaya.MPlug, ...)
    """

    lockedPlugs = []

    # If the given plug is str instead of MPlug
    if not isinstance(plug, OpenMaya.MPlug):
        nodeStr, _, plugStr = plug.partition('.')
        sList = OpenMaya.MSelectionList().add(nodeStr)
        dagNode = OpenMaya.MFnDagNode(sList.getDependNode(0))
        plug = dagNode.findPlug(plugStr, False)

    doIt = True
    while doIt:  # Trigger one time to process the given plug and then it will process all parents.
        if plug.isLocked is not lock:
            plug.isLocked = lock
            lockedPlugs.append(plug)

        doIt = plug.isChild
        if doIt:
            plug = plug.parent()

    return lockedPlugs
