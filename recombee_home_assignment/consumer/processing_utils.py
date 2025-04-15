import json
from pathlib import Path
from pyexpat import ExpatError
import shutil
from uuid import uuid4
import aiofiles
import aiohttp
from pydantic import ValidationError
import xmltodict

from models.FeedItem import FeedItem, FeedItemWithUploadReference


class FeedParsingException(Exception):
    def __init__(self, message="An error occurred while parsing the feed."):
        super().__init__(message)


def parse_and_save_xml(msg_xml: str) -> list[FeedItem]:
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


def cleanup_images_dir(images_dir, feed_upload_id):
    dir_to_delete = Path(images_dir) / str(feed_upload_id)
    if dir_to_delete.exists():
        shutil.rmtree(dir_to_delete)
