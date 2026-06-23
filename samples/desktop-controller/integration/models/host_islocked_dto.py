from pydantic import BaseModel


class HostIslockedDto(BaseModel):
    is_locked: bool
