import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import paho.mqtt.client as mqtt
import json
import threading
import time
from datetime import datetime
from collections import deque
import ssl
import certifi
import os
import re

# Import matplotlib components for embedding in Tkinter
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class SensorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Room Comfort Optimiser Dashboard (MQTT)")
        self.root.geometry("950x750")
        
        # MQTT connection state
        self.mqtt_client = None
        self.is_connected = False
        
        # Current Data
        self.current_temp = 0.0
        self.current_hum = 0.0
        self.current_light = 0.0
        
        # Data storage for plotting (keep last 50 points)
        self.max_points = 50
        self.x_data = deque(maxlen=self.max_points)
        self.y_temp = deque(maxlen=self.max_points)
        self.y_hum = deque(maxlen=self.max_points)
        self.y_light = deque(maxlen=self.max_points)
        
        # Try to load defaults from firmware config.h
        self.defaults = self.load_config_defaults()
        
        self.setup_ui()
        
    def load_config_defaults(self):
        """Helper to parse firmware/SmartRoom/config.h for default values."""
        defaults = {
            "broker": "your_cluster.s1.eu.hivemq.cloud",
            "port": "8883",
            "user": "",
            "pass": "",
            "topic": "smartroom/temperature"
        }
        
        # Try to find config.h relative to this script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.abspath(os.path.join(base_dir, "..", "firmware", "SmartRoom", "config.h"))
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    content = f.read()
                    
                    broker_match = re.search(r'#define\s+MQTT_BROKER\s+"([^"]+)"', content)
                    if broker_match: defaults["broker"] = broker_match.group(1)
                    
                    port_match = re.search(r'#define\s+MQTT_PORT\s+(\d+)', content)
                    if port_match: defaults["port"] = port_match.group(1)
                    
                    user_match = re.search(r'#define\s+MQTT_USER\s+"([^"]+)"', content)
                    if user_match: defaults["user"] = user_match.group(1)
                    
                    pass_match = re.search(r'#define\s+MQTT_PASSWORD\s+"([^"]+)"', content)
                    if pass_match: defaults["pass"] = pass_match.group(1)
                    
                    topic_match = re.search(r'#define\s+TOPIC_TEMPERATURE\s+"([^"]+)"', content)
                    if topic_match: defaults["topic"] = topic_match.group(1)
            except Exception as e:
                print(f"Error reading config.h: {e}")
                
        return defaults

    def setup_ui(self):
        # === Top Frame: Controls ===
        control_frame = ttk.LabelFrame(self.root, text="MQTT Connection Controls", padding=(10, 10))
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Broker
        ttk.Label(control_frame, text="Broker:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.broker_var = tk.StringVar(value=self.defaults["broker"])
        self.broker_entry = ttk.Entry(control_frame, textvariable=self.broker_var, width=30)
        self.broker_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Port
        ttk.Label(control_frame, text="Port:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.port_var = tk.StringVar(value=self.defaults["port"])
        self.port_entry = ttk.Entry(control_frame, textvariable=self.port_var, width=8)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Username
        ttk.Label(control_frame, text="User:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.user_var = tk.StringVar(value=self.defaults["user"])
        self.user_entry = ttk.Entry(control_frame, textvariable=self.user_var, width=15)
        self.user_entry.grid(row=0, column=5, padx=5, pady=5)
        
        # Password
        ttk.Label(control_frame, text="Pass:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.pass_var = tk.StringVar(value=self.defaults["pass"])
        self.pass_entry = ttk.Entry(control_frame, textvariable=self.pass_var, width=30, show="*")
        self.pass_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Topic
        ttk.Label(control_frame, text="Topic:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.topic_var = tk.StringVar(value=self.defaults["topic"])
        self.topic_entry = ttk.Entry(control_frame, textvariable=self.topic_var, width=20)
        self.topic_entry.grid(row=1, column=3, columnspan=3, padx=5, pady=5, sticky="we")
        
        # Connect / Disconnect Buttons
        self.connect_btn = ttk.Button(control_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=6, rowspan=2, padx=10, pady=5, sticky="ns")
        
        # Status Label
        self.status_var = tk.StringVar(value="Disconnected")
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var, foreground="red", font=("Helvetica", 10, "bold"))
        self.status_label.grid(row=0, column=7, rowspan=2, padx=10, pady=5)
        
        # === Middle Frame: Dashboard ===
        dashboard_frame = ttk.Frame(self.root, padding=(10, 10))
        dashboard_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Values Frame (Left)
        values_frame = ttk.Frame(dashboard_frame, padding=(0, 0))
        values_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Temperature
        temp_frame = ttk.LabelFrame(values_frame, text="Current Temperature", padding=(10, 10))
        temp_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.temp_var = tk.StringVar(value="--.- °C")
        self.temp_label = ttk.Label(temp_frame, textvariable=self.temp_var, font=("Helvetica", 32, "bold"))
        self.temp_label.pack(expand=True)
        
        # Humidity
        hum_frame = ttk.LabelFrame(values_frame, text="Current Humidity", padding=(10, 10))
        hum_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.hum_var = tk.StringVar(value="--.- %")
        self.hum_label = ttk.Label(hum_frame, textvariable=self.hum_var, font=("Helvetica", 32, "bold"))
        self.hum_label.pack(expand=True)
        
        # Light
        light_frame = ttk.LabelFrame(values_frame, text="Current Light Level", padding=(10, 10))
        light_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        self.light_var = tk.StringVar(value="--- lx")
        self.light_label = ttk.Label(light_frame, textvariable=self.light_var, font=("Helvetica", 32, "bold"))
        self.light_label.pack(expand=True)
        
        # Graph (Right) - Embedded Matplotlib
        graph_frame = ttk.LabelFrame(dashboard_frame, text="Sensor Data Over Time", padding=(10, 10))
        graph_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.fig = Figure(figsize=(5, 6), dpi=100)
        self.ax_temp = self.fig.add_subplot(311)
        self.ax_temp.set_ylabel("Temp (°C)")
        self.line_temp, = self.ax_temp.plot([], [], 'r-')
        
        self.ax_hum = self.fig.add_subplot(312)
        self.ax_hum.set_ylabel("Hum (%)")
        self.line_hum, = self.ax_hum.plot([], [], 'b-')
        
        self.ax_light = self.fig.add_subplot(313)
        self.ax_light.set_ylabel("Light (lx)")
        self.ax_light.set_xlabel("Time (s)")
        self.line_light, = self.ax_light.plot([], [], 'g-')
        
        self.fig.tight_layout()
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # === Bottom Frame: Logs ===
        log_frame = ttk.LabelFrame(self.root, text="Raw Data Log", padding=(10, 10))
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=8, state='disabled')
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def log_message(self, msg):
        """Thread-safe way to append text to the log area."""
        def append():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        self.root.after(0, append)
        
    def update_sensor_data(self, temp=None, hum=None, light=None):
        """Update sensor labels and graphs inside the main GUI thread."""
        if temp is not None:
            self.current_temp = temp
        if hum is not None:
            self.current_hum = hum
        if light is not None:
            self.current_light = light
            
        def update_gui():
            # Update large text
            self.temp_var.set(f"{self.current_temp:.1f} °C")
            self.hum_var.set(f"{self.current_hum:.1f} %")
            self.light_var.set(f"{self.current_light:.0f} lx")
            
            # Update graph data
            current_time = time.time()
            if not hasattr(self, 'start_time'):
                self.start_time = current_time
            
            elapsed = current_time - self.start_time
            self.x_data.append(elapsed)
            self.y_temp.append(self.current_temp)
            self.y_hum.append(self.current_hum)
            self.y_light.append(self.current_light)
            
            # Redraw plot
            self.line_temp.set_data(self.x_data, self.y_temp)
            self.ax_temp.relim()
            self.ax_temp.autoscale_view()
            
            self.line_hum.set_data(self.x_data, self.y_hum)
            self.ax_hum.relim()
            self.ax_hum.autoscale_view()
            
            self.line_light.set_data(self.x_data, self.y_light)
            self.ax_light.relim()
            self.ax_light.autoscale_view()
            
            self.canvas.draw()
            
        # Use after(0, ...) to safely update GUI from our reading thread
        self.root.after(0, update_gui)
        
    def toggle_connection(self):
        """Connect or disconnect based on state."""
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()
            
    def connect(self):
        broker = self.broker_var.get().strip()
        port_str = self.port_var.get().strip()
        user = self.user_var.get().strip()
        password = self.pass_var.get().strip()
        
        if not broker:
            messagebox.showerror("Error", "Please enter a broker address.")
            return
            
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return

        try:
            client_id = f"RCO_Desktop_{int(time.time())}"
            try:
                # Try paho-mqtt v2 API
                self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
            except AttributeError:
                # Fallback to paho-mqtt v1 API
                self.mqtt_client = mqtt.Client(client_id=client_id)
            
            if user or password:
                self.mqtt_client.username_pw_set(user, password)
            
            # Use TLS for port 8883 (HiveMQ Cloud default secure port)
            if port == 8883:
                self.mqtt_client.tls_set(ca_certs=certifi.where(), cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
                
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            self.mqtt_client.on_message = self.on_mqtt_message
            
            self.log_message(f"Connecting to {broker}:{port}...")
            
            # Use a background thread for connecting to prevent UI freeze
            def mqtt_connect_thread():
                try:
                    self.mqtt_client.connect(broker, port, 60)
                    self.mqtt_client.loop_start()
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Connection Error", f"Failed to connect:\n{str(e)}"))
                    self.root.after(0, self.disconnect)
            
            threading.Thread(target=mqtt_connect_thread, daemon=True).start()
            
            # Optimistically update UI
            self.is_connected = True
            self.status_var.set("Connecting...")
            self.status_label.config(foreground="orange")
            self.connect_btn.config(text="Disconnect")
            
            # Disable entry fields
            self.broker_entry.config(state='disabled')
            self.port_entry.config(state='disabled')
            self.user_entry.config(state='disabled')
            self.pass_entry.config(state='disabled')
            self.topic_entry.config(state='disabled')
            
            # Reset graph data
            self.x_data.clear()
            self.y_temp.clear()
            self.y_hum.clear()
            self.y_light.clear()
            self.start_time = time.time()
            
        except Exception as e:
            messagebox.showerror("Setup Error", f"Failed to setup MQTT:\n{str(e)}")

    def on_mqtt_connect(self, client, userdata, flags, rc, *args):
        if rc == 0:
            def gui_update():
                self.status_var.set("Connected")
                self.status_label.config(foreground="green")
                topic = self.topic_var.get().strip()
                self.log_message(f"Connected successfully! Subscribing to: {topic}")
                self.mqtt_client.subscribe(topic)
            self.root.after(0, gui_update)
        else:
            self.log_message(f"Connection failed with code {rc}")
            self.root.after(0, self.disconnect)
            
    def on_mqtt_disconnect(self, client, userdata, rc, *args):
        self.log_message(f"Disconnected (code {rc})")
        if self.is_connected: # If unexpected disconnect
            self.root.after(0, self.disconnect)

    def on_mqtt_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            self.log_message(f"Topic: {msg.topic} | Msg: {payload}")
            
            # Try to parse JSON
            try:
                data = json.loads(payload)
                temp = data.get("temperature")
                hum = data.get("humidity")
                light = data.get("light")
                self.update_sensor_data(temp=temp, hum=hum, light=light)
            except json.JSONDecodeError:
                # Fallback: maybe it's just a raw number for temperature?
                try:
                    val = float(payload)
                    self.update_sensor_data(temp=val)
                except ValueError:
                    self.log_message(f"Could not parse payload as JSON or float: {payload}")
                    
        except Exception as e:
            self.log_message(f"Message processing error: {str(e)}")

    def disconnect(self):
        """Disconnect and reset UI."""
        self.is_connected = False
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            
        self.status_var.set("Disconnected")
        self.status_label.config(foreground="red")
        self.connect_btn.config(text="Connect")
        
        # Enable entry fields
        self.broker_entry.config(state='normal')
        self.port_entry.config(state='normal')
        self.user_entry.config(state='normal')
        self.pass_entry.config(state='normal')
        self.topic_entry.config(state='normal')
        
def on_closing(root, app):
    """Ensure connection is closed properly on app exit."""
    if app.is_connected:
        app.disconnect()
    root.destroy()

def main():
    root = tk.Tk()
    app = SensorApp(root)
    # Ensure graceful exit
    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root, app))
    root.mainloop()

if __name__ == "__main__":
    main()