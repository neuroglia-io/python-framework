import dataclasses
from typing import Optional


@dataclasses.dataclass
class ProblemDetails:
    '''Represents the structure of a Problem Details response (RFC 7807).'''

    title: str
    '''A short, human-readable summary of the problem.'''

    status: int
    '''The HTTP status code for this occurrence of the problem.'''

    detail: Optional[str] = None
    '''A human-readable explanation specific to this occurrence of the problem.'''

    type: Optional[str] = None
    '''A URI reference that identifies the problem type.'''

    instance: Optional[str] = None
    '''A URI reference that identifies the specific occurrence of the problem.'''
    
    def is_success_status_code(self) -> bool: self.status >= 200 and self.status < 300
    ''' Determines whether the operation is successfull or not '''