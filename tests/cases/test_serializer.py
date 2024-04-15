import uuid
from neuroglia.serialization.json import JsonSerializer
from tests.data import TestData, UserDto


class TestJsonSerializer:

    _serializer: JsonSerializer = JsonSerializer()

    def test_serialize_deserialize_should_work(self):
        # arrange
        to_serialize: TestData = TestData()
        to_serialize.id = str(uuid.uuid4())
        to_serialize.name = "fake_value"
        to_serialize.data = UserDto(str(uuid.uuid4()), "John Doe", "john.doe@email.com")
        to_serialize.properties = dict(foo="bar", bar="baz", baz=69, foobar=True, bazbar=1.0)

        # act
        json: str = self._serializer.serialize(to_serialize)
        deserialized = self._serializer.deserialize_from_text(json, TestData)

        # assert
        assert vars(to_serialize) == vars(deserialized)
