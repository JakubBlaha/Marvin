# freefbot

<img src="https://github.com/JakubBlaha/freefbot/blob/master/res/logo.png?raw=true" alt="logo.png" height=200>

A simple discord bot made for personal purposes in python using [discord.py](https://github.com/Rapptz/discord.py). This bot is focused on school discord servers for students, however can be easily modified for your own purposes.


## Features
**Available commands:**
  - *eval*   - Evaluates a python expression.
  - *repeat* - Repeats the given string.
  - *rozvrh* - Send an image of our timetable.
  - *subj*   - Gives the subjects to prepare for.
  - *supl*   - Outputs the substitutions.
  - *test*   - Outputs exams from the *testy* channel.
  - *ukol*   - Outputs homeworks from the *úkoly* channel.
  - more ..

## Usage
###### the `config.yaml` file
There has to be a `config.yaml` file in the same location as he `client.py` file is. The file has to be formatted as *yaml* and some *yaml-specific* features cant be used becuase of the `yaml.safe_load` function being used. The file must contain credentials as the following example shows.
```yaml
token: TokenGoesHere    # Discord bot token
guild_id: GuildId       # The id of the guild the bot will belong to
username: MyUsername01  # moodle3.gvid.cz username
password: Password123   # moodle3.gvid.cz password
log_channel_id: 123     # the id of the channel where all logs should be sent to
channel_log_flush_interval: 10  # Max seconds the log content can stay in the buffer
presence: Hello world!  # The text that will be shown as playing a game
status: online          # A string representing an attribute of the discord.Status class

# The embed exclusion settings
embed_exclusion_channels: [] # List of channel ids to cehck in
embed_exclusion_check_interval: # The check interval in seconds
embed_exclusion_alert_channel_id: # The channel id to post notifications about outdates embeds to. If omitted, no notifications will be posted
embed_exclusion_alert_role_id: # The id of the role to tag in the notifications

# System
disable_logs: False     # When set to True, all file logging will be disabled
```
The [moodle](https://moodle3.gvid.cz) credentials are used for the `!supl` command which gives you substitutions for the current/following day depending on the document presence as they are needed to login in the course.

There is a feature called `EmbedExcluder` in the bot, which basically reminds you to remove any outdated embeds, that may have a date in their description. The *embed exclusion settings* are used to customize this feature.
