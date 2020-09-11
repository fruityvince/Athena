from Athena import AtCore

from maya import cmds
from maya.api import OpenMaya


__all__ = \
    (
        'NamespacesAreIncremental',
    )


class NamespacesAreIncremental(AtCore.Process):
    """Check for namespaces that are not incremented in a constant way (increments of 1.)

    The check can check for all namespaces or only those given by the user.

    .. note::
        - If you don't give a maxPadding the fix preserves your padding: 02, 04, 08 becomes 01, 02, 03 where 002, 004, 008
        is replaced with 001, 002, 003.
        - The check process will try to perform a rename (using the current name and a suffix) to test if the namespace
        can be renamed (It seems that there is no other way to check if a namespace can be renamed..). Off course, it
        will undo changes to keep a clean namespace.
    """

    ROOT_NAMESPACE = ':'
    TAIL_DIGITS_REGEX = re.compile('^(?P<name>.*?)(?P<number>\d+)$')

    def __init__(self):
        """ Init instance attributes """

        super(NamespacesAreIncremental, self).__init__()

        self.nonIncrementalNS = {}
        self.isChecked = False

        # Delete all empty namespaces to clean the scene.
        namespaceLib.deleteAllEmptyNamespaces()

    def check(self, fromParents=None, maxPadding=None):
        """ Check all namespaces or namespaces given by user to find theses who don't follow a logical increment.

        :param fromParents: List of parent objects to check the namespaces (will ignore all other namespaces)
        :type fromParents: list or NoneType (default: NoneType)
        :param maxPadding: Determine the padding digit count to have in the namespace number.
        :type maxPadding: int or NoneType (default: NoneType)
        """

        nonIncrementalNS = {}

        # Get the namespaces or use those given by user
        if fromParents:
            nsListFromParents = []
            for parent in fromParents:
                nsListFromParents.extend([location.rpartition(':')[0] for location in mc.listRelatives(parent, children=True) or []])
            namespaces = list(set(OpenMaya.MNamespace.makeNamepathAbsolute(inputNS) for inputNS in nsListFromParents))
        else:
            namespaces = sorted(
                list(set(OpenMaya.MNamespace.getNamespaces(OpenMaya.MNamespace.rootNamespace(), recurse=True))),
                key=lambda ns: ns.count(':'),
                reverse=True
            )

        namespaceData = {}
        baseProgressValue = 100.0 / (len(namespaces) or 1)
        for i, namespace in enumerate(namespaces):
            self.setProgressValue(i*baseProgressValue)

            # -- Test if namespace is from ref and can be renamed. (I can't find another way..)
            parent, _, currentShortNS = namespace.rpartition(':')
            testName = '{0}_old'.format(currentShortNS)
            try:
                OpenMaya.MNamespace.renameNamespace(namespace, testName, parent=parent or self.ROOT_NAMESPACE)
            except RuntimeError:
                continue  # Will be executed right after the finally statement to clean this ugly test.
            else:
                OpenMaya.MNamespace.renameNamespace('{0}:{1}'.format(parent, testName), currentShortNS, parent=parent or self.ROOT_NAMESPACE)
            # -- Namespace here can be renamed.

            # Iter through the namespace string to get its tail digit as string (e.g. '001')

            namespaceParts = self.TAIL_DIGITS_REGEX.match(namespace)
            if not namespaceParts:
                continue

            nameWithoutDigits, tailDigits = namespaceParts.groups()
            if nameWithoutDigits in namespaceData:
                namespaceData[nameWithoutDigits].append(tailDigits)
            else:
                namespaceData[nameWithoutDigits] = [tailDigits]

        nonIncrementalNSFeedback = []  # This is only used to have a more readable display - non selectable.
        for nameWithoutDigits, digitsList in namespaceData.iteritems():
            if nameWithoutDigits in nonIncrementalNS:  # One namespace of this increment have already been checked.
                continue

            digitsList.sort(key=int)  # Sort the list of digit by order, to always rename the namespace with the lower value first. (This allow to keep order)

            # There is now a coherent increment to compare with our ordered digit list
            for i, digits in enumerate(digitsList):
                version = i + 1  # Artist don't count from 0
                paddingLen = maxPadding or len(digitsList[0])  # If there is no limit, the digit count of the first namespace is used.
                if version != int(digits) or len(digits) != paddingLen:
                    oldNS = ['{0}{1}'.format(nameWithoutDigits, padding) for padding in digitsList]
                    nonIncrementalNS[nameWithoutDigits] = {
                        'old': oldNS,
                        'new': ['{0}{1}'.format(nameWithoutDigits, str(i + 1).zfill(paddingLen)) for i in xrange(len(digitsList))]
                    }
                    nonIncrementalNSFeedback.extend(oldNS)
                    break

        self.logFeedback(
            titles=('These namespace does not have a logical increment',),
            elements=(nonIncrementalNSFeedback,)
        )
        self.nonIncrementalNS = nonIncrementalNS

        self.isChecked = True
        return nonIncrementalNS

    def fix(self, **kwargs):
        """ Rename the namespace with the right digit value """

        if not self.isChecked:
            self.check(**kwargs)

        currentNS = OpenMaya.MNamespace.currentNamespace()
        for namespace, data in sorted(self.nonIncrementalNS.iteritems(), key=lambda ns: ns[0].count(':'), reverse=True):

            for oldName, newName in zip(data['old'], data['new']):

                # We can only get the parent of the current namespace
                OpenMaya.MNamespace.setCurrentNamespace(oldName)
                parent = OpenMaya.MNamespace.parentNamespace()
                if oldName.endswith(newName):
                    continue
                OpenMaya.MNamespace.renameNamespace(oldName, newName.rpartition(':')[-1], parent=parent or self.ROOT_NAMESPACE)
        OpenMaya.MNamespace.setCurrentNamespace(currentNS)

        self.isChecked = False
