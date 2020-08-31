from typing import Optional

import json
import logging


STORE_PATH = 'store.json'

logger = logging.getLogger('Store')


class Store:
    command_panel_channel_id: int
    table_url: str

    def load(self) -> bool:
        """ Load stored data. Return whether successful. """
        # Load json
        try:
            with open(STORE_PATH) as f:
                data: dict = json.load(f)
        except FileNotFoundError:
            logger.info(f'{STORE_PATH} not found. Will not load any stored data.')
            return False

        logger.info('Loaded stored data.')
        logger.debug(data)

        # Set attributes
        for key, value in data.items():
            setattr(self, key, value)

        return True

    def save(self):
        # Get data from attributes
        data = {}

        for attr, _ in self.__annotations__.items():
            value = getattr(self, attr, None)
            data[attr] = value

        # Save json
        with open(STORE_PATH, 'w') as f:
            json.dump(data, f, indent=4)
