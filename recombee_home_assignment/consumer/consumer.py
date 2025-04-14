import asyncio
import os
from pyexpat import ExpatError
from aio_pika import connect_robust
from pydantic import ValidationError
import xmltodict

from clients.db_client import DBClient
from models.Feed import Feed
from models.FeedUpload import FeedUploadStatus

host = 'localhost' if os.getenv('RABBIT_MQ_HOST') is None else os.getenv('RABBIT_MQ_HOST')
user = 'guest' if os.getenv('RABBIT_MQ_USER') is None else os.getenv('RABBIT_MQ_USER')
password = 'guest' if os.getenv('RABBIT_MQ_PASSWORD') is None else os.getenv('RABBIT_MQ_PASSWORD')
feeds_queue = 'feeds_queue' if os.getenv('RABBIT_MQ_QUEUE') is None else os.getenv('RABBIT_MQ_QUEUE')

db_host = 'localhost' if os.getenv('POSTGRES_DB_HOST') is None else os.getenv('POSTGRES_DB_HOST')
pg_db = 'feeds' if os.getenv('POSTGRES_DB') is None else os.getenv('POSTGRES_DB')
pg_user = 'user' if os.getenv('POSTGRES_PASSWORD') is None else os.getenv('POSTGRES_PASSWORD')
pg_password = 'pass' if os.getenv('POSTGRES_PASSWORD') is None else os.getenv('POSTGRES_PASSWORD')

class FeedParsingException(Exception):
    def __init__(self, message="An error occurred while parsing the feed."):
        super().__init__(message)

def parse_and_save_xml(msg_xml: str) -> list[Feed]:
    try:
        xml_as_dict = xmltodict.parse(msg_xml)
    except ExpatError:
        raise FeedParsingException("Unable to parse XML structure")

    try:
        items = xml_as_dict['rss']['channel']['item']
    except (KeyError, TypeError):
        raise FeedParsingException("Missing 'rss.channel.item' structure in XML")

    # adjust possible dict to list, or single g:additional_image_link to list
    if isinstance(items, dict):
        items = [items]
    for item in items:
        try:
            additional_image_link = item["g:additional_image_link"]
            if isinstance(additional_image_link, str):
                item["g:additional_image_link"] = [additional_image_link]
        except KeyError:
            # no need to do anything
            continue

    try:
        return [Feed(**item) for item in items]
    except ValidationError as ve:
        print(ve.errors)
        raise FeedParsingException(ve.errors)
    
async def main():
    db = DBClient(dsn=f"postgresql://{pg_user}:{pg_password}@{db_host}:5432/{pg_db}")
    await db.connect()
    connection = await connect_robust(f"amqp://{user}:{password}@{host}/")
    channel = await connection.channel()
    queue = await channel.declare_queue(f"{feeds_queue}", durable=True)

    async with queue.iterator() as queue_iter:
        print(" [*] Waiting for messages. To exit press CTRL+C")
        async for message in queue_iter:
            async with message.process():
                feed_upload_id = int(message.headers.get('feed_upload_id'))
                await db.update_feed_upload_job(feed_upload_id, status=FeedUploadStatus.PROCESSING)

                try:
                    msg_body = message.body.decode()
                    feed_items = parse_and_save_xml(msg_body)
                    await db.save_feeds(feed_items)
                    print("after succ safe")
                except FeedParsingException as e:
                    await db.update_feed_upload_job(feed_upload_id, status=FeedUploadStatus.FINISHED_ERROR, error=str(e))
                    print("exc")



if __name__ == "__main__":
    asyncio.run(main())