# Contributing to Maffia Bot

Thanks for adding commands to the bot! To keep the bot stable and avoid merge conflicts, please follow these rules when contributing:

## Ground Rules
1. **Never push directly to `main`.** Always create a new branch (or fork) for your feature or fix and open a Pull Request.
2. **Add new features as separate files in `script/commands/`.** The bot automatically loads every `.py` file inside `script/commands/` — avoid editing `main.py` unless strictly necessary.
3. **Every command file must have a `setup(bot)` function** at the bottom so `discord.py` can load it as a Cog (See how a new `<your_feature>.py`-file is made by looking in: `script/commands/general.py`).
4. **Never commit secrets or local data.** Do commit `.env`s, API tokens, or any local state files (`scripts.json`, `config.json`, etc.). Use `.gitignore` and put local state data in `data/`.
5. **Test locally before opening a PR.** Make sure the bot starts without errors and your slash commands sync and respond properly (with your own test bot).

## Pull Request Checklist
- [ ] My code is on its own branch (not `main`).
- [ ] My changes are self-contained inside `script/commands/<your_feature>.py`.
- [ ] I tested my commands on a test server without errors.