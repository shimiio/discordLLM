# Bob

A Discord chat bot that runs on a local LLM through [Ollama](https://ollama.com).
Bob lives in one channel, remembers the recent conversation, and talks with a personality
you define in a plain text file.

## Features

- Runs fully locally: no API keys or paid services, only your own GPU.
- Personality lives in a private `prompt.md`, so you can change it without touching code.
- Batches messages: Bob waits a few seconds (showing "typing…") and answers everything
  written in that time with one reply.
- Knows who is talking: each message reaches the model with the sender's name.
- Separate memory for each channel, cleared with `!reset`.
- Splits long answers into several messages to fit Discord's 2000-character limit.
- Optional streaming: the message grows live while the model writes.

## Setup

1. Install [Ollama](https://ollama.com/download) and pull a model:

   ```sh
   ollama pull llama3.1:8b
   ```

2. Create a bot in the [Discord Developer Portal](https://discord.com/developers/applications):
   - On the **Bot** page, turn on **Message Content Intent** and copy the token.
   - On **OAuth2 → URL Generator**, select the `bot` scope with the **Send Messages** and
     **Read Message History** permissions, then open the link to invite the bot to your server.

3. Install the dependencies (Python 3.11 or newer):

   ```sh
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and paste your token into it.

5. Copy `prompt.example.md` to `prompt.md` and describe your own Bob there.
   If you skip this step, Bob uses the example personality.

6. Create a text channel named `bob` on your server, then start the bot:

   ```sh
   python bot.py
   ```

## Configuration

| File | What it holds |
|---|---|
| `.env` | Your Discord token. Never commit it. |
| `config.toml` | Channel name, model, memory size, batch delay, streaming and more. |
| `prompt.md` | Bob's personality: the system prompt sent to the model. Private, not committed. |
| `prompt.example.md` | An example personality to start from. |

Restart the bot after changing any of them.

### Choosing a model

Any Ollama chat model works. Pick one that fits in your GPU's memory, or answers get much
slower. Run `ollama ps` while Bob is answering: `100% GPU` means the model fits.
