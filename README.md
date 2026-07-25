# Tagall

A simple Telegram bot that mentions **all group members** when someone says
`@everyone` or `@tagall` in a group — public or private.

Reply to any message and say `@everyone`, and the bot attaches the mentions to
that message so the whole group is pointed at it.

## How it works (and one important limitation)

Telegram's Bot API **does not let bots download a group's full member list** —
only user accounts can do that. So this bot learns members over time:

- everyone who sends a message is remembered
- everyone who joins or leaves is tracked
- group admins are fetched directly (the one list bots *are* allowed to read)

This means members who have never said anything since the bot joined won't be
tagged until they post at least once. Every popular "tag all" bot works this
way — it is a platform restriction, not a bug.

Mentions are sent in small batches with a short delay to respect Telegram's
rate limits, and members without a public @username are tagged via a
name-link mention so they still get notified.

## Setup

### 1. Create a bot

1. Open [@BotFather](https://t.me/BotFather) in Telegram and send `/newbot`.
2. Pick a name and username; BotFather gives you a **token** — keep it secret.
3. Send `/setprivacy` to BotFather, select your bot, and choose **Disable**.
   This is required so the bot can see normal group messages (to spot
   `@everyone` and to learn who the members are).

### 2. Run the bot

Requires Python 3.10+.

```bash
pip install -r requirements.txt

# Windows (PowerShell)
$env:BOT_TOKEN = "123456:ABC-your-token"
python bot.py

# Linux / macOS
export BOT_TOKEN="123456:ABC-your-token"
python bot.py
```

### 3. Add it to your group

Add the bot to any group. Making it an admin is recommended — admins reliably
receive join/leave updates, which keeps the member list accurate.

## Usage

| Trigger | Effect |
|---|---|
| `@everyone` or `@tagall` anywhere in a message | tags all opted-in members |
| `/tagall`, `/all`, `/everyone` | same, as a command |
| reply to a message + `@everyone` | mentions are attached to that message |
| `/tagme` (or `/optin`) | include me when @everyone is used |
| `/untagme` (or `/optout`) | leave me out of @everyone |

Tagging is **opt-in by default**: only members who have sent `/tagme` in the
group are mentioned, and anyone can leave the list again with `/untagme`.
Group owners who prefer the opposite (everyone tagged unless they opt out)
can run the bot with `TAGALL_DEFAULT=in`.

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `BOT_TOKEN` | *(required)* | token from @BotFather |
| `TAGALL_DB` | `members.db` | path of the SQLite file storing known members |
| `TAGALL_ADMINS_ONLY` | off | set to `1` to let only group admins trigger a tag |
| `TAGALL_DEFAULT` | `out` | `out` = members must `/tagme` to be tagged (opt-in); `in` = everyone is tagged unless they `/untagme` (opt-out) |

The bot must stay running to work — host it on any always-on machine
(a Raspberry Pi, a $5 VPS, a free-tier cloud VM, etc.).

For a Linux server with systemd, `deploy/` has a ready-made unit file and
installer: copy the project to `/root/tagall/`, create `/root/tagall/.env`
containing `BOT_TOKEN=...`, then run `bash deploy/setup.sh`.

## License

Released into the public domain under [The Unlicense](LICENSE).
Use it for anything, no restrictions, no attribution required.
