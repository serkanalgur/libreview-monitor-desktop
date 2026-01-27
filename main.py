import customtkinter as ctk
import threading
import time
import os
import sys
import multiprocessing
from PIL import Image, ImageDraw
import pystray
from plyer import notification
import matplotlib
# Force TkAgg backend for compatibility
matplotlib.use('TkAgg')

from api_client import LibreViewAPI
from config import Config
from login_view import LoginView
from dashboard_view import DashboardView

def tray_process_func(glucose_queue, command_queue, shutdown_event):
    """
    Function to run the tray icon in a separate process.
    This keeps the macOS Cocoa loop isolated from the Tkinter process.
    """
    print(f"Tray process started (PID: {os.getpid()})")
    
    # On macOS, hide the Dock icon for this process to make it feel like one app
    if sys.platform == "darwin":
        try:
            from AppKit import NSApplication, NSApplicationActivationPolicyProhibited, NSApplicationActivationPolicyAccessory
            ns_app = NSApplication.sharedApplication()
            # Policy 2 (Prohibited) hides from Dock and Menu Bar but pystray handles Menu Bar
            # let's try 1 (Accessory) which is for background apps with menu bars
            ns_app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except Exception as e:
            print(f"Failed to hide tray Dock icon: {e}")
            
    current_val = "--"
    current_color = "#2ecc71" # Default green
    
    def create_image(text, bg_color):
        width, height = 64, 64
        image = Image.new('RGB', (width, height), color=bg_color)
        dc = ImageDraw.Draw(image)
        try:
            dc.text((10, 20), text, fill=(255, 255, 255))
        except:
            pass
        return image

    def on_show(icon, item):
        command_queue.put("SHOW")

    def on_quit(icon, item):
        icon.stop()
        command_queue.put("QUIT")
        shutdown_event.set()

    def update_loop(icon):
        nonlocal current_val, current_color
        icon.visible = True
        while not shutdown_event.is_set():
            while not glucose_queue.empty():
                item = glucose_queue.get()
                if isinstance(item, tuple):
                    val, color_idx = item
                    current_val = str(val)
                    if color_idx == 2: current_color = "#f1c40f"
                    elif color_idx == 3: current_color = "#e74c3c"
                    else: current_color = "#2ecc71"
                else:
                    current_val = str(item)
                    current_color = "#2b2b2b"
                
                icon.title = f"LibreView: {current_val} mg/dL"
                icon.icon = create_image(current_val, current_color)
            time.sleep(1)

    menu = pystray.Menu(
        pystray.MenuItem("Show Monitor", on_show),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit)
    )
    
    icon = pystray.Icon("LibreView", create_image("--", "#2b2b2b"), "LibreView", menu)
    
    threading.Thread(target=update_loop, args=(icon,), daemon=True).start()
    icon.run()
    
    # Ensure main process knows we're quitting
    command_queue.put("QUIT")
    print("Tray process ending")

class LibreViewMonitorApp(ctk.CTk):
    def __init__(self, glucose_queue, command_queue):
        super().__init__()
        
        self.glucose_queue = glucose_queue
        self.command_queue = command_queue
        
        self.title("LibreView Monitor")
        self.geometry("600x700")
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.config = Config()
        self.api = LibreViewAPI(region=self.config.region)
        self.api.min_version = self.config.min_version
        
        self.stop_event = threading.Event()
        
        self.protocol("WM_DELETE_WINDOW", self._on_hide_window)
        self._show_initial_view()
        
        # Start command listener
        threading.Thread(target=self._command_listener, daemon=True).start()

    def _command_listener(self):
        while not self.stop_event.is_set():
            try:
                if not self.command_queue.empty():
                    cmd = self.command_queue.get()
                    if cmd == "SHOW":
                        self.after(0, self.show_window)
                    elif cmd == "QUIT":
                        self.after(0, self._on_closing)
            except:
                pass
            time.sleep(0.5)

    def show_window(self):
        self.deiconify()
        self.focus_force()
        self.lift()

    def _on_hide_window(self):
        self.withdraw()

    def _show_initial_view(self):
        password = self.config.get_password()
        if self.config.email and password:
            self._show_dashboard()
            threading.Thread(target=self._monitor_loop, daemon=True).start()
        else:
            self._show_login()

    def _show_login(self):
        if hasattr(self, "dashboard"):
            self.dashboard.destroy()
        self.login = LoginView(self, on_login_success=self._handle_login)
        self.login.pack(fill="both", expand=True)

    def _show_dashboard(self):
        if hasattr(self, "login"):
            self.login.destroy()
        self.dashboard = DashboardView(self, on_refresh=self._force_refresh, on_logout=self._handle_logout)
        self.dashboard.pack(fill="both", expand=True)

    def _handle_login(self, email, password):
        def _login_thread():
            if self.api.login(email, password):
                self.config.email = email
                self.config.set_password(password)
                self.config.region = self.api.region
                self.config.min_version = self.api.min_version
                self.config.save()
                
                self.after(0, self._show_dashboard)
                threading.Thread(target=self._monitor_loop, daemon=True).start()
            else:
                self.after(0, lambda: self.login.show_error("Login failed. Check credentials."))
        
        threading.Thread(target=_login_thread, daemon=True).start()

    def _handle_logout(self):
        self.config.clear()
        self.api = LibreViewAPI()
        self._show_login()

    def _force_refresh(self):
        threading.Thread(target=self._update_data, daemon=True).start()

    def _update_data(self):
        if not self.config.email: return
        
        password = self.config.get_password()
        if not self.api.token:
            if not password or not self.api.login(self.config.email, password):
                return

        data = self.api.fetch_glucose_data()
        if data:
            current = data.get("current", {})
            current_val = current.get("value")
            color_idx = current.get("color", 1)
            
            self.after(0, lambda: self.dashboard.update_data(data))
            
            try:
                self.glucose_queue.put((current_val, color_idx))
            except:
                pass
            
            self._check_alerts(current_val)
            
            if self.api.min_version != self.config.min_version:
                self.config.min_version = self.api.min_version
                self.config.save()

    def _monitor_loop(self):
        while not self.stop_event.is_set():
            self._update_data()
            for _ in range(300):
                if self.stop_event.is_set(): break
                time.sleep(1)

    def _check_alerts(self, val):
        if not val: return
        try:
            if val <= self.config.low_threshold:
                notification.notify(title="CRITICAL LOW", message=f"{val} mg/dL", app_name="LibreView")
            elif val >= self.config.high_threshold:
                notification.notify(title="HIGH ALERT", message=f"{val} mg/dL", app_name="LibreView")
        except:
            pass

    def _on_closing(self):
        self.stop_event.set()
        self.destroy()
        os._exit(0)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    if sys.platform == "darwin":
        multiprocessing.set_start_method('spawn', force=True)
    
    glucose_queue = multiprocessing.Queue()
    command_queue = multiprocessing.Queue()
    shutdown_event = multiprocessing.Event()
    
    tray_p = multiprocessing.Process(
        target=tray_process_func, 
        args=(glucose_queue, command_queue, shutdown_event),
        daemon=True
    )
    tray_p.start()
    
    app = LibreViewMonitorApp(glucose_queue, command_queue)
    try:
        app.mainloop()
    finally:
        shutdown_event.set()
        tray_p.terminate()
