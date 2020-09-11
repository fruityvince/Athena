from Athena import AtConstants
from Athena import AtUtils


class AthenaException(Exception):
    
    def __init__(self, message):
    	super(AthenaException, self).__init__(message)


class StatusException(Exception):
    pass