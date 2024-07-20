from typing import Generic, Optional, TypeVar
from neuroglia.core.problem_details import ProblemDetails

TData = TypeVar('TData')


class OperationResult(Generic[TData], ProblemDetails):
    ''' Represents the result of an operation '''

    data: Optional[TData]
    ''' Gets the data, if any, returned by the operation in case of success '''
