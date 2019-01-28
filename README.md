# freefbot

<img src="https://github.com/JakubBlaha/freefbot/blob/master/res/logo.png?raw=true" alt="logo.png" height=200>

A simple personal discord bot made for our class in python using [discord.py](https://github.com/Rapptz/discord.py).

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
username: MyUsername01  # moodle3.gvid.cz username
password: Password123   # moodle3.gvid.cz password
```
The [moodle](https://moodle3.gvid.cz) credentials are used for the `!supl` command which gives you substitutions for the current/following day depending on the document presence as they are needed to login in the course.
