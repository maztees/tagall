"""Tagall - a Telegram bot that mentions every known member of a group
when someone says @everyone or @tagall (or uses the /tagall command).

Telegram's Bot API does not allow bots to fetch a group's full member
list, so this bot remembers members as it sees them: whenever someone
sends a message, joins the group, or appears in the admin list, they
are saved. Anyone who has been active since the bot joined gets tagged.
"""

import asyncio
import html
import logging
import os
import re
import sqlite3

from telegram import Update, User
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TelegramError
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("tagall")

DB_PATH = os.environ.get("TAGALL_DB", "members.db")
ADMINS_ONLY = os.environ.get("TAGALL_ADMINS_ONLY", "").lower() in ("1", "true", "yes")

# "out" (default): members are tagged only after they opt in with /tagme.
# "in": everyone the bot knows is tagged unless they opt out with /untagme.
DEFAULT_OPT_IN = os.environ.get("TAGALL_DEFAULT", "out").lower() in ("in", "1", "true", "yes")

# Telegram only notifies a handful of mentions per message, and groups are
# rate-limited to roughly 20 bot messages per minute, so we tag in batches.
MENTIONS_PER_MESSAGE = 5
DELAY_BETWEEN_MESSAGES = 2.0

TRIGGER = re.compile(r"(?:^|\s)@(?:everyone|tagall)\b", re.IGNORECASE)


# --------------------------------------------------------------------------
# Member storage
# --------------------------------------------------------------------------

def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS members (
            chat_id    INTEGER NOT NULL,
            user_id    INTEGER NOT NULL,
            username   TEXT,
            first_name TEXT,
            opted      INTEGER,
            PRIMARY KEY (chat_id, user_id)
        )
        """
    )
    try:
        conn.execute("ALTER TABLE members ADD COLUMN opted INTEGER")
    except sqlite3.OperationalError:
        pass  # column already exists
    return conn


def remember(chat_id: int, user: User) -> None:
    if user is None or user.is_bot:
        return
    with db() as conn:
        conn.execute(
            """
            INSERT INTO members (chat_id, user_id, username, first_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (chat_id, user_id) DO UPDATE
            SET username = excluded.username, first_name = excluded.first_name
            """,
            (chat_id, user.id, user.username, user.first_name),
        )


def set_opt(chat_id: int, user: User, opted_in: bool) -> None:
    remember(chat_id, user)
    with db() as conn:
        conn.execute(
            "UPDATE members SET opted = ? WHERE chat_id = ? AND user_id = ?",
            (1 if opted_in else 0, chat_id, user.id),
        )


def forget(chat_id: int, user_id: int) -> None:
    with db() as conn:
        conn.execute(
            "DELETE FROM members WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )


def taggable_members(chat_id: int) -> list[tuple[int, str, str]]:
    """Members to mention, honouring each person's opt-in/opt-out choice.

    `opted` is NULL until someone explicitly chooses; those undecided members
    follow the group default (DEFAULT_OPT_IN).
    """
    condition = "(opted = 1 OR opted IS NULL)" if DEFAULT_OPT_IN else "opted = 1"
    with db() as conn:
        rows = conn.execute(
            "SELECT user_id, username, first_name FROM members"
            f" WHERE chat_id = ? AND {condition}",
            (chat_id,),
        ).fetchall()
    return rows


def mention(user_id: int, username: str | None, first_name: str | None) -> str:
    if username:
        return f"@{username}"
    name = html.escape(first_name or "member")
    return f'<a href="tg://user?id={user_id}">{name}</a>'


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remember everyone we can see in any group message."""
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    remember(chat.id, msg.from_user)
    if msg.reply_to_message and msg.reply_to_message.from_user:
        remember(chat.id, msg.reply_to_message.from_user)
    for user in msg.new_chat_members or []:
        remember(chat.id, user)
    if msg.left_chat_member:
        forget(chat.id, msg.left_chat_member.id)


async def on_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Keep the member list in sync with joins, leaves and bans."""
    change = update.chat_member
    if change is None:
        return
    user = change.new_chat_member.user
    status = change.new_chat_member.status
    if status in ("left", "kicked"):
        forget(update.effective_chat.id, user.id)
    else:
        remember(update.effective_chat.id, user)


async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    sender = update.effective_user
    if msg is None or chat is None or sender is None or sender.is_bot:
        return

    if ADMINS_ONLY:
        member = await chat.get_member(sender.id)
        if member.status not in ("administrator", "creator"):
            await msg.reply_text("Only group admins can tag everyone here.")
            return

    # Admins are the one part of the member list bots may fetch directly,
    # so refresh them before tagging.
    try:
        for admin in await chat.get_administrators():
            remember(chat.id, admin.user)
    except TelegramError as exc:
        log.warning("Could not fetch admins for chat %s: %s", chat.id, exc)

    targets = [row for row in taggable_members(chat.id) if row[0] != sender.id]
    if not targets:
        if DEFAULT_OPT_IN:
            await msg.reply_text(
                "I don't know anyone here yet. I learn members as they send "
                "messages, so try again once people have been active."
            )
        else:
            await msg.reply_text(
                "Nobody has opted in to being tagged yet. Members who want "
                "to be included in @everyone should send /tagme."
            )
        return

    # If the trigger was a reply to a shared message, attach the mentions to
    # that message so everyone is pointed at it.
    anchor = msg.reply_to_message or msg
    mentions = [mention(*row) for row in targets]

    for start in range(0, len(mentions), MENTIONS_PER_MESSAGE):
        text = " ".join(mentions[start : start + MENTIONS_PER_MESSAGE])
        if start == 0:
            text = "\N{PUBLIC ADDRESS LOUDSPEAKER} " + text
        while True:
            try:
                await anchor.reply_text(
                    text, parse_mode=ParseMode.HTML, disable_web_page_preview=True
                )
                break
            except RetryAfter as exc:
                await asyncio.sleep(exc.retry_after + 1)
            except TelegramError as exc:
                log.warning("Failed to send mention batch in chat %s: %s", chat.id, exc)
                break
        if start + MENTIONS_PER_MESSAGE < len(mentions):
            await asyncio.sleep(DELAY_BETWEEN_MESSAGES)


async def opt_in(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or user.is_bot:
        return
    set_opt(update.effective_chat.id, user, True)
    await update.effective_message.reply_text(
        f"Done, {user.first_name} — you'll be tagged in @everyone. "
        "Send /untagme any time to opt out."
    )


async def opt_out(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or user.is_bot:
        return
    set_opt(update.effective_chat.id, user, False)
    await update.effective_message.reply_text(
        f"Okay, {user.first_name} — you won't be tagged in @everyone. "
        "Send /tagme any time to opt back in."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    default_note = (
        "Everyone I know is tagged unless they send /untagme."
        if DEFAULT_OPT_IN
        else "Tagging is opt-in: only members who have sent /tagme are tagged."
    )
    await update.effective_message.reply_text(
        "Add me to a group, then say @everyone or @tagall (or use /tagall) "
        "to mention members.\n\n"
        f"{default_note}\n"
        "/tagme — include me in @everyone\n"
        "/untagme — leave me out of @everyone"
    )


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Set the BOT_TOKEN environment variable to the token from @BotFather."
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler(["start", "help"], help_cmd))
    app.add_handler(
        CommandHandler(
            ["tagall", "all", "everyone"], tag_all, filters=filters.ChatType.GROUPS
        )
    )
    app.add_handler(
        CommandHandler(["tagme", "optin"], opt_in, filters=filters.ChatType.GROUPS)
    )
    app.add_handler(
        CommandHandler(["untagme", "optout"], opt_out, filters=filters.ChatType.GROUPS)
    )
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & (filters.Regex(TRIGGER) | filters.CaptionRegex(TRIGGER)),
            tag_all,
        )
    )
    # Runs in a separate handler group so tracking happens on every message,
    # including the ones that trigger a tag.
    app.add_handler(MessageHandler(filters.ChatType.GROUPS, track), group=1)
    app.add_handler(ChatMemberHandler(on_chat_member, ChatMemberHandler.CHAT_MEMBER))

    log.info(
        "Tagall bot starting (default: %s, admins only: %s)",
        "opt-out" if DEFAULT_OPT_IN else "opt-in",
        ADMINS_ONLY,
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
