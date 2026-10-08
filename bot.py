import os

import discord
import ollama

TOKEN = os.environ["DISCORD_TOKEN"]
MODEL = "llama3.1:8b"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
llm = ollama.AsyncClient()

history = []


@client.event
async def on_ready():
    print(f"Bot launched as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if getattr(message.channel, "name", None) != "bob":
        return

    history.append({"role": "user", "content": message.content})

    async with message.channel.typing():
        response = await llm.chat(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Your name is Bob.",
                },
                *history[-20:],
            ],
        )

    reply = response["message"]["content"]
    history.append({"role": "assistant", "content": reply})

    await message.channel.send(reply)


client.run(TOKEN)
