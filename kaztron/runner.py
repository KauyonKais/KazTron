import asyncio
import enum
import functools
import logging
import random
import sys
from types import MethodType

from discord.ext import commands

import kaztron
from kaztron.config import get_kaztron_config

logger = logging.getLogger("kaztron.bootstrap")


class ErrorCodes:
    OK = 0
    ERROR = 1
    EXTENSION_LOAD = 7
    RETRY_MAX_ATTEMPTS = 8
    CFG_FILE = 17


def patch_smart_quotes_hack(client: commands.Bot):
    """
    Patch to convert smart quotes to ASCII quotes when processing commands in discord.py

    Because iOS by default is stupid and inserts smart quotes, and not everyone configures their
    mobile device to be SSH-friendly. WTF, Apple, way to ruin basic input expectations across your
    *entire* OS.
    """
    old_process_commands = client.process_commands
    conversion_map = {
        '\u00ab': '"',
        '\u00bb': '"',
        '\u2018': '\'',
        '\u2019': '\'',
        '\u201a': '\'',
        '\u201b': '\'',
        '\u201c': '"',
        '\u201d': '"',
        '\u201e': '"',
        '\u201f': '"',
        '\u2039': '\'',
        '\u203a': '\'',
        '\u2042': '"'
    }

    @functools.wraps(client.process_commands)
    async def new_process_commands(self, message, *args, **kwargs):
        for f, r in conversion_map.items():
            message.content = message.content.replace(f, r)
        return await old_process_commands(message, *args, **kwargs)
    client.process_commands = MethodType(new_process_commands, client)


def run(loop: asyncio.AbstractEventLoop):
    config = get_kaztron_config()
    client = commands.Bot(command_prefix='.',
        description='This an automated bot for the /r/worldbuilding discord server',
        pm_help=True)
    patch_smart_quotes_hack(client)

    # Load extensions
    startup_extensions = config.get("core", "extensions")
    client.load_extension("kaztron.cog.core")
    for extension in startup_extensions:
        logger.debug("Loading extension: {}".format(extension))
        # noinspection PyBroadException
        try:
            client.load_extension("kaztron.cog." + extension)
        except Exception:
            logger.exception('Failed to load extension {}'.format(extension))
            sys.exit(ErrorCodes.EXTENSION_LOAD)

    # noinspection PyBroadException
    try:
        loop.run_until_complete(client.login(config.get("discord", "token")))
        loop.run_until_complete(client.connect())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        logger.debug("Waiting for client to close...")
        loop.run_until_complete(client.close())
        logger.info("Client closed.")
        sys.exit(ErrorCodes.OK)
    except:
        logger.exception("Uncaught exception during bot execution")
        logger.debug("Waiting for client to close...")
        loop.run_until_complete(client.close())
        logger.info("Client closed.")

        # Let the external retry reboot the bot - attempt recovery from errors
        # sys.exit(ErrorCodes.ERROR)
        return
    finally:
        logger.debug("Cancelling pending tasks...")
        # BEGIN CONTRIB
        # Modified from code from discord.py.
        #
        # Source: https://github.com/Rapptz/discord.py/blob/
        # 09bd2f4de7cccbd5d33f61e5257e1d4dc96b5caa/discord/client.py#L517
        #
        # Original code Copyright (c) 2015-2016 Rapptz. MIT licence.
        pending = asyncio.Task.all_tasks(loop=loop)
        gathered = asyncio.gather(*pending, loop=loop)
        # noinspection PyBroadException
        try:
            gathered.cancel()
            loop.run_until_complete(gathered)
            gathered.exception()
        except Exception:
            pass
        # END CONTRIB


class Backoff:
    """
    Exponential backoff driver. Doubles retry time every failure.

    :param initial_time: Retry time after first failure.
    :param base: Exponential base. Default 2.0.
    :param max_attempts: Maximum number of attempts before giving up.
    """
    def __init__(self, initial_time=1.0, base=2.0, max_attempts=8):
        self.t0 = initial_time
        self.max = max_attempts
        self.base = base
        self.n = 0
        self.reset()

    def next(self):
        """ Return the next wait time in seconds. Raises a RuntimeError if max attempts exceeded."""
        if self.n < self.max:
            tn = self.t0 * (self.base ** self.n) + (random.randint(0, 1000) / 1000)
            self.n += 1
            return tn
        else:
            raise StopIteration("Maximum attempts exceeded")

    def reset(self):
        """ Reset the number of attempts. """
        self.n = 0
