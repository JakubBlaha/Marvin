import os
import tabula
import tabulate
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from operator import itemgetter

URL = 'https://moodle3.gvid.cz/pluginfile.php/274/mod_forum/attachment/{}/{}'
BASE_URL = 'https://moodle3.gvid.cz/course/view.php?id=3'
DOWNLOAD_PATH = os.path.join(os.path.dirname(__file__), 'downloads/')

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


def pdf_to_string(path: str, target: str = '') -> str:
    data = tabula.read_pdf(path, 'json')[0]['data']
    data = [[col['text'] for col in itemgetter(*COLS)(row)] for row in data]

    # shorten, replace names
    for row in data:
        for index, col in enumerate(row):
            for key, value in TO_REPLACE.items():
                col = col.replace(key, value)
            row[index] = col

    # expand classes
    data = _expand_classes(data)

    # delete empty rows
    data = [row for row in data if row[1]]

    # only target
    if target and target != 'all':
        data = [data[0][1:]
                ] + [row[1:] for row in _extract_target(data[1:], target)]

    # TODO
    # add dots
    # for row in data:
    #     if row[1].isdigit():
    #         row[1] += '.'

    if not data[1:]:
        string = '**Žádné suply** :frowning:'
    else:
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
    # expand classes up and down
    for i, row in enumerate(rows):
        if not row[0]:
            if i != len(rows) - 1:
                row[0] = rows[i + 1][0]
            elif i != 0:
                row[0] = rows[i - 1][0]

    # end condition
    for c in rows:
        if not c:
            rows = _expand_classes(rows)
        else:
            # clean duplicates
            last = None
            for row in rows:
                if row[0] == last:
                    row[0] = ''
                else:
                    last = row[0]

    return rows


def get_pdf_url():
    today = datetime.today()
    return URL.format(17 if today.weekday() % 2 else 14, get_pdf_fname())


def get_pdf_fname():
    today = datetime.today()
    return f'{today.day:02d}{today.month:02d}{today.year % 2000}.pdf'


def wait_for_download(dir_name, interval=.1):
    completed = False
    WAIT_EXTS = ('.tmp', '.crdownload')
    while not completed:
        for fname in os.listdir(dir_name):
            if os.path.splitext(fname)[1] in WAIT_EXTS:
                sleep(interval)
                break
        else:
            completed = True


def download_pdf(username, password, chromedriver_path=''):
    ''' Downloads the last pdf from moodle. Return pdf filename. '''
    # make download dir
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)

    # specify options
    options = Options()
    options.add_experimental_option(
        'prefs', {
            'download.default_directory': DOWNLOAD_PATH,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
        })
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')

    # setup browser
    browser = webdriver.Chrome(chromedriver_path, options=options)
    # browser.get(get_pdf_url())
    browser.get(BASE_URL)

    # get elements
    username_form = browser.find_element_by_id('username')
    password_form = browser.find_element_by_id('password')
    login_btn = browser.find_element_by_id('loginbtn')

    # login
    username_form.send_keys(username)
    password_form.send_keys(password)
    login_btn.click()

    # click first pdf
    link = browser.find_element_by_partial_link_text('.pdf')
    if link.text not in os.listdir(DOWNLOAD_PATH):
        link.click()

    # wait for download
    wait_for_download(DOWNLOAD_PATH)

    return link.text


# main function
def suplovani(target, username, password, chromedriver_path=''):
    ''' Returns suplovani for the current / following day. '''
    fname = download_pdf(username, password, chromedriver_path)

    return pdf_to_string(f'{DOWNLOAD_PATH}/{fname}', target)
