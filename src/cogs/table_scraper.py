import io
import logging
import os
import re
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from operator import itemgetter
from tempfile import gettempdir
from typing import Optional, Iterable, List

import bs4
import chart_studio
import plotly.graph_objects as go
import requests
import tabula
from PIL import Image
from discord import File
from discord.ext import tasks
from discord.ext.commands import Cog, Context, command

from cache import Cache
from client import Marvin
from command_output import CommandOutput
from decorators import del_invoc
from remote_config import RemoteConfig

DOWNLOAD_PATH = os.path.abspath(gettempdir() + '/marvin')
IMG_CACHE_PATH = 'cache/img'

logger = logging.getLogger('TableScraper')


def download_pdf(login_url: str, course_url: str, link_regex: str, username: str, password: str) -> Optional[str]:
    # Make the download directory
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)

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
        return

    # Download pdf
    logger.debug('Downloading pdf ...')
    content = session.get(links[0].get('href')).content

    pdf_path = os.path.join(DOWNLOAD_PATH, links[0].text)
    with open(pdf_path, 'wb') as f:
        f.write(content)

    return pdf_path


def pdf_to_list(path: str) -> list:
    """ Read a pdf and return as a table. """
    logger.info(f'Reading {path} ...')
    # noinspection PyTypeChecker
    data = tabula.read_pdf(path, output_format='json', pages='all')[0]['data']

    return data


def date_from_pdf_name(fname: str) -> str:
    """ Return a date as a str. Example: 010119.ext -> 1. 1. 0019. """
    _date_enc = os.path.splitext(fname)[0]
    day, month, year = _date_enc[:2], _date_enc[2:4], _date_enc[4:]

    return f'{day}. {month}. {datetime.now().year // 100}{year}'


def transpose(data: Iterable[Iterable]) -> List[List]:
    """ Make a list of columns from a list of rows and vice versa. """
    return list(map(list, zip(*data)))


SEP = '---'


class TableData:
    """
    A provider for lot of useful methods.

    This class contains a lot of useful methods and manages the table data
    internally.
    """

    data: list = []

    def __init__(self, data: list):
        self.data = data

    @property
    def width(self):
        return len(self.data[0])

    @property
    def height(self):
        return len(self.data)

    def get_cols(self) -> list:
        """ Get the data as a list of columns instead as a list of rows. """
        return transpose(self.data)

    def set_cols(self, cols: list):
        """ Update the table from a ist of columns. """
        self.data = transpose(cols)

    def extract_table_cols(self, col_indexes: list):
        # TODO We probably wanna do this similarly to the filter_rows method
        """
        Extract given columns.

        Extract given columns based on their indexes.

        Attrs:
            data: A list representing the table data.
            col_indexes: A list representing the indexes of the columns that
                will be extracted.
        """

        self.data = [[col['text'] for col in itemgetter(*col_indexes)(row)]
                     for row in self.data]

    def filter_rows(self, regex: str, separator: str = '#'):
        """
        Filter rows by a given regex, the rows matching the regex will be preserved. The regex check will be run on
        a row as a whole and every cell in the checked string will start with the string specified in the sep
        parameter.

        :param regex: The regex pattern that rows will be checked with. If the row matches the regex, it will be
            preserved.
        :param separator: The sep that every cell will start with when joined into a whole string.
        """

        joined_rows = [separator + separator.join(row) for row in self.data]
        filtered_indexes = []
        for index, row in enumerate(joined_rows):
            if re.match(regex, row):
                filtered_indexes.append(index)

        self.data = [self.data[i] for i in filtered_indexes]

    def replace_contents(self, contents: dict):
        """
        Replace individual cell contents.

        Attrs:
            contents: A dict which's keys is the content to replace and which's
                values are the new content.
        """

        for k, v in contents.items():
            for row in self.data:
                for index, cell in enumerate(row):
                    row[index] = cell.replace(k, v)

    def process_arrows(self):
        """
        Cleans up arrow cells.

        Cleans up cells that contain arrows. The cell content will be split
        by the '->' sequence and only the second part of the content will be
        preserved.
        """

        for row in self.data:
            for index, cell in enumerate(row):
                row[index] = cell.split('->', 1)[-1]

    def add_separators(self, by_col: int, sep: str = SEP):
        """
        Add separators to the table. The number of empty cells before a content will be the same
        as the number of empty cells after a content for each cell. Cells will be split like this.

        Example:
              1
            -----

              2

            -----
              3
            -----

        :param by_col: The index of the col the empty space should be counted in.
        :param sep: A string that will be used as the separator
        """

        col = self.get_cols()[by_col]

        # Decide where to put separators
        add = 1  # What will be added to the empty cells counter
        empty = 0  # The empty cells counter
        insert_at = []
        for index, content in enumerate(col):
            if content:
                add = -1
            else:
                empty += add
            if not empty:
                insert_at.append(index + 1)
                add = 1

        # Add separators to the whole table
        row_to_insert = [sep] * self.width
        for index in reversed(insert_at):
            self.data.insert(index, row_to_insert)

    def align_up(self, col_index: int, sep: str = SEP):
        """
        Align the data in the given column as much as possible to the separator upwards.

        :param col_index: The index of the column to align data in.
        :param sep: A string that will be considered as the separator.
        """

        cols = self.get_cols()
        col = cols[col_index]

        for index, content in reversed(list(enumerate(col))[1:]):
            if content == sep:
                continue
            if content and not col[index - 1]:
                col[index - 1] = content
                col[index] = ''

        cols[col_index] = col
        self.set_cols(cols)

    def strip(self):
        """ Remove empty rows and columns. """
        # Rows
        for row in self.data:
            if not ''.join(row):
                self.data.remove(row)

        # Cols
        cols = self.get_cols()
        for col in cols:
            if not ''.join(col):
                cols.remove(col)

        self.set_cols(cols)


class TableScraper(Cog, name='Substitutions'):
    CACHE_SECONDS = 600
    CACHE_KEY = 'substits'

    bot: Marvin
    data: list
    data_date: str  # User will be told the date the data belongs to

    def __init__(self, bot: Marvin):
        self.bot = bot
        self.data = []
        self.data_date = 'Yet to load'

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
        cached = Cache.load(self.CACHE_KEY, self.__class__.CACHE_SECONDS)
        if cached:
            self.data, self.data_date = cached
            logger.info('Retrieved cached data.')
            return

        # Download
        kwargs = RemoteConfig.substits_kwargs
        args = kwargs['login_url'], kwargs['course_url'], kwargs[
            'link_regex'], RemoteConfig.moodle_username, RemoteConfig.moodle_password
        path = await self.bot.loop.run_in_executor(None, download_pdf, *args)

        if not path:
            logger.warning('Path to the downloaded pdf was not returned. Cannot process it further!')
            return

        # Convert
        data = await self.bot.loop.run_in_executor(None, pdf_to_list, path)

        # Clean up
        logger.debug('Preparing data ...')
        table = TableData(data)
        table.extract_table_cols(RemoteConfig.substits_col_indexes)
        table.process_arrows()
        table.replace_contents(RemoteConfig.substits_replace_contents)
        table.filter_rows(r'^#(\d\.[A-Z]|#)')  # We are matching a class notation or an empty cell
        table.add_separators(0)
        table.align_up(0)
        table.filter_rows(f'^#(?!{SEP})')
        table.strip()
        # table.add_headers(RemoteConfig.substits_headers)

        # Save for later use
        self.data = table.data

        # Save date
        filename = os.path.basename(path)
        numbers = os.path.splitext(filename)[0]
        day, month, year = numbers[:2], numbers[2:4], numbers[4:]
        self.data_date = f'{day}. {month}. {datetime.now().year // 100}{year}'

        logger.debug('Done')

        # We are caching the data and the date simultaneously
        # to ensure that they match
        Cache.cache(self.CACHE_KEY, (self.data, self.data_date))

    @command(aliases=['supl', 'suply', 'sub'])
    @del_invoc
    async def substits(self, ctx: Context, target=None):
        """
        Outputs the latest substitutions.

        The last pdf file from the remote-configured course is pulled using the local-config credentials
        and converted to a table. If you wanna get the full substitution list (not a filtered one, as by default),
        type `!substits .` or `!substits all` instead.
        """

        await ctx.trigger_typing()

        # Get target
        if not target:
            target = RemoteConfig.default_substits_target

        # Filter data
        data = deepcopy(self.data)
        if target not in ('all', '.'):
            # Split merged cells
            for index, row in list(enumerate(data))[1:]:
                if not row[0]:
                    data[index][0] = data[index - 1][0]

            # Get the filtered data
            data = [row for index, row in enumerate(self.data) if target in data[index][0]]
        data = transpose(data)

        # Tell, if there are no data matching the filter
        if not data:
            await CommandOutput(ctx, title='**No substitutions!**   (╯°□°）╯︵ ┻━┻').send()
            return

        # Hash in order to look for a cached image
        string = str(data) + target
        bytes_ = string.encode()
        result = sha256(bytes_).hexdigest()
        path = os.path.join(IMG_CACHE_PATH, result + '.png')

        # Look for a cached image
        if not os.path.isfile(path):
            logger.info('Generating new figure ...')

            # Generate if not cached
            os.makedirs(IMG_CACHE_PATH, exist_ok=True)

            # Generate figure
            colors = [[('#2C2F33', '#23272A')[i % 2]] * len(data) for i in range(len(data[0]))]
            colors = transpose(colors)

            # Make text bold
            headers = [f'<b>{i}</b>' for i in RemoteConfig.substits_headers]
            data = [
                [f'<b>{i}</b>' for i in j]
                for j in data
            ]

            # noinspection PyUnresolvedReferences
            fig = go.Figure(
                data=go.Table(
                    header=dict(values=headers, fill=dict(color='#7289DA'),
                                font=dict(color='#FEFEFE')),
                    cells=dict(values=data, fill=dict(color=colors), font=dict(color='#FEFEFE'), line=dict(width=0),
                               height=26)
                )
            )

            # Request image generation
            chart_studio.session.sign_in(RemoteConfig.chart_studio_username, str(RemoteConfig.chart_studio_token))
            img_bytes = chart_studio.plotly.image.get(fig, width=700, height=2000)

            # Open with PIL
            img = Image.open(io.BytesIO(img_bytes))
            img = img.convert("RGBA")

            # Replace white with alpha
            img.putdata(
                [(0, 0, 0, 0) if i == (255, 255, 255, 255) else i for i in img.getdata()]
            )

            # Crop to content
            img = img.crop(img.getbbox())

            # Save
            img.save(path, 'PNG')

        else:
            logger.debug(f'Using cached image {path}')

        # Send header
        await CommandOutput(ctx, wide=True, invoc=False,
                            title=f'The substitution list for the day **{self.data_date}**').send(register=False)

        # Send table
        await ctx.send(file=File(path, filename=f'Substitutions_{self.data_date}.png'))

        # Send footer
        await CommandOutput(ctx, wide=True, author=False, title=f'**{len(data[0])}** entries 👆').send(register=False)


def setup(bot):
    bot.add_cog(TableScraper(bot))
