import os
import tkinter as tk
import customtkinter as ctk
import auth

# Exact Color Palette from your Wireframe
BG_VOID = "#0b0714"       # Deep dark purple-black background
GRID_LINE = "#18122b"     # Subtle grid lines
PANEL_BG = "#110c21"      # Card & sidebar background
BORDER_PURPLE = "#482a7a" # Purple card outline
BORDER_CYAN = "#00f3ff"   # Active cyan outline
NEON_CYAN = "#00f3ff"     # Bright cyan accent
NEON_PINK = "#ff007f"     # Bright magenta/pink accent
NEON_YELLOW = "#ffea00"   # Arcade yellow text/icons
TEXT_WHITE = "#ffffff"
TEXT_MUTED = "#7b7396"

ctk.set_appearance_mode("dark")

class FuuRooWireframeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FuuRoo // SIA Project System")
        self.geometry("1020x680")
        self.resizable(False, False)
        self.configure(fg_color=BG_VOID)

        # Load pixel font if placed in folder, else use clean monospace
        self.font_family = "Consolas"
        if os.path.exists("PressStart2P-Regular.ttf"):
            try:
                ctk.FontManager.load_font("PressStart2P-Regular.ttf")
                self.font_family = "Press Start 2P"
            except Exception:
                pass

        # 1. Draw the Retro Grid Background
        self.bg_canvas = tk.Canvas(self, width=1020, height=680, bg=BG_VOID, highlightthickness=0)
        self.bg_canvas.place(x=0, y=0)
        self.draw_retro_grid()

        # Top Neon Purple Accent Line
        self.bg_canvas.create_line(0, 2, 1020, 2, fill="#8a2be2", width=3)

        # 2. Build Left Sidebar & Right Main Panel
        self.build_sidebar()
        self.main_panel = ctk.CTkFrame(
            self, width=660, height=580, fg_color=PANEL_BG,
            border_width=2, border_color=BORDER_CYAN, corner_radius=0
        )
        self.main_panel.place(x=320, y=42)
        self.main_panel.pack_propagate(False)

        self.show_auth_module()

    def draw_retro_grid(self):
        grid_size = 28
        for x in range(0, 1020, grid_size):
            self.bg_canvas.create_line(x, 0, x, 680, fill=GRID_LINE, width=1)
        for y in range(0, 680, grid_size):
            self.bg_canvas.create_line(0, y, 1020, y, fill=GRID_LINE, width=1)

    def f(self, size, bold=True):
        # Slightly scale down size if Press Start 2P is active since pixel fonts are wide
        actual_size = max(8, size - 3) if self.font_family == "Press Start 2P" else size
        return (self.font_family, actual_size, "bold" if bold else "normal")

    # ================= LEFT SIDEBAR (MODULES + PROJECT INFO) =================
    def build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self, width=265, height=440, fg_color=PANEL_BG,
            border_width=2, border_color=BORDER_PURPLE, corner_radius=0
        )
        sidebar.place(x=30, y=42)
        sidebar.pack_propagate(False)

        # Header: MODULES
        ctk.CTkLabel(
            sidebar, text="🎮 MODULES", font=self.f(14),
            text_color=NEON_YELLOW, anchor="w"
        ).pack(fill="x", padx=18, pady=(18, 12))

        modules = [
            ("🔑  1. AUTH /\n     OAUTH", True),
            ("👻  2. GAMES (3A)", False),
            ("🔧  3. UTILITIES\n     (3B)", False),
            ("🔗  4. SOCIAL (3C)", False),
        ]

        for label_text, is_active in modules:
            btn = ctk.CTkButton(
                sidebar,
                text=label_text,
                font=self.f(11),
                height=48,
                anchor="w",
                corner_radius=0,
                fg_color="#132238" if is_active else "#161029",
                hover_color="#1c2f4a",
                border_width=2 if is_active else 1,
                border_color=NEON_CYAN if is_active else BORDER_PURPLE,
                text_color=TEXT_WHITE if is_active else "#b8b0d0",
                command=lambda active=is_active: self.handle_nav_click(active)
            )
            btn.pack(fill="x", padx=16, pady=6)

        # Divider Line
        divider = tk.Frame(sidebar, height=1, bg=BORDER_PURPLE)
        divider.pack(fill="x", padx=16, pady=(14, 10))

        # PROJECT INFO Section
        ctk.CTkLabel(
            sidebar, text="PROJECT INFO", font=self.f(12),
            text_color=NEON_YELLOW, anchor="w"
        ).pack(fill="x", padx=18, pady=(2, 8))

        info_rows = [
            ("STACK:", "Python + API", TEXT_WHITE),
            ("STYLE:", "Friv / Tetr.io", NEON_CYAN),
            ("DB RECORDS:", "20 Faker Rows", NEON_PINK),
        ]

        for key, val, val_color in info_rows:
            row = ctk.CTkFrame(sidebar, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=2)
            ctk.CTkLabel(row, text=key, font=self.f(10, False), text_color=TEXT_MUTED).pack(side="left")
            ctk.CTkLabel(row, text=val, font=self.f(10, True), text_color=val_color).pack(side="right")

    def handle_nav_click(self, is_auth):
        if is_auth:
            self.show_auth_module()
        else:
            self.status_lbl.configure(text="! AUTHENTICATE FIRST TO UNLOCK MODULE", text_color=NEON_YELLOW)

    def clear_main_panel(self):
        for w in self.main_panel.winfo_children():
            w.destroy()

    # ================= RIGHT PANEL: MODULE 1 (AUTH & OAUTH 2.0) =================
    def show_auth_module(self):
        self.clear_main_panel()

        # Header Row
        header_row = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        header_row.pack(fill="x", padx=25, pady=(20, 10))

        ctk.CTkLabel(
            header_row,
            text="🛡️ MODULE 1: AUTHENTICATION & OAUTH\n   2.0",
            font=self.f(15), text_color=NEON_CYAN, justify="left"
        ).pack(side="left")

        req_badge = ctk.CTkFrame(
            header_row, width=72, height=42, fg_color="#132238",
            border_width=1, border_color=NEON_CYAN, corner_radius=0
        )
        req_badge.pack(side="right")
        req_badge.pack_propagate(False)
        ctk.CTkLabel(req_badge, text="REQ\n#1", font=self.f(11), text_color=NEON_CYAN).pack(expand=True)

        # Cyan Horizontal Rule under Header
        tk.Frame(self.main_panel, height=1, bg=NEON_CYAN).pack(fill="x", padx=25, pady=(4, 22))

        # Yellow Astronaut/Player Avatar Circle
        avatar_canvas = tk.Canvas(self.main_panel, width=64, height=64, bg=PANEL_BG, highlightthickness=0)
        avatar_canvas.pack(pady=(0, 10))
        avatar_canvas.create_oval(4, 4, 60, 60, fill="#241744", outline=BORDER_PURPLE, width=2)
        avatar_canvas.create_text(32, 32, text="🧑‍🚀", font=("Segoe UI Emoji", 24))

        # SYSTEM LOGIN Title
        ctk.CTkLabel(
            self.main_panel, text="SYSTEM LOGIN",
            font=self.f(20), text_color=TEXT_WHITE
        ).pack(pady=(2, 4))

        ctk.CTkLabel(
            self.main_panel, text="AUTHENTICATE TO UNLOCK ALL RETRO MODULES",
            font=self.f(10, False), text_color=TEXT_MUTED
        ).pack(pady=(0, 22))

        # Form Container (centered width matching wireframe)
        form_box = ctk.CTkFrame(self.main_panel, fg_color="transparent", width=460)
        form_box.pack()

        # USERNAME / EMAIL
        ctk.CTkLabel(
            form_box, text="USERNAME / EMAIL",
            font=self.f(11), text_color=NEON_CYAN, anchor="w"
        ).pack(fill="x", pady=(0, 5))

        self.user_entry = ctk.CTkEntry(
            form_box, width=460, height=42, corner_radius=0,
            fg_color="#090612", border_width=1, border_color=BORDER_PURPLE,
            font=self.f(13, False), text_color=NEON_YELLOW
        )
        self.user_entry.insert(0, "player_one")
        self.user_entry.pack(pady=(0, 14))

        # PASSCODE
        ctk.CTkLabel(
            form_box, text="PASSCODE",
            font=self.f(11), text_color=NEON_CYAN, anchor="w"
        ).pack(fill="x", pady=(0, 5))

        self.pass_entry = ctk.CT