import os

import dramatiq

from dramatiq.middleware import AsyncIO
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from clients.db_client import DBClient
from consumer.processing_utils import process_feeds
from logger import get_logger


logger = get_logger("CONSUMER SERVICE V2")

rabbit_mq_host = os.getenv("RABBIT_MQ_HOST", "localhost")
rabbit_mq_user = os.getenv("RABBIT_MQ_USER", "guest")
rabbit_mq_pass = os.getenv("RABBIT_MQ_PASSWORD", "guest")

db_host = os.getenv("POSTGRES_DB_HOST", "localhost")
pg_db = os.getenv("POSTGRES_DB", "feeds")
pg_user = os.getenv("POSTGRES_USER", "user")
pg_password = os.getenv("POSTGRES_PASSWORD", "pass")
pg_port = os.getenv("POSTGRES_PORT", "5432")

images_dir = os.getenv("SHARED_IMAGES_DIR", "./app/images")


db = DBClient(dsn=f"postgresql://{pg_user}:{pg_password}@{db_host}:{pg_port}/{pg_db}")
db_connected = False
rabbitmq_broker = RabbitmqBroker(
    url=f"amqp://{rabbit_mq_user}:{rabbit_mq_pass}@{rabbit_mq_host}/"
)

#keeping here just for reference - didn't work because another event loop was being used

# class DBConnectionMiddleware(dramatiq.Middleware):
#     def __init__(self, db):
#         self.db: DBClient = db
#         self.started = False

#     def before_worker_boot(self, broker, worker):
#         if not self.started:
#             loop = asyncio.get_event_loop()
#             loop.run_until_complete(self.db.connect())
#             self.started = True

#     def after_worker_stops(self, broker, worker):
#         loop = asyncio.get_event_loop()
#         loop.run_until_complete(self.db.close())


# rabbitmq_broker.add_middleware(DBConnectionMiddleware(db))

rabbitmq_broker.add_middleware(AsyncIO())
dramatiq.set_broker(rabbitmq_broker)


@dramatiq.actor
async def process_feeds_v2(feed_upload_id: int, xml_string: str):
    global db_connected
    logger.info(f"Started processing feed upload with id {feed_upload_id}")

    if not db_connected:
        await db.connect()
        db_connected = True
    await process_feeds(feed_upload_id, xml_string, images_dir, logger, db)
