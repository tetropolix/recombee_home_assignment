import asyncio
import os

from clients.db_client import DBClient
from clients.rabbitmq_client import RabbitMQClient
from consumer.processing_utils import (
    FeedParsingException,
    cleanup_images_dir,
    download_images_for_whole_feed,
)
from logger import get_logger
from models.FeedUpload import FeedUploadStatus

logger = get_logger("CONSUMER SERVICE")

rabbit_mq_host = os.getenv("RABBIT_MQ_HOST", "localhost")
rabbit_mq_user = os.getenv("RABBIT_MQ_USER", "guest")
rabbit_mq_pass = os.getenv("RABBIT_MQ_PASSWORD", "guest")
rabbit_mq_queue = os.getenv("RABBIT_MQ_QUEUE", "feeds_queue")

db_host = os.getenv("POSTGRES_DB_HOST", "localhost")
pg_db = os.getenv("POSTGRES_DB", "feeds")
pg_user = os.getenv("POSTGRES_USER", "user")
pg_password = os.getenv("POSTGRES_PASSWORD", "pass")
pg_port = os.getenv("POSTGRES_PORT", "5432")

images_dir = os.getenv("SHARED_IMAGES_DIR", "./app/images")


async def main():
    logger.info("Starting consumer service")

    rabbitmq_client = RabbitMQClient(
        user=rabbit_mq_user,
        password=rabbit_mq_pass,
        host=rabbit_mq_host,
        queue=rabbit_mq_queue,
        exchange=None,
        routing_key=None,
    )
    db = DBClient(
        dsn=f"postgresql://{pg_user}:{pg_password}@{db_host}:{pg_port}/{pg_db}"
    )

    await db.connect()
    await rabbitmq_client.connect_for_consuming()

    async with rabbitmq_client.get_queue().iterator() as queue_iter:
        logger.info("Ready for processing")
        async for message in queue_iter:
            async with message.process():

                feed_upload_id = message.headers.get("feed_upload_id")
                if not isinstance(
                    feed_upload_id, int
                ):  # was unable to type it into the int
                    raise ValueError(
                        "Expected an integer value as feed_upload_id from header"
                    )

                try:
                    # update associated feed upload job
                    await db.update_feed_upload_job(
                        feed_upload_id, status=FeedUploadStatus.PROCESSING
                    )

                    # parse xml and save images
                    feed_items = await download_images_for_whole_feed(
                        feed_upload_id,
                        message.body.decode(),
                        images_dir,
                    )

                    # save feed items + update the associated upload job
                    await db.save_feed_items(feed_items)
                except FeedParsingException as e:
                    await db.update_feed_upload_job(
                        feed_upload_id,
                        status=FeedUploadStatus.FINISHED_ERROR,
                        error=f"{FeedParsingException.__name__}: {str(e)}",
                    )
                    cleanup_images_dir(images_dir, feed_upload_id)
                    logger.warning(f"FeedParsingException has occured - {str(e)}")
                except Exception as e:
                    await db.update_feed_upload_job(
                        feed_upload_id,
                        status=FeedUploadStatus.FINISHED_ERROR,
                        error=f"Non xml-processing exception: {str(e)}",
                    )
                    cleanup_images_dir(images_dir, feed_upload_id)
                    logger.warning(
                        f"Non xml-processing exception has occured: {str(e)}"
                    )


if __name__ == "__main__":
    asyncio.run(main())
