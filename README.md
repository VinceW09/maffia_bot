# Maffiaboss Discord Bot

A modular `discord.py` bot built for our server to automate weekly *Blood on the Clocktower* script polls, event scheduling, and party commands.

## How It Works

The bot automates weekly *Blood on the Clocktower* script selection and session setup:

* **Script Library:** Stores available scripts along with their character sheet images.
* **Automated Multi-Poll Voting:** Splits the script list into chained Discord polls (handling Discord's 10-option limit automatically) and opens a thread with all character sheets.
* **Winner Announcement:** Tallies votes across all active polls and announces the winning script with its character sheet image (or highlights ties).
* **Modular Extensions:** Additional utility and party commands are loaded automatically from `script/commands/`.

## Project Structure

```text
maffiaboss-discord-bot/
├── data/                    # Untracked local data
├── script/
│   ├── main.py              # Bot entry point and automatic Cog loader
│   └── commands/
│       ├── general.py       # Party/Utility commands
│       ├── weekly_poll.py   # Special BOTC Poll feature
|       └── ...              # Feel free to contribute with your own ideas!
├── .env                     # Your bot token (not tracked in Git)
├── .gitignore
├── CONTRIBUTING.md
└── README.md
```

## Running Locally

1. **Clone the repository:**
    ```bash
    git clone https://github.com/VinceW09/maffiaboss-discord-bot.git
    cd maffiaboss-discord-bot
    ```

2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Configure your bot token:**
    Create a `.env` file in the root folder and add your own test bot token from the [Discord Developer Portal](https://discord.com/developers/applications):
    ```env
    TOKEN="your_discord_bot_token_here"
    ```
    *(Make sure **Message Content Intent** and **Server Members Intent** are enabled in the Developer Portal.)*

4. **Invite your bot to your server**
    Inside `Overview > Installation` uncheck `User Install` and under `Default Install Settings > Scopes` add the `bot` scope.
    Then copy the `Discord Provided Link` and choose your discord server. (You must have admin privileges)

5. **Start the bot:**
    ```bash
    python script/main.py
    ```