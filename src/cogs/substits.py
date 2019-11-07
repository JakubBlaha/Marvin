import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Optional, List

import PIL.ImageOps
import bs4
import requests
from PIL.Image import Image
from discord import File
from discord.ext import tasks
from discord.ext.commands import Cog, Context, command
from pdf2image import pdf2image

from cache import Cache
from client import Marvin
from command_output import CommandOutput
from decorators import del_invoc
from remote_config import RemoteConfig
from utils import ImageUtils

BG_COLOR = (35, 39, 42)
CACHE_KEY = 'substits'
CACHE_SECONDS = 600

logger = logging.getLogger('Substits')


@dataclass
class PdfScrapeResult:
    data: Optional[bytes]
    filename: Optional[str]
    succeeded: bool


def get_pdf_data(login_url: str, course_url: str, link_regex: str, username: str, password: str) -> PdfScrapeResult:
    # Create session
    session = requests.Session()

    # Login
    logger.debug('Logging into moodle ...')
    session.post(login_url, data={'username': username, 'password': password})

    # Load course
    logger.debug('Loading course ...')
    html = session.get(course_url).text

    # Extract first (latest) link
    logger.debug('Getting link ...')
    soup = bs4.BeautifulSoup(html, 'html.parser')
    links = [a for a in soup.find_all('a') if re.match(link_regex, a.text)]

    if not links:
        return PdfScrapeResult(None, None, False)

    # Get the filename
    filename = links[0].text

    # Download pdf
    logger.debug('Getting pdf ...')
    data = session.get(links[0].get('href')).content

    return PdfScrapeResult(data, filename, True)


def date_from_pdf_name(fname: str) -> str:
    """ Return a date as a str. Example: 010119.ext -> 1. 1. 0019. """
    _date_enc = os.path.splitext(fname)[0]
    day, month, year = _date_enc[:2], _date_enc[2:4], _date_enc[4:]

    return f'{day}. {month}. {datetime.now().year // 100}{year}'


async def send_image(ctx: Context, img: Image):
    # Save to a buffer
    fp = BytesIO()
    img.save(fp, format='PNG')
    fp.seek(0)

    # Send image
    await ctx.send(file=File(fp, filename='substits.png'))


def images_to_bytes(images: List[Image]) -> List[bytes]:
    """ Convert a list of PIL images to a list of byte-strings to optimize caching. """
    result = []

    for img in images:
        buffer = BytesIO()
        img.save(buffer, 'png')
        result.append(buffer.getvalue())

    return result


def images_from_bytes(bytes_: List[bytes]) -> List[Image]:
    """ Convert a list of bytes-strings to a list of PIL images to restore from cache. """
    result = []

    for b in bytes_:
        buffer = BytesIO(b)
        result.append(PIL.Image.open(buffer))

    return result


def process_image(img: Image) -> Image:
    """ Enhance a copy of the image with a nicer design. """
    # Get absolute bbox from relative bbox
    w, h = img.size
    rl, rt, rr, rb = RemoteConfig.substits_pdf_bbox  # Relative bbox
    al, at, ar, ab = w * rl, h * rt, w * rr, h * rb  # Absolute values

    # Crop the image with absolute values
    img = img.crop((al, at, ar, ab))

    # Crop to content
    img = img.crop(img.getbbox())

    # Invert the colors
    img = ImageUtils.invert_colors(img)

    # Add background
    bg_img = PIL.Image.new('RGBA', img.size, BG_COLOR)
    img = PIL.Image.alpha_composite(bg_img, img)

    # Add a border
    border = int(max(img.size) * .05)
    img = PIL.ImageOps.expand(img, border=border, fill=BG_COLOR)

    return img


class Substits(Cog, name='Substitutions'):
    bot: Marvin
    _date: str  # User will be informed about the date of the pdf
    _images: List[Image]

    def __init__(self, bot: Marvin):
        self.bot = bot
        self._date = 'Yet to load'
        self._images = []

        # Start loop
        self.bot.add_listener(self.on_ready)

        # # Start the plotly orca server
        # self.bot.loop.run_in_executor(None, go.Figure().to_image)

    async def on_ready(self):
        self.reload_data.start()

    # noinspection PyCallingNonCallable
    @tasks.loop(seconds=CACHE_SECONDS)
    async def reload_data(self):
        # Do not download if cached data is unexpired
        # Used when bot restarts frequently

        # Load cached
        cached = Cache.load(CACHE_KEY, CACHE_SECONDS)
        if cached:
            self._date = cached[0]
            self._images = images_from_bytes(cached[1])
            logger.debug('Loaded cached images')
            return

        # Download
        kwargs = RemoteConfig.substits_kwargs
        args = kwargs['login_url'], kwargs['course_url'], kwargs[
            'link_regex'], RemoteConfig.moodle_username, RemoteConfig.moodle_password
        result = await self.bot.loop.run_in_executor(None, get_pdf_data, *args)

        if result.succeeded:
            logger.debug('Successfully got the pdf data.')
        else:
            logger.warning('No pdf data returned. Cannot process it further!')
            return

        # Save date
        self._date = date_from_pdf_name(result.filename)

        logger.debug('Done')

        # Convert pdf to images
        logger.debug('Converting to images...')
        self._images = pdf2image.convert_from_bytes(result.data, fmt='png', transparent=True)
        logger.debug(f'Conversion done: {self._images}')

        # Process the images to be nicer
        self._images = [process_image(img) for img in self._images]

        # Cache
        Cache.cache(CACHE_KEY, (self._date, images_to_bytes(self._images)))

    @command(aliases=['supl', 'suply', 'sub'])
    @del_invoc
    async def substits(self, ctx: Context):
        """
        Outputs the latest substitutions.

        The last pdf file from the remote-configured course is pulled and an enhanced image if the pdf is sent.
        """

        await ctx.trigger_typing()

        # Send header
        await CommandOutput(ctx, wide=True,
                            title=f'The substitution list for the day **{self._date}**').send(register=False)

        for img in self._images:
            await send_image(ctx, img)


def setup(bot):
    bot.add_cog(Substits(bot))
