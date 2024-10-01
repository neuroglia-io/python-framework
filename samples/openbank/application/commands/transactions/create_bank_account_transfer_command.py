from dataclasses import dataclass
from decimal import Decimal
import logging
from typing import Optional
from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mapping import Mapper
from neuroglia.mapping.mapper import map_from
from neuroglia.mediation.mediator import CommandHandler
from samples.openbank.domain.models import BankAccount
from samples.openbank.domain.models.bank_account import BankTransactionTypeV1, BankTransactionV1
from samples.openbank.integration.commands.transactions import CreateBankAccountTransferCommandDto
from samples.openbank.integration.models.bank import BankTransactionDto

log = logging.getLogger(__name__)


@map_from(CreateBankAccountTransferCommandDto)
@dataclass
class CreateBankAccountTransferCommand:
    ''' Represents the command used to create a new bank account transfer '''

    from_bank_account_id: str
    ''' Gets the id of the bank account to transfer the specified amount from '''

    to_bank_account_id: str
    ''' Gets the id of the bank account to transfer the specified amount to '''

    amount: Decimal
    ''' Gets the amount to transfer '''

    communication: Optional[str] = None
    ''' Gets the communication, if any, associated with the transfer to create '''


class CreateBankAccountTransferCommandHandler(CommandHandler[CreateBankAccountTransferCommand, OperationResult[BankTransactionDto]]):
    ''' Represents the service used to handle CreateBankAccountTransferCommands '''

    def __init__(self, mapper: Mapper, bank_accounts: Repository[BankAccount, str]):
        self.mapper = mapper
        self.bank_accounts = bank_accounts

    mapper: Mapper

    bank_accounts: Repository[BankAccount, str]

    async def handle_async(self, command: CreateBankAccountTransferCommand) -> OperationResult[BankTransactionDto]:
        if command.from_bank_account_id == command.to_bank_account_id:
            return self.bad_request("Cannot perform a transfer from a bank account to itself")

        from_bank_account = await self.bank_accounts.get_async(command.from_bank_account_id)
        if from_bank_account is None:
            return self.not_found(BankAccount, command.from_bank_account_id)

        to_bank_account = await self.bank_accounts.get_async(command.to_bank_account_id)
        if to_bank_account is None:
            return self.not_found(BankAccount, command.to_bank_account_id)

        transaction = BankTransactionV1(BankTransactionTypeV1.TRANSFER, Decimal(command.amount), from_bank_account.id(), to_bank_account.id(), command.communication)
        if not from_bank_account.try_add_transaction(transaction):
            log.info(f"A transaction from {command.from_bank_account_id} to {command.to_bank_account_id} for {command.amount} was declined due to insufficient funds")
            print(f"A transaction from {command.from_bank_account_id} to {command.to_bank_account_id} for {command.amount} was declined due to insufficient funds")  # todo: remove
            return self.bad_request("Insufficient funds")
        if not to_bank_account.try_add_transaction(transaction):
            raise Exception("The beneficiary of a transaction of type 'TRANSFER' should never invalidate it for insufficient funds, thus this exception should never be raised")

        await self.bank_accounts.update_async(from_bank_account)
        await self.bank_accounts.update_async(to_bank_account)

        return self.ok(self.mapper.map(transaction, BankTransactionDto))
