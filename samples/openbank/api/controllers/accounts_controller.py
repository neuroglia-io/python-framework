from typing import List
from classy_fastapi.decorators import get, post
from neuroglia.data.queries.generic import GetByIdQuery
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase
from samples.openbank.application.commands.accounts import CreateBankAccountCommand
from samples.openbank.application.queries import AccountsByOwnerQuery
from samples.openbank.integration.commands.accounts import CreateBankAccountCommandDto
from samples.openbank.integration.models.bank import BankAccountDto


class AccountsController(ControllerBase):

    def __init__(
        self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator
    ):
        ControllerBase.__init__(self, service_provider, mapper, mediator)

    @post(
        "/create/",
        response_model=BankAccountDto,
        status_code=201,
        responses=ControllerBase.error_responses,
    )
    async def create_bank_account(
        self, command: CreateBankAccountCommandDto
    ) -> BankAccountDto:
        """Creates a new bank account"""
        return self.process(
            await self.mediator.execute_async(
                self.mapper.map(command, CreateBankAccountCommand)
            )
        )

    @get(
        "/byid/{id}",
        response_model=BankAccountDto,
        responses=ControllerBase.error_responses,
    )
    async def get_bank_account_by_id(self, id: str) -> BankAccountDto:
        """Gets the bank account with the specified id"""
        return self.process(
            await self.mediator.execute_async(GetByIdQuery[BankAccountDto, str](id))
        )

    @get(
        "/byowner/{owner_id}",
        response_model=List[BankAccountDto],
        responses=ControllerBase.error_responses,
    )
    async def get_bank_account_by_owner_id(self, owner_id: str) -> List[BankAccountDto]:
        """Gets the bank account for the given owner id"""
        return self.process(
            await self.mediator.execute_async(AccountsByOwnerQuery(owner_id=owner_id))
        )
