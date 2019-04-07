import os, sys
import tabula
import tabulate
from operator import itemgetter
from tempfile import gettempdir
import mechanize

sys.path.insert(0, os.path.abspath(os.path.join(__file__, os.pardir,
                                                os.pardir)))
from logger import Logger

BASE_URL = 'https://moodle3.gvid.cz/course/view.php?id=3'
DOWNLOAD_PATH = os.path.abspath(gettempdir() + '/freefbot')

# Table
COLS = (0, 1, 3, 4, 5)
TO_REPLACE = {
    # degrees
    'Mgr.': '',
    ', Ph.D.': '',
    'Dr.': '',
    # names
    'Šatný': 'Peťa',
    'Kopečková': 'Kopec',
    'Doležal': 'Doly',
    # head
    'Hodina': 'H.',
    # other
    '->': '>',
    'Odpadlo': 'odp.'
}
MAX_COL = max(COLS)
HEADERS = ['Třída', 'Hodina', 'Předmět', 'Kdo supluje', 'Učebna']


def pdf_to_string(path: str, target: str = '') -> str:
    # read pdf
    Logger.info(f'Command: Reading {path}..')
    data = tabula.read_pdf(path, 'json')[0]['data']

    # fix data
    for index, row in enumerate(data):
        if MAX_COL > len(row):
            data.pop(index)
            Logger.warning(f'!supl: Invalid data at index {index}')

    data = [[col['text'] for col in itemgetter(*COLS)(row)] for row in data]

    # ensure headers
    if data[0][1].isdigit():
        data.insert(0, HEADERS)

    # shorten, replace names
    Logger.info('Command: Replacing strings..')
    for row in data:
        for index, col in enumerate(row):
            for key, value in TO_REPLACE.items():
                col = col.replace(key, value)
            row[index] = col

    # expand classes
    Logger.info('Command: Trying to match classes..')
    data = _expand_classes(data)

    # remove redundant
    _last = None
    for row in data:
        if row[0] == _last:
            row[0] = ''
        else:
            _last = row[0]

    # delete empty rows
    Logger.info('Command: Deleting empty rows..')
    data = [row for row in data if row[1]]

    # only target
    if target and target != 'all':
        Logger.info(f'Command: Extracting {target} substitutions..')
        data = [data[0][1:]
                ] + [row[1:] for row in _extract_target(data[1:], target)]

    if not data[1:]:
        Logger.info('Command: No matching substitutions found')
        string = '**Žádné suply** :frowning:'
    else:
        Logger.info('Command: Found substitutions')
        string = f'```fix\n{tabulate.tabulate(data[1:], headers=data[0])}```'
    return string


def _extract_target(data, target):
    on_target = False
    new_data = []
    for row in data:
        if target in row[0]:
            on_target = True
        elif row[0]:
            on_target = False

        if on_target:
            new_data.append(row)

    return new_data


def _expand_classes(rows: list) -> list:
    ''' Expands classes to other rows. Return expanded. '''

    # Get rows which's [0] has a value and the rows next to it don't
    # "Able" stands for "expandable"
    # for example:
    #  | - - - - |
    #  | A - - - | <- able row
    #  | - - - - |
    able_rows = [
        i + 1 for i in range(len(rows) - 2)
        if rows[i + 1] and not (rows[i][0] or rows[i + 2][0])
    ]

    index_add = 1  # The range that the able row can reach to
    while True:
        if '' not in [r[0] for r in rows]:
            # Full
            break
        if index_add > len(rows) / 2:
            break

        for i, row in enumerate(rows):
            if i not in able_rows:
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

    return rows


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


def substitutions(target, username, password):
    ''' Return substitutions for the current / following day. '''
    _local_path = download_pdf(username, password)

    # extract date
    _date_enc = os.path.splitext(os.path.split(_local_path)[1])[0]
    day, month, year = _date_enc[:2], _date_enc[2:4], _date_enc[4:]

    # get table
    s = pdf_to_string(_local_path, target)

    # join date and table
    return f'*{day}. {month}. 20{year}*\n' + s


if __name__ == "__main__":
    download_pdf('', '')
