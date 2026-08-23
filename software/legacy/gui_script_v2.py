import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import serial
import serial.tools.list_ports
import threading

# Εισαγωγές για το γράφημα και τα εργαλεία
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.ticker import FormatStrFormatter

class ArduinoLoggerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Arduino Data Logger Pro")
        self.root.geometry("1000x750") 
        self.root.minsize(900, 650)

        # Μεταβλητές Κατάστασης
        self.serial_port = None
        self.is_logging = False
        self.log_thread = None
        self.file = None
        
        # Μοναδικός κωδικός για κάθε τρέξιμο (αποτρέπει τα "φαντάσματα")
        self.run_id = 0 

        # Δεδομένα Γραφήματος & Στατιστικών
        self.time_data = []
        self.rs_data = []
        self.all_rs_values = [] # Για τον υπολογισμό του μέσου όρου
        self.max_points = 100

        self.setup_ui()
        self.refresh_ports()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        # Κεντρικό Container
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Αριστερή Στήλη (Ρυθμίσεις, Έλεγχος, Στατιστικά)
        left_column = ttk.Frame(main_frame, padding=5)
        left_column.pack(side="left", fill="y")

        # Δεξιά Στήλη (Γράφημα)
        right_column = ttk.Frame(main_frame, padding=5)
        right_column.pack(side="right", fill="both", expand=True)

        # --- 1. ΡΥΘΜΙΣΕΙΣ ΣΥΝΔΕΣΗΣ ---
        settings_frame = ttk.LabelFrame(left_column, text="Ρυθμίσεις Σύνδεσης", padding=10)
        settings_frame.pack(fill="x", pady=5)

        ttk.Label(settings_frame, text="Θύρα (COM):").grid(row=0, column=0, sticky="w")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(settings_frame, textvariable=self.port_var, state="readonly", width=12)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(settings_frame, text="🔄", width=3, command=self.refresh_ports).grid(row=0, column=2)

        ttk.Label(settings_frame, text="Baud Rate:").grid(row=1, column=0, sticky="w")
        self.baud_var = tk.StringVar(value="115200")
        self.baud_combo = ttk.Combobox(settings_frame, textvariable=self.baud_var, state="readonly", width=12)
        self.baud_combo['values'] = ("9600", "115200", "250000")
        self.baud_combo.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(settings_frame, text="Αρχείο:").grid(row=2, column=0, sticky="w")
        self.file_var = tk.StringVar(value="data.txt")
        ttk.Entry(settings_frame, textvariable=self.file_var, width=15).grid(row=2, column=1, padx=5, pady=5)
        
        # --- ΝΕΟ: Κουμπί για περιήγηση στον υπολογιστή ---
        ttk.Button(settings_frame, text="📁", width=3, command=self.browse_file).grid(row=2, column=2)

        # --- 2. ΕΛΕΓΧΟΣ ---
        control_frame = ttk.Frame(left_column, padding=5)
        control_frame.pack(fill="x", pady=5)
        self.start_btn = ttk.Button(control_frame, text="▶ Έναρξη", command=self.start_logging)
        self.start_btn.pack(fill="x", pady=2)
        self.stop_btn = ttk.Button(control_frame, text="⏹ Διακοπή", command=self.stop_logging, state="disabled")
        self.stop_btn.pack(fill="x", pady=2)
        
        # --- Checkbox ---
        self.show_all_var = tk.BooleanVar(value=False)
        self.show_all_chk = ttk.Checkbutton(
            control_frame, 
            text="Προβολή όλου του ιστορικού", 
            variable=self.show_all_var,
            command=self.refresh_graph_view 
        )
        self.show_all_chk.pack(fill="x", pady=10)

        # --- 3. ΖΩΝΤΑΝΑ ΣΤΑΤΙΣΤΙΚΑ ---
        stats_frame = ttk.LabelFrame(left_column, text="Στατιστικά (MΩ)", padding=10)
        stats_frame.pack(fill="x", pady=5)

        self.max_val_var = tk.StringVar(value="0.000")
        self.min_val_var = tk.StringVar(value="0.000")
        self.avg_val_var = tk.StringVar(value="0.000")

        ttk.Label(stats_frame, text="Μέγιστο (Max):").grid(row=0, column=0, sticky="w")
        ttk.Label(stats_frame, textvariable=self.max_val_var, font=("Arial", 10, "bold")).grid(row=0, column=1, padx=10, sticky="e")

        ttk.Label(stats_frame, text="Ελάχιστο (Min):").grid(row=1, column=0, sticky="w")
        ttk.Label(stats_frame, textvariable=self.min_val_var, font=("Arial", 10, "bold")).grid(row=1, column=1, padx=10, sticky="e")

        ttk.Label(stats_frame, text="Μέσος Όρος:").grid(row=2, column=0, sticky="w")
        ttk.Label(stats_frame, textvariable=self.avg_val_var, font=("Arial", 10, "bold")).grid(row=2, column=1, padx=10, sticky="e")

        # --- 4. LIVE LOG ---
        log_frame = ttk.LabelFrame(left_column, text="Live Log", padding=5)
        log_frame.pack(fill="both", expand=True, pady=5)
        self.log_text = tk.Text(log_frame, width=30, height=10, state="disabled", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

        # --- 5. ΓΡΑΦΗΜΑ & TOOLBAR (ΔΕΞΙΑ) ---
        self.fig, self.ax = plt.subplots(figsize=(7, 5), dpi=100)
        
        self.ax.set_title("Resistance vs Time", fontsize=14, fontweight='bold')
        self.ax.set_xlabel("Χρόνος (ms)")
        self.ax.set_ylabel("Rs Filtered (MΩ)")
        self.ax.yaxis.set_major_formatter(FormatStrFormatter('%.3f'))
        self.ax.grid(True, linestyle="--", alpha=0.6)
        
        self.line, = self.ax.plot([], [], color='#0078D7', marker='o', markersize=2, linewidth=1)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_column)
        self.canvas.draw()
        
        self.toolbar = NavigationToolbar2Tk(self.canvas, right_column)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports: self.port_combo.current(0)

    # --- ΝΕΑ ΣΥΝΑΡΤΗΣΗ: Ανοίγει παράθυρο περιήγησης στον υπολογιστή ---
    def browse_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Επιλογή Αρχείου Αποθήκευσης"
        )
        # Αν ο χρήστης επιλέξει αρχείο (δεν πατήσει ακύρωση)
        if filename:
            self.file_var.set(filename)

    def update_stats(self, val, current_run_id):
        if current_run_id != self.run_id: return
        
        self.all_rs_values.append(val)
        mx = max(self.all_rs_values)
        mn = min(self.all_rs_values)
        av = sum(self.all_rs_values) / len(self.all_rs_values)
        
        self.max_val_var.set(f"{mx:.3f}")
        self.min_val_var.set(f"{mn:.3f}")
        self.avg_val_var.set(f"{av:.3f}")

    def refresh_graph_view(self):
        if not self.time_data: return 
        
        if self.show_all_var.get():
            self.line.set_xdata(self.time_data)
            self.line.set_ydata(self.rs_data)
        else:
            self.line.set_xdata(self.time_data[-self.max_points:])
            self.line.set_ydata(self.rs_data[-self.max_points:])
            
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

    def update_graph(self, time_ms, rs_val, current_run_id):
        if current_run_id != self.run_id: return
        
        self.time_data.append(time_ms)
        self.rs_data.append(rs_val)
        self.refresh_graph_view()

    def log_msg(self, msg, current_run_id):
        if current_run_id != self.run_id: return
        
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def start_logging(self):
        port = self.port_var.get()
        if not port or port == "Δεν βρέθηκε": return
        
        try:
            self.serial_port = serial.Serial(port, int(self.baud_var.get()), timeout=1)
            
            # Ανοίγουμε το αρχείο στο Path που έχει επιλέξει ο χρήστης
            self.file = open(self.file_var.get(), 'w', encoding='utf-8')
            self.file.write("t_ms,RsFilt_MOhm\n")

            self.is_logging = True
            self.run_id += 1  
            
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            
            self.all_rs_values.clear()
            self.time_data.clear()
            self.rs_data.clear()
            self.line.set_xdata([])
            self.line.set_ydata([])

            self.log_thread = threading.Thread(target=self.read_serial_data, args=(self.run_id,), daemon=True)
            self.log_thread.start()
        except Exception as e:
            messagebox.showerror("Σφάλμα", str(e))

    def read_serial_data(self, current_run_id):
        try:
            if self.serial_port.is_open:
                self.serial_port.reset_input_buffer()
                self.serial_port.readline() 
        except Exception:
            pass

        while self.is_logging and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if not line or line.startswith("t_ms"): continue
                    
                    parts = line.split(',')
                    if len(parts) == 6:
                        t_str = parts[0].strip()   
                        rs_str = parts[5].strip()  
                        
                        try:
                            if rs_str.lower() != "nan":
                                t_val = int(t_str)
                                rs_val = float(rs_str)
                                
                                self.file.write(f"{t_val},{rs_val}\n")
                                self.file.flush()
                                
                                self.root.after(0, self.log_msg, f"{t_val}ms -> {rs_val}MΩ", current_run_id)
                                self.root.after(0, self.update_graph, t_val, rs_val, current_run_id)
                                self.root.after(0, self.update_stats, rs_val, current_run_id)
                        except ValueError: 
                            pass
            except Exception as e: 
                print(f"Σφάλμα ανάγνωσης: {e}")
                break

    def stop_logging(self):
        self.is_logging = False
        if self.serial_port: self.serial_port.close()
        if self.file: self.file.close()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def on_closing(self):
        self.stop_logging()
        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ArduinoLoggerGUI(root)
    root.mainloop()