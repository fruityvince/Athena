from Athena import AtCore

from maya import cmds
from maya.api import OpenMaya


__all__ = \
    (
        'CleanCompoundConnections',
    )


class CleanCompoundConnections(AtCore.Process):
    """Will iterate through all plugs of all nodes in the scene and remove the connections from parent of compound plugs
    that have at least one child with an input connection.

    ..notes:
        This process is meant to remove useless connections in the Dependency Graph and reduce dirty propagation.
    """

    def __init__(self):
        """Init process instance attributes"""
        self.toFix = []
        self.data = {}

    def check(self):
        """Iterate through all Dependency Nodes of the maya scene and check for any of their compound plugs if they have
        both connections on the parent and on one or more child. If so, the connections can be optimised by moving
        connections from the input parent source attributes to the children with no input connections.
        """

        # Reset the process feedback and attributes.
        self.clearFeedback()
        self.toFix = []
        self.data = {}

        # Get and iter through all valid dependency nodes.
        iterator = OpenMaya.MItDependencyNodes(OpenMaya.MFn.kInvalid)
        while not iterator.isDone():

            # Retrieve Dependency Node function set and iter through all plugs.
            nodeFn = OpenMaya.MFnDependencyNode(iterator.thisNode())
            for i in xrange(nodeFn.attributeCount()):

                # Get the plug from the index and continue if its not a compound parent or if it is not connected.
                iPlug = nodeFn.findPlug(nodeFn.attribute(i), True)
                if not iPlug.isCompound or iPlug.isChild or not iPlug.isConnected:
                    continue

                # Get the plug input connection (Empty list or list with one value).
                iInputPlug = iPlug.source()
                if not iInputPlug or iInputPlug.isNull:
                    continue

                # Iter on the list to get the connected children.
                connectedChildren = []
                for j in xrange(iPlug.numChildren()):
                    jPlug = iPlug.child(j)
                    if jPlug.connectedTo(True, False):
                        connectedChildren.append(jPlug)
                if not connectedChildren:
                    continue

                # Store the check data using the plug name, also used for display.
                plugName = iPlug.name()
                self.toFix.append(plugName)
                self.data[plugName] = {'parent': iPlug, 'source': iInputPlug, 'connectedChildren': connectedChildren}

            iterator.next()

        # Add the feedback and set the process to True.
        self.addFeedback("All these nodes have dirty compound attribute's connections",
                         toDisplay=self.toFix,
                         documentation='WIP doc')
        self.isChecked = True

    def fix(self):
        """Iter through all error to remove parent input connections and move them to the right children plugs."""

        # If the fix is runt without check, launch check to retrieve data.
        if not self.isChecked:
            self.check()

        # Define DGModifer for both parent and children
        parentCompoundModifier = OpenMaya.MDGModifier()
        childCompoundModifier = OpenMaya.MDGModifier()

        for parent in self.toFix:
            # Retrieve data from the check
            parentCompoundPlug = self.data[parent]['parent']
            parentSourcePlug = self.data[parent]['source']
            connectedChildren = self.data[parent]['connectedChildren']

            # Add the parent disconnection in the DG Modifier and iter through all of its children.
            parentCompoundModifier.disconnect(parentSourcePlug, parentCompoundPlug)
            for i in xrange(parentCompoundPlug.numChildren()):
                childPlug = parentCompoundPlug.child(i)
                if childPlug in connectedChildren:
                    continue
                childCompoundModifier.connect(parentSourcePlug.child(i), childPlug)  # We need the index to get the same child in parent source.

        # Remove all parent's input connections at once.
        parentCompoundModifier.doIt()
        del parentCompoundModifier

        # Reconnect all parent's input children that need to be connected to parent children.
        childCompoundModifier.doIt()
        del childCompoundModifier

        # Process is now fixed and need to be re-checked.
        self.isChecked = False
