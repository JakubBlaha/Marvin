import datetime
import logging
import os
import pickle
import sqlite3
from dataclasses import dataclass

import dateparser
from discord import Message, RawMessageDeleteEvent, RawMessageUpdateEvent
from discord.ext.commands import Cog, Context, group, has_role
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery
from oauthlib.oauth2 import InvalidGrantError

from client import Marvin
from cogs.config import GuildConfig
from decorators import del_invoc
from timeout_message import TimeoutMessage
from utils import UserInput

logger = logging.getLogger('CalendarIntegration')
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

SECRET_FILENAME = 'secret.json'


@dataclass
class Event:
    """
    An abstraction for the google API event json.
    """
    summary: str
    description: str
    start_datetime: datetime.datetime

    def to_dict(self):
        date = self.start_datetime.date().isoformat()

        return {
            'summary': self.summary,
            'description': self.description,
            'start': {
                'date': date
            },
            'end': {
                'date': date
            }
        }


class CalendarIntegration(Cog):
    def __init__(self, bot: Marvin):
        self.bot = bot

        # Check for the secret file
        if not os.path.isfile(SECRET_FILENAME):
            logger.critical('Google API client secret file not found!')
            raise FileNotFoundError(f'Google API client secret file {SECRET_FILENAME} not found!')

        # Connect DB
        self.conn = sqlite3.connect('sqlite.db')
        self.cursor = self.conn.cursor()

        # Create events table
        with self.conn:
            self.cursor.execute('create table if not exists events (message_id INTEGER, event_id TEXT)')

    @group()
    async def calendar(self, ctx: Context):
        """ Google calendar integration commands. """

    @calendar.command()
    @del_invoc
    @has_role('admin')
    async def setup(self, ctx: Context):
        """
        Setup the google calendar integration.

        You will be sent a url to login with your google account. After you do so,
        you will be given a code allowing Marvin to access your calendar. Send the
        code back to Marvin and he will be ready to serve you!
        """

        # Create the flow
        flow = InstalledAppFlow.from_client_secrets_file('secret.json',
                                                         scopes=['https://www.googleapis.com/auth/calendar.events'])
        # noinspection PyProtectedMember
        flow.redirect_uri = InstalledAppFlow._OOB_REDIRECT_URI

        # Ask the user to complete the authorization
        code = await UserInput(ctx).ask('Complete the authorization',
                                        'Please **visit the following url**, grant me permissions to access your '
                                        'calendar events and **gimme the code** displayed at the end of the '
                                        'authorization process.\n'
                                        f'{flow.authorization_url()[0]}')

        if not code:
            await TimeoutMessage(ctx).send('**Authorization process cancelled!**')
            return

        # Get the credentials
        try:
            flow.fetch_token(code=code)
        except InvalidGrantError:
            await TimeoutMessage(ctx).send('**Invalid code. Please run the setup again!**')

        # Store the credentials
        os.makedirs('creds/calendar', exist_ok=True)
        with open(f'creds/calendar/{ctx.guild.id}', 'wb') as f:
            pickle.dump(flow.credentials, f)

    @staticmethod
    def _get_service(guild_id: int):
        """ Get the google calendar service. Raise FileNotFound error if the credentials file is not found. """
        # Get the credentials
        with open(f'creds/calendar/{guild_id}', 'rb') as f:
            creds = pickle.load(f)

        # Create the service
        return discovery.build('calendar', 'v3', credentials=creds)

    @staticmethod
    def _get_event_from_message(msg: Message) -> [None, Event]:
        """ Build an Event instance from a message. """
        # Ignore messages without embeds
        if not msg.embeds:
            return

        emb = msg.embeds[0]
        datetime_ = dateparser.parse(emb.description or '')

        # Ignore messages without datetime
        if not datetime_:
            return

        # Ensure the date is in the future
        if datetime_ < datetime.datetime.now():
            datetime_ = datetime_.replace(year=datetime_.year + 1)

        # Prepare the event details
        description = f'{emb.fields[0].name}\n{emb.fields[0].value}' if emb.fields else None
        return Event(emb.title, description, datetime_)

    @Cog.listener()
    async def on_message(self, msg: Message):
        await self._sync_event(msg)

    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        channel = await self.bot.fetch_channel(payload.data['channel_id'])
        msg = await channel.fetch_message(payload.message_id)

        await self._sync_event(msg)

    async def _sync_event(self, msg: Message):
        """ Create an event in google calendar or update an existing one assigned to the message. """
        if not (event := self._get_event_from_message(msg)):
            return

        # Look in the database for an event id assigned to the message
        self.cursor.execute('SELECT * FROM events WHERE message_id = ?', (msg.id,))
        _, event_id = self.cursor.fetchone() or (None, None)  # message_id, event_id

        calendar_id = GuildConfig.get_by_guild_id(msg.guild.id, 'calendar_id')

        try:
            service = self._get_service(msg.guild.id)
        except FileNotFoundError:
            logger.info(f'Credentials file for the guild {msg.guild.id} not found!')
            return

        if not event_id:
            event = service.events().insert(calendarId=calendar_id, body=event.to_dict()).execute()
            logger.info('Event created: ' + event.get('htmlLink'))

            # Add the event into the database
            with self.conn:
                self.cursor.execute('insert into events values (?, ?)', (msg.id, event['id']))

        else:
            event_data = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            event_data.update(event.to_dict())

            service.events().update(calendarId=calendar_id, eventId=event_id, body=event_data).execute()

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        # Look in the database whether an event for the message already exists
        self.cursor.execute('SELECT * FROM events WHERE message_id = ?', (payload.message_id,))
        _, event_id = self.cursor.fetchone() or (None, None)  # message_id, event_id

        if event_id:
            try:
                service = self._get_service(payload.guild_id)
            except FileNotFoundError:
                logger.info(f'Credentials file for the guild {payload.guild_id} not found!')
                return

            calendar_id = GuildConfig.get_by_guild_id(payload.guild_id, 'calendar_id')
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()


def setup(bot: Marvin):
    cog = CalendarIntegration(bot)
    bot.add_cog(cog)
