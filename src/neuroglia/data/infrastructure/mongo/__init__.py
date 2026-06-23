"""
MongoDB data infrastructure for Neuroglia.

Provides MongoDB repository implementations:
- MongoRepository: Sync PyMongo-based repository with queryable support
- MotorRepository: Async Motor-based repository for async applications (recommended)
- EnhancedMongoRepository: Advanced operations with enhanced features

For async applications (FastAPI, asyncio), use MotorRepository.
For sync applications, use MongoRepository or EnhancedMongoRepository.

Note:
    This package uses lazy imports (PEP 562) to separate sync and async dependencies.
    MotorRepository can be imported without pymongo installed.
    Sync repositories (MongoRepository, EnhancedMongoRepository) require pymongo.
"""

from typing import TYPE_CHECKING

# Eagerly import async/motor-based components (no pymongo dependency)
from .motor_query import MotorQuery, MotorQueryBuilder, MotorQueryProvider
from .motor_repository import MotorRepository
from .serialization_helper import MongoSerializationHelper
from .typed_mongo_query import TypedMongoQuery, with_typed_mongo_query

# Type stubs for lazy-loaded sync repositories (satisfies type checkers)
if TYPE_CHECKING:
    from .enhanced_mongo_repository import EnhancedMongoRepository
    from .mongo_repository import (
        MongoQueryProvider,
        MongoRepository,
        MongoRepositoryOptions,
    )

__all__ = [
    # Async repository (recommended for FastAPI/asyncio)
    "MotorRepository",
    # Async query support
    "MotorQuery",
    "MotorQueryBuilder",
    "MotorQueryProvider",
    # Sync repositories (lazy-loaded, require pymongo)
    "MongoRepository",
    "MongoQueryProvider",
    "MongoRepositoryOptions",
    "EnhancedMongoRepository",
    # Query support
    "TypedMongoQuery",
    "with_typed_mongo_query",
    # Utilities
    "MongoSerializationHelper",
]


def __getattr__(name: str):
    """
    Lazy import mechanism for sync repositories (PEP 562).

    This allows MotorRepository to be imported without pymongo installed.
    Sync repositories are only imported when explicitly requested.

    Args:
        name: The attribute name being accessed

    Returns:
        The requested module attribute

    Raises:
        AttributeError: If the attribute doesn't exist
        ModuleNotFoundError: If pymongo is not installed when accessing sync repos
    """
    # Lazy import sync repositories (require pymongo)
    if name == "EnhancedMongoRepository":
        from .enhanced_mongo_repository import EnhancedMongoRepository

        return EnhancedMongoRepository
    elif name == "MongoRepository":
        from .mongo_repository import MongoRepository

        return MongoRepository
    elif name == "MongoQueryProvider":
        from .mongo_repository import MongoQueryProvider

        return MongoQueryProvider
    elif name == "MongoRepositoryOptions":
        from .mongo_repository import MongoRepositoryOptions

        return MongoRepositoryOptions

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
