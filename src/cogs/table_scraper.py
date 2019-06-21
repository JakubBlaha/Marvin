import io
import os  # , sys
from datetime import datetime
from operator import itemgetter
from tempfile import gettempdir
from typing import Iterable

import mechanize
import tabula
import tabulate
from discord import Embed, File
from discord.ext.commands import Cog, Context, command
from PIL import Image

from command_modules.message_split import split as msg_split
from config import Config
from logger import Logger
from preload import Preloader
from utils.list_to_image import ListToImageBuilder

BASE_URL = 'https://moodle3.gvid.cz/course/view.php?id=3'
DOWNLOAD_PATH = os.path.abspath(gettempdir() + '/freefbot')
MAX_ROWS_IN_PART = 4


def download_pdf(username, password):
    ''' Download the latest pdf file. Return its local path. '''
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
    ''' Read a pdf and return as a table. '''
    Logger.info(f'Command: Reading {path}..')
    data = tabula.read_pdf(path, 'json')[0]['data']

    # fix data
    _cols_to_ext = Config.get('table_cols', [])
    if not _cols_to_ext:
        Logger.warning('Command: No columns to extract!')

    _latest_required_col_index = max(_cols_to_ext)
    for index, row in enumerate(data):
        if len(row) < _latest_required_col_index:
            data.pop(index)
            Logger.warning(f'!supl: Invalid data at index {index}')

    # Filter columns
    data = [[col['text'] for col in itemgetter(*_cols_to_ext)(row)]
            for row in data]

    # ensure headers
    if Config.table_headers and data[0][1].isdigit():
        data.insert(0, Config.table_headers)

    # Replace with custom data
    for key, value in Config.get('table_replacements', {}).items():
        data = [[i.replace(key, value) for i in j] for j in data]

    return data


def process_arrows(data: list) -> list:
    '''
    Cleans up arrow cells.

    Used to clean up cells that contain arrows. The cell content will be split
    by the '->' sequence and only the second part of the content will be
    preserved.

    Args:
        data: A 2D table-like list.

    Returns:
        A 2D table-like list.
    '''

    for row in data:
        for index, cell in enumerate(row):
            row[index] = cell.split('->', 1)[-1]

    return data


def fix_merged_cells(rows: list) -> list:
    ''' Return the data with fixed merged cells. '''
    _root_rows = [
        i + 1 for i in range(len(rows) - 2)
        if rows[i + 1] and not (rows[i][0] or rows[i + 2][0])
    ]

    index_add = 1  # The range of the roots
    while True:
        if '' not in [r[0] for r in rows]:
            # Full
            break
        if index_add > len(rows) / 2:
            break

        for i, row in enumerate(rows):
            if i not in _root_rows:
                # Not expandable
                continue
            if (i - index_add < 0) or (i + index_add >= len(rows)):
                # Out of bounds
                continue
            if rows[i + index_add][0] or rows[i - index_add][0]:
                # Either side is not empty
                continue
            # Expand it
            rows[i + index_add][0] = row[0]
            rows[i - index_add][0] = row[0]

        # Increase the range
        index_add += 1

    # Remove empty rows
    rows = [i for i in rows if i[1]]

    return rows


def extract_target(data, target, with_headers=True):
    ''' Return a table filtered by the first column. Contains. '''
    if target in ('.', 'all'):
        return data

    _new_data = [data[0]] if with_headers else []
    _new_data += filter(lambda x: target in x[0], data)

    return _new_data


def build_section_cells(data: list) -> list:
    for index, row in reversed(list(enumerate(data))):
        if index < 1:
            break

        if row[0] == data[index - 1][0]:
            row[0] = ''

    return data


def date_from_fname(fname: str) -> str:
    ''' Return a date as a str. Example: 010119.ext -> 1. 1. 0019. '''
    _date_enc = os.path.splitext(fname)[0]
    day, month, year = _date_enc[:2], _date_enc[2:4], _date_enc[4:]

    return f'{day}. {month}. {datetime.now().year // 100}{year}'


def get_file(img: Image.Image) -> File:
    _buffer = io.BytesIO()
    img.save(_buffer, 'PNG')
    _buffer.seek(0)

    return File(_buffer, 'img.png')


class TableScraper(Cog):
    _preloader: Preloader

    def __init__(self, bot):
        self._preloader = Preloader(bot.loop, self.preloader_feed,
                                    (Config.username, Config.password))

    def preloader_feed(self, username: str, password: str) -> list:
        ''' The function to run in the preloader. '''
        _local_path = download_pdf(username, password)
        return (_local_path, pdf_to_list(_local_path))

    @command(aliases=['supl', 'suply'])
    async def substits(self, ctx: Context, target='3.F'):
        '''
        Outputs the latest substitutions.
        
        The substitutions are pulled from moodle3.gvid.cz using mechanize,
        logging in with username and password from the config file and clicking
        the last pdf link. Then transformed to text using tabula-py. If you
        want to output all substitutions instead of only the targetted,
        type '.' or 'all' as the target argument.
        '''

        await ctx.trigger_typing()

        _local_path, _data = self._preloader.output
        _fname = os.path.split(_local_path)[1]

        # Generate the table
        _data = process_arrows(_data)
        _data = fix_merged_cells(_data)
        _data = extract_target(_data, target)
        _data = build_section_cells(_data)

        # Generate, send the images
        _builder = ListToImageBuilder(_data, footer=date_from_fname(_fname))
        _builder.set_header()

        # Send chunks
        for img in _builder.generate():
            await ctx.send(file=get_file(img))


def setup(bot):
    bot.add_cog(TableScraper(bot))
