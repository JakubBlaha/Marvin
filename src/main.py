import click

from client import Marvin
from config import Config
from help import CustomHelpCommand
from exceptions import MarvinInitializeException


def main():
    try:
        client = Marvin(command_prefix=Config.command_prefix, help_command=CustomHelpCommand())
    except MarvinInitializeException:
        click.secho('Marvin could not be initialized and must exit.', fg='red')
        return
    
    client.run(Config.token)


if __name__ == "__main__":
    main()
