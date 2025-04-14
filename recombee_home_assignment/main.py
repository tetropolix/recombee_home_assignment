from typing import Optional
import aio_pika
from fastapi import FastAPI, HTTPException, Header, Request
import os
from contextlib import asynccontextmanager

from clients.db_client import DBClient
from models.Feed import Feed
from models.FeedUploadResponse import FeedUploadResponse

db_host = 'localhost' if os.getenv('POSTGRES_DB_HOST') is None else os.getenv('POSTGRES_DB_HOST')
pg_db = 'feeds' if os.getenv('POSTGRES_DB') is None else os.getenv('POSTGRES_DB')
pg_user = 'user' if os.getenv('POSTGRES_PASSWORD') is None else os.getenv('POSTGRES_PASSWORD')
pg_password = 'pass' if os.getenv('POSTGRES_PASSWORD') is None else os.getenv('POSTGRES_PASSWORD')

rabbit_mq_user = 'guest' if os.getenv('RABBIT_MQ_USER') is None else os.getenv('RABBIT_MQ_USER')
rabbit_mq_pass = 'guest' if os.getenv('RABBIT_MQ_PASS') is None else os.getenv('RABBIT_MQ_PASS')
rabbit_mq_host = 'localhost' if os.getenv('RABBIT_MQ_USER') is None else os.getenv('RABBIT_MQ_USER')
rabbit_mq_exchange= 'feeds_exchange' if os.getenv('RABBIT_MQ_EXCHANGE') is None else os.getenv('RABBIT_MQ_EXCHANGE')
rabbit_mq_queue = 'feeds_queue' if os.getenv('RABBIT_MQ_QUEUE') is None else os.getenv('RABBIT_MQ_QUEUE')
rabbit_mq_rt_key = 'feeds_queue' if os.getenv('RABBIT_MQ_URT_KEY') is None else os.getenv('RABBIT_MQ_URT_KEY')

@asynccontextmanager
async def lifespan(app: FastAPI):
    global channel
    global db
    connection = await aio_pika.connect_robust(f"amqp://{rabbit_mq_user}:{rabbit_mq_pass}@{rabbit_mq_host}/")
    channel = await connection.channel()

    exchange = await channel.declare_exchange(f"{rabbit_mq_exchange}", aio_pika.ExchangeType.DIRECT, durable=True)
    queue = await channel.declare_queue(f"{rabbit_mq_queue}", durable=True)
    await queue.bind(exchange, routing_key=f"{rabbit_mq_rt_key}")

    app.state.rabbit_connection = connection
    app.state.rabbit_channel = channel
    app.state.rabbit_exchange = exchange
    db = DBClient(dsn=f"postgresql://{pg_user}:{pg_password}@{db_host}:5432/{pg_db}")
    await db.connect()

    yield
    
    await app.state.rabbit_connection.close()
    await db.close()

app = FastAPI(lifespan=lifespan)

@app.post("/feeds", response_model=FeedUploadResponse)
async def upload_feed(request: Request, content_type: Optional[str] = Header(None)):
    if content_type != "application/xml":
        raise HTTPException(status_code=415, detail="Unsupported Media Type. Expected 'application/xml'")

    try:
        request_xml = await request.body()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading request body: {str(e)}")
    
    feed_upload_id = await db.create_feed_upload_job()

    try:
        message = aio_pika.Message(
            request_xml,
            delivery_mode=2,
            headers={"feed_upload_id": feed_upload_id},
            content_type="application/xml"
        )
        await channel.default_exchange.publish(
            message,
            routing_key= f"{rabbit_mq_rt_key}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send to RabbitMQ: {str(e)}")

    return FeedUploadResponse(id=feed_upload_id)
