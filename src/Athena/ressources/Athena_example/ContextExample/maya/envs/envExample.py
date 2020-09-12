from Athena.AtCore import Tag, Link, ID, Status
header = \
(
    ID.NoConstructionHistory,
    ID.NoNGons,
    ID.NoTris,
    ID.TestCheck,
    ID.NoStaticAnimKeys,
    ID.CleanCompoundConnections,
    ID.NamespacesAreIncremental,
)

register = \
{
    ID.NoConstructionHistory:
        {
            'process': 'Athena.ressources.Athena_example.ContextExample.maya.processes.noConstructionHistory.NoConstructionHistory', 
            'category': 'Scene Sanity',
            'tags': Tag.NON_BLOCKING | Tag.NO_BATCH,
            'arguments': 
                {
                    '__init__': ((), {})
                },
            'statusOverrides':
              {
                  'NODES_WITH_HISTORY': {Status.FailStatus: Status.CRITICAL},
              },
        },

    ID.NoNGons:
        {
            'process': 'Athena.ressources.Athena_example.ContextExample.maya.processes.noNGons.NoNGons',
            'category': 'Model Sanity',
            # 'links': 
            #   (
            #       (ID.NoConstructionHistory, Link.CHECK, Link.FIX),
            #   ),
        },

    ID.NoTris:
        {
            'process': 'Athena.ressources.Athena_example.ContextExample.maya.processes.noTris.NoTris',
            'category': 'Model Sanity',
        },


    ID.TestCheck:
        {
            'process': 'Athena.ressources.Athena_example.ContextExample.maya.processes.testCheck.TestCheck',
            'category': 'Sanity Test',
        }, 

    ID.NoStaticAnimKeys:
        {
            'process': 'Athena.ressources.Athena_example.ContextExample.maya.processes.noStaticAnimKeys.NoStaticAnimKeys',
            'category': 'Animation',
        },

    ID.CleanCompoundConnections:  # Second NoTris check to test if the wrapp of the class attribute is an issue. It should not.
        {
            'process': 'Athena.ressources.Athena_example.ContextExample.maya.processes.cleanCompoundConnections.CleanCompoundConnections',
            'category': 'Dependency Graph Sanity',
        },

    ID.NamespacesAreIncremental:
        {
            'process': 'Athena.ressources.Athena_example.ContextExample.maya.processes.namespacesAreIncremental.NamespacesAreIncremental',
            'category': 'Scene Sanity',
        },
}

settings = \
{
    'recheck': True,
    'orderFeedbacksByPriority': False,
    'feedbackDisplayWarning': True,
    'feedbackDisplayWarningLimit': 100,
    'allowRequestStop': True,
}
