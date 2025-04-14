from datetime import datetime
from enum import IntEnum
from typing import Optional


class FeedUploadStatus(IntEnum):
    QUEUED = 1
    PROCESSING = 2
    FINISHED = 3
    FINISHED_ERROR = 4


class FeedUpload():
    id: Optional[int] = None
    status: FeedUploadStatus
    error: Optional[str] = None
    created_at: Optional[datetime] = None
