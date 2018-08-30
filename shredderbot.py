#!/usr/bin/env python3
# vim: foldmethod=marker
import os
import re
import logging
import logging.handlers
import sys

import curio
from nettirely import IrcBot, NO_SPLITTING

# Logging {{{
handlers = []

stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(
    logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
)
handlers.append(stream_handler)
del stream_handler

file_handler = logging.handlers.TimedRotatingFileHandler(
    "shredderbot.log", when="D", interval=1, backupCount=7
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("[%(levelname)s @ %(asctime)-15s] %(name)s: %(message)s")
)
handlers.append(file_handler)
del file_handler

# Needed to set the "max level" for the above handlers. If we don't set this to
# DEBUG but for example to INFO, all the handlers are limited to INFO.
logging.basicConfig(handlers=handlers, level=logging.DEBUG)

del handlers
# }}}

bot = IrcBot()


# Autojoin {{{
@bot.on_connect
async def initialize_joins(self):
    self.state.setdefault("channels", [])


@bot.on_command("!join", 1)
async def join(self, _sender, source, channel):
    self.state["channels"].append(channel)
    await self.join_channel(channel)
    await self.send_privmsg(source, f"Joining {channel!r} ...")


# }}}


# Spammer RegExp {{{
@bot.on_connect
async def initialize_spammer_database(self):
    self.state.setdefault("spammer_regexps", [])
    self.state.setdefault("first_messages", {})


@bot.on_command("!addspammer", 1)
async def add_spammer(self, sender, source, spammer_nickname):
    first_spammer_message = self.state["first_messages"][spammer_nickname]
    first_spammer_message = "^" + re.escape(first_spammer_message)

    await self.send_privmsg(
        source, f"Added {first_spammer_message!r} as a RegExp."
    )
    self.state["spammer_regexps"].append(first_spammer_message)


@bot.on_command("!addspamregexp", NO_SPLITTING)
async def add_spam_regexp(self, sender, source, spam_regexp):
    self.state["spammer_regexps"].append(spam_regexp)
    await self.send_privmsg(source, f"Added {spam_regexp!r} as a RegExp.")


@bot.on_command("!removespamregexp", NO_SPLITTING)
async def remove_spam_regexp(self, sender, source, spam_regexp):
    try:
        self.state["spammer_regexps"].remove(spam_regexp)
    except ValueError:
        await self.send_privmsg(
            source, f"Couldn't remove {spam_regexp!r} from the RegExps."
        )
    else:
        await self.send_privmsg(
            source, f"Removed {spam_regexp!r} from the RegExps."
        )


@bot.on_privmsg
async def kick_spammers(self, sender, channel, message):
    for spam_pattern in self.state["spammer_regexps"]:
        if re.search(spam_pattern, message) is not None:
            await self.kick(channel, sender.nick, "spamming detected")
            break


@bot.on_command("!spammer_regexps", NO_SPLITTING)
async def send_spammer_regexps(self, sender, source, _):
    for index, regexp in enumerate(self.state["spammer_regexps"]):
        await self.send_privmsg(source, f"{index + 1}. {regexp!r}")


# }}}


async def main():
    nickname = os.environ.get("IRC_NICKNAME", "shredderbot")
    password = os.environ.get("IRC_PASSWORD")

    await bot.connect(
        nickname, "chat.freenode.net", sasl_password=password, enable_ssl=True
    )

    for channel in bot.state.get("channels", []):
        await bot.join_channel(channel)

    await bot.mainloop()


if __name__ == "__main__":
    curio.run(main)
