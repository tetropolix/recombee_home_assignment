from datetime import datetime
from typing import Optional
from .FeedUploadResponse import FeedUploadResponse
from models.FeedUpload import FeedUploadStatus


class FeedUploadStatusResponse(FeedUploadResponse):
    status: FeedUploadStatus
    error: Optional[str]
    feed_processing_started_at: Optional[datetime]
    feed_processing_successfully_finished_at: Optional[datetime]

    class Config:
        use_enum_values = False
        json_encoders = {
            FeedUploadStatus: lambda v: v.name
        }