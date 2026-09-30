"""
VaultGuard - Modern Professional CustomTkinter GUI Interface
"""

import sys
import os
import pyperclip
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox

# Import core engine
from vaultguard_core import (
    is_master_password_set,
    create_master_password,
    verify_master_password,
    save_vault,
    get_account_status,
    generate_password,
    evaluate_password_strength,
    get_vault_stats,
    ROTATION_DAYS
)

# Set global CTK theme settings
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class VaultGuardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VaultGuard - NextGen Password Vault")
        self.geometry("1100x720")
        self.minsize(950, 600)

        # Center window on screen
        self.center_window()

        # Session variables
        self.vault = {}
        self.master_password = None
        self.salt = None

        # Container frame
        self.container = ctk.CTkFrame(self, corner_radius=0)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Start with authentication check
        self.show_auth_screen()

    def center_window(self):
        self.update_idletasks()
        width = 1100
        height = 720
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    # ---------------------------------------------------------
    # AUTHENTICATION & LOCK SCREEN
    # ---------------------------------------------------------

    def show_auth_screen(self):
        """Displays Login or Setup Master Password View."""
        # Clear container
        for widget in self.container.winfo_children():
            widget.destroy()

        auth_frame = ctk.CTkFrame(self.container, fg_color=("gray95", "#0F172A"))
        auth_frame.grid(row=0, column=0, sticky="nsew")
        auth_frame.grid_rowconfigure(0, weight=1)
        auth_frame.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(auth_frame, width=420, corner_radius=16, fg_color=("white", "#1E293B"), border_width=1, border_color=("gray85", "#334155"))
        card.grid(row=0, column=0, padx=20, pady=20)

        # App Icon & Title
        title_label = ctk.CTkLabel(
            card,
            text="🔐 VaultGuard",
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color=("#1E293B", "#F8FAFC")
        )
        title_label.pack(pady=(40, 20))

        is_setup = not is_master_password_set()

        if is_setup:
            header_msg = "Create Master Password"
            desc_msg = "Set a strong master password to encrypt your vault."
        else:
            header_msg = "Unlock Your Vault"
            desc_msg = "Enter your master password to access accounts."

        ctk.CTkLabel(
            card,
            text=header_msg,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=("#3B82F6", "#60A5FA")
        ).pack(pady=(5, 2))

        ctk.CTkLabel(
            card,
            text=desc_msg,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray60", "#64748B")
        ).pack(pady=(0, 20))

        # Inputs
        pass_entry = ctk.CTkEntry(
            card,
            width=320,
            height=44,
            placeholder_text="Master Password",
            show="•",
            font=ctk.CTkFont(size=14),
            corner_radius=8
        )
        pass_entry.pack(pady=8)
        pass_entry.focus()

        confirm_entry = None
        if is_setup:
            confirm_entry = ctk.CTkEntry(
                card,
                width=320,
                height=44,
                placeholder_text="Confirm Master Password",
                show="•",
                font=ctk.CTkFont(size=14),
                corner_radius=8
            )
            confirm_entry.pack(pady=8)

        # Status Error Feedback Label
        error_label = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=12), text_color="#EF4444")
        error_label.pack(pady=(4, 8))

        def handle_auth(event=None):
            pwd = pass_entry.get().strip()
            if not pwd:
                error_label.configure(text="Master password cannot be empty.")
                return

            if is_setup:
                cpwd = confirm_entry.get().strip()
                if pwd != cpwd:
                    error_label.configure(text="Passwords do not match!")
                    return
                if len(pwd) < 6:
                    error_label.configure(text="Master password must be at least 6 characters.")
                    return

                success, msg = create_master_password(pwd)
                if success:
                    # Log in after creation
                    ok, _, vault, salt = verify_master_password(pwd)
                    if ok:
                        self.vault = vault
                        self.master_password = pwd
                        self.salt = salt
                        self.show_main_dashboard()
                else:
                    error_label.configure(text=msg)
            else:
                ok, msg, vault, salt = verify_master_password(pwd)
                if ok:
                    self.vault = vault
                    self.master_password = pwd
                    self.salt = salt
                    self.show_main_dashboard()
                else:
                    error_label.configure(text="Access Denied: Incorrect Master Password")

        # Bind Enter Key
        pass_entry.bind("<Return>", handle_auth)
        if confirm_entry:
            confirm_entry.bind("<Return>", handle_auth)

        action_btn_text = "CREATE VAULT" if is_setup else "UNLOCK VAULT"
        action_btn = ctk.CTkButton(
            card,
            text=action_btn_text,
            width=320,
            height=44,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            corner_radius=8,
            command=handle_auth
        )
        action_btn.pack(pady=(10, 40))

    # ---------------------------------------------------------
    # MAIN VAULT DASHBOARD LAYOUT
    # ---------------------------------------------------------

    def show_main_dashboard(self):
        """Builds main application window with sidebar & tab views."""
        for widget in self.container.winfo_children():
            widget.destroy()

        self.main_frame = ctk.CTkFrame(self.container, fg_color=("gray95", "#0B0F19"))
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # 1. SIDEBAR
        self.build_sidebar()

        # 2. MAIN CONTENT AREA
        self.content_area = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_area.grid_rowconfigure(1, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        # Filter and Search State
        self.search_query = ""
        self.category_filter = "All"

        # Show default Vault tab
        self.switch_tab("vault")

    def build_sidebar(self):
        sidebar = ctk.CTkFrame(self.main_frame, width=240, corner_radius=0, fg_color=("white", "#111827"), border_width=1, border_color=("gray85", "#1F2937"))
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Header Title
        logo_label = ctk.CTkLabel(
            sidebar,
            text="🔐 VaultGuard",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=("#1E293B", "#F8FAFC")
        )
        logo_label.pack(padx=20, pady=(25, 2))

        status_badge = ctk.CTkLabel(
            sidebar,
            text="● Vault Unlocked",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#10B981"
        )
        status_badge.pack(padx=20, pady=(0, 25))

        # Nav Buttons
        self.nav_buttons = {}

        nav_items = [
            ("vault", "📦  Accounts Vault"),
            ("generator", "⚡  Password Generator"),
            ("audit", "🔔  Security Audit"),
            ("settings", "⚙️  Settings")
        ]

        for tab_id, label in nav_items:
            btn = ctk.CTkButton(
                sidebar,
                text=label,
                anchor="w",
                height=40,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                fg_color="transparent",
                text_color=("gray30", "#94A3B8"),
                hover_color=("gray90", "#1E293B"),
                corner_radius=8,
                command=lambda t=tab_id: self.switch_tab(t)
            )
            btn.pack(fill="x", padx=15, pady=4)
            self.nav_buttons[tab_id] = btn

        # Bottom Stats Box inside Sidebar
        stats_box = ctk.CTkFrame(sidebar, fg_color=("gray90", "#1E293B"), corner_radius=12)
        stats_box.pack(fill="x", padx=15, pady=(40, 15), side="bottom")

        stats = get_vault_stats(self.vault)

        ctk.CTkLabel(stats_box, text="Vault Health", font=ctk.CTkFont(size=12, weight="bold"), text_color=("gray20", "#E2E8F0")).pack(anchor="w", padx=12, pady=(10, 2))
        
        # Health Bar
        score = stats["security_score"]
        bar_color = "#10B981" if score >= 75 else ("#F59E0B" if score >= 50 else "#EF4444")
        
        progress = ctk.CTkProgressBar(stats_box, height=8, progress_color=bar_color, fg_color=("gray75", "#334155"))
        progress.set(score / 100)
        progress.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(
            stats_box,
            text=f"Score: {score}%  •  {stats['total_accounts']} Items",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "#94A3B8")
        ).pack(anchor="w", padx=12, pady=(0, 10))

        # Lock Button
        lock_btn = ctk.CTkButton(
            sidebar,
            text="🔒 Lock Vault",
            height=36,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            command=self.lock_vault
        )
        lock_btn.pack(fill="x", padx=15, pady=(0, 20), side="bottom")

    def switch_tab(self, tab_name):
        """Switches active view tab."""
        self.current_tab = tab_name

        # Highlight active button
        for t_id, btn in self.nav_buttons.items():
            if t_id == tab_name:
                btn.configure(fg_color=("#3B82F6", "#2563EB"), text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=("gray30", "#94A3B8"))

        # Clear Content Area
        for widget in self.content_area.winfo_children():
            widget.destroy()

        if tab_name == "vault":
            self.render_vault_view()
        elif tab_name == "generator":
            self.render_generator_view()
        elif tab_name == "audit":
            self.render_audit_view()
        elif tab_name == "settings":
            self.render_settings_view()

    # ---------------------------------------------------------
    # TAB 1: ACCOUNTS VAULT VIEW
    # ---------------------------------------------------------

    def render_vault_view(self):
        # 1. Header with Search & Add Account Button
        header = ctk.CTkFrame(self.content_area, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header.grid_columnconfigure(0, weight=1)

        search_entry = ctk.CTkEntry(
            header,
            placeholder_text="🔍 Search accounts by service or username...",
            height=42,
            font=ctk.CTkFont(size=13),
            corner_radius=10,
            fg_color=("white", "#1E293B"),
            border_color=("gray80", "#334155")
        )
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 15))
        search_entry.insert(0, self.search_query)

        def on_search(event=None):
            self.search_query = search_entry.get().strip().lower()
            self.refresh_account_list()

        search_entry.bind("<KeyRelease>", on_search)

        add_btn = ctk.CTkButton(
            header,
            text="➕  Add Account",
            height=42,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            corner_radius=10,
            command=self.open_add_account_modal
        )
        add_btn.grid(row=0, column=1)

        # 2. Scrollable Accounts List Container
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.content_area,
            fg_color="transparent",
            corner_radius=0
        )
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.refresh_account_list()

    def refresh_account_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        filtered_items = []
        for service, acc in self.vault.items():
            uname = acc.get("username", "").lower()
            sname = service.lower()
            if not self.search_query or (self.search_query in sname or self.search_query in uname):
                filtered_items.append((service, acc))

        if not filtered_items:
            empty_card = ctk.CTkFrame(self.scroll_frame, fg_color=("white", "#1E293B"), corner_radius=12)
            empty_card.pack(fill="x", pady=20, padx=5)
            
            msg = "No accounts found in your vault!" if not self.vault else f"No results matching '{self.search_query}'"
            ctk.CTkLabel(
                empty_card,
                text=f"📭 {msg}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=("gray40", "#94A3B8")
            ).pack(pady=40)
            return

        for service, acc in filtered_items:
            self.build_account_card(service, acc)

    def build_account_card(self, service: str, acc: dict):
        card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=("white", "#1E293B"),
            corner_radius=12,
            border_width=1,
            border_color=("gray85", "#334155")
        )
        card.pack(fill="x", pady=6, padx=2)
        card.grid_columnconfigure(1, weight=1)

        # Initial Avatar Icon
        initial = service[0].upper() if service else "?"
        avatar = ctk.CTkFrame(card, width=44, height=44, corner_radius=10, fg_color=("#DBEAFE", "#1E3A8A"))
        avatar.grid(row=0, column=0, rowspan=2, padx=15, pady=15)
        avatar.grid_propagate(False)

        ctk.CTkLabel(
            avatar,
            text=initial,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#1D4ED8", "#93C5FD")
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Details Column Container
        details_box = ctk.CTkFrame(card, fg_color="transparent")
        details_box.grid(row=0, column=1, rowspan=2, sticky="w", pady=10, padx=(0, 10))

        # Service & Expiry Badge
        title_box = ctk.CTkFrame(details_box, fg_color="transparent")
        title_box.pack(anchor="w", pady=(0, 2))

        ctk.CTkLabel(
            title_box,
            text=service,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=("#0F172A", "#F8FAFC")
        ).pack(side="left")

        status = get_account_status(acc.get("last_changed", ""))
        badge = ctk.CTkFrame(title_box, fg_color=status["color"], corner_radius=6)
        badge.pack(side="left", padx=10)

        ctk.CTkLabel(
            badge,
            text=status["badge_text"],
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="white"
        ).pack(padx=8, pady=2)

        # Username
        ctk.CTkLabel(
            details_box,
            text=f"👤 {acc.get('username', '')}",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "#94A3B8")
        ).pack(anchor="w", pady=(0, 2))

        # Password Line with Show/Hide Toggle Button
        pass_line = ctk.CTkFrame(details_box, fg_color="transparent")
        pass_line.pack(anchor="w", pady=(2, 0))

        raw_password = acc.get("password", "")
        is_showing = False

        pass_lbl = ctk.CTkLabel(
            pass_line,
            text="🔑 ••••••••••••",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "#94A3B8")
        )
        pass_lbl.pack(side="left")

        def toggle_password_visibility():
            nonlocal is_showing
            is_showing = not is_showing
            if is_showing:
                pass_lbl.configure(
                    text=f"🔑 {raw_password}",
                    font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                    text_color="#60A5FA"
                )
                toggle_btn.configure(
                    text="🙈 Hide",
                    fg_color=("#DBEAFE", "#1E3A8A"),
                    text_color=("#1D4ED8", "#93C5FD")
                )
            else:
                pass_lbl.configure(
                    text="🔑 ••••••••••••",
                    font=ctk.CTkFont(size=12),
                    text_color=("gray50", "#94A3B8")
                )
                toggle_btn.configure(
                    text="👁️ Show",
                    fg_color=("gray85", "#334155"),
                    text_color=("black", "white")
                )

        toggle_btn = ctk.CTkButton(
            pass_line,
            text="👁️ Show",
            width=65,
            height=22,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("gray85", "#334155"),
            text_color=("black", "white"),
            hover_color=("gray75", "#475569"),
            corner_radius=6,
            command=toggle_password_visibility
        )
        toggle_btn.pack(side="left", padx=8)

        # Password Actions Frame (Copy Password, Copy Username, Edit, Delete)
        actions_frame = ctk.CTkFrame(card, fg_color="transparent")
        actions_frame.grid(row=0, column=2, rowspan=2, padx=15, pady=15, sticky="e")

        # Copy Password Button
        copy_pass_btn = ctk.CTkButton(
            actions_frame,
            text="📋 Password",
            width=90,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#3B82F6",
            hover_color="#2563EB",
            corner_radius=8,
            command=lambda p=acc.get("password", ""): self.copy_to_clipboard(p, "Password copied to clipboard!")
        )
        copy_pass_btn.pack(side="left", padx=3)

        # Copy Username Button
        copy_user_btn = ctk.CTkButton(
            actions_frame,
            text="👤 User",
            width=70,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("gray85", "#334155"),
            text_color=("black", "white"),
            hover_color=("gray75", "#475569"),
            corner_radius=8,
            command=lambda u=acc.get("username", ""): self.copy_to_clipboard(u, "Username copied to clipboard!")
        )
        copy_user_btn.pack(side="left", padx=3)

        # Edit Button
        edit_btn = ctk.CTkButton(
            actions_frame,
            text="✏️",
            width=36,
            height=34,
            font=ctk.CTkFont(size=13),
            fg_color=("gray85", "#334155"),
            hover_color=("gray75", "#475569"),
            corner_radius=8,
            command=lambda s=service, a=acc: self.open_edit_account_modal(s, a)
        )
        edit_btn.pack(side="left", padx=3)

        # Delete Button
        delete_btn = ctk.CTkButton(
            actions_frame,
            text="🗑️",
            width=36,
            height=34,
            font=ctk.CTkFont(size=13),
            fg_color="#EF4444",
            hover_color="#DC2626",
            corner_radius=8,
            command=lambda s=service: self.delete_account_confirm(s)
        )
        delete_btn.pack(side="left", padx=3)

    def copy_to_clipboard(self, text: str, msg: str):
        pyperclip.copy(text)
        self.show_toast(msg)

    def show_toast(self, text: str):
        """Displays temporary notification toast."""
        toast = ctk.CTkFrame(self.container, fg_color="#10B981", corner_radius=20)
        toast.place(relx=0.5, rely=0.92, anchor="center")

        label = ctk.CTkLabel(
            toast,
            text=f"✅  {text}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white"
        )
        label.pack(padx=20, pady=8)

        self.after(2200, toast.destroy)

    # ---------------------------------------------------------
    # MODAL DIALOGS: ADD / EDIT ACCOUNT
    # ---------------------------------------------------------

    def open_add_account_modal(self):
        self.build_account_modal(title="Add New Account", is_edit=False)

    def open_edit_account_modal(self, service: str, acc: dict):
        self.build_account_modal(title=f"Edit Account: {service}", is_edit=True, orig_service=service, orig_acc=acc)

    def build_account_modal(self, title: str, is_edit: bool = False, orig_service: str = "", orig_acc: dict = None):
        modal = ctk.CTkToplevel(self)
        modal.title(title)
        modal.geometry("450x520")
        modal.resizable(False, False)
        modal.grab_set()  # Make window modal

        # Center modal
        x = self.winfo_x() + (self.winfo_width() // 2) - 225
        y = self.winfo_y() + (self.winfo_height() // 2) - 260
        modal.geometry(f"+{x}+{y}")

        card = ctk.CTkFrame(modal, fg_color=("white", "#1E293B"))
        card.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            card, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color=("#0F172A", "#F8FAFC")
        ).pack(pady=(15, 20))

        # Service Entry
        ctk.CTkLabel(card, text="Service Name (e.g., Google, GitHub)", font=ctk.CTkFont(size=12, weight="bold"), text_color=("gray30", "#94A3B8")).pack(anchor="w", padx=20)
        service_entry = ctk.CTkEntry(card, width=370, height=40, font=ctk.CTkFont(size=13))
        service_entry.pack(padx=20, pady=(2, 12))
        if is_edit:
            service_entry.insert(0, orig_service)
            service_entry.configure(state="disabled")  # Primary key

        # Username Entry
        ctk.CTkLabel(card, text="Username / Email", font=ctk.CTkFont(size=12, weight="bold"), text_color=("gray30", "#94A3B8")).pack(anchor="w", padx=20)
        username_entry = ctk.CTkEntry(card, width=370, height=40, font=ctk.CTkFont(size=13))
        username_entry.pack(padx=20, pady=(2, 12))
        if is_edit and orig_acc:
            username_entry.insert(0, orig_acc.get("username", ""))

        # Password Entry
        ctk.CTkLabel(card, text="Password", font=ctk.CTkFont(size=12, weight="bold"), text_color=("gray30", "#94A3B8")).pack(anchor="w", padx=20)

        pass_frame = ctk.CTkFrame(card, fg_color="transparent")
        pass_frame.pack(padx=20, pady=(2, 12), fill="x")

        password_entry = ctk.CTkEntry(pass_frame, width=220, height=40, show="•", font=ctk.CTkFont(size=13))
        password_entry.pack(side="left")
        if is_edit and orig_acc:
            password_entry.insert(0, orig_acc.get("password", ""))

        is_modal_pass_shown = False
        def toggle_modal_pass():
            nonlocal is_modal_pass_shown
            is_modal_pass_shown = not is_modal_pass_shown
            password_entry.configure(show="" if is_modal_pass_shown else "•")
            eye_btn.configure(text="🙈" if is_modal_pass_shown else "👁️")

        eye_btn = ctk.CTkButton(
            pass_frame, text="👁️", width=50, height=40, font=ctk.CTkFont(size=14), fg_color=("gray85", "#334155"), command=toggle_modal_pass
        )
        eye_btn.pack(side="left", padx=5)

        def gen_quick_pass():
            p = generate_password(length=16)
            password_entry.delete(0, "end")
            password_entry.insert(0, p)
            password_entry.configure(show="")

        gen_btn = ctk.CTkButton(
            pass_frame, text="⚡ Gen", width=80, height=40, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#3B82F6", command=gen_quick_pass
        )
        gen_btn.pack(side="right")

        # Error label
        err_lbl = ctk.CTkLabel(card, text="", text_color="#EF4444", font=ctk.CTkFont(size=12))
        err_lbl.pack(pady=4)

        def save_action():
            s = service_entry.get().strip() if not is_edit else orig_service
            u = username_entry.get().strip()
            p = password_entry.get().strip()

            if not s or not u or not p:
                err_lbl.configure(text="Please fill in all fields.")
                return

            if not is_edit and s in self.vault:
                err_lbl.configure(text="An account for this service already exists!")
                return

            self.vault[s] = {
                "username": u,
                "password": p,
                "last_changed": datetime.now().strftime("%Y-%m-%d")
            }

            save_vault(self.vault, self.master_password, self.salt)
            modal.destroy()
            self.refresh_account_list()
            self.build_sidebar()  # refresh sidebar health score
            self.show_toast(f"Account '{s}' saved successfully!")

        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(15, 10))

        cancel_btn = ctk.CTkButton(btn_box, text="Cancel", width=170, height=40, fg_color=("gray80", "#334155"), text_color=("black", "white"), command=modal.destroy)
        cancel_btn.pack(side="left")

        save_btn = ctk.CTkButton(btn_box, text="Save Account", width=180, height=40, fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(weight="bold"), command=save_action)
        save_btn.pack(side="right")

    def delete_account_confirm(self, service: str):
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the account for '{service}'?"):
            if service in self.vault:
                del self.vault[service]
                save_vault(self.vault, self.master_password, self.salt)
                self.refresh_account_list()
                self.build_sidebar()
                self.show_toast(f"Deleted account '{service}'")

    # ---------------------------------------------------------
    # TAB 2: PASSWORD GENERATOR VIEW
    # ---------------------------------------------------------

    def render_generator_view(self):
        card = ctk.CTkFrame(self.content_area, fg_color=("white", "#1E293B"), corner_radius=16, border_width=1, border_color=("gray85", "#334155"))
        card.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(card, text="⚡ Password Generator", font=ctk.CTkFont(size=22, weight="bold"), text_color=("#0F172A", "#F8FAFC")).pack(pady=(25, 5))
        ctk.CTkLabel(card, text="Generate cryptographically strong passwords instantly.", font=ctk.CTkFont(size=13), text_color=("gray50", "#94A3B8")).pack(pady=(0, 20))

        # Output Box
        output_frame = ctk.CTkFrame(card, fg_color=("gray95", "#0F172A"), corner_radius=12, border_width=1, border_color=("gray80", "#334155"))
        output_frame.pack(fill="x", padx=40, pady=10)

        self.gen_pass_label = ctk.CTkLabel(output_frame, text="", font=ctk.CTkFont(family="Consolas", size=20, weight="bold"), text_color="#3B82F6")
        self.gen_pass_label.pack(side="left", padx=20, pady=15)

        copy_btn = ctk.CTkButton(
            output_frame, text="📋 Copy", width=90, height=38, font=ctk.CTkFont(weight="bold"), fg_color="#10B981", hover_color="#059669",
            command=lambda: self.copy_to_clipboard(self.gen_pass_label.cget("text"), "Password copied to clipboard!")
        )
        copy_btn.pack(side="right", padx=15)

        # Strength Bar
        self.strength_bar = ctk.CTkProgressBar(card, height=10, corner_radius=5)
        self.strength_bar.pack(fill="x", padx=40, pady=(15, 5))
        self.strength_lbl = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.strength_lbl.pack()

        # Options Controls Frame
        opts_frame = ctk.CTkFrame(card, fg_color="transparent")
        opts_frame.pack(fill="x", padx=40, pady=20)

        # Length Slider
        length_box = ctk.CTkFrame(opts_frame, fg_color="transparent")
        length_box.pack(fill="x", pady=10)

        self.length_val_lbl = ctk.CTkLabel(length_box, text="Password Length: 16", font=ctk.CTkFont(size=14, weight="bold"))
        self.length_val_lbl.pack(side="left")

        def on_slider(val):
            length = int(val)
            self.length_val_lbl.configure(text=f"Password Length: {length}")
            self.update_generated_password()

        self.length_slider = ctk.CTkSlider(length_box, from_=8, to=48, number_of_steps=40, command=on_slider)
        self.length_slider.set(16)
        self.length_slider.pack(side="right", fill="x", expand=True, padx=(20, 0))

        # Checkbox Controls
        chk_frame = ctk.CTkFrame(opts_frame, fg_color="transparent")
        chk_frame.pack(fill="x", pady=15)

        self.chk_upper = ctk.CTkCheckBox(chk_frame, text="Uppercase (A-Z)", font=ctk.CTkFont(size=13), command=self.update_generated_password)
        self.chk_upper.select()
        self.chk_upper.pack(side="left", expand=True)

        self.chk_lower = ctk.CTkCheckBox(chk_frame, text="Lowercase (a-z)", font=ctk.CTkFont(size=13), command=self.update_generated_password)
        self.chk_lower.select()
        self.chk_lower.pack(side="left", expand=True)

        self.chk_digits = ctk.CTkCheckBox(chk_frame, text="Digits (0-9)", font=ctk.CTkFont(size=13), command=self.update_generated_password)
        self.chk_digits.select()
        self.chk_digits.pack(side="left", expand=True)

        self.chk_symbols = ctk.CTkCheckBox(chk_frame, text="Symbols (!@#$)", font=ctk.CTkFont(size=13), command=self.update_generated_password)
        self.chk_symbols.select()
        self.chk_symbols.pack(side="left", expand=True)

        # Regenerate Button
        regen_btn = ctk.CTkButton(
            card, text="🔄 Generate New Password", height=44, font=ctk.CTkFont(size=14, weight="bold"), fg_color="#3B82F6", hover_color="#2563EB", command=self.update_generated_password
        )
        regen_btn.pack(pady=20)

        self.update_generated_password()

    def update_generated_password(self):
        length = int(self.length_slider.get())
        u = bool(self.chk_upper.get())
        l = bool(self.chk_lower.get())
        d = bool(self.chk_digits.get())
        s = bool(self.chk_symbols.get())

        p = generate_password(length=length, upper=u, lower=l, digits=d, symbols=s)
        self.gen_pass_label.configure(text=p)

        eval_res = evaluate_password_strength(p)
        self.strength_bar.configure(progress_color=eval_res["color"])
        self.strength_bar.set(eval_res["score"] / 100)
        self.strength_lbl.configure(text=f"Strength: {eval_res['label']} ({eval_res['score']}%)", text_color=eval_res["color"])

    # ---------------------------------------------------------
    # TAB 3: SECURITY AUDIT VIEW
    # ---------------------------------------------------------

    def render_audit_view(self):
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Overview Stats Card
        stats = get_vault_stats(self.vault)
        header_card = ctk.CTkFrame(scroll, fg_color=("white", "#1E293B"), corner_radius=16, border_width=1, border_color=("gray85", "#334155"))
        header_card.pack(fill="x", pady=10)

        ctk.CTkLabel(header_card, text="🔔 Password Security & Health Audit", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(header_card, text=f"Accounts require password rotation every {ROTATION_DAYS} days for maximum security.", font=ctk.CTkFont(size=12), text_color=("gray50", "#94A3B8")).pack(pady=(0, 15))

        metrics_box = ctk.CTkFrame(header_card, fg_color="transparent")
        metrics_box.pack(fill="x", padx=20, pady=(0, 20))
        metrics_box.grid_columnconfigure((0, 1, 2), weight=1)

        def make_stat_box(parent, col, title, val, color):
            box = ctk.CTkFrame(parent, fg_color=("gray95", "#0F172A"), corner_radius=12)
            box.grid(row=0, column=col, sticky="ew", padx=8, pady=5)
            ctk.CTkLabel(box, text=val, font=ctk.CTkFont(size=24, weight="bold"), text_color=color).pack(pady=(12, 0))
            ctk.CTkLabel(box, text=title, font=ctk.CTkFont(size=12), text_color=("gray50", "#94A3B8")).pack(pady=(0, 12))

        make_stat_box(metrics_box, 0, "Total Accounts", str(stats["total_accounts"]), "#3B82F6")
        make_stat_box(metrics_box, 1, "Overdue Accounts", str(stats["overdue_count"]), "#EF4444" if stats["overdue_count"] > 0 else "#10B981")
        make_stat_box(metrics_box, 2, "Weak Passwords", str(stats["weak_passwords"]), "#F59E0B" if stats["weak_passwords"] > 0 else "#10B981")

        # Overdue list
        ctk.CTkLabel(scroll, text="🚨 Overdue / Pending Password Changes", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(20, 10))

        has_alerts = False
        for service, acc in self.vault.items():
            status = get_account_status(acc.get("last_changed", ""))
            if status["level"] in ["due", "overdue", "warning"]:
                has_alerts = True
                card = ctk.CTkFrame(scroll, fg_color=("white", "#1E293B"), corner_radius=12, border_width=1, border_color=("gray85", "#334155"))
                card.pack(fill="x", pady=4)
                card.grid_columnconfigure(1, weight=1)

                ctk.CTkLabel(card, text=f"🔑 {service}", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=15, pady=12)
                ctk.CTkLabel(card, text=f"Last changed {status['days_passed']} days ago", font=ctk.CTkFont(size=12), text_color=("gray50", "#94A3B8")).grid(row=0, column=1, sticky="w")

                badge = ctk.CTkFrame(card, fg_color=status["color"], corner_radius=6)
                badge.grid(row=0, column=2, padx=15)
                ctk.CTkLabel(badge, text=status["badge_text"], font=ctk.CTkFont(size=11, weight="bold"), text_color="white").pack(padx=10, pady=4)

                update_btn = ctk.CTkButton(
                    card, text="Update Now", width=100, height=32, font=ctk.CTkFont(size=11, weight="bold"), fg_color="#3B82F6",
                    command=lambda s=service, a=acc: self.open_edit_account_modal(s, a)
                )
                update_btn.grid(row=0, column=3, padx=15)

        if not has_alerts:
            good_card = ctk.CTkFrame(scroll, fg_color=("white", "#1E293B"), corner_radius=12)
            good_card.pack(fill="x", pady=10)
            ctk.CTkLabel(good_card, text="🎉 Great job! All passwords are up to date.", font=ctk.CTkFont(size=13, weight="bold"), text_color="#10B981").pack(pady=25)

    # ---------------------------------------------------------
    # TAB 4: SETTINGS VIEW
    # ---------------------------------------------------------

    def render_settings_view(self):
        card = ctk.CTkFrame(self.content_area, fg_color=("white", "#1E293B"), corner_radius=16, border_width=1, border_color=("gray85", "#334155"))
        card.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(card, text="⚙️ Preferences & Security Settings", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(25, 20))

        # Appearance Theme Toggle
        theme_box = ctk.CTkFrame(card, fg_color=("gray95", "#0F172A"), corner_radius=12)
        theme_box.pack(fill="x", padx=40, pady=10)

        ctk.CTkLabel(theme_box, text="Appearance Theme", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=20, pady=20)

        def change_theme(mode):
            ctk.set_appearance_mode(mode)

        theme_option = ctk.CTkOptionMenu(theme_box, values=["Dark", "Light", "System"], command=change_theme, font=ctk.CTkFont(weight="bold"))
        theme_option.set(ctk.get_appearance_mode())
        theme_option.pack(side="right", padx=20)

        # Master Password Change
        pass_box = ctk.CTkFrame(card, fg_color=("gray95", "#0F172A"), corner_radius=12)
        pass_box.pack(fill="x", padx=40, pady=10)

        ctk.CTkLabel(pass_box, text="Master Security", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=20, pady=20)

        change_mp_btn = ctk.CTkButton(
            pass_box, text="Change Master Password", fg_color="#3B82F6", font=ctk.CTkFont(weight="bold"),
            command=self.open_change_master_password_modal
        )
        change_mp_btn.pack(side="right", padx=20)

    def open_change_master_password_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Change Master Password")
        modal.geometry("400x350")
        modal.grab_set()

        card = ctk.CTkFrame(modal, fg_color=("white", "#1E293B"))
        card.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(card, text="Change Master Password", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 15))

        new_pass = ctk.CTkEntry(card, width=320, placeholder_text="New Master Password", show="•")
        new_pass.pack(pady=8)

        confirm_pass = ctk.CTkEntry(card, width=320, placeholder_text="Confirm New Master Password", show="•")
        confirm_pass.pack(pady=8)

        err_lbl = ctk.CTkLabel(card, text="", text_color="#EF4444")
        err_lbl.pack(pady=4)

        def do_change():
            p1 = new_pass.get().strip()
            p2 = confirm_pass.get().strip()
            if not p1 or not p2:
                err_lbl.configure(text="Fields cannot be empty.")
                return
            if p1 != p2:
                err_lbl.configure(text="Passwords do not match.")
                return
            if len(p1) < 6:
                err_lbl.configure(text="Password must be at least 6 chars.")
                return

            create_master_password(p1)
            ok, msg, vault, salt = verify_master_password(p1)
            if ok:
                self.vault = vault
                self.master_password = p1
                self.salt = salt
                modal.destroy()
                self.show_toast("Master Password changed successfully!")

        ctk.CTkButton(card, text="Update Password", fg_color="#10B981", command=do_change).pack(pady=15)

    def lock_vault(self):
        self.vault = {}
        self.master_password = None
        self.salt = None
        self.show_auth_screen()


def main():
    app = VaultGuardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
