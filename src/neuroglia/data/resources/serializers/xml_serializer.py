"""XML serializer for resources.

This module provides XML serialization capabilities for resource objects,
extending the Neuroglia TextSerializer interface.
"""

import logging
from typing import Any, Optional, Type
from xml.etree import ElementTree as ET
from xml.dom import minidom

from neuroglia.serialization.abstractions import TextSerializer

log = logging.getLogger(__name__)


class XmlResourceSerializer(TextSerializer):
    """XML serializer for resource objects."""

    def __init__(self, root_element_name: str = "resource"):
        self.root_element_name = root_element_name

    def serialize(self, value: Any) -> bytearray:
        """Serialize the specified value to XML bytes."""
        xml_text = self.serialize_to_text(value)
        return bytearray(xml_text.encode("utf-8"))

    def deserialize(self, input_bytes: bytearray, expected_type: Optional[Type] = None) -> Any:
        """Deserialize XML bytes into a value."""
        xml_text = input_bytes.decode("utf-8")
        return self.deserialize_from_text(xml_text, expected_type)

    def serialize_to_text(self, value: Any) -> str:
        """Serialize the specified value to XML text."""
        try:
            # Create root element
            root = ET.Element(self.root_element_name)

            # Convert value to XML elements
            self._add_value_to_element(root, "data", value)

            # Convert to pretty-printed string
            xml_string = ET.tostring(root, encoding="unicode")

            # Parse with minidom for pretty printing
            dom = minidom.parseString(xml_string)
            pretty_xml = dom.toprettyxml(indent="  ", encoding=None)

            # Remove empty lines and clean up
            lines = [line for line in pretty_xml.splitlines() if line.strip()]
            return "\n".join(lines)

        except Exception as e:
            log.error(f"Failed to serialize value to XML: {e}")
            raise

    def deserialize_from_text(self, input_text: str, expected_type: Optional[Type] = None) -> Any:
        """Deserialize XML text into a value."""
        try:
            root = ET.fromstring(input_text)

            # Find the data element
            data_element = root.find("data")
            if data_element is not None:
                return self._element_to_value(data_element)

            # If no data element, convert the root
            return self._element_to_value(root)

        except ET.ParseError as e:
            log.error(f"Failed to parse XML: {e}")
            raise
        except Exception as e:
            log.error(f"Failed to deserialize XML text: {e}")
            raise

    def _add_value_to_element(self, parent: ET.Element, name: str, value: Any) -> None:
        """Add a value to an XML element."""

        if value is None:
            element = ET.SubElement(parent, name)
            element.set("type", "null")
            return

        # Handle dataclasses
        if hasattr(value, "__dataclass_fields__"):
            element = ET.SubElement(parent, name)
            element.set("type", "object")
            for field in value.__dataclass_fields__:
                field_value = getattr(value, field)
                self._add_value_to_element(element, field, field_value)
            return

        # Handle objects with __dict__
        if hasattr(value, "__dict__"):
            element = ET.SubElement(parent, name)
            element.set("type", "object")
            for key, obj_value in value.__dict__.items():
                if not key.startswith("_"):  # Skip private attributes
                    self._add_value_to_element(element, key, obj_value)
            return

        # Handle lists
        if isinstance(value, list):
            element = ET.SubElement(parent, name)
            element.set("type", "array")
            for i, item in enumerate(value):
                self._add_value_to_element(element, f"item_{i}", item)
            return

        # Handle dictionaries
        if isinstance(value, dict):
            element = ET.SubElement(parent, name)
            element.set("type", "object")
            for key, dict_value in value.items():
                # XML element names can't contain certain characters
                safe_key = self._make_xml_safe(str(key))
                self._add_value_to_element(element, safe_key, dict_value)
            return

        # Handle enums
        if hasattr(value, "value"):
            element = ET.SubElement(parent, name)
            element.set("type", "enum")
            element.text = str(value.value)
            return

        # Handle datetime objects
        if hasattr(value, "isoformat"):
            element = ET.SubElement(parent, name)
            element.set("type", "datetime")
            element.text = value.isoformat()
            return

        # Handle primitive types
        if isinstance(value, bool):
            element = ET.SubElement(parent, name)
            element.set("type", "boolean")
            element.text = str(value).lower()
        elif isinstance(value, int):
            element = ET.SubElement(parent, name)
            element.set("type", "integer")
            element.text = str(value)
        elif isinstance(value, float):
            element = ET.SubElement(parent, name)
            element.set("type", "float")
            element.text = str(value)
        elif isinstance(value, str):
            element = ET.SubElement(parent, name)
            element.set("type", "string")
            element.text = value
        else:
            # For other types, convert to string
            element = ET.SubElement(parent, name)
            element.set("type", "string")
            element.text = str(value)

    def _element_to_value(self, element: ET.Element) -> Any:
        """Convert an XML element to a Python value."""

        element_type = element.get("type", "string")

        if element_type == "null":
            return None

        if element_type == "object":
            result = {}
            for child in element:
                result[child.tag] = self._element_to_value(child)
            return result

        if element_type == "array":
            result = []
            for child in element:
                result.append(self._element_to_value(child))
            return result

        if element_type == "boolean":
            return element.text.lower() == "true" if element.text else False

        if element_type == "integer":
            return int(element.text) if element.text else 0

        if element_type == "float":
            return float(element.text) if element.text else 0.0

        # Default to string
        return element.text if element.text else ""

    def _make_xml_safe(self, name: str) -> str:
        """Make a string safe for use as an XML element name."""
        # Replace invalid characters with underscores
        safe_name = ""
        for char in name:
            if char.isalnum() or char in ["-", "_", "."]:
                safe_name += char
            else:
                safe_name += "_"

        # Ensure it starts with a letter or underscore
        if safe_name and not (safe_name[0].isalpha() or safe_name[0] == "_"):
            safe_name = "_" + safe_name

        return safe_name or "unnamed"
