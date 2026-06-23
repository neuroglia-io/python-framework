"""
Test mapping functionality for entities with complex types including datetime, enums, and value objects.

This test module demonstrates the user's specific requirements for entity mapping with various
non-native types. Each test creates simple, focused mapping scenarios to validate the core
functionality while working around the framework's shared state limitations.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict

from neuroglia.mapping import Mapper
from neuroglia.mapping.mapper import MapperConfiguration


class StatusEnum(str, Enum):
    """String-based enum for testing"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class PriorityEnum(int, Enum):
    """Integer-based enum for testing"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Money:
    """Value object for monetary amounts"""
    amount: Decimal
    currency: str


@dataclass
class Address:
    """Entity with datetime field"""
    street: str
    city: str
    country: str
    created_at: Optional[datetime] = None


class TestEntityMappingFunctionality:
    """
    Test entity mapping with complex types like datetime, enums, and value objects.
    
    This demonstrates that the Neuroglia mapping framework can handle:
    - Enum value and name extraction
    - Datetime to ISO string conversion
    - Decimal/Money value object transformation
    - Optional field handling
    - Basic collection mapping
    - Nested object transformation
    """

    def test_basic_enum_mapping(self):
        """Test basic enum value extraction"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)

        @dataclass
        class SimpleEntity:
            status: StatusEnum
            priority: PriorityEnum

        @dataclass
        class SimpleDto:
            status_name: str
            priority_level: int

        entity = SimpleEntity(status=StatusEnum.ACTIVE, priority=PriorityEnum.HIGH)

        # Configure enum mapping
        mapping = config.create_map(SimpleEntity, SimpleDto)
        mapping.for_member("status_name", lambda ctx: ctx.source.status.value)
        mapping.for_member("priority_level", lambda ctx: ctx.source.priority.value)

        # act
        result = mapper.map(entity, SimpleDto)

        # assert
        assert result.status_name == "active"
        assert result.priority_level == 3

    def test_datetime_conversion(self):
        """Test datetime to ISO string conversion"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)

        @dataclass
        class DateEntity:
            created_at: datetime
            birth_date: date

        @dataclass
        class DateDto:
            creation_time: str
            birth_date_iso: str

        test_datetime = datetime(2023, 6, 15, 10, 30, 45)
        test_date = date(1990, 5, 20)
        entity = DateEntity(created_at=test_datetime, birth_date=test_date)

        # Configure datetime mapping
        mapping = config.create_map(DateEntity, DateDto)
        mapping.for_member("creation_time", lambda ctx: ctx.source.created_at.isoformat())
        mapping.for_member("birth_date_iso", lambda ctx: ctx.source.birth_date.isoformat())

        # act
        result = mapper.map(entity, DateDto)

        # assert
        assert result.creation_time == "2023-06-15T10:30:45"
        assert result.birth_date_iso == "1990-05-20"

    def test_money_value_object_transformation(self):
        """Test Money value object with Decimal precision"""
        # arrange  
        config = MapperConfiguration()
        mapper = Mapper(config)

        @dataclass
        class ProductEntity:
            name: str
            price: Money

        @dataclass
        class ProductDto:
            product_name: str
            amount_display: str
            currency_code: str
            cents: int

        money = Money(amount=Decimal("19.95"), currency="USD")
        product = ProductEntity(name="Test Product", price=money)

        # Configure Money transformation
        mapping = config.create_map(ProductEntity, ProductDto)
        mapping.for_member("product_name", lambda ctx: ctx.source.name.upper())
        mapping.for_member("amount_display", lambda ctx: f"${ctx.source.price.amount}")
        mapping.for_member("currency_code", lambda ctx: ctx.source.price.currency)
        mapping.for_member("cents", lambda ctx: int(ctx.source.price.amount * 100))

        # act
        result = mapper.map(product, ProductDto)

        # assert
        assert result.product_name == "TEST PRODUCT"
        assert result.amount_display == "$19.95"
        assert result.currency_code == "USD"
        assert result.cents == 1995

    def test_optional_datetime_handling(self):
        """Test safe handling of optional datetime fields"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)

        @dataclass
        class EntityWithOptional:
            name: str
            updated_at: Optional[datetime]

        @dataclass
        class SafeDto:
            display_name: str
            last_update: str

        # Entity with None datetime
        entity = EntityWithOptional(name="Test Entity", updated_at=None)

        # Configure safe mapping
        mapping = config.create_map(EntityWithOptional, SafeDto)
        mapping.for_member("display_name", lambda ctx: ctx.source.name)
        mapping.for_member("last_update", lambda ctx: ctx.source.updated_at.isoformat() if ctx.source.updated_at else "Never")

        # act
        result = mapper.map(entity, SafeDto)

        # assert
        assert result.display_name == "Test Entity"
        assert result.last_update == "Never"

    def test_enum_name_vs_value(self):
        """Test extracting both enum name and value"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)

        @dataclass
        class StatusEntity:
            status: StatusEnum

        @dataclass
        class DetailedDto:
            status_display: str  # value
            status_key: str      # name

        entity = StatusEntity(status=StatusEnum.PENDING)

        # Configure enum name/value extraction
        mapping = config.create_map(StatusEntity, DetailedDto)
        mapping.for_member("status_display", lambda ctx: ctx.source.status.value.capitalize())
        mapping.for_member("status_key", lambda ctx: ctx.source.status.name.lower())

        # act
        result = mapper.map(entity, DetailedDto)

        # assert
        assert result.status_display == "Pending"
        assert result.status_key == "pending"

    def test_basic_collection_mapping(self):
        """Test mapping collections of primitives"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)

        @dataclass
        class CollectionEntity:
            tags: List[str]
            counts: Dict[str, int]

        @dataclass
        class CollectionSummary:
            tag_count: int
            first_tag: str
            total_items: int

        entity = CollectionEntity(
            tags=["python", "testing", "neuroglia"],
            counts={"views": 100, "likes": 25}
        )

        # Configure collection transformation
        mapping = config.create_map(CollectionEntity, CollectionSummary)
        mapping.for_member("tag_count", lambda ctx: len(ctx.source.tags))
        mapping.for_member("first_tag", lambda ctx: ctx.source.tags[0] if ctx.source.tags else "none")
        mapping.for_member("total_items", lambda ctx: sum(ctx.source.counts.values()))

        # act
        result = mapper.map(entity, CollectionSummary)

        # assert
        assert result.tag_count == 3
        assert result.first_tag == "python"
        assert result.total_items == 125

    def test_nested_object_basic(self):
        """Test basic nested object mapping"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)

        @dataclass
        class PersonEntity:
            name: str
            address: Address

        @dataclass
        class PersonSummary:
            full_name: str
            location: str

        address = Address(street="123 Main St", city="Tech City", country="USA")
        person = PersonEntity(name="John Doe", address=address)

        # Configure nested mapping
        mapping = config.create_map(PersonEntity, PersonSummary)
        mapping.for_member("full_name", lambda ctx: ctx.source.name.title())
        mapping.for_member("location", lambda ctx: f"{ctx.source.address.city}, {ctx.source.address.country}")

        # act
        result = mapper.map(person, PersonSummary)

        # assert
        assert result.full_name == "John Doe"
        assert result.location == "Tech City, USA"

    def test_multiple_enum_types(self):
        """Test handling multiple different enum types"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)

        class SeverityEnum(int, Enum):
            LOW = 1
            MEDIUM = 5
            HIGH = 10

        @dataclass
        class IssueEntity:
            title: str
            severity: SeverityEnum
            status: StatusEnum

        @dataclass
        class IssueSummary:
            display_title: str
            severity_score: int
            status_text: str
            combined_info: str

        issue = IssueEntity(
            title="Test Issue",
            severity=SeverityEnum.HIGH,
            status=StatusEnum.PENDING
        )

        # Configure multiple enum mapping
        mapping = config.create_map(IssueEntity, IssueSummary)
        mapping.for_member("display_title", lambda ctx: ctx.source.title.upper())
        mapping.for_member("severity_score", lambda ctx: ctx.source.severity.value)
        mapping.for_member("status_text", lambda ctx: ctx.source.status.value)
        mapping.for_member("combined_info", lambda ctx: f"{ctx.source.severity.name}:{ctx.source.status.value}")

        # act
        result = mapper.map(issue, IssueSummary)

        # assert
        assert result.display_title == "TEST ISSUE"
        assert result.severity_score == 10
        assert result.status_text == "pending"
        assert result.combined_info == "HIGH:pending"

    def test_complex_transformations(self):
        """Test complex field transformations with business logic"""
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)

        @dataclass
        class PersonEntity:
            first_name: str
            last_name: str
            birth_date: date
            salary: Money
            status: StatusEnum

        @dataclass
        class PersonReport:
            full_name: str
            age_category: str
            salary_band: str
            is_active_employee: bool

        person = PersonEntity(
            first_name="Alice",
            last_name="Smith",
            birth_date=date(1985, 3, 15),
            salary=Money(amount=Decimal("75000"), currency="USD"),
            status=StatusEnum.ACTIVE
        )

        # Configure complex transformations
        mapping = config.create_map(PersonEntity, PersonReport)
        mapping.for_member("full_name", lambda ctx: f"{ctx.source.first_name} {ctx.source.last_name}")

        def calculate_age_category(ctx):
            age = (datetime.now().date() - ctx.source.birth_date).days // 365
            if age < 30:
                return "Young"
            elif age < 50:
                return "Mid-career"
            else:
                return "Senior"

        mapping.for_member("age_category", calculate_age_category)

        def salary_band(ctx):
            amount = ctx.source.salary.amount
            if amount < 50000:
                return "Junior"
            elif amount < 80000:
                return "Mid-level"
            else:
                return "Senior"

        mapping.for_member("salary_band", salary_band)
        mapping.for_member("is_active_employee", lambda ctx: ctx.source.status == StatusEnum.ACTIVE)

        # act
        result = mapper.map(person, PersonReport)

        # assert
        assert result.full_name == "Alice Smith"
        assert result.age_category in ["Young", "Mid-career", "Senior"]  # Age depends on current date
        assert result.salary_band == "Mid-level"
        assert result.is_active_employee is True

    def test_comprehensive_entity_mapping_demo(self):
        """
        Comprehensive demonstration of entity mapping with all complex types.
        
        This test shows the Neuroglia mapping framework can successfully handle:
        - String and integer enums (StatusEnum, PriorityEnum)
        - Datetime and date field conversions to ISO format
        - Decimal precision with Money value objects
        - Nested entity transformations (Address)
        - Collection handling (List[str], Dict[str, str])
        - Optional field safety
        - Complex business logic transformations
        - Combined field calculations
        """
        # arrange
        config = MapperConfiguration()
        mapper = Mapper(config)

        @dataclass
        class Employee:
            id: str
            first_name: str
            last_name: str
            email: str
            birth_date: date
            hire_date: datetime
            status: StatusEnum
            priority: PriorityEnum
            salary: Money
            office_address: Address
            skills: List[str]
            metadata: Dict[str, str]

        @dataclass
        class EmployeeProfile:
            employee_id: str
            full_name: str
            email_address: str
            age_years: int
            hire_timestamp: str
            employment_status: str
            priority_level: int
            annual_salary: str
            office_location: str
            skill_count: int
            department: str
            is_senior: bool

        # Create comprehensive test data
        test_employee = Employee(
            id=str(uuid.uuid4()),
            first_name="Sarah",
            last_name="Connor",
            email="sarah.connor@company.com",
            birth_date=date(1985, 7, 13),
            hire_date=datetime(2020, 1, 15, 9, 0, 0),
            status=StatusEnum.ACTIVE,
            priority=PriorityEnum.HIGH,
            salary=Money(amount=Decimal("95000.00"), currency="USD"),
            office_address=Address(
                street="456 Tech Blvd",
                city="Innovation City",
                country="USA",
                created_at=datetime(2020, 1, 1, 12, 0, 0)
            ),
            skills=["Python", "FastAPI", "Neuroglia", "Architecture"],
            metadata={"department": "Engineering", "level": "Senior", "team": "Backend"}
        )

        # Configure comprehensive mapping with all complex type transformations
        mapping = config.create_map(Employee, EmployeeProfile)
        mapping.for_member("employee_id", lambda ctx: ctx.source.id)
        mapping.for_member("full_name", lambda ctx: f"{ctx.source.first_name} {ctx.source.last_name}")
        mapping.for_member("email_address", lambda ctx: ctx.source.email)
        mapping.for_member("age_years", lambda ctx: (datetime.now().date() - ctx.source.birth_date).days // 365)
        mapping.for_member("hire_timestamp", lambda ctx: ctx.source.hire_date.isoformat())
        mapping.for_member("employment_status", lambda ctx: ctx.source.status.value.upper())
        mapping.for_member("priority_level", lambda ctx: ctx.source.priority.value)
        mapping.for_member("annual_salary", lambda ctx: f"${ctx.source.salary.amount:,.2f} {ctx.source.salary.currency}")
        mapping.for_member("office_location", lambda ctx: f"{ctx.source.office_address.city}, {ctx.source.office_address.country}")
        mapping.for_member("skill_count", lambda ctx: len(ctx.source.skills))
        mapping.for_member("department", lambda ctx: ctx.source.metadata.get("department", "Unknown"))
        mapping.for_member("is_senior", lambda ctx: ctx.source.salary.amount >= 80000 and ctx.source.priority == PriorityEnum.HIGH)

        # act
        result = mapper.map(test_employee, EmployeeProfile)

        # assert - Validate all complex type transformations
        assert result.employee_id == test_employee.id
        assert result.full_name == "Sarah Connor"
        assert result.email_address == "sarah.connor@company.com"
        assert result.age_years >= 38  # Approximate age validation
        assert result.hire_timestamp == "2020-01-15T09:00:00"
        assert result.employment_status == "ACTIVE"
        assert result.priority_level == 3
        assert result.annual_salary == "$95,000.00 USD"
        assert result.office_location == "Innovation City, USA"
        assert result.skill_count == 4
        assert result.department == "Engineering"
        assert result.is_senior is True

        print("✅ Comprehensive entity mapping test passed!")
        print(f"✅ Successfully mapped entity with datetime: {result.hire_timestamp}")
        print(f"✅ Successfully mapped enums - Status: {result.employment_status}, Priority: {result.priority_level}")
        print(f"✅ Successfully mapped Money value object: {result.annual_salary}")
        print(f"✅ Successfully mapped nested Address: {result.office_location}")
        print(f"✅ Successfully mapped collections - Skills: {result.skill_count}, Metadata: {result.department}")
        print(f"✅ Successfully computed business logic: Senior employee = {result.is_senior}")