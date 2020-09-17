from Athena.AtCore import Tag, Link, ID, Status

header = \
(
	ID.TestCheck,
)

register = \
{

	ID.TestCheck:
		{
			'process': 'Athena.ressources.examples.Athena_Ue4Editor.processes.testCheck.TestCheck',
			'category': 'Sanity Test',
		}, 

}

parameters = \
{
	'recheck': True
}
