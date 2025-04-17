from datetime import datetime
import asyncpg
from typing import Optional

from logger import get_logger
from models.FeedItem import FeedItemWithUploadReference
from models.FeedUpload import FeedUpload, FeedUploadStatus

logger = get_logger(__name__)


class DBClient:
    FEED_ITEMS_TABLE = "feed_items"
    FEED_UPLOADS_TABLE = "feed_uploads"

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if self.pool is not None and not self.pool._closed:
            logger.info("Reusing existing connection pool")
            return self.pool
        logger.info(f"Creating connection pool using {self.dsn} dsn")
        self.pool = await asyncpg.create_pool(dsn=self.dsn, min_size=5, max_size=8)
        logger.info("Connection pool created")

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("Connection pool closed")

    def get_connection_pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("Connection pool is None")
        return self.pool

    async def get_feed_upload_items(
        self, feed_upload_id: int, item_id: Optional[str] = None
    ) -> list[FeedItemWithUploadReference]:
        sql = f"""
            SELECT 
                feed_upload_id, id, feed_item_id, title, description, link, image_link,
                additional_image_link, price, condition, availability,
                brand, gtin, item_group_id, sale_price
            FROM {self.FEED_ITEMS_TABLE}
            WHERE feed_upload_id = $1
        """

        params: list[str | int] = [feed_upload_id]

        if item_id:
            sql += " AND feed_item_id = $2"
            params.append(item_id)

        async with self.get_connection_pool().acquire() as conn:
            rows = await conn.fetch(sql, *params)
        logger.info(
            f"{len(rows)} records were retrieved for feed_upload_id {feed_upload_id} and item_id {item_id}"
        )
        return [
            FeedItemWithUploadReference.model_construct(**dict(row)) for row in rows
        ]

    async def save_feed_items(self, feed_items: list[FeedItemWithUploadReference], upload_feed_finished_at: Optional[datetime] = None):
        if not feed_items:
            return

        update_sql = f"""
                    UPDATE {self.FEED_UPLOADS_TABLE}
                    SET status = $1, error = $2, successfully_finished_at = $4
                    WHERE id = $3
                """

        columns = FeedItemWithUploadReference.db_columns()
        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
        insert_feed_items_sql = f"""
            INSERT INTO {self.FEED_ITEMS_TABLE} ({', '.join(columns)})
            VALUES ({placeholders})
        """

        rows = [
            tuple(feed_item.to_db_dict().get(col) for col in columns)
            for feed_item in feed_items
        ]

        logger.info(f"Saving {len(feed_items)} feed_items")

        async with self.get_connection_pool().acquire() as conn:
            async with conn.transaction():
                await conn.executemany(insert_feed_items_sql, rows)
                await conn.execute(
                    update_sql,
                    FeedUploadStatus.FINISHED,
                    None,
                    feed_items[0].feed_upload_id,
                    upload_feed_finished_at or datetime.now()
                )

    async def create_feed_upload_job(self) -> int:
        sql = f"""
            INSERT INTO {self.FEED_UPLOADS_TABLE} (status, error)
            VALUES ($1, $2)
            RETURNING id
        """
        async with self.get_connection_pool().acquire() as conn:
            row = await conn.fetchrow(sql, FeedUploadStatus.QUEUED, None)
            logger.info(f"Created feed upload job with {row['id']} id")
            return row["id"]

    async def get_feed_upload_job(self, feed_upload_id: int) -> FeedUpload | None:
        sql = f"""
            SELECT id, status, error, created_at, successfully_finished_at
            FROM {self.FEED_UPLOADS_TABLE}
            WHERE id = $1
        """

        async with self.get_connection_pool().acquire() as conn:
            row = await conn.fetchrow(sql, feed_upload_id)
            logger.info(
                f"Retrieved feed upload job with {feed_upload_id} id {'succsessfuly' if row is not None else 'unsuccessfuly'}"
            )

        if not row:
            return None

        return FeedUpload(**dict(row))

    async def update_feed_upload_job(
        self,
        feed_upload_id: int,
        status: Optional[FeedUploadStatus] = None,
        error: Optional[str] = None,
    ):
        fields = []
        values = []
        i = 1

        if status is not None:
            fields.append(f"status = ${i}")
            values.append(status.value)
            i += 1

        if error is not None:
            fields.append(f"error = ${i}")
            values.append(error)
            i += 1

        values.append(feed_upload_id)
        sql = f"""
            UPDATE {self.FEED_UPLOADS_TABLE}
            SET {', '.join(fields)}
            WHERE id = ${i}
        """

        async with self.get_connection_pool().acquire() as conn:
            await conn.execute(sql, *values)
            logger.info(
                f"Updated feed upload job with {feed_upload_id} id, with {status} - {status.name if status is not None else None} as status and {error} as error"
            )
