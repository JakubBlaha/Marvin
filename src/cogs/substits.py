import logging
import os
import re
import traceback
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Optional

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
from config import Config

BG_COLOR = (35, 39, 42)
CACHE_KEY = 'substits'
CACHE_SECONDS = 600
ATTACHMENT_FILENAME = 'substits.png'

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


def date_from_pdf_name(filename: str) -> str:
    """ Return a date as a str. Example: 010119.ext -> 1. 1. 0019. """
    _date_enc = os.path.splitext(filename)[0]
    day, month, year = _date_enc[:2], _date_enc[2:4], _date_enc[4:]

    return f'{day}. {month}. {datetime.now().year // 100}{year}'


def crop_page(img: Image) -> Image:
    """ Crop a copy of the image as defined in the RemoteConfig. """
    # Get absolute bbox from relative bbox
    w, h = img.size
    rl, rt, rr, rb = RemoteConfig.substits_pdf_bbox  # Relative bbox
    al, at, ar, ab = w * rl, h * rt, w * rr, h * rb  # Absolute values

    # Crop the image with absolute values
    img = img.crop((al, at, ar, ab))

    return img


def enhance_image(img: Image) -> Image:
    """ Enhance a copy the image with a dark mode and padding. """
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
    _image: Image

    def __init__(self, bot: Marvin):
        self.bot = bot
        self._date = 'Yet to load'

        # Start loop
        if Config.moodle_username and Config.moodle_password:
            self.bot.add_listener(self.on_ready)
        else:
            logger.info(
                'Skipping substitutions scraping as no valid moodle credentials are provided.')

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
            self._date, _bytes = cached
            self._image = PIL.Image.open(BytesIO(_bytes))
            logger.debug('Loaded cached images')
            return

        # Download
        kwargs = RemoteConfig.substits_kwargs
        args = kwargs['login_url'], kwargs['course_url'], kwargs[
            'link_regex'], Config.moodle_username, Config.moodle_password
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
        try:
            ims = pdf2image.convert_from_bytes(
                result.data, fmt='png', transparent=True)
        except Exception:
            logger.error('Failed to convert PDF to PNG.')
            logger.error(traceback.format_exc())
            return

        logger.debug(f'Conversion done: {ims}')

        # Crop the images as defined in RemoteConfig
        ims = [crop_page(im) for im in ims]

        # Combine into a one big image
        widths, heights = zip(*(i.size for i in ims))

        total_width = sum(widths)
        max_height = max(heights)

        im = PIL.Image.new('RGBA', (total_width, max_height))

        x_offset = 0
        for _im in ims:
            im.paste(_im, (x_offset, 0))
            x_offset += _im.size[0]

        # Crop to content
        im = im.crop(im.getbbox())

        # Make the image look nicer
        self._image = enhance_image(im)

        # Cache
        buffer = BytesIO()
        self._image.save(buffer, 'PNG')
        Cache.cache(CACHE_KEY, (self._date, buffer.getvalue()))

    @command(aliases=['supl', 'suply', 'sub'])
    @del_invoc
    async def substits(self, ctx: Context):
        """
        Outputs the latest substitutions.

        The last pdf file from the remote-configured course is pulled and an enhanced image if the pdf is sent.
        """

        await ctx.trigger_typing()

        # Save to a buffer
        fp = BytesIO()
        self._image.save(fp, format='PNG')
        fp.seek(0)

        # Create an embed
        out = CommandOutput(
            ctx, title=f'The substitution list for the day **{self._date}**')
        out.embed.set_image(url=f'attachment://{ATTACHMENT_FILENAME}')

        # Send the embed and the attachment
        await out.send(register=False, file=File(fp, ATTACHMENT_FILENAME))


def setup(bot):
    bot.add_cog(Substits(bot))
