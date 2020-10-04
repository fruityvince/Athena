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

descriptions = \
{
    ID.NoConstructionHistory:
        {
            'process': 'Athena.ressources.examples.Athena_Maya.processes.noConstructionHistory.NoConstructionHistory', 
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
            'process': 'Athena.ressources.examples.Athena_Maya.processes.noNGons.NoNGons',
            'category': 'Model Sanity',
            'links': 
              (
                  (ID.NoTris, Link.CHECK, Link.CHECK),
              ),
        },

    ID.NoTris:
        {
            'process': 'Athena.ressources.examples.Athena_Maya.processes.noTris.NoTris',
            'tags': Tag.DEPENDANT,
            'category': 'Model Sanity',
        },


    ID.TestCheck:
        {
            'process': 'Athena.ressources.examples.Athena_Maya.processes.testCheck.TestCheck',
            'category': 'Sanity Test',
        }, 

    ID.NoStaticAnimKeys:
        {
            'process': 'Athena.ressources.examples.Athena_Maya.processes.noStaticAnimKeys.NoStaticAnimKeys',
            'category': 'Animation',
        },

    ID.CleanCompoundConnections:
        {
            'process': 'Athena.ressources.examples.Athena_Maya.processes.cleanCompoundConnections.CleanCompoundConnections',
            'category': 'Dependency Graph Sanity',
        },

    ID.NamespacesAreIncremental:
        {
            'process': 'Athena.ressources.examples.Athena_Maya.processes.namespacesAreIncremental.NamespacesAreIncremental',
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
