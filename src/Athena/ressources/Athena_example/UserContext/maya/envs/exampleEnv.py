from Athena.AtCore import Tag, Link, ID

header = \
(
	ID.BestModelEver,
	ID.ThisCheckIsBad,
	ID.TestForSanityCheck,
	ID.DemoCheckSG,
	ID.JustAnotherNonBlockingCheck,
	ID.NoNGons,
	ID.NoTris,
)

register = \
{

	ID.ThisCheckIsBad:
		{
			'process': 'Athena.ressources.Athena_example.UserContext.maya.processes.modeling.ThisCheckIsBad', 
			'category': 'Scene Sanity',
			'tags': Tag.OPTIONAL | Tag.NO_BATCH
		},

	ID.BestModelEver:
		{
			'process': 'Athena.ressources.Athena_example.UserContext.maya.processes.modeling.BestModelEver', 
			'category': 'Model Sanity',
			'tags': Tag.NO_BATCH,
			'arguments': 
				{
					'__init__': ([], {'color': 'Brown'})
				}
		},

	ID.TestForSanityCheck:
		{
			'process': 'Athena.ressources.Athena_example.UserContext.maya.processes.testCheck.TestForSanityCheck',
			'tags': Tag.DEPENDANT | Tag.OPTIONAL | Tag.NO_BATCH,
			'category': 'Test'
		},

	ID.DemoCheckSG:
		{
			'process': 'Athena.ressources.Athena_example.UserContext.maya.processes.shading.DemoCheckSG',
			'tags': Tag.NO_BATCH
		},

	ID.JustAnotherNonBlockingCheck:
		{
			'process': 'Athena.ressources.Athena_example.UserContext.maya.processes.modeling.JustAnotherNonBlockingCheck', 
			'tags': Tag.NON_BLOCKING | Tag.NO_BATCH,
			'links': 
				[
					(ID.NoNGons, Link.FIX, Link.CHECK), 
					(ID.NoTris, Link.FIX, Link.CHECK)
				],
		},

	ID.NoNGons:
		{
			'process': 'Athena.ressources.Athena_example.UserContext.maya.processes.modeling.NoNGons',
			'tags': Tag.NO_BATCH,
			'category': 'Model Sanity',
			'links': 
				[
					(ID.TestForSanityCheck, Link.CHECK, Link.CHECK),
				]
		},

	ID.NoTris:
		{
			'process': 'Athena.ressources.Athena_example.UserContext.maya.processes.modeling.NoTris',
			'category': 'Model Sanity',
		}, 

}

parameters = \
{
	'recheck': True
}