import asyncpg
from typing import Optional, Type

from models.Feed import Feed
from models.FeedUpload import FeedUpload, FeedUploadStatus

class DBClient:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(dsn=self.dsn)

    async def close(self):
        if self.pool:
            await self.pool.close()
    
    def get_connection_pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("Connection pool is None")
        return self.pool

    async def save_feeds(self, feeds: list[Feed]):
        table = "feed_items"

        if not feeds:
            return

        columns = Feed.db_columns()
        placeholders = ', '.join(f'${i+1}' for i in range(len(columns)))
        sql = f'''
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT (id) DO NOTHING
        '''

        rows = [tuple(feed.to_db_dict().get(col) for col in columns) for feed in feeds]

        async with self.get_connection_pool().acquire() as conn:
            async with conn.transaction():
                await conn.executemany(sql, rows)
    
    async def create_feed_upload_job(self) -> int:
        sql = """
            INSERT INTO feed_uploads (status, error)
            VALUES ($1, $2)
            RETURNING id
        """
        async with self.get_connection_pool().acquire() as conn:
            row = await conn.fetchrow(sql, FeedUploadStatus.QUEUED, None)
            return row["id"]
        
    async def update_feed_upload_job(self, job_id: int, status: Optional[FeedUploadStatus] = None, error: Optional[str] = None):
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

        values.append(job_id)
        sql = f"""
            UPDATE feed_uploads
            SET {', '.join(fields)}
            WHERE id = ${i}
        """

        async with self.get_connection_pool().acquire() as conn:
            await conn.execute(sql, *values)
