from typing import Optional
from pydantic import BaseModel, Field


class FeedItem(BaseModel):
    id: Optional[int] = None
    feed_item_id: str = Field(validation_alias="g:id")
    title: str
    description: str
    link: str
    image_link: Optional[str] = Field(default=None, validation_alias="g:image_link")
    additional_image_link: Optional[list[str]] = Field(
        default=None, validation_alias="g:additional_image_link"
    )
    price: Optional[str] = Field(default=None, validation_alias="g:price")
    condition: Optional[str] = Field(default=None, validation_alias="g:condition")
    availability: Optional[str] = Field(default=None, validation_alias="g:availability")
    brand: Optional[str] = Field(default=None, validation_alias="g:brand")
    gtin: Optional[str] = Field(default=None, validation_alias="g:gtin")
    item_group_id: Optional[str] = Field(
        default=None, validation_alias="g:item_group_id"
    )
    sale_price: Optional[str] = Field(default=None, validation_alias="g:sale_price")

    @classmethod
    def db_columns(cls, include_id: bool = False) -> list[str]:
        columns = list(cls.model_fields.keys())
        if not include_id and "id" in columns:
            columns.remove("id")
        return columns

    def to_db_dict(self) -> dict:
        return self.model_dump(by_alias=False, exclude_none=True)

    def to_model_dict(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)


class FeedItemWithUploadReference(FeedItem):
    feed_upload_id: int
