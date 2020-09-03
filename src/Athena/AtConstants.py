PROGRAM_NAME = 'Athena'

VERSION = '2.0.0-wip'

AVAILABLE_SOFTWARE = ('maya', 'katana', 'houdini', 'nuke', 'mari', 'ue4editor', 'blender')

CHECK = 'check'

FIX = 'fix'

TOOL = 'tool'

AVAILABLE_DISPLAY_MODE = ('Header', 'Category', 'Alphabetically')

ENV_TEMPLATE = '{package}.{athenaPackage}.{software}.envs'

PROGRESSBAR_FORMAT = '  %p% - {0}'

PROCESS_TEMPLATE = \
'''
from Athena import AtCore

class {ProcessName}(AtCore.Process):
	"""This docstring will be displayed in the help popup.
	You should really explain clearly what the check, fix and other overrided method will do.

	Check: 
		Explain clearly what this check will do.

	Fix: 
		Explain clearly how the fix will correst the errors.

	Misc: 
		- Here you can specify if there is specificities to know before using this check
		- You can also give details on what issue could happen
	"""

	def __init__(self):
		""" Docstring is a good pratice """

		pass

	def check(self):
		""" Docstring is a good pratice """

		pass

	def fix(self):
		""" Docstring is a good pratice """

		pass

	def tool(self):
		""" Docstring is a good pratice """

		pass

'''

# If types change, unit tests from AtTest must be updated too.
BLUEPRINT_TEMPLATE = \
{
	'process': '',  # String
	'category': '',  # String
	'arguments': {'': ([], {})},  # Dict with str key and tuple with a tuple and a dict as value.
	'tags': 0,  # Integer - AtCore.Tag
	'links': (('', '', '')),  # Tuple of tuple that contains three str, the target ID, the source method and the target method.
	'statusOverrides': {'': {}},  # Dict that contains name of the threads to overrides and a dict with new status indexed by status type.
	'options': {}  # Dict with str key and values.
}

PARAMETERS_TEMPLATE = \
{
	'recheck': True,
	'orderFeedbacksByPriority': False,
	'feedbackDisplayWarning': True,
	'feedbackDisplayWarningLimit': 100,
}

NO_DOCUMENTATION_AVAILABLE = '\nNo documentation available for this process.\n'

WIKI_LINK = 'https://github.com/gpijat/Athena'
REPORT_BUG_LINK = 'https://github.com/gpijat/Athena/issues'
