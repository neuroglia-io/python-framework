from neuroglia.core.operation_result import OperationResult
from neuroglia.data.infrastructure.abstractions import QueryableRepository
from neuroglia.mediation.mediator import Query, QueryHandler

from samples.openbank.integration.models.bank import BankAccountDto


class AccountsByOwnerQuery(Query[OperationResult[BankAccountDto]]):
    ''' Represents the query used to get an account by its owner id'''
    owner_id: str

    def __init__(self, owner_id: str):
        self.owner_id = owner_id


class AccountsByOwnerQueryHandler(QueryHandler[AccountsByOwnerQuery, OperationResult[BankAccountDto]]):
    ''' Represents the service used to handle AccountsByOwnerQuery instances '''

    def __init__(self, repository: QueryableRepository[BankAccountDto, str]):
        self.repository = repository

    repository: QueryableRepository[BankAccountDto, str]

    async def handle_async(self, query: AccountsByOwnerQuery) -> OperationResult[BankAccountDto]:
        res = (await self.repository.query_async()).where(lambda u: u.owner_id == query.owner_id)
        print(res)
        return self.ok(res.to_list())
