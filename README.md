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
token: ...              # Discord bot token
guild_id: ...           # The id of the guild the bot will belong to
log_channel_id: ...     # the id of the channel where all logs should be sent to
channel_log_flush_interval: 10  # Max seconds the log content can stay in the buffer
presence: Hello world!  # The text that will be shown as playing a game
status: online          # A string representing an attribute of the discord.Status class

# System
disable_logs: False     # When set to True, all file logging will be disabled

# Command preferences
username: MyUsername01  # moodle3.gvid.cz username
password: Password123   # moodle3.gvid.cz password
table_replacements: {'example': 'ex.'}  # Dict of replacement values to replace the content of the table from the output of the !substits command with
table_headers: ['#', 'Name']  # ... table headers
table_cols: [0, 1]  # ... table cols to be extracted
```
The [moodle](https://moodle3.gvid.cz) credentials are used for the `!supl` command which gives you substitutions for the current/following day depending on the document presence as they are needed to login in the course.


### The Embed excluder
The *Embed excluder* will add the ❌ reaction to any outdated embed found in channels with the 🔔 emoji in their topic.

### The Cleverbot integration
Upon sending a message which *freefbot* is tagged in, the message will be forwarded to *Cleverbot* and a response will be awaited. Upon receiving a response or running into a `TimeoutException` an appropriate text will be sent to the channel.

### The Command panel
The Command panel is a feature, which provides the ability to execute commands more easily. That is done by reaction (clicking the emoji) that is already preset on the Command panel message. The message is an embed with all the emojis described. All messages generated in this channel will be deleted after a 60 seconds period.

*The Command panel is a channel-specific feature, so use it in a dedicated channel only.*

### The Event notifier
The Event notifier will periodically scan each channel having the 🔔 emoji in it's topic every 10 minutes and edit the `general` channel's description so it contains a summary of all of the scanned embeds.

### The remote config
The remote config feature allows to store the bot configuration in a separate discord channel with the name `config`. The last message from the channel will be taken and converted by the `yaml` module. An example content of such a message can be found below.

```yaml
control_panel_channel_id: ...

auto_reactor_channel_ids: [...]
auto_reactor_reaction_ids: [...]

timetable_url: https://www.example.com
```
