from Athena.AtCore import Tag, Link, ID, Status

header = \
(
	ID.TestCheck,
)

register = \
{

	ID.TestCheck:
		{
			'process': 'Athena.ressources.Athena_example.Ajna_Test.ue4editor.processes.testCheck.TestCheck',
			'category': 'Sanity Test',
		}, 

}

parameters = \
{
	'recheck': True
}
