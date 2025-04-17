import json
from logging import Logger
from pathlib import Path
from pyexpat import ExpatError
import shutil
from uuid import uuid4
import aiofiles
import aiohttp
from pydantic import ValidationError
import xmltodict

from clients.db_client import DBClient
from models.FeedItem import FeedItem, FeedItemWithUploadReference
from models.FeedUpload import FeedUploadStatus


class FeedParsingException(Exception):
    def __init__(self, message="An error occurred while parsing the feed."):
        super().__init__(message)

async def process_feeds(feed_upload_id: int, xml_string: str, images_dir: str, logger: Logger, db: DBClient):
    """
    Method processes whole background logic on provided xml feed
    """
    try:
        # update associated feed upload job
        await db.update_feed_upload_job(
            feed_upload_id, status=FeedUploadStatus.PROCESSING
        )

        # parse xml and save images
        feed_items = await download_images_for_whole_feed(
            feed_upload_id,
            xml_string,
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

def parse_xml_to_feed_items(msg_xml: str) -> list[FeedItem]:
    try:
        xml_as_dict = xmltodict.parse(msg_xml)
    except ExpatError:
        raise FeedParsingException("Unable to parse XML structure")

    try:
        items = xml_as_dict["rss"]["channel"]["item"]
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
        return [FeedItem(**item) for item in items]
    except ValidationError as ve:
        raise FeedParsingException(json.dumps(ve.errors()[0]))


async def download_images(
    feed_items: list[FeedItemWithUploadReference], base_dir: str
) -> dict[str, tuple[str, list[str]]]:  # horrible output struct :/
    """
    Method iterates over all feed items, and saves image references into the feed upload id dir.

    :feed_items: feed items to iterate
    :param base_dir: directory should contain feed upload directory by its' id and associated images
    :return: dict where key represents feed_item.feed_item_id and the value represents tuple of image_link and list of additional_image_link with new image IDs
    """
    if len(feed_items) == 0:
        return {}

    images_dir = Path(base_dir) / str(feed_items[0].feed_upload_id)
    images_dir.mkdir(parents=True, exist_ok=True)
    output_dict = {}

    for feed_item in feed_items:
        image_link = None
        additional_image_link = None

        if feed_item.image_link:
            image_link = feed_item.image_link
        if feed_item.additional_image_link:
            additional_image_link = feed_item.additional_image_link
        output_dict[feed_item.feed_item_id] = (image_link, additional_image_link)

    async with aiohttp.ClientSession() as session:
        for feed_item_id, tpl in output_dict.items():
            new_image_link = None
            new_additional_image_link = None
            if tpl[0] is not None:
                new_image_link = await download_image(session, tpl[0], images_dir)
            if tpl[1] is not None:
                new_additional_image_link = [
                    await download_image(session, url, images_dir) for url in tpl[1]
                ]

            # update output_dict
            output_dict[feed_item_id] = (new_image_link, new_additional_image_link)

    return output_dict


async def download_image(session: aiohttp.ClientSession, url: str, images_dir: Path):
    async with session.get(url) as resp:
        if resp.status == 200:
            ext = Path(url).suffix
            new_image_id = uuid4().hex
            filename = f"{new_image_id}{ext}"
            file_path = Path(images_dir / filename)

            async with aiofiles.open(file_path, "wb") as f:
                content = await resp.read()
                await f.write(content)

        else:
            raise FeedParsingException(f"Unable to download image from: {url}")
        return new_image_id


async def download_images_for_whole_feed(
    feed_upload_id: int, xml_to_parse: str, base_dir: str
) -> list[FeedItemWithUploadReference]:
    """
    Method parses provided xml string and feed items' associated images

    :param feed_upload_id: feed upload id which will be referenced by every feed_item
    :param xml_to_parse: xml as string which will be parsed
    :base_dir: directory which will store downloaded images in {feed_upload_id} dir

    :return: list of FeedItemWithUploadReference ready to save
    """
    feed_items = [
        FeedItemWithUploadReference.model_construct(
            feed_upload_id=feed_upload_id, **dict(item)
        )
        for item in parse_xml_to_feed_items(xml_to_parse)
    ]
    new_image_ids = await download_images(feed_items, base_dir)
    for feed_item in feed_items:
        try:
            image_ids = new_image_ids[feed_item.feed_item_id]
            feed_item.image_link = image_ids[0]
            feed_item.additional_image_link = image_ids[1]
        except KeyError:
            pass

    return feed_items


def cleanup_images_dir(images_dir, feed_upload_id):
    dir_to_delete = Path(images_dir) / str(feed_upload_id)
    if dir_to_delete.exists():
        shutil.rmtree(dir_to_delete)
