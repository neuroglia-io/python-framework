from dataclasses import dataclass
from decimal import Decimal
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mapping.mapper import Mapper, map_from
from neuroglia.mediation import CommandHandler
from samples.openbank.domain.models import BankAccount
from samples.openbank.domain.models.person import Person
from samples.openbank.integration.commands.accounts import CreateBankAccountCommandDto
from samples.openbank.integration.models.bank import BankAccountDto


@map_from(CreateBankAccountCommandDto)
@dataclass
class CreateBankAccountCommand:
    ''' Represents the command used to create a new bank account '''

    owner_id: str
    ''' Gets the id of the owner of the bank account to create '''

    overdraft_limit: Decimal = Decimal("0")
    ''' Gets the default overdraft limit for the bank account to create '''


class CreateBankAccountCommandHandler(CommandHandler[CreateBankAccountCommand, OperationResult[BankAccountDto]]):
    ''' Represents the service used to handle CreateBankAccountCommands '''

    def __init__(self, mapper: Mapper, persons: Repository[Person, str], bank_accounts: Repository[BankAccount, str]):
        self.mapper = mapper
        self.persons = persons
        self.bank_accounts = bank_accounts

    mapper: Mapper

    persons: Repository[Person, str]

    bank_accounts: Repository[BankAccount, str]

    async def handle_async(self, command: CreateBankAccountCommand) -> OperationResult[BankAccountDto]:
        person = await self.persons.get_async(command.owner_id)
        if person is None:
            return self.not_found(Person, command.owner_id)
        bank_account = await self.bank_accounts.add_async(BankAccount(person, command.overdraft_limit))
        return self.created(self.mapper.map(bank_account.state, BankAccountDto))
