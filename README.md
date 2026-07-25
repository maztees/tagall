# Tagall

A simple Telegram bot that mentions **all opted-in group members** when someone
says `@everyone` or `@tagall` in a group — public or private.

- Members join the tag list with `/tagme` and leave it with `/untagme` —
  nobody gets tagged unless they chose to.
- Reply to any message and say `@everyone`, and the mentions attach to that
  message, pointing the whole group at it.
- Members without a public @username are tagged with a clickable name link,
  so they still get notified.

**One honest limitation:** Telegram does not let bots download a group's full
member list — no bot can do this, it is a platform rule. Tagall learns members
as they post, join, or send `/tagme`. Someone the bot has never seen cannot be
tagged until they send at least one message.

---

## Set it up — complete walkthrough

Follow these in order. You'll be done in about 10 minutes.

### Part 1 — Create your bot in Telegram

1. Open Telegram and search for **@BotFather** (it has a blue verified badge).
2. Tap **Start**.
3. Send the message: `/newbot`
4. BotFather asks for a **name** — this is the display name people see.
   Example: `Tagall`. Send it.
5. BotFather asks for a **username** — it must be unique and end in `bot`.
   Example: `MyGroupTagBot`. Send it.
6. BotFather replies with a **token** — a long code like
   `1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxx`.
   **Copy it and keep it secret.** Anyone who has it controls your bot.

### Part 2 — Turn off privacy mode (required!)

Still chatting with BotFather:

1. Send: `/setprivacy`
2. Tap your bot's name.
3. Tap **Disable**.

Without this the bot cannot see normal group messages, so `@everyone` would
never work.

### Part 3 — Add the command menu (recommended)

Still in BotFather:

1. Send: `/setcommands`
2. Tap your bot's name.
3. Copy-paste this whole block as one message:

   ```
   tagall - Tag all opted-in members
   tagme - Include me in @everyone
   untagme - Leave me out of @everyone
   help - How this bot works
   ```

Now group members will see these commands pop up whenever they type `/`.

### Part 4 — Get the code onto your computer

You need [Python 3.10 or newer](https://www.python.org/downloads/) —
on Windows, tick **"Add Python to PATH"** during installation.

Then download this project:

- **Easy way:** click the green **Code** button at the top of this GitHub
  page → **Download ZIP** → unzip it anywhere.
- **Git way:**
  ```bash
  git clone https://github.com/maztees/tagall.git
  cd tagall
  ```

### Part 5 — Start the bot

Open a terminal **in the project folder** and run:

**Windows (PowerShell):**
```powershell
pip install -r requirements.txt
$env:BOT_TOKEN = "paste-your-token-here"
python bot.py
```

**Linux / macOS:**
```bash
pip install -r requirements.txt
export BOT_TOKEN="paste-your-token-here"
python bot.py
```

You should see `Tagall bot starting`. Leave this window open — the bot only
works while it is running. (For 24/7 hosting see below.)

### Part 6 — Add the bot to your group

1. Open your group in Telegram.
2. Tap the group name at the top → **Add members** (or **Edit → Members**).
3. Search for your bot's username and add it.
4. Recommended: make it an **admin** (group name → Edit → Administrators →
   Add Administrator). It needs no special rights — admin status just lets it
   track joins and leaves reliably.

### Part 7 — Use it!

1. Everyone who wants to be tagged sends `/tagme` in the group (one time).
2. Anyone can now write `@everyone` or `@tagall` in any message — the bot
   tags all opted-in members (except the person who triggered it).
3. To point everyone at a specific message: **reply** to it and say
   `@everyone` — the mentions attach to that message.
4. Changed your mind? Send `/untagme` and you won't be tagged anymore.

---

## Commands and triggers

| You send | What happens |
|---|---|
| `@everyone` or `@tagall` anywhere in a message | tags all opted-in members |
| `/tagall`, `/all`, `/everyone` | same, as a command |
| reply to a message + `@everyone` | mentions attach to that message |
| `/tagme` (or `/optin`) | include me in future tags |
| `/untagme` (or `/optout`) | stop tagging me |
| `/help` | short explanation in chat |

In groups with several bots, add your bot's username to target it
specifically: `/tagme@MyGroupTagBot`.

## Configuration (optional)

Set these as environment variables before starting the bot:

| Variable | Default | Meaning |
|---|---|---|
| `BOT_TOKEN` | *(required)* | the token from BotFather |
| `TAGALL_DB` | `members.db` | where the SQLite member list is stored |
| `TAGALL_ADMINS_ONLY` | off | `1` = only group admins can trigger a tag |
| `TAGALL_DEFAULT` | `out` | `out` = members must `/tagme` to be tagged; `in` = everyone is tagged unless they `/untagme` |

## Running it 24/7

The bot works only while `python bot.py` is running. For always-on operation,
run it on any small server or spare machine. On Linux with systemd, this repo
includes ready-made files: copy the project to `/root/tagall/`, create
`/root/tagall/.env` containing `BOT_TOKEN=your-token`, then run
`bash deploy/setup.sh` — this installs it as a service that starts on boot
and restarts itself if it crashes.

## Troubleshooting

- **The bot ignores `@everyone` completely** — privacy mode is still on.
  Redo Part 2, then remove the bot from the group and add it back.
- **"Nobody has opted in to being tagged yet"** — working as intended:
  members must send `/tagme` in the group once (Part 7, step 1).
- **Commands don't pop up when typing `/`** — redo Part 3.
- **`Conflict: terminated by other getUpdates request` in the logs** — the
  bot is running twice (e.g. on your PC *and* a server). Stop one copy.
- **Bot stopped responding after closing the terminal** — that's expected;
  the bot runs only while the window is open. See "Running it 24/7".

## License

[MIT](LICENSE) — free to use, modify, and redistribute for any purpose;
just keep the copyright notice with copies.
