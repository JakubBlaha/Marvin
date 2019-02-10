import os, sys
import tabula
import tabulate
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from operator import itemgetter
from tempfile import gettempdir

sys.path.insert(0, os.path.abspath(
    os.path.join(__file__, os.pardir, os.pardir)))
from logger import Logger

BASE_URL = 'https://moodle3.gvid.cz/course/view.php?id=3'
DOWNLOAD_PATH = os.path.abspath(gettempdir() + '/freefbot')

# Selenium
EXPERIMENTAL_OPTIONS = ('prefs', {
    'download.default_directory': DOWNLOAD_PATH,
    'download.prompt_for_download': False,
    'download.directory_upgrade': True,
})
OPTIONS = ('--headless', '--disable-gpu')

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

    # ensure headers
    if row[0] != HEADERS:
        data.insert(0, HEADERS)

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


def _expand_classes(rows):
    ''' Expands classes to other rows. `rows` is list. Return expanded. '''

    able_rows = [
        i + 1 for i in range(len(rows) - 2)
        if rows[i + 1] and not(rows[i][0] or rows[i + 2][0])
    ]

    index_add = 1
    while True:
        # exit condition
        for row in rows:
            if not row[0] and index_add < len(rows):
                break
        else:
            # exit
            break

        # expand rows[0]
        for i, row in enumerate(rows):
            if i in able_rows:
                if rows[i + index_add][0]:
                    continue
                if rows[i - index_add][0]:
                    continue
                rows[i + index_add][0] = row[0]
                rows[i - index_add][0] = row[0]

        index_add += 1

    return rows


def wait_for_download(path, interval=.1):
    ''' Wait for file to be created. Return the file path. '''
    while not os.path.isfile(path):
        sleep(interval)

    return path


def download_pdf(username, password, chromedriver_path=''):
    ''' Downloads the last pdf from moodle. Return the pdf filename. '''
    # make download dir
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)

    # specify options
    Logger.info('Selenium: Generating options..\nExperimental options: '
                f'{EXPERIMENTAL_OPTIONS}\nOptions: {OPTIONS}')
    options = Options()
    options.add_experimental_option(*EXPERIMENTAL_OPTIONS)
    for opt in OPTIONS:
        options.add_argument(opt)

    # setup browser
    Logger.info('Selenium: Initializing browser..')
    Logger.info(f'Selenium: Chromedriver path: {chromedriver_path}')
    browser = webdriver.Chrome(chromedriver_path, options=options)

    # Load page
    Logger.info(f'Selenium: Loading initial page.. {BASE_URL}')
    browser.get(BASE_URL)

    # get elements
    Logger.info(f'Selenium: Getting page elements..')
    username_form = browser.find_element_by_id('username')
    password_form = browser.find_element_by_id('password')
    login_btn = browser.find_element_by_id('loginbtn')

    # login
    Logger.info(f'Selenium: Logging in..')
    username_form.send_keys(username)
    password_form.send_keys(password)
    login_btn.click()

    # setup download
    browser.command_executor._commands["send_command"] = (
        "POST", '/session/$sessionId/chromium/send_command')
    params = {
        'cmd': 'Page.setDownloadBehavior',
        'params': {
            'behavior': 'allow',
            'downloadPath': DOWNLOAD_PATH
        }
    }
    browser.execute("send_command", params)

    # click first pdf
    Logger.info('Selenium: Finding the last posted pdf..')
    link = browser.find_element_by_partial_link_text('.pdf')
    Logger.info(f'Selenium: Found link with href {link.get_attribute("href")}')
    if link.text not in os.listdir(DOWNLOAD_PATH):
        link.click()

    # wait for download
    Logger.info(f'Selenium: Waiting for {link.text} to download..')
    ret = wait_for_download(os.path.join(DOWNLOAD_PATH, link.text))
    Logger.info(f'Command: Found {ret}')

    return link.text


# main function
def suplovani(target, username, password, chromedriver_path=''):
    ''' Returns suplovani for the current / following day. '''
    fname = download_pdf(username, password, chromedriver_path)

    return pdf_to_string(f'{DOWNLOAD_PATH}/{fname}', target)
