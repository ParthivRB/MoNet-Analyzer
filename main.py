import os
import json
import sys
import threading
import pandas as pd
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from monet_engine import MoNetEngine

# --- SETUP PATHS ---
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

SETTINGS_FILE = BASE_DIR / "app_settings.json"
DEFAULT_MODEL_PATH = BASE_DIR / "models" / "FINALmodel_300.h5"
DEFAULT_DIR = Path.home()

# --- MEMORY ---
def load_settings():
    defaults = {"last_input": str(DEFAULT_DIR), "filter_mode": "All"}
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f: return {**defaults, **json.load(f)}
        except: pass
    return defaults

def save_settings(key, value):
    current = load_settings()
    current[key] = str(value)
    with open(SETTINGS_FILE, "w") as f: json.dump(current, f, indent=2)
    return current

def scan_folder(folder):
    items = []
    folder_path = Path(folder)
    for r, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".csv"):
                full_path = Path(r) / f
                try:
                    rel_path = full_path.relative_to(folder_path)
                except:
                    rel_path = Path(f)
                items.append({
                    "file_name": f, "rel_path": rel_path,
                    "full_path": str(full_path)
                })
    return sorted(items, key=lambda x: x["rel_path"])

# --- GUI ---
class MoNetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MoNet-Analyzer")
        self.geometry("950x780")
        
        self.engine = MoNetEngine()
        self.settings = load_settings()
        self.paths = {"input": tk.StringVar(value=self.settings["last_input"])}
        
        # Filter Logic
        self.filter_var = tk.StringVar(value=self.settings.get("filter_mode", "All"))
        self.motion_types = ["All", "Brownian", "FBM", "CTRW"]
        self.explain_text = tk.StringVar()
        
        self.items = []
        self.stop_flag = False  # Flag to control stopping
        
        self._ui()
        self._update_explanation() 

    def _ui(self):
        nb = ttk.Notebook(self); nb.pack(fill="both", expand=1, padx=10, pady=5)
        t1, t2, t3 = ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb)
        nb.add(t1, text="1. Scan"); nb.add(t2, text="2. Settings"); nb.add(t3, text="3. Run")

        # --- Tab 1: Scan ---
        frame_in = ttk.Frame(t1); frame_in.pack(pady=20)
        ttk.Label(frame_in, text="Input Data Folder:").grid(row=0, column=0, padx=5)
        ttk.Entry(frame_in, textvariable=self.paths["input"], width=50).grid(row=0, column=1, padx=5)
        ttk.Button(frame_in, text="Browse", command=self._browse).grid(row=0, column=2, padx=5)
        
        ttk.Button(t1, text="SCAN FILES", command=self._scan).pack(pady=10)
        self.lbl_count = ttk.Label(t1, text="No files loaded.")
        self.lbl_count.pack()

        # --- Tab 2: Settings ---
        ttk.Label(t2, text="Filtering Mode", font=("Arial", 12, "bold")).pack(pady=10)
        
        frame_filter = ttk.Frame(t2); frame_filter.pack(pady=5)
        for m_type in self.motion_types:
            rb = ttk.Radiobutton(
                frame_filter, text=f"Keep {m_type}", variable=self.filter_var, value=m_type,
                command=self._update_explanation
            )
            rb.pack(anchor="w", pady=2)
            
        # Explanation Box
        lbl_explain = ttk.Label(t2, textvariable=self.explain_text, foreground="#555", wraplength=400, justify="center")
        lbl_explain.pack(pady=15)

        # --- Tab 3: Run ---
        cols = ("File Name", "Status", "Total Tracks", "Filtered Tracks")
        self.tree = ttk.Treeview(t3, columns=cols, show="headings")
        self.tree.pack(fill="both", expand=1, padx=5, pady=5)
        for c in cols: self.tree.heading(c, text=c)
        self.tree.column("File Name", width=250)
        self.tree.column("Total Tracks", width=100, anchor="center")
        self.tree.column("Filtered Tracks", width=100, anchor="center")
        
        # Button Frame for RUN and STOP
        btn_frame = ttk.Frame(t3)
        btn_frame.pack(pady=10)

        self.run_btn = ttk.Button(btn_frame, text="RUN BATCH ANALYSIS", command=self._run_batch)
        self.run_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="STOP PROCESSING", command=self._stop_batch, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        # --- LOG BOX (Updated Font) ---
        ttk.Label(t3, text="Combined Status Log:").pack(anchor="w", padx=10, pady=(10, 0))
        
        self.log_text = tk.Text(
            t3, height=12, state="disabled", 
            bg="#1e1e1e",           # Dark Background
            fg="#d4d4d4",           # Light Text
            insertbackground="white", 
            font=("Arial", 12),     # <--- BIGGER, NORMAL FONT
            relief="flat",
            highlightthickness=1, 
            highlightbackground="#444"
        )
        self.log_text.pack(fill="x", padx=10, pady=(5, 15))

    def _browse(self):
        p = filedialog.askdirectory(initialdir=self.settings.get("last_input", str(DEFAULT_DIR)))
        if p: 
            self.paths["input"].set(p)
            save_settings("last_input", p)

    def _update_explanation(self):
        save_settings("filter_mode", self.filter_var.get())
        mode = self.filter_var.get()
        if mode == "All": txt = "No filtering. All particle tracks will be saved."
        elif mode == "Brownian": txt = "Normal Diffusion.\nKeeps particles moving freely in liquid.\n(Random motion)"
        elif mode == "FBM": txt = "Fractional Brownian Motion.\nKeeps particles in crowded/elastic environments.\n(Bumping and bouncing back)"
        elif mode == "CTRW": txt = "Continuous Time Random Walk.\nKeeps particles that get trapped in obstacles.\n(Stick-and-slip motion)"
        else: txt = ""
        self.explain_text.set(txt)

    def _scan(self):
        if not self.paths["input"].get(): return messagebox.showerror("Error", "Select Input Folder first.")
        try:
            self.items = scan_folder(self.paths["input"].get())
            self.tree.delete(*self.tree.get_children())
            for item in self.items:
                self.tree.insert("", "end", values=(item["file_name"], "Pending", "-", "-"))
            self.lbl_count.config(text=f"Found {len(self.items)} CSV files.")
            messagebox.showinfo("Scan", f"Found {len(self.items)} files.")
        except Exception as e: messagebox.showerror("Error", str(e))

    def _log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _update_row(self, filename, status, total="-", filtered="-"):
        for item in self.tree.get_children():
            if self.tree.item(item)["values"][0] == filename:
                self.tree.item(item, values=(filename, status, total, filtered))
                break

    def _stop_batch(self):
        """Called when STOP button is pressed."""
        self.stop_flag = True
        self._log("🛑 Stopping requested... Finishing current file...")
        self.stop_btn.config(state="disabled") # Prevent double clicking

    def _run_batch(self):
        if not DEFAULT_MODEL_PATH.exists():
            return messagebox.showerror("Error", f"Model missing:\n{DEFAULT_MODEL_PATH}")
        if not self.items: return messagebox.showerror("Error", "Scan files first.")

        input_root = Path(self.paths["input"].get())
        filter_mode = self.filter_var.get()
        output_root = input_root.parent / f"MoNet_{input_root.name}"

        # Reset Stop Flag
        self.stop_flag = False
        
        # Toggle Buttons
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        
        self.log_text.config(state="normal"); self.log_text.delete("1.0", "end"); self.log_text.config(state="disabled")

        def worker():
            self._log(f"🚀 Starting Batch Analysis...")
            self._log(f"🧠 Loading Model: {DEFAULT_MODEL_PATH.name}...")
            
            success, msg = self.engine.load_model(str(DEFAULT_MODEL_PATH))
            if not success:
                self._log(f"❌ CRITICAL ERROR: {msg}")
                self._reset_buttons()
                return

            try:
                self._log(f"📂 Creating Output Folder: {output_root}")
                output_root.mkdir(exist_ok=True)
                with open(output_root / "processing_info.txt", "w") as f:
                    f.write(f"Source: {input_root}\nFilter: {filter_mode}\nModel: {DEFAULT_MODEL_PATH.name}\n")
            except Exception as e:
                self._log(f"❌ Error creating folder: {e}")
                self._reset_buttons()
                return

            for item in self.items:
                # CHECK STOP FLAG
                if self.stop_flag:
                    self._log("🛑 Batch processing stopped by user.")
                    break

                fname = item["file_name"]
                self._update_row(fname, "Running...")
                self._log(f"⏳ Processing {fname}...")
                
                # Run Logic
                filtered_df, count_orig, count_filt, msg = self.engine.run_inference(item["full_path"], filter_mode)

                if filtered_df is None:
                    self._log(f"❌ Failed {fname}: {msg}")
                    self._update_row(fname, "Error", 0, 0)
                else:
                    dest_folder = output_root / item["rel_path"].parent
                    dest_folder.mkdir(parents=True, exist_ok=True)
                    
                    out_name = f"{item['rel_path'].stem}_{filter_mode}.csv"
                    filtered_df.to_csv(dest_folder / out_name, index=False)

                    self._log(f"✅ {fname}: {count_orig} -> {count_filt} tracks kept")
                    self._update_row(fname, "Done", count_orig, count_filt)

            if not self.stop_flag:
                self._log("🎉 --- Batch Complete ---")
                messagebox.showinfo("Done", f"Analysis complete.\nSaved to: {output_root}")
            else:
                messagebox.showinfo("Stopped", "Processing stopped by user.")
            
            self._reset_buttons()

        threading.Thread(target=worker, daemon=True).start()

    def _reset_buttons(self):
        # Helper to reset buttons after run or stop
        self.run_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

if __name__ == "__main__": 
    MoNetApp().mainloop()