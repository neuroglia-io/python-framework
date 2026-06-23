#!/usr/bin/env python3
"""Debug script to test QueryHandler discovery in Mario Pizzeria"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("Testing Mario Pizzeria QueryHandler discovery...")

try:
    import inspect

    from neuroglia.core import ModuleLoader, TypeFinder
    from neuroglia.mediation.mediator import CommandHandler, QueryHandler

    # Load the queries module
    print("Loading application.queries module...")
    queries_module = ModuleLoader.load("application.queries")
    print(f"Module loaded successfully: {queries_module}")

    # List all classes in the module
    print("\nClasses found in module:")
    for name, cls in inspect.getmembers(queries_module, inspect.isclass):
        print(f"  - {name}: {cls}")
        print(f"    MRO: {cls.__mro__}")
        if hasattr(cls, "__parameters__"):
            print(f"    Has __parameters__: {cls.__parameters__}")
        else:
            print("    No __parameters__ attribute")
        if name.endswith("Handler"):
            print(f"    Is QueryHandler subclass: {issubclass(cls, QueryHandler)}")

    # Test the exact predicate used in mediation (FIXED VERSION)
    print("\nTesting QueryHandler predicate...")
    predicate = lambda cls: (inspect.isclass(cls) and (not hasattr(cls, "__parameters__") or len(cls.__parameters__) < 1) and issubclass(cls, QueryHandler) and cls != QueryHandler)

    query_handlers = TypeFinder.get_types(queries_module, predicate, include_sub_modules=True)
    print(f"QueryHandlers found: {query_handlers}")

    # Test command predicate for comparison
    print("\nLoading application.commands module...")
    commands_module = ModuleLoader.load("application.commands")
    command_predicate = lambda cls: (inspect.isclass(cls) and (not hasattr(cls, "__parameters__") or len(cls.__parameters__) < 1) and issubclass(cls, CommandHandler) and cls != CommandHandler)

    command_handlers = TypeFinder.get_types(commands_module, command_predicate, include_sub_modules=True)
    print(f"CommandHandlers found: {command_handlers}")

except Exception as e:
    import traceback

    print(f"Error: {e}")
    traceback.print_exc()

print("Debug complete.")
