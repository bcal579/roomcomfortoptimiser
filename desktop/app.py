import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import threading
import time
from datetime import datetime
from collections import deque

# Import matplotlib components for embedding in Tkinter
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class SensorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wio Terminal Sensor Dashboard")
        self.root.geometry("900x750")
        
        # Serial connection state
        self.serial_conn = None
        self.is_connected = False
        self.read_thread = None
        
        # Data storage for plotting (keep last 50 points)
        self.max_points = 50
        self.x_data = deque(maxlen=self.max_points)
        self.y_temp = deque(maxlen=self.max_points)
        self.y_hum = deque(maxlen=self.max_points)
        self.y_light = deque(maxlen=self.max_points)
        
        self.setup_ui()
        self.update_ports()
        
    def setup_ui(self):
        # === Top Frame: Controls ===
        control_frame = ttk.LabelFrame(self.root, text="Connection Controls", padding=(10, 10))
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Port Selection
        ttk.Label(control_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5)
        self.port_var = tk.StringVar()
        self.port_combobox = ttk.Combobox(control_frame, textvariable=self.port_var, width=25)
        self.port_combobox.grid(row=0, column=1, padx=5, pady=5)
        
        refresh_btn = ttk.Button(control_frame, text="Refresh Ports", command=self.update_ports)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Baud Rate
        ttk.Label(control_frame, text="Baud Rate:").grid(row=0, column=3, padx=5, pady=5)
        self.baud_var = tk.StringVar(value="9600")
        self.baud_entry = ttk.Entry(control_frame, textvariable=self.baud_var, width=10)
        self.baud_entry.grid(row=0, column=4, padx=5, pady=5)
        
        # Connect / Disconnect Buttons
        self.connect_btn = ttk.Button(control_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=5, padx=5, pady=5)
        
        # Status Label
        self.status_var = tk.StringVar(value="Disconnected")
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var, foreground="red", font=("Helvetica", 10, "bold"))
        self.status_label.grid(row=0, column=6, padx=10, pady=5)
        
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

    def update_ports(self):
        """Discover available serial ports."""
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.port_combobox['values'] = port_list
        if port_list:
            self.port_combobox.set(port_list[0])
            
    def log_message(self, msg):
        """Thread-safe way to append text to the log area."""
        def append():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        self.root.after(0, append)
        
    def update_sensor_data(self, temp, hum, light):
        """Update sensor labels and graphs inside the main GUI thread."""
        def update_gui():
            # Update large text
            self.temp_var.set(f"{temp:.1f} °C")
            self.hum_var.set(f"{hum:.1f} %")
            self.light_var.set(f"{light:.0f} lx")
            
            # Update graph data
            current_time = time.time()
            if not hasattr(self, 'start_time'):
                self.start_time = current_time
            
            elapsed = current_time - self.start_time
            self.x_data.append(elapsed)
            self.y_temp.append(temp)
            self.y_hum.append(hum)
            self.y_light.append(light)
            
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
        port = self.port_var.get()
        baudrate = self.baud_var.get()
        
        if not port:
            messagebox.showerror("Error", "Please select a serial port.")
            return
            
        try:
            # Initialize serial connection
            self.serial_conn = serial.Serial(port, int(baudrate), timeout=1)
            self.is_connected = True
            
            # Update GUI elements
            self.status_var.set("Connected")
            self.status_label.config(foreground="green")
            self.connect_btn.config(text="Disconnect")
            self.port_combobox.config(state='disabled')
            self.baud_entry.config(state='disabled')
            
            self.log_message(f"Connected to {port} at {baudrate} baud.")
            
            # Reset graph data
            self.x_data.clear()
            self.y_temp.clear()
            self.y_hum.clear()
            self.y_light.clear()
            self.start_time = time.time()
            
            self.ax_temp.clear()
            self.ax_temp.set_ylabel("Temp (°C)")
            self.line_temp, = self.ax_temp.plot([], [], 'r-')
            
            self.ax_hum.clear()
            self.ax_hum.set_ylabel("Hum (%)")
            self.line_hum, = self.ax_hum.plot([], [], 'b-')
            
            self.ax_light.clear()
            self.ax_light.set_ylabel("Light (lx)")
            self.ax_light.set_xlabel("Time (s)")
            self.line_light, = self.ax_light.plot([], [], 'g-')
            
            self.canvas.draw()
            
            # Start a background thread to prevent UI freezing
            self.read_thread = threading.Thread(target=self.read_serial_data, daemon=True)
            self.read_thread.start()
            
        except serial.SerialException as e:
            messagebox.showerror("Connection Error", f"Failed to connect to {port}:\n{str(e)}")
        except ValueError:
            messagebox.showerror("Error", "Invalid baud rate.")
            
    def disconnect(self):
        """Disconnect and reset UI."""
        self.is_connected = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            
        self.status_var.set("Disconnected")
        self.status_label.config(foreground="red")
        self.connect_btn.config(text="Connect")
        self.port_combobox.config(state='normal')
        self.baud_entry.config(state='normal')
        
        self.log_message("Disconnected.")
        
    def read_serial_data(self):
        """Background thread loops and reads data from the serial port."""
        while self.is_connected and self.serial_conn and self.serial_conn.is_open:
            try:
                # Read incoming line, decode to string, and remove whitespace/newlines
                line = self.serial_conn.readline().decode('utf-8').strip()
                if line:
                    self.log_message(f"Received: {line}")
                    try:
                        # Assume data format is comma separated: "temp, hum, light"
                        # e.g. "25.3, 45.2, 300"
                        parts = line.split(',')
                        if len(parts) >= 3:
                            temp = float(parts[0].strip())
                            hum = float(parts[1].strip())
                            light = float(parts[2].strip())
                            self.update_sensor_data(temp, hum, light)
                        elif len(parts) == 1:
                            # Fallback if only one value is sent (assume temp)
                            temp = float(parts[0].strip())
                            self.update_sensor_data(temp, 0.0, 0.0)
                        else:
                            self.log_message("Warning: Unexpected data format.")
                    except ValueError:
                        self.log_message("Warning: Ignored non-numeric data.")
            except serial.SerialException:
                # Handle cases where the device is physically unplugged
                if self.is_connected:
                    self.log_message("Error: Device disconnected unexpectedly.")
                    self.root.after(0, self.disconnect)
                break
            except Exception as e:
                self.log_message(f"Read error: {str(e)}")

def on_closing(root, app):
    """Ensure serial port is closed properly on app exit."""
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
