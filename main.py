import customtkinter as ctk
import threading
import time
import os
import sys
import multiprocessing
from PIL import Image, ImageDraw, ImageTk
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
    
    # Try to load a project icon (icon.png) to use as tray icon if available
    proj_root = os.path.abspath(os.path.dirname(__file__))
    icon_png_path = os.path.join(proj_root, 'icon.png')
    _tray_base_icon = None
    if os.path.exists(icon_png_path):
        try:
            _tray_base_icon = Image.open(icon_png_path).convert('RGBA').resize((64, 64))
        except:
            _tray_base_icon = None

    def create_image(text, bg_color):
        # Create a circular colored tray icon and render the glucose value.
        # Titlebar/icon of the main window is set elsewhere and will not change.
        size = (64, 64)
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        dc = ImageDraw.Draw(img)

        # Draw circle background
        try:
            radius = min(size) // 2 - 4
            center = (size[0] // 2, size[1] // 2)
            bbox = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
            dc.ellipse(bbox, fill=bg_color)
        except Exception:
            dc.rectangle([0, 0, size[0], size[1]], fill=bg_color)

        # Draw value text centered
        try:
            txt = str(text)
            # basic font sizing heuristic
            font_size = 28 if len(txt) <= 2 else 20
            try:
                from PIL import ImageFont
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None

            w, h = dc.textsize(txt, font=font)
            text_pos = (center[0] - w // 2, center[1] - h // 2)
            dc.text(text_pos, txt, fill=(255, 255, 255), font=font)
        except Exception:
            pass

        return img

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
            updated = False
            while not glucose_queue.empty():
                item = glucose_queue.get()
                if isinstance(item, tuple):
                    val, color_idx = item
                    # format numeric value
                    try:
                        if val is None:
                            current_val = None
                        else:
                            current_val = int(round(float(val)))
                    except Exception:
                        current_val = str(val)

                    if color_idx == 2:
                        current_color = "#f1c40f"
                    elif color_idx == 3:
                        current_color = "#e74c3c"
                    else:
                        current_color = "#2ecc71"
                else:
                    # unknown payload
                    try:
                        current_val = int(round(float(item)))
                    except Exception:
                        current_val = None
                    current_color = "#2b2b2b"

                updated = True

            # Always refresh the tray icon so it's kept in sync
            display_val = current_val if current_val is not None else "--"
            icon.title = f"LibreView: {display_val} mg/dL"
            try:
                icon.icon = create_image(display_val, current_color)
            except Exception:
                pass
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

        # Set window icon per-platform if an icon is present in project root
        proj_root = os.path.abspath(os.path.dirname(__file__))
        try:
            ico = os.path.join(proj_root, 'icon.ico')
            png = os.path.join(proj_root, 'icon.png')
            # Windows: prefer .ico but fall back to PNG via iconphoto
            if sys.platform == 'win32':
                if os.path.exists(ico):
                    try:
                        self.iconbitmap(ico)
                    except Exception:
                        pass
                elif os.path.exists(png):
                    try:
                        img = ImageTk.PhotoImage(Image.open(png))
                        self.iconphoto(False, img)
                        self._tk_icon_image = img
                    except Exception:
                        pass
            else:
                # Try PNG for Tk window icon (works on Linux and sometimes macOS)
                if os.path.exists(png):
                    try:
                        img = ImageTk.PhotoImage(Image.open(png))
                        self.iconphoto(False, img)
                        # keep a reference to avoid GC
                        self._tk_icon_image = img
                    except Exception:
                        pass

                # On macOS, also attempt to set the Dock icon via AppKit if available
                if sys.platform == 'darwin':
                    icns = os.path.join(proj_root, 'icon.icns')
                    try:
                        if os.path.exists(icns):
                            from AppKit import NSApplication, NSImage
                            ns_app = NSApplication.sharedApplication()
                            ns_img = NSImage.alloc().initWithContentsOfFile_(icns)
                            ns_app.setApplicationIconImage_(ns_img)
                    except Exception:
                        pass
        except Exception:
            pass
        
        ctk.set_default_color_theme("blue")

        self.config = Config()
        # Apply stored appearance mode (light/dark/system)
        try:
            ctk.set_appearance_mode(self.config.appearance_mode or "system")
        except Exception:
            try:
                ctk.set_appearance_mode("system")
            except Exception:
                pass
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
        self.dashboard = DashboardView(self, on_refresh=self._force_refresh, on_logout=self._handle_logout, config=self.config)
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
