from typing import Optional
from pydantic import BaseModel, Field

class Feed(BaseModel):
    id: str = Field(validation_alias="g:id")
    title: str
    description: str
    link: Optional[str]