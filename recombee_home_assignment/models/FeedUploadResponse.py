from pydantic import BaseModel


class FeedUploadResponse(BaseModel):
    id: int