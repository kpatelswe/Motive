from uuid import UUID

from pydantic import BaseModel


class UserOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    avatar_url: str | None

    model_config = {"from_attributes": True}
