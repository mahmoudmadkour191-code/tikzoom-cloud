import asyncio
import os
import pathlib
import re
import shutil
import time
from collections.abc import Callable, Coroutine, Iterable
from datetime import datetime
from html import escape
from mimetypes import guess_type
from pathlib import Path
from string import capwords

import aiofiles
import aiofiles.os
import aiojobs
from aiogram.enums import MessageEntityType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from humanize import naturalsize
from PIL import Image as PILImage
from PIL.Image import Resampling

from nazurin.models import Caption
from nazurin.utils.decorators import async_wrap
from nazurin.utils.exceptions import NazurinError

from . import logger

FILENAME_MAX_LENGTH = 255
CAPTION_MAX_LENGTH = 1024


WRONG_FILE_IDENTIFIER = "Wrong file identifier/HTTP URL specified"
INVALID_HTTP_URL_CONTENT = "Failed to get HTTP URL content"
GROUP_SEND_FAILED = "Group send failed"
WEBPAGE_CURL_FAILED = "WEBPAGE_CURL_FAILED"

# https://core.telegram.org/bots/api#sendphoto
TG_PHOTO_WIDTH_HEIGHT_RATIO_LIMIT = 20
TG_PHOTO_DIMENSION_LIMIT = 10000
TG_PHOTO_FILE_SIZE_LIMIT = 10 * 1024 * 1024  # 10 MB


async def handle_bad_request(message: Message, error: TelegramBadRequest):
    logger.error("BadRequest exception: {}", error)
    if not message:
        return
    if (
        WRONG_FILE_IDENTIFIER in error.message
        or INVALID_HTTP_URL_CONTENT in error.message
        or WEBPAGE_CURL_FAILED in error.message
    ):
        await message.reply(
            "Failed to send image as photo, maybe the size is too big, "
            "consider using download option or try again.\n"
            f"Message: {message.text}\n"
            f"Error: {error}",
        )
    elif GROUP_SEND_FAILED in error.message:
        await message.reply(
            "Failed to send images because one of them is too large, "
            "consider using download option or try again.\n"
            f"Message: {message.text}\n"
            f"Error: {error}",
        )
    else:
        raise error


def sanitize_path_segment(segment: str) -> str:
    """
    Remove invalid characters from a path segment. e.g. `/\\<>:"|?*`.
    """

    segment = re.sub(r"[\"*/:<>?\\|]+", "_", segment)  # reserved characters
    segment = re.sub(r"[\t\n\r\f\v]+", " ", segment)
    segment = re.sub(r"\u202E|\u200E|\u200F", "", segment)  # RTL marks
    return segment


def sanitize_filename(name: str) -> str:
    # https://docs.microsoft.com/zh-cn/windows/win32/fileio/naming-a-file
    name = sanitize_path_segment(name)
    filename, ext = os.path.splitext(name)
    filename = filename.strip()
    if Path(filename).is_reserved():
        filename = "_" + filename
    name = filename + ext
    if len(name) > FILENAME_MAX_LENGTH:
        name = filename[: FILENAME_MAX_LENGTH - len(ext)] + ext
    return name


def sanitize_path(
    path: os.PathLike,
    sanitize: Callable[[str], str] = sanitize_path_segment,
) -> pathlib.PurePath:
    """
    Remove invalid characters from a path.
    Apply `sanitize` function to every segment and join them as PurePath.
    """

    segments = pathlib.PurePath(path).parts
    segments = [
        sanitize(segment) if segment != "/" else segment for segment in segments
    ]
    return pathlib.PurePath(*segments)


def sanitize_caption(caption: Caption) -> str:
    content = caption.text
    if len(content) > CAPTION_MAX_LENGTH:
        content = content[:1024]
    content = escape(content, quote=False)
    return content


def get_urls_from_message(message: Message) -> list[str]:
    if message.entities:
        entities = message.entities
        text = message.text
    elif message.caption_entities:
        entities = message.caption_entities
        text = message.caption
    else:
        return []
    # Telegram counts entity offset and length in UTF-16 code units
    text = text.encode("utf-16-le")
    urls = []
    for item in entities:
        if item.type == MessageEntityType.TEXT_LINK:
            urls.append(item.url)
        elif item.type == MessageEntityType.URL:
            offset = item.offset
            length = item.length
            urls.append(text[offset * 2 : (offset + length) * 2].decode("utf-16-le"))
    return urls


def is_image(url: str) -> bool:
    """
    Guess if a file is image by extension
    """

    filetype = str(guess_type(url)[0])
    return filetype.startswith("image")


def ensure_existence(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


async def ensure_existence_async(path: str):
    if not await aiofiles.os.path.exists(path):
        await aiofiles.os.makedirs(path, exist_ok=True)


def snake_to_pascal(name: str):
    """Convert snake_case to PascalCase"""
    return capwords(name.replace("_", " ")).replace(" ", "")


async def read_by_chunks(path: str, chunk_size: int = 4 * 1024 * 1024):
    async with aiofiles.open(path, "rb") as f:
        chunk = await f.read(chunk_size)
        while chunk:
            yield chunk
            chunk = await f.read(chunk_size)


def fromisoformat(date: str):
    """
    A polyfill for `datetime.fromisoformat` before Python 3.11.

    Prior to Python 3.11, `datetime.fromisoformat` does not recognize
    UTC timezone represented as 'Z'.

    https://docs.python.org/3/library/datetime.html?highlight=fromisoformat#datetime.datetime.fromisoformat
    """

    if date.endswith("Z"):
        date = date[:-1] + "+00:00"
    return datetime.fromisoformat(date)


def fromasctimeformat(date: str):
    """
    Convert a string in an asctime-like format (but with timezone)
    to datetime object. e.g. "Sat Oct 22 08:45:05 -0500 2022"
    """

    return datetime.strptime(date, "%a %b %d %H:%M:%S %z %Y")


def format_error(error: Exception) -> str:
    error_type = type(error).__name__
    error_msg = escape(str(error), quote=False)
    return f"({error_type}) {error_msg}"


async def remove_files_older_than(path: str, days: int):
    """Remove files in `path` whose last access time is older than `days`."""
    if not await aiofiles.os.path.exists(path):
        return
    now = time.time()
    deadline = now - days * 86400
    entries = await aiofiles.os.scandir(path)
    for entry in entries:
        if entry.stat().st_atime < deadline:
            if entry.is_file():
                await aiofiles.os.remove(entry.path)
            elif entry.is_dir():
                shutil.rmtree(entry.path)


@async_wrap
def check_image(path: str | os.PathLike) -> bool:
    """
    Check if file is a valid image and not truncated.
    """

    try:
        with PILImage.open(path) as image:
            image.verify()

        # verify() does not detect all the possible image defects
        # e.g. truncated images, try to open the image to detect
        with PILImage.open(path) as image:
            image.load()
        return True
    except OSError as error:
        logger.warning("Invalid image {}: {}", path, error)
        return False


@async_wrap
def resize_image_for_telegram(path: str | os.PathLike) -> Path:
    """
    Resize image if it exceeds Telegram Bot API limits:
    - File size: max 10 MB
    - Dimensions: width + height must not exceed 10,000

    Returns the path to the resized image (or original if no resize needed).
    """

    path = Path(path)
    file_size = path.stat().st_size

    try:
        with PILImage.open(path) as image:
            width, height = image.size
            dimension_sum = width + height

            if height != 0 and width / height > TG_PHOTO_WIDTH_HEIGHT_RATIO_LIMIT:
                raise NazurinError(
                    f"Width and height ratio of image exceeds Telegram limit "
                    f"({width} / {height} > {TG_PHOTO_WIDTH_HEIGHT_RATIO_LIMIT}, "
                    "try download option.",
                )

            needs_resize = (
                file_size > TG_PHOTO_FILE_SIZE_LIMIT
                or dimension_sum > TG_PHOTO_DIMENSION_LIMIT
            )
            if not needs_resize:
                return path

            scale_factor = 1.0

            if dimension_sum > TG_PHOTO_DIMENSION_LIMIT:
                dimension_scale = (
                    TG_PHOTO_DIMENSION_LIMIT / dimension_sum * 0.95
                )  # 5% margin
                scale_factor = min(scale_factor, dimension_scale)
                logger.info(
                    "Image {} exceeds dimension limit ({} + {} > {}), "
                    "scaling down by {:.2f}x",
                    path.name,
                    width,
                    height,
                    TG_PHOTO_DIMENSION_LIMIT,
                    dimension_scale,
                )

            if file_size > TG_PHOTO_FILE_SIZE_LIMIT:
                # Estimate scale factor needed for file size
                # PNG compression varies, but we can estimate based on area reduction
                # For safety, use aggressive scaling for large files
                file_scale = max(
                    0.5, (TG_PHOTO_FILE_SIZE_LIMIT / file_size) ** 0.5 * 0.8
                )  # Square root scaling with 80% safety margin
                scale_factor = min(scale_factor, file_scale)
                logger.info(
                    "Image {} exceeds file size limit ({} > {}), "
                    "scaling down by {:.2f}x",
                    path.name,
                    file_size,
                    TG_PHOTO_FILE_SIZE_LIMIT,
                    file_scale,
                )

            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)

            resized_image = image.copy()
            resized_image = resized_image.resize(
                (new_width, new_height), Resampling.LANCZOS
            )

            stem = path.stem
            suffix = path.suffix
            parent = path.parent
            resized_path = parent / f"{stem}_resized{suffix}"

            if suffix.lower() in [".jpg", ".jpeg"]:
                resized_image.save(
                    resized_path, format="JPEG", optimize=True, quality=85
                )
            elif suffix.lower() == ".png":
                resized_image.save(resized_path, format="PNG", optimize=True)
            else:
                resized_image.save(resized_path, optimize=True)

            new_file_size = resized_path.stat().st_size
            logger.info(
                "Resized image {} -> {} ({}x{} -> {}x{}, {} -> {})",
                path.name,
                resized_path.name,
                width,
                height,
                new_width,
                new_height,
                naturalsize(file_size, binary=True),
                naturalsize(new_file_size, binary=True),
            )

            return resized_path

    except OSError as error:
        logger.warning("Failed to resize image {}: {}", path, error)
        return path


async def run_in_pool(tasks: Iterable[Coroutine], pool_size: int):
    scheduler = await aiojobs.create_scheduler(limit=pool_size)
    jobs: list[aiojobs.Job] = [await scheduler.spawn(task) for task in tasks]
    await asyncio.gather(*[job.wait() for job in jobs])
    await scheduler.close()
