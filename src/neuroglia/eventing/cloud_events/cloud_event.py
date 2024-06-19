from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


class CloudEventSpecVersion:
    ''' Exposes all supported versions of the Cloud Event Specification '''

    v1_0: str = "1.0"
    ''' Gets the version '1.0' of the Cloud Event Specification '''


@dataclass
class CloudEvent:
    '''
    Represents a Cloud Event.

    Attributes:
        id (str): A string that uniquely identifies the cloud event in the scope of its source.
        specversion (str): The version of the CloudEvents specification which the event uses. Defaults to '1.0'.
        time (Optional[datetime]): The date and time at which the event has been produced.
        source (str): The cloud event's source.
        type (str): The cloud event's type.
        subject (Optional[str]): A value that describes the subject of the event in the context of the event producer.
        datacontenttype (Optional[str]): The cloud event's data content type. Defaults to 'application/json'.
        dataschema (Optional[str]): An URI that references the versioned schema of the event's data.
        data (Optional[Any]): The event's data, if any. Only used if the event has been formatted using the structured mode.
        data_base64 (Optional[str]): The event's binary data, encoded in base 64. Used if the event has been formatted using the binary mode.
        extensionAttributes (Optional[Dict[str, Any]]): A mapping containing the event's extension attributes.
    '''

    id: str
    ''' Gets/sets string that uniquely identifies the cloud event in the scope of its source. '''

    source: str
    ''' Gets/sets the cloud event's source. Must be an absolute URI. '''

    type: str
    ''' Gets/sets the cloud event's source. Should be a reverse DNS domain name, which must only contain lowercase alphanumeric, '-' and '.' characters. '''

    specversion: str = '1.0'  # Default value for specversion
    ''' Gets/sets the version of the CloudEvents specification which the event uses. Defaults to '1.0'. '''

    sequencetype: Optional[str] = None
    ''' Gets/sets the type of the sequence. '''

    sequence: Optional[int] = None
    ''' Gets/sets the sequence of the event. '''

    time: Optional[datetime] = None
    ''' Gets/sets the date and time at which the event has been produced. '''

    subject: Optional[str] = None
    ''' Gets/sets value that describes the subject of the event in the context of the event producer. '''

    datacontenttype: Optional[str] = 'application/json'  # Default value for datacontenttype
    ''' Gets/sets the cloud event's data content type. Defaults to 'application/json'. '''

    dataschema: Optional[str] = None
    ''' Gets/sets an URI, if any, that references the versioned schema of the event's data. '''

    data: Optional[Any] = None
    ''' Gets/sets the event's data, if any. Only used if the event has been formatted using the structured mode. '''

    data_base64: Optional[str] = None
    ''' Gets/sets the event's binary data, encoded in base 64. Used if the event has been formatted using the binary mode. '''

    def get_attribute(self, name: str) -> Optional[Any]:
        ''' Gets the value of the attribute with the specified name, if any '''
        if not name:
            raise ValueError("Attribute name cannot be empty or None.")
        self.__dict__[name] if name in self.__dict__.keys() else None
