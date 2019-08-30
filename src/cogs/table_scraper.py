import logging
import os
import re
from datetime import datetime
from operator import itemgetter
from tempfile import gettempdir
from typing import Optional

import bs4
import requests
import tabula
from discord.ext import tasks
from discord.ext.commands import Cog, Context, command

from cache import Cache
from client import FreefClient
from command_output import CommandOutput
from decorators import del_invoc
from remote_config import RemoteConfig
from utils import ListToImageBuilder

DOWNLOAD_PATH = os.path.abspath(gettempdir() + '/freefbot')

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
    data = tabula.read_pdf(path, 'json')[0]['data']

    return data


def date_from_pdf_name(fname: str) -> str:
    """ Return a date as a str. Example: 010119.ext -> 1. 1. 0019. """
    _date_enc = os.path.splitext(fname)[0]
    day, month, year = _date_enc[:2], _date_enc[2:4], _date_enc[4:]

    return f'{day}. {month}. {datetime.now().year // 100}{year}'


class TableData:
    """
    A provider for lot of useful methods.

    This class contains a lot of useful methods and manages the table data
    internally.
    """

    data: list = []

    def __init__(self, data: list):
        self.data = data

    def get_cols(self) -> list:
        """ Get the data as a list of columns instead as a list of rows. """
        return list(map(list, zip(*self.data)))

    def set_cols(self, cols: list):
        """ Update the table from a ist of columns. """
        self.data = list(map(list, zip(*cols)))

    def extract_table_cols(self, col_indexes: list):
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

    def add_headers(self, headers: list):
        """
        Add headers to the data.

        Adds the given headers do the data. The headers will be inserted at the
        index 0.

        Attrs:
            headers: A list containing the headers. The headers should be of
                the same length as the width of the table is.
        """

        self.data.insert(0, headers)

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

    def v_split_cells(self, col_indexes: list):
        """
        Splits merged cells into individual rows vertically.

        Merged cells are represented by a single cell with a valid content
        surrounded by a non-valid content such as ''. The cells will be split
        only vertically.

        Attrs:
            col_indexes: A list containing the column indexes to be split.
        """

        _data = self.get_cols()

        # Split cols
        for col in [_data[i] for i in col_indexes]:
            _range = 1
            _bases = [(i, c) for i, c in enumerate(col) if c]

            while '' in col:
                for index, cell in _bases:
                    # Ensure in bounds
                    if (index - _range) < 0 or (index + _range) >= len(col):
                        continue

                    # Ensure both sides are empty
                    if col[index - _range] or col[index + _range]:
                        continue

                    col[index + _range] = cell
                    col[index - _range] = cell

                _range += 1

        self.set_cols(_data)

        # Delete columns that would only represent the merged cell
        # Find first col index not present in the list
        _base_col_index = min(
            set(range(max(col_indexes) + 2)) - set(col_indexes))
        for row in self.data:
            if not row[_base_col_index]:
                self.data.remove(row)

    def v_merge_cells(self, up: bool = True):
        """
        Merge all cells with the same data vertically.

        All cells in all columns with the same data will be merged, but only
        vertically. The data will be aligned either up or down.

        Attrs:
            up: Whether the data should be aligned up. If this value is False,
                the data will be aligned down. Default is True (up).
        """

        _data = self.get_cols()

        for col in _data:
            for index in range(*((len(_data) - 1, -1,
                                  -1) if up else (len(_data),))):
                try:
                    if col[index - 1 if up else 1] == col[index]:
                        col[index] = ''
                except IndexError:
                    pass

        self.set_cols(_data)

        # Remove empty rows
        for row in self.data:
            if not ''.join(row):
                self.data.remove(row)


class TableScraper(Cog, name='Substitutions'):
    CACHE_SECONDS = 600
    CACHE_KEY = 'substits'

    bot: FreefClient
    data: list
    data_date: str  # User will be told the date the data belongs to

    def __init__(self, bot: FreefClient):
        self.bot = bot
        self.data = []
        self.data_date = 'Yet to load'

        # Start loop
        self.bot.add_listener(self.on_ready)

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
        table.add_headers(RemoteConfig.substits_headers)
        table.replace_contents(RemoteConfig.substits_replace_contents)
        table.process_arrows()
        table.v_split_cells([0])
        table.v_merge_cells()

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

    @command(aliases=['supl', 'suply'])
    @del_invoc
    async def substits(self, ctx: Context, target=None):
        """
        Outputs the latest substitutions.

        The last pdf file from the remote-configured course is pulled using the local-config credentials
        and converted to a table. If you wanna get the full substitution list (not a filtered one, as by default),
        type `!substits .` or `!substits all` instead.
        """

        await ctx.trigger_typing()

        headers = self.data[:1]
        data = self.data[1:]

        # Get target
        if not target:
            target = RemoteConfig.default_substits_target

        # Filter data
        if target not in ('all', '.'):
            data = list(filter(lambda x: x[0] == target, data))

        # Tell, if there are no data matching the filter
        if not data:
            await CommandOutput(ctx, title='**No substitutions!**   (╯°□°）╯︵ ┻━┻').send()
            return

        # Send header
        await CommandOutput(ctx, wide=True, invoc=False,
                            title=f'The substitution list for the day **{self.data_date}**').send(register=False)

        # Generate, send the images
        builder = ListToImageBuilder(headers + data)
        builder.set_headers_font()

        for img in builder.generate(convert_to_file=True):
            await ctx.send(file=img)

        # Send footer
        await CommandOutput(ctx, wide=True, author=False, title=f'**{len(data)}** entries 👆').send(register=False)


def setup(bot):
    bot.add_cog(TableScraper(bot))
