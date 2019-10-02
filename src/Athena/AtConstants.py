PROGRAM_NAME = 'Athena'

VERSION = 'alpha 0.0.1'

AVAILABLE_SOFTWARE = ['maya', 'katana', 'houdini', 'nuke', 'mari']

AVAILABLE_DISPLAY_MODE = ['Blueprint', 'Category', 'Alphabetically']

ENV_TEMPLATE = '{package}.{athenaPackage}.{software}.env'

PROGRESSBAR_FORMAT = '  %p% - {0}'

PROCESS_TEMPLATE = \
'''
from Athena import AtCore

class {ProcessName}(AtCore.Process):
	"""This docstring will be displayed in the help popup.
	You should really explain clearly what the check, fix and other overrided method will do.

	Check: Explain clearly what this check will do.

	Fix: Explain clearly how the fix will correst the errors.

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

BLUEPRINT_TEMPLATE = {'process': '', 
					  'arguments': {'': ([], {})},
					  'tags': [[]], 
					  'links': [[]]}

NO_DOCUMENTATION_AVAILABLE = '\nNo documentation available for this process.\n'