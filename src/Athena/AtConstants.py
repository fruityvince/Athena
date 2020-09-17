PROGRAM_NAME = 'Athena'

VERSION = '2.0.0-wip'

AVAILABLE_SOFTWARE = ('maya', 'katana', 'houdini', 'nuke', 'mari', 'ue4editor', 'blender')

STANDALONE = 'standalone'

CHECK = 'check'

FIX = 'fix'

TOOL = 'tool'

AVAILABLE_DISPLAY_MODE = ('Header', 'Category', 'Alphabetically')

DEFAULT_CATEGORY = 'Other'

PROGRESSBAR_FORMAT = '  %p% - {0}'

# If types change, unit tests from AtTest must be updated too.
BLUEPRINT_TEMPLATE = \
{
	'process': '',  # String
	'category': '',  # String
	'arguments': {'': ([], {})},  # Dict with str key and tuple with a tuple and a dict as value.
	'tags': 0,  # Integer - AtCore.Tag
	'links': (('', '', '')),  # Tuple of tuple that contains three str, the target ID, the source method and the target method.
	'statusOverrides': {'': {}},  # Dict that contains name of the threads to overrides and a dict with new status indexed by status type.
	'settings': {}  # Dict with str key and values.
}

SETTINGS_TEMPLATE = \
{
	'recheck': True,
	'orderFeedbacksByPriority': False,
	'feedbackDisplayWarning': True,
	'feedbackDisplayWarningLimit': 100,
	'allowRequestStop': True,
	'disableSelection': False,
	'globalContextManagers': (),
	'checkContextManagers': (),
	'fixContextManagers': (),
	'toolContextManagers': (),
}

NO_DOCUMENTATION_AVAILABLE = '\nNo documentation available for this process.\n'

WIKI_LINK = 'https://github.com/gpijat/Athena'
REPORT_BUG_LINK = 'https://github.com/gpijat/Athena/issues'

DUMMY_PROCESS_TEMPLATE = \
'''
from Athena import AtCore


__all__ = \\
	(
		'DummyProcess',
	)


@AtCore.automatic
class DummyProcess(AtCore.Process):
    """Class Documentation (Will be used to document the process if _doc_ is not implemented."""

    _name_ = 'DummyProcess'
    _doc_ = \\
    """This is a process template that must be implemented..

    This documentation will be available to show to user in an UI. You may implement this sunder attribute to
    display an user related documentation. Else class documentation will be displayed.
    """

    DUMMY_THREAD = AtCore.Thread(title='The items above are not compliant with this Process.')

    def __init__(self):
    	super(DummyProcess, self).__init__()
    	# Implement your __init__ here !!!

    def check(self):
    	# Implement your check here !!!
    	pass

    def fix(self):
    	# Implement your check here !!!
    	pass

    def tool(self):
    	# Implement your check here !!!
    	pass

'''

DUMMY_BLUEPRINT_TEMPLATE = \
'''
from Athena.AtCore import Tag, Link, ID, Status

header = \\
(
    ID.DummyProcess,
)

register = \\
{
    ID.DummyProcess:
        {
            'process': '',
            'category': '',
            'arguments': 
            	{
            		'__init__': ([], {}),
            		'check': ([], {}),
            		'fix': ([], {}),
            		'tool': ([], {}),
            	},
            'tags': Tag.NO_TAG,
            'links': (('', '', '')),
            'statusOverride':
            	{
            		'DUMMY_THREAD': {},
            	},
            'settings': {},
        },
}

settings = \\
{
    'recheck': True,
    'orderFeedbacksByPriority': False,
    'feedbackDisplayWarning': True,
    'feedbackDisplayWarningLimit': 100,
    'allowRequestStop': True,
}
'''