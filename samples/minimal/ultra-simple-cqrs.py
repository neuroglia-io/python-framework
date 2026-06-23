"""
Ultra-Simple CQRS Example
========================

This example shows how to use the convenience methods for the absolute
simplest CQRS setup possible.
"""

import asyncio
import uuid
from dataclasses import dataclass

from neuroglia.core.operation_result import OperationResult
from neuroglia.dependency_injection.service_provider import ServiceCollection
from neuroglia.mediation import (
    Command,
    CommandHandler,
    InMemoryRepository,
    Mediator,
    Query,
    QueryHandler,
)


# Models
@dataclass
class Note:
    id: str
    content: str


@dataclass
class NoteDto:
    id: str
    content: str


# Commands & Queries
@dataclass
class AddNoteCommand(Command[OperationResult[NoteDto]]):
    content: str


@dataclass
class GetNoteQuery(Query[OperationResult[NoteDto]]):
    note_id: str


# Handlers
class AddNoteHandler(CommandHandler[AddNoteCommand, OperationResult[NoteDto]]):
    def __init__(self, repository: InMemoryRepository[Note]):
        super().__init__()
        self.repository = repository

    async def handle_async(self, request: AddNoteCommand) -> OperationResult[NoteDto]:
        note = Note(str(uuid.uuid4()), request.content)
        await self.repository.save_async(note)

        dto = NoteDto(note.id, note.content)
        return self.created(dto)


class GetNoteHandler(QueryHandler[GetNoteQuery, OperationResult[NoteDto]]):
    def __init__(self, repository: InMemoryRepository[Note]):
        super().__init__()
        self.repository = repository

    async def handle_async(self, request: GetNoteQuery) -> OperationResult[NoteDto]:
        note = await self.repository.get_by_id_async(request.note_id)

        if not note:
            return self.not_found(Note, request.note_id)

        dto = NoteDto(note.id, note.content)
        return self.ok(dto)


async def main():
    # Create app with dependencies - manually register handlers in registry
    services = ServiceCollection()
    services.add_singleton(InMemoryRepository[Note])
    services.add_singleton(Mediator)
    services.add_scoped(AddNoteHandler)
    services.add_scoped(GetNoteHandler)
    provider = services.build()

    # Register handlers in mediator's handler registry
    if not hasattr(Mediator, "_handler_registry"):
        Mediator._handler_registry = {}
    Mediator._handler_registry[AddNoteCommand] = AddNoteHandler
    Mediator._handler_registry[GetNoteQuery] = GetNoteHandler

    mediator: Mediator = provider.get_service(Mediator)  # type: ignore

    # Add a note
    result = await mediator.execute_async(AddNoteCommand("Hello, World!"))
    print(f"Added note: {result.data.content}")

    # Get the note
    get_result = await mediator.execute_async(GetNoteQuery(result.data.id))
    print(f"Retrieved note: {get_result.data.content}")


if __name__ == "__main__":
    asyncio.run(main())
