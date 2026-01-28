import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime

class DashboardView(ctk.CTkFrame):
    def __init__(self, master, on_refresh, on_logout, config=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_refresh = on_refresh
        self.on_logout = on_logout
        self.config = config

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabview: Monitor and Settings
        self.tabview = ctk.CTkTabview(self)
        self.tabview.add("Monitor")
        self.tabview.add("Settings")
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        # Monitor container
        self.monitor_frame = self.tabview.tab("Monitor")
        self.monitor_frame.grid_columnconfigure(0, weight=1)
        self.monitor_frame.grid_rowconfigure(1, weight=1)

        # Upper Header (inside monitor tab)
        self.header_frame = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        # col0: title, col1: spacer, col2: logout
        self.header_frame.grid_columnconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(self.header_frame, text="Current Glucose", font=ctk.CTkFont(size=16))
        self.title_label.grid(row=0, column=0, sticky="w")

        self.logout_button = ctk.CTkButton(self.header_frame, text="Logout", width=90, height=24,
                                           fg_color="transparent", border_width=1, command=self.on_logout)
        self.logout_button.grid(row=0, column=2, sticky="e", padx=(12,0))
        
        # Value Display
        self.value_frame = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        self.value_frame.grid(row=1, column=0, sticky="nsew", padx=20)
        self.value_frame.grid_columnconfigure(0, weight=1)
        
        # Fonts: allow dynamic resizing so the trend arrow remains visible
        self._glucose_font_base = 120
        self._trend_font_base = 48
        self.glucose_label = ctk.CTkLabel(self.value_frame, text="--", font=ctk.CTkFont(size=self._glucose_font_base, weight="bold"))
        self.glucose_label.grid(row=0, column=0, pady=(12, 6))

        self.trend_label = ctk.CTkLabel(self.value_frame, text="", font=ctk.CTkFont(size=self._trend_font_base))
        self.trend_label.grid(row=1, column=0, pady=(0, 12))
        
        self.time_label = ctk.CTkLabel(self.value_frame, text="Last updated: Never", font=ctk.CTkFont(size=12))
        self.time_label.grid(row=2, column=0)

        # Graph Area
        # Try to add rounded corners to the graph area when supported by CTk
        try:
            self.graph_frame = ctk.CTkFrame(self.monitor_frame, corner_radius=10)
        except Exception:
            self.graph_frame = ctk.CTkFrame(self.monitor_frame)
        self.graph_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=20)
        self.graph_frame.grid_columnconfigure(0, weight=1)
        self.graph_frame.grid_rowconfigure(0, weight=1)
        
        self.fig, self.ax = plt.subplots(figsize=(6, 3), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b') # Matches CTK dark mode
        self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='white')
        for spine in self.ax.spines.values():
            spine.set_color('white')
            
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        # inset the canvas so rounded corners of the CTkFrame are visible
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        # initialize graph frame background to match figure
        try:
            rgba = self.fig.get_facecolor()
            if isinstance(rgba, (tuple, list)) and len(rgba) >= 3:
                r, g, b = rgba[0], rgba[1], rgba[2]
                hexc = '#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255))
            else:
                hexc = None
            if hexc:
                try:
                    self.graph_frame.configure(fg_color=hexc)
                except Exception:
                    pass
                try:
                    self.canvas.get_tk_widget().configure(bg=hexc)
                except Exception:
                    pass
        except Exception:
            pass
        
        # Status Bar
        self.status_bar = ctk.CTkLabel(self.monitor_frame, text="Ready", font=ctk.CTkFont(size=10))
        self.status_bar.grid(row=3, column=0, sticky="ew", padx=20, pady=5)

        # Settings tab UI
        self._build_settings_tab()
        # Keep last graph points so we can redraw after theme changes
        self._last_graph_points = []
        # Apply initial widget theme (logout button styling etc.)
        try:
            self._apply_widget_theme()
        except Exception:
            pass

    def update_data(self, glucose_data):
        if not glucose_data:
            return
            
        current = glucose_data.get("current", {})
        val = current.get("value")
        trend = current.get("trend")
        color_idx = current.get("color", 1) # 1: Green, 2: Yellow, 3: Red etc.
        
        # Trend arrows mapping
        trends = {
            1: "↓", # Falling quickly
            2: "↘", # Falling
            3: "→", # Stable
            4: "↗", # Rising
            5: "↑", # Rising quickly
        }
        arrow = trends.get(trend, "")
        
        # Color mapping (theme-aware)
        appearance = 'system'
        try:
            appearance = ctk.get_appearance_mode() or 'system'
        except Exception:
            appearance = 'system'

        if appearance.lower() == 'light':
            # darker, more viewable colors on light backgrounds
            color_map = {
                1: '#00796b', # higher-contrast teal for light backgrounds
                2: '#b8860b', # goldenrod/yellow
                3: '#c0392b', # slightly darker red
            }
            text_color = 'black'
        else:
            color_map = {1: '#2ecc71', 2: '#f1c40f', 3: '#e74c3c'}
            text_color = 'white'

        color = color_map.get(color_idx, color_map[1])

        # Adjust glucose font size to avoid overlapping the trend arrow
        try:
            txt = str(val)
            ln = len(txt)
            if ln <= 2:
                size = self._glucose_font_base
            elif ln == 3:
                size = int(self._glucose_font_base * 0.75)
            else:
                size = int(self._glucose_font_base * 0.55)
        except Exception:
            size = self._glucose_font_base

        try:
            self.glucose_label.configure(text=f"{val}", text_color=color, font=ctk.CTkFont(size=size, weight="bold"))
        except Exception:
            try:
                self.glucose_label.configure(text=f"{val}", text_color=color)
            except Exception:
                pass

        try:
            self.trend_label.configure(text=arrow, text_color=text_color, font=ctk.CTkFont(size=int(self._trend_font_base * 0.9)))
        except Exception:
            try:
                self.trend_label.configure(text=arrow, text_color=text_color)
            except Exception:
                pass
        self.time_label.configure(text=f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        
        graph_payload = glucose_data.get("graph", [])
        # store latest graph payload for redraws when theme changes
        try:
            self._last_graph_points = graph_payload or []
        except Exception:
            self._last_graph_points = []
        # (debug prints removed)

        self._update_graph(graph_payload)
        self.status_bar.configure(text="Data updated successfully")

    def _update_graph(self, graph_points):
        self.ax.clear()
        # theme-aware background colors
        appearance = "system"
        try:
            appearance = ctk.get_appearance_mode() or 'system'
        except Exception:
            appearance = 'system'

        eff_app = appearance.lower()
        # treat 'system' as 'dark' to avoid automatic white backgrounds
        if eff_app == 'system':
            eff_app = 'dark'

        if eff_app == 'light':
            bg_color = '#f3f3f5'  # slightly off-white to avoid full white
            fg_color = 'black'
            line_color = '#1f77b4'
        else:
            bg_color = '#2b2b2b'
            fg_color = 'white'
            line_color = '#3498db'

        # Apply figure and axes background and sync frame/canvas
        try:
            self.fig.patch.set_facecolor(bg_color)
        except Exception:
            pass
        self.ax.set_facecolor(bg_color)

        try:
            self._sync_graph_bg(bg_color)
        except Exception:
            pass

        # Apply tick and spine colors so styling is correct even when there's no data
        try:
            self.ax.tick_params(colors=fg_color)
        except Exception:
            pass
        for spine in self.ax.spines.values():
            try:
                spine.set_color(fg_color)
            except Exception:
                pass

        if not graph_points:
            self.canvas.draw()
            return
            
        times = []
        values = []
        for p in graph_points:
            # accept multiple key variants depending on API payload
            ts_raw = p.get("Timestamp") or p.get("timestamp") or p.get("FactoryTimestamp")
            # prefer mg/dL value when available
            val_raw = p.get("ValueInMgPerDl") or p.get("Value") or p.get("value")
            if not ts_raw or val_raw is None:
                continue

            ts_str = str(ts_raw).strip()
            dt = None
            # Try a list of known timestamp formats
            tried = []
            try:
                # ISO style first
                ts_iso = ts_str.split('.')[0].rstrip('Z')
                dt = datetime.fromisoformat(ts_iso)
            except Exception:
                tried.append('iso')

            if dt is None:
                # Common US format like: 1/27/2026 11:48:33 PM
                fmts = [
                    '%m/%d/%Y %I:%M:%S %p',
                    '%m/%d/%Y %H:%M:%S',
                    '%Y-%m-%d %H:%M:%S',
                ]
                for f in fmts:
                    try:
                        dt = datetime.strptime(ts_str, f)
                        break
                    except Exception:
                        tried.append(f)

            if dt is None:
                continue

            # Ensure numeric value (ValueInMgPerDl is likely already mg/dL int)
            try:
                val = float(val_raw)
            except Exception:
                continue

            times.append(dt)
            values.append(val)
        
        if times:
            # Smooth the values for a nicer curve in the UI
            try:
                if len(values) > 3:
                    window = 5 if len(values) >= 5 else 3
                    kernel = np.ones(window) / window
                    smooth_vals = np.convolve(values, kernel, mode='same')
                else:
                    smooth_vals = values
            except Exception:
                smooth_vals = values

            line = self.ax.plot(times, smooth_vals, color=line_color, linewidth=2, antialiased=True)[0]
            # Place marker on the smoothed value so point and line match visually
            try:
                last_y = smooth_vals[-1]
            except Exception:
                last_y = values[-1]
            scatter = self.ax.scatter(times[-1], last_y, color=line_color, s=30)
            # Animate the line and marker fade-in
            try:
                line.set_alpha(0.0)
                scatter.set_alpha(0.0)
                self._animate_line(line, scatter)
            except Exception:
                pass

            # Format X axis
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
            self.ax.tick_params(axis='x', rotation=45, labelsize=8)

            # Threshold lines
            self.ax.axhline(y=180, color='red', linestyle='--', alpha=0.3)
            self.ax.axhline(y=70, color='red', linestyle='--', alpha=0.3)

            self.ax.set_ylim(40, 300)
            
        self.fig.tight_layout()
        try:
            # Ensure canvas widget background matches figure (convert RGBA to hex)
            rgba = self.fig.get_facecolor()
            if isinstance(rgba, tuple) or isinstance(rgba, list):
                try:
                    r, g, b, a = rgba
                    hexc = '#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255))
                except Exception:
                    hexc = None
            else:
                hexc = None

            if hexc:
                self.canvas.get_tk_widget().configure(bg=hexc)
        except Exception:
            pass
        self.canvas.draw()

    def set_loading(self, is_loading):
        if is_loading:
            self.status_bar.configure(text="Updating data...")
        else:
            self.status_bar.configure(text="Ready")

    def _open_settings(self):
        # kept for compatibility; settings are available in the Settings tab
        try:
            self.tabview.set("Settings")
        except Exception:
            pass

    def _build_settings_tab(self):
        settings_tab = self.tabview.tab("Settings")
        settings_tab.grid_columnconfigure(0, weight=1)
        lbl = ctk.CTkLabel(settings_tab, text="Appearance", font=ctk.CTkFont(size=16))
        lbl.grid(row=0, column=0, sticky='w', padx=20, pady=(16,8))

        values = ["Light", "Dark"]
        current = "System"
        try:
            if self.config and getattr(self.config, 'appearance_mode', None):
                # map any stored 'system' value to 'Dark' to avoid graph bg issues
                stored = (self.config.appearance_mode or 'dark')
                if stored.lower() == 'system':
                    stored = 'dark'
                current = stored.capitalize()
        except Exception:
            current = 'Dark'

        self.appearance_segment = ctk.CTkSegmentedButton(settings_tab, values=values)
        self.appearance_segment.grid(row=1, column=0, sticky='ew', padx=20)
        try:
            self.appearance_segment.set(current)
        except Exception:
            pass

        apply_btn = ctk.CTkButton(settings_tab, text="Apply", width=80, command=self._apply_appearance)
        apply_btn.grid(row=2, column=0, sticky='e', padx=20, pady=16)

    def _apply_appearance(self):
        sel = None
        try:
            sel = self.appearance_segment.get()
        except Exception:
            try:
                sel = str(self.appearance_segment._variable.get()).capitalize()
            except Exception:
                sel = None

        if not sel:
            sel = 'System'

        mode = sel.lower()
        if mode not in ('light', 'dark', 'system'):
            mode = 'system'

        try:
            ctk.set_appearance_mode(mode)
        except Exception:
            pass

        if self.config:
            try:
                self.config.appearance_mode = mode
                self.config.save()
            except Exception:
                pass

        # refresh matplotlib theme and redraw
        try:
            # update figure facecolor (use slightly off-white for light mode)
            if mode == 'light':
                self.fig.patch.set_facecolor('#f3f3f5')
            else:
                self.fig.patch.set_facecolor('#2b2b2b')
        except Exception:
            pass

        try:
            # redraw using last known data so the plot updates fully
            self._update_graph(self._last_graph_points or [])
        except Exception:
            pass

        try:
            self._apply_widget_theme()
        except Exception:
            pass
        try:
            self._refresh_label_colors()
        except Exception:
            pass

    def _refresh_label_colors(self):
        # Update trend/glucose label colors immediately to match current theme
        try:
            app = ctk.get_appearance_mode() or 'system'
        except Exception:
            app = 'system'

        if app.lower() == 'light':
            text_col = 'black'
        else:
            text_col = 'white'

        try:
            self.trend_label.configure(text_color=text_col)
        except Exception:
            pass

    def _animate_line(self, line, scatter, steps=10, delay=30):
        # fade-in animation by increasing alpha
        def step(i=0):
            a = (i + 1) / steps
            try:
                line.set_alpha(a)
            except Exception:
                pass
            try:
                scatter.set_alpha(a)
            except Exception:
                pass
            try:
                self.canvas.draw_idle()
            except Exception:
                pass
            if i + 1 < steps:
                try:
                    self.after(delay, lambda: step(i + 1))
                except Exception:
                    pass

        try:
            step(0)
        except Exception:
            pass

    def _sync_graph_bg(self, bg_color):
        # Ensure CTkFrame and canvas background match the matplotlib figure color.
        hexc = None
        if isinstance(bg_color, str) and bg_color.startswith('#'):
            hexc = bg_color
        else:
            try:
                rgba = self.fig.get_facecolor()
                if isinstance(rgba, (tuple, list)) and len(rgba) >= 3:
                    r, g, b = rgba[0], rgba[1], rgba[2]
                    hexc = '#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255))
            except Exception:
                hexc = None

        if hexc:
            try:
                self.graph_frame.configure(fg_color=hexc)
            except Exception:
                pass
            try:
                self.canvas.get_tk_widget().configure(bg=hexc)
            except Exception:
                pass

    def _apply_widget_theme(self):
        # adjust widget colors (e.g., logout button) to maintain contrast in light mode
        mode = 'system'
        try:
            mode = ctk.get_appearance_mode() or 'system'
        except Exception:
            mode = 'system'

        if mode.lower() == 'light':
            btn_fg = '#e6e6e6'
            text_col = 'black'
        else:
            btn_fg = 'transparent'
            text_col = 'white'

        try:
            self.logout_button.configure(fg_color=btn_fg, text_color=text_col)
        except Exception:
            pass
