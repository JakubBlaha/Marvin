import os


DATA_DIR = './data/'


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)