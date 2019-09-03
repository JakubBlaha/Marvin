import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from discord.ext.commands import Cog, command, Context

from config import Config
from timeout_message import TimeoutMessage

password = Config.token.encode()
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=b'Marvin',
    iterations=100000,
    backend=default_backend()
)
key = base64.urlsafe_b64encode(kdf.derive(password))
fernet = Fernet(key)


def encrypt(string: str) -> str:
    """ Return string encrypted by the API key. """
    return fernet.encrypt(string.encode()).decode()


def decrypt(string: str) -> str:
    """ Return string decrypted by yhe API key. """
    return fernet.decrypt(string.encode()).decode()


class EncryptedString(str):
    def __new__(cls, content):
        return super().__new__(cls, decrypt(content))


class SecurityCog(Cog):
    @command(hidden=True)
    async def encrypt(self, ctx: Context, *, string: str):
        """
        Encrypt sensitive data so it can be placed publicly in the `#config` channel. Use **only in the DM channel** to
        prevent anyone from stealing your credentials.
        """
        # We need to delete the message as soon as possible, therefore we are not using @del_invoc, which would
        # delete the message after the command execution and deleting the message directly
        if ctx.guild:
            await ctx.message.delete()

        encrypted = encrypt(string)

        await TimeoutMessage(ctx, 10).send(
            f'✅ **Here is you encrypted data. Place it in the corresponding config entry:**\n{encrypted}')


def setup(bot):
    bot.add_cog(SecurityCog())
