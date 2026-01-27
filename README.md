# LibreView Monitor Desktop App

A modern, cross-platform desktop application to track your glucose levels in real-time using the LibreView API. Built with Python, CustomTkinter, and Matplotlib.

![Aesthetics](https://img.shields.io/badge/Aesthetics-Premium-blueviolet)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-blue)

## Features
- **Real-time Monitoring**: Fetches glucose data every 3-5 minutes.
- **Modern UI**: Dark-themed dashboard with color-coded alerts.
- **Historical Graph**: 8-hour glucose trend visualization.
- **Color-Coded Tray Icon**: System tray icon that changes color based on glucose levels.
- **Secure Storage**: Local AES encryption for credentials (no Keychain prompts).
- **macOS Optimized**: Hidden Dock icon for the tray process and native notifications.

---

## 🛠 Installation (Development)

Follow these steps to set up the project locally:

### 1. Prerequisites
- **Python 3.10** or higher installed on your system.

### 2. Clone the Repository
```bash
git clone <repository-url>
cd libre
```

### 3. Set Up Virtual Environment
**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the Application
```bash
python main.py
```

---

## 📦 Building Standalone Executables

If you want to create a standalone application that doesn't require Python to be installed:

### macOS (.app)
1. Ensure you are on a Mac.
2. Run the build script:
   ```bash
   ./build.sh
   ```
3. Find your app in `dist/LibreViewMonitor.app`.

### Windows (.exe)
1. Ensure you are on a Windows machine.
2. Run the batch script:
   ```cmd
   build_win.bat
   ```
3. Find your executable in `dist/LibreViewMonitor/LibreViewMonitor.exe`.

---

## 📝 Usage Notes

- **Login**: Use your **LibreLinkUp** credentials (the same ones you use in the mobile app for sharing data).
- **Tray Icon**:
  - **Green**: Healthy range (70-180 mg/dL).
  - **Yellow**: Elevated levels (>180 mg/dL).
  - **Red**: Low glucose alert (<70 mg/dL).
- **Closing the window**: On macOS, clicking the red "X" will hide the window to the tray. Use "Show Monitor" from the tray icon to bring it back.

---

## 🔒 Security
Your password is encrypted locally using the `cryptography` library. A unique key is generated on your first run and stored in `~/.libreview_monitor.key`. The encrypted credentials are saved in `~/.libreview_monitor.json`.

---

## Credits
API logic inspired by [libreview-monitor](https://github.com/HansKre/libreview-monitor).
