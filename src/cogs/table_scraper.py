import io
import os
from datetime import datetime
from operator import itemgetter
from tempfile import gettempdir
from typing import Iterable

import mechanize
import tabula
from PIL import Image
from discord import Embed, File
from discord.ext.commands import Cog, Context, command

from client import FreefClient
from config import Config
from logger import Logger
from preload import Preloader
from utils import ListToImageBuilder

BASE_URL = 'https://moodle3.gvid.cz/course/view.php?id=3'
DOWNLOAD_PATH = os.path.abspath(gettempdir() + '/freefbot')
MAX_ROWS_IN_PART = 4


def download_pdf(username, password):
    """ Download the latest pdf file. Return its local path. """
    # Make the download directory
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)

    # Setup the browser
    Logger.info('Mechanize: Preparing the browser..')
    br = mechanize.Browser()

    Logger.info('Mechanize: Loading the initial page..')
    br.open(BASE_URL)

    # Fill in the forms
    Logger.info('Mechanize: Filling in the form..')
    br.select_form(nr=0)
    br['username'] = username
    br['password'] = password
    br.submit()

    # Download the pdf
    Logger.info('Mechanize: Downloading the pdf..')
    for link in br.links():
        if '.pdf' in link.text:
            _local_path = os.path.join(DOWNLOAD_PATH, link.text)
            br.retrieve(link.url, _local_path)
            Logger.info(f'Mechanize: The pdf wa downloaded to {_local_path}')
            return _local_path


def pdf_to_list(path: str) -> str:
    """ Read a pdf and return as a table. """
    Logger.info(f'Command: Reading {path}..')
    data = tabula.read_pdf(path, 'json')[0]['data']

    return data


def date_from_fname(fname: str) -> str:
    """ Return a date as a str. Example: 010119.ext -> 1. 1. 0019. """
    _date_enc = os.path.splitext(fname)[0]
    day, month, year = _date_enc[:2], _date_enc[2:4], _date_enc[4:]

    return f'{day}. {month}. {datetime.now().year // 100}{year}'


def get_file(img: Image.Image) -> File:
    _buffer = io.BytesIO()
    img.save(_buffer, 'PNG')
    _buffer.seek(0)

    return File(_buffer, 'img.png')


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


class TableScraper(Cog):
    bot: FreefClient
    _preloader: Preloader

    def __init__(self, bot: FreefClient):
        self.bot = bot
        self._preloader = Preloader(bot.loop, self.preloader_feed,
                                    (Config.username, Config.password))

    @staticmethod
    def preloader_feed(username: str, password: str) -> Iterable:
        """ The function to run in the preloader. """
        _local_path = download_pdf(username, password)
        return _local_path, pdf_to_list(_local_path)

    @command(aliases=['supl', 'suply'])
    async def substits(self, ctx: Context, target='3.F'):
        """
        Outputs the latest substitutions.

        The substitutions are pulled from moodle3.gvid.cz using mechanize,
        logging in with username and password from the config file and clicking
        the last pdf link. Then transformed to text using tabula-py. If you
        want to output all substitutions instead of only the targeted,
        type '.' or 'all' as the target argument.
        """

        await ctx.trigger_typing()

        _local_path, _data = self._preloader.output
        _fname = os.path.split(_local_path)[1]

        # Process the data
        _table = TableData(_data)
        _table.extract_table_cols(self.bot['substits_col_indexes'] or [])
        _table.add_headers(self.bot['substits_headers'] or [])
        _table.replace_contents(self.bot['substits_replace_contents'] or {})
        _table.process_arrows()
        _table.v_split_cells([0])
        _table.v_merge_cells()

        _headers = _table.data[:1]
        _data = _table.data[1:]

        _embed = Embed()

        # Filter data
        if target not in ('all', '.'):
            _data = list(filter(lambda x: x[0] == target, _data))

        # Embed
        if not _data:
            _embed.title = '**No substitutions!**   (╯°□°）╯︵ ┻━┻'

        _embed.description = f'{ctx.author.display_name}, `{ctx.message.content}`'
        await ctx.send(embed=_embed)

        if not _data:
            return

        # Generate, send the images
        _builder = ListToImageBuilder(_headers + _data,
                                      footer=date_from_fname(_fname))
        _builder.set_header()

        # Send chunks
        for img in _builder.generate():
            await ctx.send(file=get_file(img))


def setup(bot):
    bot.add_cog(TableScraper(bot))
