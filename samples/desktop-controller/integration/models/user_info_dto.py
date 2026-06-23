import datetime

from pydantic import BaseModel


class UserInfoDto(BaseModel):
    """Represents the the User Info of the Desktop."""

    session_id: str

    username: str

    created_at: datetime.datetime

    last_modified: datetime.datetime


class SetUserInfoCommandDto(BaseModel):
    """Represents the command used to set the User Info of the Desktop."""

    candidate_name: str
