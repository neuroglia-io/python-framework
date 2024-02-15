from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mapping import Mapper
from neuroglia.mapping.mapper import map_from
from neuroglia.mediation.mediator import CommandHandler
from samples.openbank.domain.models import BankAccount
from samples.openbank.domain.models.bank_account import BankTransactionTypeV1, BankTransactionV1
from samples.openbank.integration.commands.transactions import CreateBankAccountDepositCommandDto
from samples.openbank.integration.models.bank import BankTransactionDto


@map_from(CreateBankAccountDepositCommandDto)
@dataclass
class CreateBankAccountDepositCommand:
    ''' Represents the command used to create a new bank account deposit'''

    depositor_id: str
    ''' Gets the id of the person who deposit the cash'''

    to_bank_account_id: str
    ''' Gets the id of the bank account where the deposit is made'''

    amount: Decimal
    ''' Gets the amount to deposit '''

    communication: Optional[str] = None
    ''' Gets the communication, if any, associated with the deposit to create '''


class CreateBankAccountDepositCommandHandler(CommandHandler[CreateBankAccountDepositCommand, OperationResult[BankTransactionDto]]):
    ''' Represents the service used to handle CreateBankAccountDepositCommand '''

    def __init__(self, mapper: Mapper, bank_accounts: Repository[BankAccount, str]):
        self.mapper = mapper
        self.bank_accounts = bank_accounts

    mapper: Mapper

    bank_accounts: Repository[BankAccount, str]

    async def handle_async(self, command: CreateBankAccountDepositCommand) -> OperationResult[BankTransactionDto]:
        if command.amount <= 0:
            return self.bad_request("Cannot perform a deposit of a negative or null value.")

        to_bank_account = await self.bank_accounts.get_async(command.to_bank_account_id)
        if to_bank_account is None:
            return self.not_found(BankAccount, command.to_bank_account_id)

        if to_bank_account.state.owner_id != command.depositor_id:
            return self.bad_request("The depositor must own the account.")

        transaction = BankTransactionV1(BankTransactionTypeV1.DEPOSIT, Decimal(command.amount), None, to_bank_account.id(), command.communication)

        if command.communication is None or len(command.communication) == 0:
            command.communication = f"{transaction.id}: user {to_bank_account.state.owner_id} deposited {command.amount}EUR in cash."

        if not to_bank_account.try_add_transaction(transaction):
            raise Exception("The beneficiary of a transaction of type 'DEPOSIT' should never invalidate it for insufficient funds, thus this exception should never be raised")

        await self.bank_accounts.update_async(to_bank_account)

        return self.ok(self.mapper.map(transaction, BankTransactionDto))
