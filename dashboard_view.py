import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime

class DashboardView(ctk.CTkFrame):
    def __init__(self, master, on_refresh, on_logout, **kwargs):
        super().__init__(master, **kwargs)
        self.on_refresh = on_refresh
        self.on_logout = on_logout
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Upper Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Current Glucose", font=ctk.CTkFont(size=16))
        self.title_label.grid(row=0, column=0, sticky="w")
        
        self.logout_button = ctk.CTkButton(self.header_frame, text="Logout", width=80, height=24, 
                                           fg_color="transparent", border_width=1, command=self.on_logout)
        self.logout_button.grid(row=0, column=2, sticky="e")
        
        # Value Display
        self.value_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.value_frame.grid(row=1, column=0, sticky="nsew", padx=20)
        self.value_frame.grid_columnconfigure(0, weight=1)
        
        self.glucose_label = ctk.CTkLabel(self.value_frame, text="--", font=ctk.CTkFont(size=120, weight="bold"))
        self.glucose_label.grid(row=0, column=0, pady=(20, 0))
        
        self.trend_label = ctk.CTkLabel(self.value_frame, text="", font=ctk.CTkFont(size=48))
        self.trend_label.grid(row=1, column=0, pady=(0, 20))
        
        self.time_label = ctk.CTkLabel(self.value_frame, text="Last updated: Never", font=ctk.CTkFont(size=12))
        self.time_label.grid(row=2, column=0)

        # Graph Area
        self.graph_frame = ctk.CTkFrame(self)
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
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        
        # Status Bar
        self.status_bar = ctk.CTkLabel(self, text="Ready", font=ctk.CTkFont(size=10))
        self.status_bar.grid(row=3, column=0, sticky="ew", padx=20, pady=5)

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
        
        # Color mapping (Simplified)
        color = "#2ecc71" # Green
        if color_idx == 2: color = "#f1c40f" # Yellow
        elif color_idx == 3: color = "#e74c3c" # Red
        
        self.glucose_label.configure(text=f"{val}", text_color=color)
        self.trend_label.configure(text=arrow)
        self.time_label.configure(text=f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        
        graph_payload = glucose_data.get("graph", [])
        # Lightweight logging to help debug graph payload shape
        try:
            print(f"[Dashboard] Received graph payload: count={len(graph_payload)}")
            for i, item in enumerate(graph_payload[:5]):
                print(f"[Dashboard] graph[{i}] = {item}")
        except Exception:
            pass

        self._update_graph(graph_payload)
        self.status_bar.configure(text="Data updated successfully")

    def _update_graph(self, graph_points):
        self.ax.clear()
        self.ax.set_facecolor('#2b2b2b')
        
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
            self.ax.plot(times, values, color='#3498db', linewidth=2)
            self.ax.scatter(times[-1], values[-1], color='#3498db', s=30)
            
            # Format X axis
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
            self.ax.tick_params(axis='x', rotation=45, labelsize=8)
            
            # Threshold lines
            self.ax.axhline(y=180, color='red', linestyle='--', alpha=0.3)
            self.ax.axhline(y=70, color='red', linestyle='--', alpha=0.3)
            
            self.ax.set_ylim(40, 300)
            
        self.fig.tight_layout()
        self.canvas.draw()

    def set_loading(self, is_loading):
        if is_loading:
            self.status_bar.configure(text="Updating data...")
        else:
            self.status_bar.configure(text="Ready")
