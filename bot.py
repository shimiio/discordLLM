import asyncio
import os
import re
import time
import tomllib
from collections import defaultdict
from pathlib import Path

import discord
import ollama
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
DISCORD_LIMIT = 2000  # Discord's maximum message length

load_dotenv(BASE_DIR / ".env")
TOKEN = os.environ["DISCORD_TOKEN"]

with open(BASE_DIR / "config.toml", "rb") as f:
    config = tomllib.load(f)

CHANNEL = config["discord"]["channel"]
RESET_COMMAND = config["discord"]["reset_command"]
RESET_MESSAGE = config["discord"]["reset_message"]
MODEL = config["ollama"]["model"]
prompt_path = BASE_DIR / config["chat"]["prompt_file"]
if not prompt_path.exists():
    print(f"{prompt_path.name} not found, using prompt.example.md")
    prompt_path = BASE_DIR / "prompt.example.md"
SYSTEM_PROMPT = prompt_path.read_text(encoding="utf-8").strip()
HISTORY_LIMIT = config["chat"]["history_limit"]
BATCH_DELAY = config["chat"]["batch_delay"]
STREAM = config["chat"]["stream"]
UPDATE_INTERVAL = config["chat"]["update_interval"]

# Matches a "Bob:" name prefix the model sometimes copies from the chat history.
names = "|".join(re.escape(name) for name in config["chat"]["bot_names"])
NAME_PREFIX = re.compile(rf"^\s*\**({names})\**\s*:\s*\**\s*", re.IGNORECASE)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
llm = ollama.AsyncClient(host=config["ollama"]["host"])

# Separate memory for every channel, keyed by channel id.
histories = defaultdict(list)
# Channels where a batch timer is already running.
waiting = set()
# One answer at a time per channel, so replies don't overlap.
locks = defaultdict(asyncio.Lock)


def clean_reply(text):
    return NAME_PREFIX.sub("", text)


def split_message(text, limit=DISCORD_LIMIT):
    """Split text into parts that fit Discord's limit, preferring line breaks."""
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut <= 0:
            cut = text.rfind(" ", 0, limit)
        if cut <= 0:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts


async def stream_reply(channel, messages):
    """Stream the model's answer into Discord, editing messages as text arrives."""
    sent = []  # Discord messages Bob has sent for this answer
    shown = []  # text currently shown in each of those messages
    text = ""

    async def show():
        for i, part in enumerate(split_message(clean_reply(text))):
            if i < len(sent):
                if shown[i] != part:
                    await sent[i].edit(content=part)
                    shown[i] = part
            else:
                sent.append(await channel.send(part))
                shown.append(part)

    async with channel.typing():
        last_update = time.monotonic()
        stream = await llm.chat(model=MODEL, messages=messages, stream=True)
        async for chunk in stream:
            text += chunk["message"]["content"]
            if STREAM and time.monotonic() - last_update >= UPDATE_INTERVAL:
                await show()
                last_update = time.monotonic()

    await show()
    return clean_reply(text)


@client.event
async def on_ready():
    print(f"Bot launched as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if getattr(message.channel, "name", None) != CHANNEL:
        return

    channel_id = message.channel.id
    history = histories[channel_id]

    if message.content.strip() == RESET_COMMAND:
        history.clear()
        await message.channel.send(RESET_MESSAGE)
        return

    history.append(
        {"role": "user", "content": f"{message.author.display_name}: {message.content}"}
    )

    # The first message starts the timer; messages during the wait just join the batch.
    if channel_id in waiting:
        return
    waiting.add(channel_id)
    async with message.channel.typing():
        await asyncio.sleep(BATCH_DELAY)
    waiting.discard(channel_id)

    async with locks[channel_id]:
        # Nothing new since Bob's last answer.
        if not history or history[-1]["role"] == "assistant":
            return

        # Messages that arrive while Bob is answering go after his reply, into the next batch.
        answered = len(history)
        reply = await stream_reply(
            message.channel,
            [{"role": "system", "content": SYSTEM_PROMPT}, *history[-HISTORY_LIMIT:]],
        )
        history.insert(answered, {"role": "assistant", "content": reply})
        del history[:-HISTORY_LIMIT]


client.run(TOKEN)
