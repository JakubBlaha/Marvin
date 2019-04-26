from datetime import datetime
from tempfile import gettempdir
from operator import itemgetter
from typing import Iterable
import os  #, sys

from discord.ext.commands import Cog, command
import mechanize
import tabula
import tabulate

from preload import Preloader
from config import Config
from logger import Logger
from command_modules.message_split import split as msg_split

BASE_URL = 'https://moodle3.gvid.cz/course/view.php?id=3'
DOWNLOAD_PATH = os.path.abspath(gettempdir() + '/freefbot')


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

    # Remove redundant split cells
    for index, row in reversed(list(enumerate(rows))):
        if index < 1:
            break

        if row[0] == rows[index - 1][0]:
            row[0] = ''

    # Remove empty rows
    rows = [i for i in rows if i[1]]

    return rows


def extract_target(data, target, with_headers=True):
    ''' Return a table filtered by the first column. Contains. '''
    if target == '.':
        return data

    _new_data = [data[0]] if with_headers else []
    _new_data += filter(lambda x: target in x[0], data)

    return _new_data


def get_string(data: Iterable) -> str:
    ''' Return a ready-to-send str made from the table. '''

    if len(data) < 2:
        return "**No substitutions** (╯°□°）╯︵ ┻━┻"
    return f'```fix\n{tabulate.tabulate(data[1:], headers=data[0])}```'


def date_from_fname(fname: str) -> str:
    ''' Return a date as a str. Example: 010119.ext -> 1. 1. 0019. '''
    _date_enc = os.path.splitext(fname)[0]
    day, month, year = _date_enc[:2], _date_enc[2:4], _date_enc[4:]

    return f'{day}. {month}. {datetime.now().year // 100}{year}'


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
    async def substits(self, ctx, target='3.F'):
        '''
        Outputs the latest substitutions.
        
        The substitutions are pulled from moodle3.gvid.cz using mechanize,
        logging in with username and password from the config file and clicking
        the last pdf link. Then transformed to text using tabula-py. If you
        want to output all substitutions instead of only the targetted ones,
        type '.' as the target argument.
        '''

        await ctx.trigger_typing()

        _local_path = self._preloader.output[0]
        _fname = os.path.split(_local_path)[1]

        _data = self._preloader.output[1]
        _data = fix_merged_cells(_data)
        _data = extract_target(_data, target)
        _data = f'**{date_from_fname(_fname)}**' + get_string(_data)

        for chunk in msg_split(_data):
            await ctx.send(chunk)


def setup(bot):
    bot.add_cog(TableScraper(bot))