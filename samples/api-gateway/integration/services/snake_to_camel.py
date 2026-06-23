import datetime

import humps
from pydantic import BaseModel


class CamelModel(BaseModel):
    """A pydantic.BaseModel with CamelCase aliases."""

    class Config:
        """Configuration for a CamelModel."""

        alias_generator = humps.camelize
        populate_by_name = True
        from_attributes = True


if __name__ == "__main__":

    class NestedModel(CamelModel):
        another_snake_case_attribute: str = "nested_value"

    class OriginalModel(CamelModel):
        snake_case_attribute: str = "value"
        nested_model: NestedModel = NestedModel()

    # OriginalModel will be converted from CamelCase automatically
    original_model = OriginalModel()
    print(original_model.model_dump_json())
    print(original_model)
    print(
        OriginalModel.model_validate(
            {
                "snakeCaseAttribute": "new_value",
                "nestedModel": {"anotherSnakeCaseAttribute": "new_nested_value"},
            }
        )
    )
    print(datetime.datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds"))
