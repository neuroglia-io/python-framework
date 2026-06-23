"""Test if parameterized generic types compare equal in Python."""

from typing import Generic, TypeVar

T = TypeVar("T")


class Repository(Generic[T]):
    pass


class User:
    pass


class Product:
    pass


# Test if parameterized types compare equal
type1 = Repository[User]
type2 = Repository[User]
type3 = Repository[Product]

print("Testing Parameterized Type Equality:")
print("=" * 60)
print(f"Repository[User] == Repository[User]: {type1 == type2}")
print(f"Repository[User] is Repository[User]: {type1 is type2}")
print(f"Repository[User] == Repository[Product]: {type1 == type3}")
print()
print(f"Type 1: {type1}")
print(f"Type 2: {type2}")
print(f"Type 3: {type3}")
print()
print(f"Hash Repository[User] (1): {hash(type1)}")
print(f"Hash Repository[User] (2): {hash(type2)}")
print(f"Hash Repository[Product]: {hash(type3)}")
print()
print("Conclusion:")
if type1 == type2:
    print("✅ Python's parameterized types DO compare equal!")
    print("✅ The existing v0.4.2 code should work fine with == comparison")
else:
    print("❌ Parameterized types don't compare equal - need special handling")
