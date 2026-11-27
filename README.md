# Maffiaboss Discord Bot

A modular `discord.py` bot built to simplify *Blood on the Clocktower* script polls.

## Features

* **Script Library:** The bot can store up to 260 scripts along with character sheets.
* **Automated Poll:** Takes stored scripts and generates polls (and splits them if necessary).
* **Modularity:** Additional commands can easily be made in `script/commands/`.

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

4. **Invite your bot to your server:**
    Make sure to uncheck `User Install` inside `Overview > Installation`, as well as adding the `bot` scope under `Default Install Settings > Scopes`.

5. **Start the bot:**
    ```bash
    python script/main.py
    ```
