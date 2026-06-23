"""YAML serializer for resources.

This module provides YAML serialization capabilities for resource objects,
extending the Neuroglia TextSerializer interface.
"""

import logging
from typing import Any, Optional, Type

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from neuroglia.serialization.abstractions import TextSerializer

log = logging.getLogger(__name__)


class YamlResourceSerializer(TextSerializer):
    """YAML serializer for resource objects."""

    def __init__(self):
        if not YAML_AVAILABLE:
            raise ImportError(
                "PyYAML is required for YAML serialization. Install with: pip install pyyaml"
            )

        # Configure YAML with safe loading and clean output
        self.yaml_dumper = yaml.SafeDumper
        self.yaml_loader = yaml.SafeLoader

        # Configure YAML dumper for clean output
        self.yaml_dumper.add_representer(type(None), self._represent_none)

    @staticmethod
    def _represent_none(dumper, value):
        """Represent None values as null in YAML."""
        return dumper.represent_scalar("tag:yaml.org,2002:null", "null")

    def serialize(self, value: Any) -> bytearray:
        """Serialize the specified value to YAML bytes."""
        yaml_text = self.serialize_to_text(value)
        return bytearray(yaml_text.encode("utf-8"))

    def deserialize(self, input_bytes: bytearray, expected_type: Optional[Type] = None) -> Any:
        """Deserialize YAML bytes into a value."""
        yaml_text = input_bytes.decode("utf-8")
        return self.deserialize_from_text(yaml_text, expected_type)

    def serialize_to_text(self, value: Any) -> str:
        """Serialize the specified value to YAML text."""
        try:
            # Convert dataclasses and objects to dictionaries
            serializable_value = self._make_serializable(value)

            # Generate YAML with clean formatting
            yaml_text = yaml.dump(
                serializable_value,
                Dumper=self.yaml_dumper,
                default_flow_style=False,
                allow_unicode=True,
                indent=2,
                sort_keys=False,
            )

            return yaml_text

        except Exception as e:
            log.error(f"Failed to serialize value to YAML: {e}")
            raise

    def deserialize_from_text(self, input_text: str, expected_type: Optional[Type] = None) -> Any:
        """Deserialize YAML text into a value."""
        try:
            return yaml.load(input_text, Loader=self.yaml_loader)
        except yaml.YAMLError as e:
            log.error(f"Failed to deserialize YAML: {e}")
            raise
        except Exception as e:
            log.error(f"Failed to deserialize YAML text: {e}")
            raise

    def _make_serializable(self, obj: Any) -> Any:
        """Convert objects to serializable dictionaries."""
        if obj is None:
            return None

        # Handle dataclasses
        if hasattr(obj, "__dataclass_fields__"):
            return {
                field: self._make_serializable(getattr(obj, field))
                for field in obj.__dataclass_fields__
            }

        # Handle objects with __dict__
        if hasattr(obj, "__dict__"):
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith("_"):  # Skip private attributes
                    result[key] = self._make_serializable(value)
            return result

        # Handle lists
        if isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]

        # Handle dictionaries
        if isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}

        # Handle enums
        if hasattr(obj, "value"):
            return obj.value

        # Handle datetime objects
        if hasattr(obj, "isoformat"):
            return obj.isoformat()

        # Return primitive types as-is
        if isinstance(obj, (str, int, float, bool)):
            return obj

        # For other types, try to convert to string
        return str(obj)

    @staticmethod
    def is_available() -> bool:
        """Check if YAML serialization is available."""
        return YAML_AVAILABLE
