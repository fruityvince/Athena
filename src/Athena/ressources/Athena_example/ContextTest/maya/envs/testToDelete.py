from Athena.AtCore import Tag, Link, ID, Status

header = \
(
    ID.NoConstructionHistory,
    ID.NoNGons,
    ID.NoTris,
    ID.TestCheck,
)

register = \
{
    ID.NoConstructionHistory:
        {
            'process': 'Athena.ressources.Athena_example.ContextTest.maya.processes.noConstructionHistory.NoConstructionHistory', 
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
            'process': 'Athena.ressources.Athena_example.ContextTest.maya.processes.noNGons.NoNGons',
            'category': 'Model Sanity',
            # 'links': 
            #   (
            #       (ID.NoConstructionHistory, Link.CHECK, Link.FIX),
            #   ),
        },

    ID.NoTris:
        {
            'process': 'Athena.ressources.Athena_example.ContextTest.maya.processes.noTris.NoTris',
            'category': 'Model Sanity',
        },

    ID.TestCheck:  # Second NoTris check to test if the wrapp of the class attribute is an issue. It should not.
        {
            'process': 'Athena.ressources.Athena_example.ContextTest.maya.processes.noTris.NoTris',
            'category': 'Model Sanity',
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
