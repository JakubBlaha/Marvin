# freefbot

<img src="https://github.com/JakubBlaha/freefbot/blob/master/res/logo.png?raw=true" alt="logo.png" height=200>

A simple discord bot made for personal purposes in python using [discord.py](https://github.com/Rapptz/discord.py). This bot is focused on school discord servers for students, however can be easily modified for your own purposes.


## Features
**Available commands:**
  - *eval*     - Evaluates a python expression.
  - *repeat*   - Repeats the given string.
  - *table*    - Sends the timetable.
  - *subj*     - Outputs the subjects for this / the next day.
  - *substits* - Outputs the substitutions.
  - *test*     - Outputs exams from the *testy* channel.
  - *ukol*     - Outputs homeworks from the *úkoly* channel.
  - more ..

## Usage
There needs to be a `src/config.yaml` file with some critical information.
```yaml
token: ...
guild_id: ...
presence: Hello world!  # The text that will be shown as playing a game
status: online          # A string representing an attribute of the discord.Status class

# Logging
disable_logs: False
log_channel_id: ...
channel_log_flush_interval: 10

# Command specific
username: ...           # moodle username
password: ...           # moodle password
```

### The remote config
The remote config feature allows to store the bot configuration in a separate discord channel with the name `config`. The last message from the channel will be taken and parsed by the `yaml` module. An example content of such a message can be found below.

```yaml
# The Control Panel
control_panel_channel_id: ...

# The auto Reactor
auto_reactor_channel_ids: [...]
auto_reactor_reaction_ids: [...]

# The !table command
timetable_url: https://www.example.com

# The !substits command
substits_col_indexes: [...]       # Considered columns
substits_headers: [...]           # Custom table headers
substits_replace_contents: {...}  # Pairs of original -> replaced keywords in the table
```

### The embed builder
The bot contains an embed builder which can build new and edit existing embeds in a user-friendly way. Only few commands and message reactions are used in the process.

**Commands**
  - `new` - The bot will kindly ask for the required information and build an embed based on the information provided.
  - `edit` - A group of subcommands used to edit an existing embed. The syntax of the subcommand is `!embed edit [embed index] [subcommand] [value]`. An embed index has to be passed right before any of the subcommand. The index is counted from *0* and includes only the embeds, but no messages containing no embeds. `title`, `url`, `description`, `color`, `footer` and `fields` subcommands are available.
  
    All of the subcommands require an actual value to be passed after the subcommand as already stated, *except* the `fields` subcommand, which will guide you through the process.

    The following actions are available during the field editing.

    Reaction | Action
    ---------|-------
    ➕ | Add field
    ✏ | Edit field
    ➖ | Remove field
    ↩ | Undo
    ↪ | Redo
    ✅ | Save


**Examples**
> Editing the title of the *most recent* embed title to `My awesome title`.
```
!embed edit 0 title My awesome title
```
> Editing the embed fields of the *second most recent* embed.
```
!embed edit 1 fields
```
We can also use aliases for the subcommands. For example `t` will become `title`, `d` `description`, etc. Note that the alias for the `footer` subcommand is `foo` and not `f`, since that one is for `fields`. A full list of aliases can be retrieved by either of these commands.
```
!help embed edit
!embed edit
```

### The Embed excluder
The *Embed excluder* will add the ❌ reaction to any outdated embed found in channels with the 🔔 emoji in their topic.

### The Cleverbot integration
Upon sending a message which *freefbot* is tagged in, the message will be forwarded to *Cleverbot* and a response will be awaited. Upon receiving a response or running into a `TimeoutException` an appropriate text will be sent to the channel. Cleverbot will not be initialized until requested, therefore the first message may take a while to process.

### The Command panel
The Command panel is a feature, which provides the ability to execute commands more easily. That is done by reaction (clicking the emoji) that is already preset on the Command panel message. The message is an embed with all the emojis described. All messages generated in this channel will be deleted after a 60 seconds period.

*The Command panel is a channel-specific feature, so use it in a dedicated channel only.*

### The Event notifier
The Event notifier will periodically scan each channel having the 🔔 emoji in it's topic every 10 minutes and edit the `general` channel's description so it contains a summary of all of the scanned embeds.

### The `!substits` command
The table scraper is a sort of a personal feature, but can be easily modified if needed. The scraper downloads a pdf file from moodle, extracts a table from it and sends the data as a set of constructed images. All of the configuration but the *username* and *password*, which are stored in the *local config*, are stored in the *remote config*.

### The Twitch Client
The twitch client watches for messages with emote names in them and replaces them with their actual images using discord embeds. If the emoji names is the only content of the message, the message will be deleted.