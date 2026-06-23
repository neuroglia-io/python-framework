from pydantic import BaseModel


class TestHostScriptCommandDto(BaseModel):
    user_input: str
