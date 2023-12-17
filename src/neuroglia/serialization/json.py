import json
from typing import Optional, Type

class JsonSerializer:
    ''' Represents the service used to serialize/deserialize to/from JSON '''    

    def deserialize(input: str, type : Optional[Type] = None):
        ''' Deserializes the specified JSON into a new instance of the specified type '''
        return json.loads(input)