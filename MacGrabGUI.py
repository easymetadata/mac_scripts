#!/usr/bin/env python3
"""
MacGrab GUI — A simple Tkinter front-end for MacGrab.sh
Requires: macOS 10.14+, Python 3 (ships with macOS), Terminal Full Disk Access
Usage:    python3 MacGrabGUI.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import sys

SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MacGrab.sh")

# ──────────────────────────────────────────────────────────────
# Colour / font tokens
# ──────────────────────────────────────────────────────────────
BG          = "#1e1e2e"
SURFACE     = "#27273a"
BORDER      = "#3a3a55"
ACCENT      = "#7c6af7"
ACCENT_DARK = "#5b4dd6"
FG          = "#cdd6f4"
FG_DIM      = "#8a8aab"
SUCCESS     = "#a6e3a1"
ERROR       = "#f38ba8"
WARNING     = "#f9e2af"
LOG_BG      = "#13131e"
FONT_BODY   = ("SF Pro Display", 13)
FONT_MONO   = ("Menlo", 11)
FONT_HEAD   = ("SF Pro Display", 15, "bold")
FONT_SMALL  = ("SF Pro Display", 11)


class MacGrabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MacGrab")
        self.resizable(True, True)
        self.minsize(680, 520)
        self.configure(bg=BG)
        self._proc = None
        self._running = False
        self._build_ui()
        self._check_script()

    # ──────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG, pady=18)
        hdr.pack(fill="x", padx=28)

        tk.Label(hdr, text="🔒  MacGrab", font=FONT_HEAD,
                 bg=BG, fg=FG).pack(side="left")
        tk.Label(hdr, text="macOS forensic snapshot collector",
                 font=FONT_SMALL, bg=BG, fg=FG_DIM).pack(side="left", padx=(10, 0), pady=(3, 0))

        # ── Config card ─────────────────────────────────────
        card = tk.Frame(self, bg=SURFACE, bd=0, relief="flat",
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=28, pady=(0, 14))

        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="x", padx=18, pady=14)

        # -- Target directory row --
        tk.Label(inner, text="Target Directory", font=FONT_BODY,
                 bg=SURFACE, fg=FG).grid(row=0, column=0, sticky="w", pady=(0, 8))

        dir_row = tk.Frame(inner, bg=SURFACE)
        dir_row.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        inner.columnconfigure(0, weight=1)
        dir_row.columnconfigure(0, weight=1)

        self.target_var = tk.StringVar()
        dir_entry = tk.Entry(dir_row, textvariable=self.target_var,
                             font=FONT_BODY, bg=LOG_BG, fg=FG, insertbackground=FG,
                             relief="flat", bd=0,
                             highlightthickness=1, highlightbackground=BORDER)
        dir_entry.grid(row=0, column=0, sticky="ew", ipady=6, padx=(0, 8))

        browse_btn = tk.Button(dir_row, text="Browse…", font=FONT_SMALL,
                               bg=SURFACE, fg=ACCENT, activebackground=BORDER,
                               activeforeground=ACCENT, relief="flat", bd=0,
                               cursor="hand2",
                               highlightthickness=1, highlightbackground=BORDER,
                               padx=12, pady=4,
                               command=self._browse)
        browse_btn.grid(row=0, column=1)

        # -- Password row --
        tk.Label(inner, text="sudo Password", font=FONT_BODY,
                 bg=SURFACE, fg=FG).grid(row=2, column=0, sticky="w", pady=(0, 8))

        self.pwd_var = tk.StringVar()
        pwd_entry = tk.Entry(inner, textvariable=self.pwd_var, show="•",
                             font=FONT_BODY, bg=LOG_BG, fg=FG, insertbackground=FG,
                             relief="flat", bd=0,
                             highlightthickness=1, highlightbackground=BORDER)
        pwd_entry.grid(row=3, column=0, sticky="ew", ipady=6, pady=(0, 4))

        tk.Label(inner, text="Required — the script must run as root",
                 font=FONT_SMALL, bg=SURFACE, fg=FG_DIM).grid(row=4, column=0, sticky="w")

        # ── Action buttons ───────────────────────────────────
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=28, pady=(0, 14))

        self.run_btn = tk.Button(btn_row, text="▶  Run MacGrab",
                                 font=("SF Pro Display", 13, "bold"),
                                 bg=ACCENT, fg="#ffffff",
                                 activebackground=ACCENT_DARK, activeforeground="#ffffff",
                                 relief="flat", bd=0, cursor="hand2",
                                 padx=20, pady=8,
                                 command=self._toggle_run)
        self.run_btn.pack(side="left")

        self.clear_btn = tk.Button(btn_row, text="Clear Log",
                                   font=FONT_SMALL,
                                   bg=SURFACE, fg=FG_DIM,
                                   activebackground=BORDER, activeforeground=FG,
                                   relief="flat", bd=0, cursor="hand2",
                                   padx=14, pady=8,
                                   command=self._clear_log)
        self.clear_btn.pack(side="left", padx=(10, 0))

        # ── Log area ─────────────────────────────────────────
        log_frame = tk.Frame(self, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=28, pady=(0, 8))

        tk.Label(log_frame, text="Output Log", font=FONT_SMALL,
                 bg=BG, fg=FG_DIM).pack(anchor="w", pady=(0, 4))

        self.log = scrolledtext.ScrolledText(
            log_frame, font=FONT_MONO, bg=LOG_BG, fg=FG,
            insertbackground=FG, relief="flat", bd=0,
            highlightthickness=1, highlightbackground=BORDER,
            state="disabled", wrap="word"
        )
        self.log.pack(fill="both", expand=True)

        # Tag colours for log lines
        self.log.tag_config("info",    foreground=FG)
        self.log.tag_config("success", foreground=SUCCESS)
        self.log.tag_config("error",   foreground=ERROR)
        self.log.tag_config("warning", foreground=WARNING)
        self.log.tag_config("dim",     foreground=FG_DIM)

        # ── Status bar ───────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready")
        sb = tk.Frame(self, bg=SURFACE, height=28)
        sb.pack(fill="x", side="bottom")
        tk.Label(sb, textvariable=self.status_var, font=FONT_SMALL,
                 bg=SURFACE, fg=FG_DIM, anchor="w", padx=14).pack(fill="x")

    # ──────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────
    def _check_script(self):
        if not os.path.isfile(SCRIPT_PATH):
            self._log(f"⚠  MacGrab.sh not found at: {SCRIPT_PATH}\n"
                      "Place MacGrabGUI.py in the same folder as MacGrab.sh.", "error")
            self.run_btn.configure(state="disabled")

    def _browse(self):
        path = filedialog.askdirectory(title="Select target directory")
        if path:
            self.target_var.set(path)

    def _toggle_run(self):
        if self._running:
            self._stop()
        else:
            self._start()

    def _start(self):
        target = self.target_var.get().strip()
        password = self.pwd_var.get()

        if not target:
            messagebox.showwarning("Missing input", "Please select a target directory.")
            return
        if not password:
            messagebox.showwarning("Missing input", "Please enter your sudo password.")
            return
        if not os.path.isdir(target):
            if not messagebox.askyesno("Directory not found",
                                       f"'{target}' does not exist.\nCreate it and continue?"):
                return

        self._running = True
        self.run_btn.configure(text="⏹  Stop", bg="#e06c75", activebackground="#c0555f")
        self._set_status("Running…")
        self._clear_log()
        self._log(f"Starting MacGrab → {target}\n", "dim")

        thread = threading.Thread(target=self._run_script,
                                  args=(target, password), daemon=True)
        thread.start()

    def _stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            self._log("\n⚠  Stopped by user.\n", "warning")
        self._finish(cancelled=True)

    def _run_script(self, target, password):
        try:
            cmd = ["sudo", "-S", "bash", SCRIPT_PATH, target]
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            # Feed the password once to sudo via stdin
            self._proc.stdin.write(password + "\n")
            self._proc.stdin.flush()
            self._proc.stdin.close()

            for line in self._proc.stdout:
                self.after(0, self._append_line, line)

            self._proc.wait()
            rc = self._proc.returncode

            if rc == 0:
                self.after(0, self._log, "\n✅  MacGrab completed successfully.\n", "success")
                self.after(0, self._set_status, "Completed ✓")
            else:
                self.after(0, self._log,
                           f"\n❌  Script exited with code {rc}.\n", "error")
                self.after(0, self._set_status, f"Failed (exit {rc})")

        except Exception as exc:
            self.after(0, self._log, f"\n❌  Error: {exc}\n", "error")
            self.after(0, self._set_status, "Error")
        finally:
            self.after(0, self._finish)

    def _append_line(self, line):
        """Colour-code individual log lines based on content keywords."""
        tag = "info"
        low = line.lower()
        if any(k in low for k in ("error", "failed", "cannot", "denied")):
            tag = "error"
        elif any(k in low for k in ("success", "successfully", "complete", "done")):
            tag = "success"
        elif any(k in low for k in ("warning", "warn", "skip")):
            tag = "warning"
        self._log(line, tag)

    def _log(self, text, tag="info"):
        self.log.configure(state="normal")
        self.log.insert("end", text, tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _finish(self, cancelled=False):
        self._running = False
        self._proc = None
        self.run_btn.configure(text="▶  Run MacGrab", bg=ACCENT, activebackground=ACCENT_DARK)
        if cancelled:
            self._set_status("Stopped")

    def _set_status(self, text):
        self.status_var.set(text)


# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = MacGrabApp()
    # Center window on screen
    app.update_idletasks()
    w, h = 720, 580
    x = (app.winfo_screenwidth()  - w) // 2
    y = (app.winfo_screenheight() - h) // 2
    app.geometry(f"{w}x{h}+{x}+{y}")
    app.mainloop()
