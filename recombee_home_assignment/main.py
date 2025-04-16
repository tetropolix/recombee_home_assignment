from pathlib import Path
from typing import Optional
import aio_pika
from fastapi import FastAPI, HTTPException, Header, Request
import os
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from clients.db_client import DBClient
from clients.rabbitmq_client import RabbitMQClient
from models.FeedItem import FeedItem
from models.feeds_api_response.FeedUploadResponse import FeedUploadResponse
from models.feeds_api_response.FeedUploadStatusResponse import FeedUploadStatusResponse

db_host = os.getenv("POSTGRES_DB_HOST", "localhost")
pg_db = os.getenv("POSTGRES_DB", "feeds")
pg_user = os.getenv("POSTGRES_USER", "user")
pg_password = os.getenv("POSTGRES_PASSWORD", "pass")
pg_port = os.getenv("POSTGRES_PORT", "5432")

rabbit_mq_user = os.getenv("RABBIT_MQ_USER", "guest")
rabbit_mq_pass = os.getenv("RABBIT_MQ_PASS", "guest")
rabbit_mq_host = os.getenv("RABBIT_MQ_HOST", "localhost")
rabbit_mq_exchange = os.getenv("RABBIT_MQ_EXCHANGE", "feeds_exchange")
rabbit_mq_queue = os.getenv("RABBIT_MQ_QUEUE", "feeds_queue")
rabbit_mq_rt_key = os.getenv("RABBIT_MQ_RT_KEY", "feeds_queue")

images_dir = os.getenv("SHARED_IMAGES_DIR", "./app/images")


@asynccontextmanager
async def lifespan(app: FastAPI):
    rabbitmq_client = RabbitMQClient(
        user=rabbit_mq_user,
        password=rabbit_mq_pass,
        host=rabbit_mq_host,
        exchange=rabbit_mq_exchange,
        queue=rabbit_mq_queue,
        routing_key=rabbit_mq_rt_key
    )
    db = DBClient(dsn=f"postgresql://{pg_user}:{pg_password}@{db_host}:{pg_port}/{pg_db}")
    
    await rabbitmq_client.connect_for_publishing()
    await db.connect()

    app.state.rabbitmq_client = rabbitmq_client
    app.state.db = db

    yield

    await rabbitmq_client.close()
    await db.close()


app = FastAPI(lifespan=lifespan)

def rabbitmq_client() -> RabbitMQClient:
    return app.state.rabbitmq_client

def db_client() -> DBClient:
    return app.state.db

@app.post("/feeds", response_model=FeedUploadResponse)
async def upload_feed(request: Request, content_type: Optional[str] = Header(None)):
    if content_type != "application/xml":
        raise HTTPException(
            status_code=415, detail="Unsupported Media Type. Expected 'application/xml'"
        )

    try:
        request_xml = await request.body()
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error reading request body: {str(e)}"
        )

    feed_upload_id = await db_client().create_feed_upload_job()

    try:
        message = aio_pika.Message(
            request_xml,
            delivery_mode=2,
            headers={"feed_upload_id": feed_upload_id},
            content_type="application/xml",
        )
        await rabbitmq_client().get_channel().default_exchange.publish(
            message, routing_key=f"{rabbit_mq_rt_key}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send to RabbitMQ: {str(e)}"
        )

    return FeedUploadResponse(id=feed_upload_id)


@app.get("/feeds/{feed_id}", response_model=FeedUploadStatusResponse)
async def get_feed(feed_id: int):
    feed_upload_job = await db_client().get_feed_upload_job(feed_id)
    if feed_upload_job is None:
        raise HTTPException(
            status_code=404, detail=f"Feed upload with id {feed_id} was not found."
        )

    return FeedUploadStatusResponse(
        id=feed_id,
        status=feed_upload_job.status,
        error=feed_upload_job.error,
        feed_processing_started_at=feed_upload_job.created_at,
    )


@app.get("/feeds/{feed_id}/items", response_model=list[str])
async def get_feed_item_ids(feed_id: int):
    # maybe add check whether feed_id is even present as feed_upload?
    items = await db_client().get_feed_upload_items(feed_id)
    return [item.feed_item_id for item in items]


@app.get(
    "/feeds/{feed_id}/items/{item_id}",
    response_model=FeedItem, response_model_exclude={"id"}
)
async def get_feed_item(feed_id: int, item_id: str):
    items = await db_client().get_feed_upload_items(feed_id, item_id)
    if len(items) < 1:
        raise HTTPException(
            status_code=404,
            detail=f"Item specified by feed_id {feed_id} and item_id {item_id} was not found.",
        )
    return items[0]


@app.get("/feeds/{feed_id}/images", response_model=list[str])
async def get_feed_images(feed_id: int):
    items = await db_client().get_feed_upload_items(feed_id)

    # feed may contain 0 images, so no 404 is returned

    image_ids = []
    for item in items:  # no list comprehension because it was hard to read
        if item.image_link is not None:
            image_ids.append(item.image_link)
        if item.additional_image_link is not None:
            image_ids.extend(item.additional_image_link)

    return image_ids


@app.get("/feeds/{feed_id}/images/{image_id}")
async def get_feed_image(feed_id: int, image_id: str):
    feed_path = Path(images_dir) / str(feed_id)

    if not feed_path.exists():
        raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found")

    image_files = list(feed_path.glob(f"{image_id}*"))

    if not image_files:
        raise HTTPException(
            status_code=404, detail=f"Image {image_id} not found in feed {feed_id}"
        )

    return FileResponse(image_files[0])
