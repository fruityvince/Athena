from Athena.AtCore import Tag, Link, ID, Status

header = \
(
    ID.NoConstructionHistory,
    ID.NoNGons,
    ID.NoTris,
    ID.TestCheck,
    ID.NoStaticAnimKeys,
    ID.Test,
)

register = \
{
    ID.NoConstructionHistory:
        {
            'process': 'Athena.ressources.Athena_example.Ajna_Test.maya.processes.noConstructionHistory.NoConstructionHistory', 
            'category': 'Scene Sanity',
            'tags': Tag.NON_BLOCKING | Tag.NO_BATCH,
            'arguments': 
                {
                    '__init__': ((), {})
                },
            # 'statusOverrides':
            #   {
            #       'NODES_WITH_HISTORY': {Status.FailStatus: Status.CRITICAL},
            #   },
        },

    ID.NoNGons:
        {
            'process': 'Athena.ressources.Athena_example.Ajna_Test.maya.processes.noNGons.NoNGons',
            'category': 'Model Sanity',
            # 'links': 
            #   (
            #       (ID.NoConstructionHistory, Link.CHECK, Link.FIX),
            #   ),
        },

    ID.NoTris:
        {
            'process': 'Athena.ressources.Athena_example.Ajna_Test.maya.processes.noTris.NoTris',
            'category': 'Model Sanity',
        },

    ID.Test:  # Second NoTris check to test if the wrapp of the class attribute is an issue. It should not.
        {
            'process': 'Athena.ressources.Athena_example.Ajna_Test.maya.processes.noTris.NoTris',
            'category': 'Model Sanity',
        }, 

    ID.TestCheck:
        {
            'process': 'Athena.ressources.Athena_example.Ajna_Test.maya.processes.testCheck.TestCheck',
            'category': 'Sanity Test',
        }, 

    ID.NoStaticAnimKeys:
        {
            'process': 'Athena.ressources.Athena_example.Ajna_Test.maya.processes.noStaticAnimKeys.NoStaticAnimKeys',
            'category': 'Animation',
        },
}

parameters = \
{
    'recheck': True,
    'orderFeedbacksByPriority': False,
    'feedbackDisplayWarning': True,
    'feedbackDisplayWarningLimit': 100,
}
