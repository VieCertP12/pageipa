import customtkinter as ctk
from tkinter import filedialog, messagebox
import requests
import base64
import os
import threading
import sys
import urllib.parse
import zipfile
import plistlib
import subprocess
import shutil
import time
import io
import datetime
from PIL import Image

# --- CONFIG CỦA BẠN (CẬP NHẬT LẠI TOKEN NẾU CẦN) ---
DOMAIN = "sharechungchi.com"
OWNER = "VieCertP12"
REPO = "pageipa"
# Token này lấy từ code bạn gửi, hãy đảm bảo nó còn sống
TOKEN_DEFAULT = "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" 
TAG_RELEASE = "esignipa" # Nơi chứa file nặng
LINK4SUB_BASE_URL = f"https://{DOMAIN}/link4sub/"

# Thư mục local (Để Git đẩy lên)
LOCAL_IPA_DIR = "ipa"
LOCAL_PLIST_DIR = "esignplist"

# --- FIREBASE CHECK ---
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

# --- CRYPTOGRAPHY CHECK ---
try:
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.hazmat.backends import default_backend
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- COLORS & THEME ---
COLOR_BG_MAIN = "#F5F5F7"
COLOR_SIDEBAR = "#E8E8ED"
COLOR_CARD    = "#FFFFFF"
COLOR_ACCENT  = "#007AFF"
COLOR_SUCCESS = "#34C759"
COLOR_ERROR   = "#FF3B30"
COLOR_TEXT    = "#1D1D1F"

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class ThaiSonV50(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Thái Sơn Tool V51 - Git Hybrid Pro") # Đổi tên nhẹ để phân biệt
        self.geometry("1100x850")
        self.configure(fg_color=COLOR_BG_MAIN)
        try: self.iconbitmap(resource_path("icon.ico"))
        except: pass

        # --- VARIABLES ---
        self.token_var = ctk.StringVar(value=TOKEN_DEFAULT)
        self.tag_var = ctk.StringVar(value=TAG_RELEASE)
        self.operation_mode = ctk.IntVar(value=0) 
        
        # Cert Vars
        self.p12_path = ctk.StringVar()
        self.prov_path = ctk.StringVar()
        self.p12_pass = ctk.StringVar()
        
        # Auto Check Vars
        self.cert_real_cn = ctk.StringVar(value="Chưa có thông tin")
        self.cert_status_str = ctk.StringVar(value="Waiting...")
        
        # App Info Vars
        self.ipa_path = ctk.StringVar()
        self.status_msg = ctk.StringVar(value="Sẵn sàng.")
        self.final_link = ctk.StringVar()
        self.app_name = ctk.StringVar()
        self.bundle_id = ctk.StringVar()
        self.version = ctk.StringVar(value="1.0")
        self.plist_name = ctk.StringVar()
        self.icon_path = ctk.StringVar()
        self.use_custom_icon = ctk.BooleanVar(value=False)

        # Config Vars
        self.use_link4sub = ctk.BooleanVar(value=True)
        self.l4s_title = ctk.StringVar(value="Tải App")
        self.l4s_subtitle = ctk.StringVar(value="Lấy link tải xuống...")
        self.l4s_note = ctk.StringVar(value="")

        self.sync_web = ctk.BooleanVar(value=True)
        self.app_desc = ctk.StringVar(value="")
        self.app_type = ctk.StringVar(value="esign")
        self.app_badge = ctk.StringVar(value="")
        self.use_custom_web_name = ctk.BooleanVar(value=False)
        self.web_custom_name = ctk.StringVar(value="")

        # Auto Trigger Check khi nhập pass
        self.p12_pass.trace_add("write", lambda *args: self.check_certificate_details())
        self.p12_path.trace_add("write", lambda *args: self.check_certificate_details())

        self.db_admin = None; self.db_l4s = None      
        threading.Thread(target=self.connect_databases, daemon=True).start()
        
        # Tạo thư mục local nếu chưa có
        if not os.path.exists(LOCAL_IPA_DIR): os.makedirs(LOCAL_IPA_DIR)
        if not os.path.exists(LOCAL_PLIST_DIR): os.makedirs(LOCAL_PLIST_DIR)

        self.setup_ui()

    def connect_databases(self):
        if not FIREBASE_AVAILABLE: self.status_msg.set("⚠️ Thiếu thư viện firebase"); return
        try:
            k1 = resource_path("firebase_key.json")
            if os.path.exists(k1):
                c1 = credentials.Certificate(k1)
                a1 = firebase_admin.initialize_app(c1, name="app_admin")
                self.db_admin = firestore.client(app=a1)
        except: pass
        try:
            k2 = resource_path("link4sub_key.json")
            if os.path.exists(k2):
                c2 = credentials.Certificate(k2)
                a2 = firebase_admin.initialize_app(c2, name="app_l4s")
                self.db_l4s = firestore.client(app=a2)
        except: pass

    # --- UI SETUP (GIỮ NGUYÊN GIAO DIỆN BẠN GỬI) ---
    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)

        # SIDEBAR
        self.sidebar = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="THÁI SƠN\nTOOL V51", font=("Arial", 20, "bold"), text_color=COLOR_ACCENT).pack(pady=(30, 20))
        
        f_con = ctk.CTkFrame(self.sidebar, fg_color="transparent"); f_con.pack(fill="x", padx=10)
        self.ent_tk = ctk.CTkEntry(f_con, textvariable=self.token_var, show="•", height=30); self.ent_tk.pack(fill="x", pady=(0,5))
        ctk.CTkButton(f_con, text="KẾT NỐI API", height=30, fg_color="#34C759", command=self.load_tags_thread).pack(fill="x")
        self.combo_tag = ctk.CTkComboBox(f_con, variable=self.tag_var, height=30); self.combo_tag.pack(fill="x", pady=(5,0))
        self.lbl_status = ctk.CTkLabel(self.sidebar, textvariable=self.status_msg, font=("Arial", 11), text_color="#555", wraplength=180, justify="left")
        self.lbl_status.pack(side="bottom", padx=10, pady=10)

        # MAIN VIEW
        self.main_view = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_view.grid(row=0, column=1, sticky="nsew", padx=20, pady=10)

        # 1. MODE & FILE
        self.add_section("1. CHẾ ĐỘ & FILE IPA")
        c1 = self.create_card()
        
        # Mode Selection
        f_mode = ctk.CTkFrame(c1, fg_color="transparent"); f_mode.pack(fill="x", pady=5)
        self.rad_a = ctk.CTkRadioButton(f_mode, text="Giữ nguyên (Đã Sign)", variable=self.operation_mode, value=0, command=self.toggle_ui_mode, font=("Arial", 12))
        self.rad_a.pack(side="left", padx=20)
        self.rad_b = ctk.CTkRadioButton(f_mode, text="Mod & Sign (Cần Cert)", variable=self.operation_mode, value=1, command=self.toggle_ui_mode, font=("Arial", 12, "bold"))
        self.rad_b.pack(side="left", padx=20)

        # IPA Selection
        f_fl = ctk.CTkFrame(c1, fg_color="#F2F2F7", corner_radius=6); f_fl.pack(fill="x", pady=10, padx=10)
        ctk.CTkEntry(f_fl, textvariable=self.ipa_path, height=35, border_width=0, fg_color="transparent", placeholder_text="Đường dẫn file .ipa").pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(f_fl, text="CHỌN FILE", width=100, fg_color="#5856D6", command=self.browse_ipa).pack(side="right", padx=5, pady=3)

        # 2. INFO APP
        self.add_section("2. THÔNG TIN ỨNG DỤNG")
        self.card_info = self.create_card()
        f_gd = ctk.CTkFrame(self.card_info, fg_color="transparent"); f_gd.pack(fill="x", pady=5)
        self.ent_name = self.add_input(f_gd, "Tên App:", self.app_name, 0, 0)
        self.ent_ver = self.add_input(f_gd, "Version:", self.version, 0, 1)
        self.ent_id = self.add_input(f_gd, "Bundle ID:", self.bundle_id, 1, 0)
        self.ent_plist = self.add_input(f_gd, "Tên Plist:", self.plist_name, 1, 1)
        
        f_ic = ctk.CTkFrame(self.card_info, fg_color="transparent"); f_ic.pack(fill="x", pady=5, padx=10)
        self.chk_icon = ctk.CTkCheckBox(f_ic, text="Thay Icon", variable=self.use_custom_icon, command=self.toggle_icon); self.chk_icon.pack(side="left")
        self.btn_icon = ctk.CTkButton(f_ic, text="Chọn Ảnh...", width=80, height=25, command=self.browse_icon, state="disabled"); self.btn_icon.pack(side="left", padx=10)

        # --- CERT SECTION ---
        self.box_cert = ctk.CTkFrame(self.main_view, fg_color=COLOR_CARD, corner_radius=10)
        
        f_hc = ctk.CTkFrame(self.box_cert, fg_color="transparent"); f_hc.pack(fill="x", padx=15, pady=(15,0))
        ctk.CTkLabel(f_hc, text="CẤU HÌNH CHỨNG CHỈ", font=("Arial", 12, "bold"), text_color="#888").pack(anchor="w")

        f_pw = ctk.CTkFrame(self.box_cert, fg_color="transparent"); f_pw.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(f_pw, text="Mật khẩu P12:", font=("Arial", 12, "bold")).pack(side="left", padx=(0,10))
        ctk.CTkEntry(f_pw, textvariable=self.p12_pass, width=250, placeholder_text="Nhập mật khẩu...").pack(side="left", fill="x", expand=True)

        f_act = ctk.CTkFrame(self.box_cert, fg_color="transparent"); f_act.pack(fill="x", padx=15, pady=5)
        self.btn_zip = ctk.CTkButton(f_act, text="📂 NHẬP TỪ ZIP (AUTO)", height=35, fg_color="#FF9500", font=("Arial", 12, "bold"), command=self.import_cert_from_zip)
        self.btn_zip.pack(side="left", fill="x", expand=True, padx=(0, 5))

        f_man = ctk.CTkFrame(f_act, fg_color="transparent"); f_man.pack(side="right", fill="x", expand=True, padx=(5, 0))
        ctk.CTkButton(f_man, text="Chọn P12", width=90, height=35, fg_color="#E5E5EA", text_color="black", command=lambda: self.browse(self.p12_path, "P12", "*.p12")).pack(side="left", padx=2)
        ctk.CTkButton(f_man, text="Chọn Prov", width=90, height=35, fg_color="#E5E5EA", text_color="black", command=lambda: self.browse(self.prov_path, "Prov", "*.mobileprovision")).pack(side="left", padx=2)

        f_paths = ctk.CTkFrame(self.box_cert, fg_color="transparent"); f_paths.pack(fill="x", padx=15, pady=(5,0))
        self.ent_p12_disp = ctk.CTkEntry(f_paths, textvariable=self.p12_path, state="readonly", height=20, font=("Arial", 10), border_width=0, fg_color="transparent", text_color="gray")
        self.ent_p12_disp.pack(fill="x")
        self.ent_prov_disp = ctk.CTkEntry(f_paths, textvariable=self.prov_path, state="readonly", height=20, font=("Arial", 10), border_width=0, fg_color="transparent", text_color="gray")
        self.ent_prov_disp.pack(fill="x")

        f_live = ctk.CTkFrame(self.box_cert, fg_color="#F2F2F7", corner_radius=6)
        f_live.pack(fill="x", padx=15, pady=(5, 15))
        
        f_l1 = ctk.CTkFrame(f_live, fg_color="transparent"); f_l1.pack(fill="x", padx=10, pady=(8,2))
        ctk.CTkLabel(f_l1, text="Cert Name (CN):", width=110, anchor="w", font=("Arial", 11, "bold"), text_color="#555").pack(side="left")
        self.ent_cn = ctk.CTkEntry(f_l1, textvariable=self.cert_real_cn, state="readonly", border_width=0, fg_color="transparent", font=("Arial", 11, "bold"), text_color=COLOR_ACCENT)
        self.ent_cn.pack(side="left", fill="x", expand=True)

        f_l2 = ctk.CTkFrame(f_live, fg_color="transparent"); f_l2.pack(fill="x", padx=10, pady=(0,8))
        ctk.CTkLabel(f_l2, text="Status:", width=110, anchor="w", font=("Arial", 11, "bold"), text_color="#555").pack(side="left")
        self.ent_status = ctk.CTkEntry(f_l2, textvariable=self.cert_status_str, state="readonly", border_width=0, fg_color="transparent", font=("Arial", 12, "bold"))
        self.ent_status.pack(side="left", fill="x", expand=True)


        # 3. ADVANCED CONFIG
        self.add_section("3. CẤU HÌNH WEB & SHORT LINK")
        c_adv = self.create_card()
        
        f_sw1 = ctk.CTkFrame(c_adv, fg_color="transparent"); f_sw1.pack(fill="x", pady=5)
        self.sw_l4s = ctk.CTkSwitch(f_sw1, text="Dùng Link4Sub", variable=self.use_link4sub, font=("Arial", 12, "bold"), command=self.toggle_l4s_ui)
        self.sw_l4s.pack(side="left", padx=10)
        self.sw_sync = ctk.CTkSwitch(f_sw1, text="Sync 3060ti Admin", variable=self.sync_web, font=("Arial", 12, "bold"), command=self.toggle_web_ui)
        self.sw_sync.pack(side="left", padx=20)

        self.box_l4s = ctk.CTkFrame(c_adv, fg_color="#F9F9F9", corner_radius=6)
        self.add_input_simple(self.box_l4s, "Tiêu đề:", self.l4s_title)
        self.add_input_simple(self.box_l4s, "Phụ đề:", self.l4s_subtitle)
        
        self.box_web = ctk.CTkFrame(c_adv, fg_color="#F9F9F9", corner_radius=6)
        ctk.CTkCheckBox(self.box_web, text="Đổi tên Web", variable=self.use_custom_web_name, command=self.toggle_web_name).pack(anchor="w", padx=10, pady=5)
        self.ent_web_name = ctk.CTkEntry(self.box_web, textvariable=self.web_custom_name, placeholder_text="Tên hiển thị...")
        f_types = ctk.CTkFrame(self.box_web, fg_color="transparent"); f_types.pack(fill="x", pady=5, padx=10)
        ctk.CTkComboBox(f_types, variable=self.app_type, values=["esign", "cert", "mods"], width=100).pack(side="left")
        ctk.CTkComboBox(f_types, variable=self.app_badge, values=["", "HOT", "NEW"], width=80).pack(side="left", padx=10)

        # RUN BUTTON (Nút quan trọng)
        self.btn_run = ctk.CTkButton(self.main_view, text="TIẾN HÀNH UPLOAD (GIT HYBRID)", height=45, font=("Arial", 14, "bold"), fg_color=COLOR_ACCENT, command=self.start_thread)
        self.btn_run.pack(fill="x", pady=20)
        
        f_res = ctk.CTkFrame(self.main_view, fg_color="white", corner_radius=8); f_res.pack(fill="x")
        self.ent_link = ctk.CTkEntry(f_res, textvariable=self.final_link, state="readonly", border_width=0, fg_color="transparent", justify="center")
        self.ent_link.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(f_res, text="Copy", width=60, fg_color="#EEE", text_color="black", command=self.copy_link).pack(side="right", padx=5, pady=5)

        self.after(100, lambda: [self.toggle_ui_mode(), self.toggle_l4s_ui(), self.toggle_web_ui(), self.toggle_web_name()])

    # --- UI HELPERS ---
    def create_card(self):
        f = ctk.CTkFrame(self.main_view, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color="#E5E5EA")
        f.pack(fill="x", pady=5, ipadx=10, ipady=10); return f
    def add_section(self, t): ctk.CTkLabel(self.main_view, text=t, font=("Arial", 13, "bold"), text_color="#888", anchor="w").pack(fill="x", pady=(20,5))
    def add_input(self, p, lbl, var, r, c):
        f = ctk.CTkFrame(p, fg_color="transparent"); f.grid(row=r, column=c, sticky="ew", padx=5, pady=5); p.grid_columnconfigure(c, weight=1)
        ctk.CTkLabel(f, text=lbl, font=("Arial", 11, "bold"), text_color="#555", anchor="w").pack(fill="x")
        e = ctk.CTkEntry(f, textvariable=var, height=30); e.pack(fill="x")
        return e
    def add_input_simple(self, p, lbl, var):
        f = ctk.CTkFrame(p, fg_color="transparent"); f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=lbl, width=80, anchor="w", font=("Arial", 11)).pack(side="left", padx=10)
        ctk.CTkEntry(f, textvariable=var, height=30).pack(side="left", fill="x", expand=True, padx=(0,10))

    # --- LOGIC GIAO DIỆN ---
    def toggle_ui_mode(self):
        m = self.operation_mode.get()
        if m == 0:
            self.rad_a.configure(text_color=COLOR_ACCENT, font=("Arial", 12, "bold"))
            self.rad_b.configure(text_color=COLOR_TEXT, font=("Arial", 12, "normal"))
            self.box_cert.pack_forget()
            for e in [self.ent_name, self.ent_id, self.ent_ver]: e.configure(state="readonly", fg_color="#F5F5F7")
            self.chk_icon.configure(state="disabled")
        else:
            self.rad_a.configure(text_color=COLOR_TEXT, font=("Arial", 12, "normal"))
            self.rad_b.configure(text_color=COLOR_ACCENT, font=("Arial", 12, "bold"))
            self.box_cert.pack(fill="x", pady=10, after=self.card_info)
            for e in [self.ent_name, self.ent_id, self.ent_ver]: e.configure(state="normal", fg_color="white")
            self.chk_icon.configure(state="normal")

    def toggle_l4s_ui(self):
        if self.use_link4sub.get(): self.box_l4s.pack(fill="x", padx=10, pady=5)
        else: self.box_l4s.pack_forget()
    def toggle_web_ui(self):
        if self.sync_web.get(): self.box_web.pack(fill="x", padx=10, pady=5)
        else: self.box_web.pack_forget()
    def toggle_web_name(self):
        if self.use_custom_web_name.get(): self.ent_web_name.pack(fill="x", padx=10, pady=5)
        else: self.ent_web_name.pack_forget()

    # --- LOGIC CORE ---
    def log(self, s): self.status_msg.set(s)
    
    def browse(self, v, t, e): 
        f = filedialog.askopenfilename(filetypes=[(t,e)])
        if f: v.set(f)

    def import_cert_from_zip(self):
        zip_path = filedialog.askopenfilename(filetypes=[("Zip Cert", "*.zip")])
        if not zip_path: return
        try:
            extract_path = resource_path("temp_cert_extracted")
            if os.path.exists(extract_path): shutil.rmtree(extract_path) 
            os.makedirs(extract_path)
            found_p12 = None; found_prov = None
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(extract_path)
                for root, dirs, files in os.walk(extract_path):
                    for file in files:
                        if file.endswith(".p12") and not found_p12: found_p12 = os.path.abspath(os.path.join(root, file))
                        elif file.endswith(".mobileprovision") and not found_prov: found_prov = os.path.abspath(os.path.join(root, file))
            if found_p12: self.p12_path.set(found_p12)
            if found_prov: self.prov_path.set(found_prov)
            self.log("✅ Đã nhập Zip. Hãy nhập mật khẩu.")
        except Exception as e: self.log(f"Lỗi Zip: {e}")

    def check_certificate_details(self):
        if not CRYPTO_AVAILABLE: return
        p12 = self.p12_path.get(); pwd = self.p12_pass.get()
        if not os.path.exists(p12): return
        try:
            with open(p12, "rb") as f: p12_data = f.read()
            p12_obj = pkcs12.load_key_and_certificates(p12_data, pwd.encode() if pwd else b"", backend=default_backend())
            cert = p12_obj[1]
            try: cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            except: cn = "Unknown"
            self.cert_real_cn.set(cn)
            now = datetime.datetime.now(); not_after = cert.not_valid_after
            if now > not_after:
                self.cert_status_str.set(f"ĐÃ HẾT HẠN (Expired: {not_after.strftime('%Y-%m-%d')})")
                self.ent_status.configure(text_color=COLOR_ERROR)
            else:
                days = (not_after - now).days
                self.cert_status_str.set(f"LIVE (Còn {days} ngày) - Exp: {not_after.strftime('%Y-%m-%d')})")
                self.ent_status.configure(text_color=COLOR_SUCCESS)
        except ValueError:
            self.cert_status_str.set("Sai Mật khẩu P12")
            self.ent_status.configure(text_color=COLOR_ERROR)
        except Exception:
            self.cert_status_str.set("Chưa thể đọc file...")
            self.ent_status.configure(text_color="gray")

    def browse_icon(self): self.browse(self.icon_path, "Img", "*.png;*.jpg")
    def browse_ipa(self):
        f = filedialog.askopenfilename(filetypes=[("IPA", "*.ipa")])
        if f: 
            self.ipa_path.set(f); self.plist_name.set(os.path.splitext(os.path.basename(f))[0].replace(" ", "_"))
            threading.Thread(target=self.analyze_ipa, args=(f,), daemon=True).start()
    
    def toggle_icon(self): self.btn_icon.configure(state="normal" if self.use_custom_icon.get() else "disabled")
    
    def analyze_ipa(self, path):
        try:
            with zipfile.ZipFile(path, 'r') as z:
                c = [n for n in z.namelist() if n.endswith("Info.plist") and "Payload/" in n]; c.sort(key=len)
                if c:
                    with z.open(c[0]) as p:
                        d = plistlib.load(p)
                        self.after(0, lambda: [
                            self.app_name.set(d.get("CFBundleDisplayName") or d.get("CFBundleName") or "App"),
                            self.bundle_id.set(d.get("CFBundleIdentifier") or "com.app"),
                            self.version.set(d.get("CFBundleShortVersionString") or "1.0")
                        ])
        except: pass

    def load_tags_thread(self): threading.Thread(target=self.load_tags, daemon=True).start()
    def load_tags(self):
        # Hàm này giữ lại để check API, nhưng không quan trọng bằng Git Push
        try:
            r = requests.get(f"https://api.github.com/repos/{OWNER}/{REPO}/releases", headers={"Authorization":f"token {self.token_var.get()}"})
            if r.ok: self.combo_tag.configure(values=[x['tag_name'] for x in r.json()]); self.tag_var.set(r.json()[0]['tag_name']); self.log("Đã tải Tag.")
        except: self.log("Lỗi tải Tag.")
        
    def copy_link(self): self.clipboard_clear(); self.clipboard_append(self.final_link.get()); self.log("Copied.")

    # --- NEW: EXTRACT ICON FROM IPA ---
    def extract_icon_from_ipa(self, ipa_path):
        try:
            temp_icon_path = "temp_extracted_icon.png"
            max_size = 0; best_file = None
            with zipfile.ZipFile(ipa_path, 'r') as z:
                for n in z.namelist():
                    if n.startswith("Payload/") and n.endswith(".png") and "AppIcon" in n:
                        info = z.getinfo(n)
                        if info.file_size > max_size: max_size = info.file_size; best_file = n
                if not best_file:
                    for n in z.namelist():
                        if n.startswith("Payload/") and n.endswith(".png") and not "Launch" in n:
                            info = z.getinfo(n)
                            if info.file_size > max_size: max_size = info.file_size; best_file = n
                if best_file:
                    with z.open(best_file) as src, open(temp_icon_path, "wb") as dst: shutil.copyfileobj(src, dst)
                    return temp_icon_path
            return None
        except Exception as e: print(f"Lỗi extract icon: {e}"); return None

    # --- SIGNING LOGIC ---
    def modify_and_sign(self, ipa_in, ipa_out, icon_in, new_id, new_name):
        self.log("🔧 Đang Mod & Sign...")
        try:
            icon_data = None
            if icon_in: img = Image.open(icon_in).convert("RGBA").resize((180, 180)); buf = io.BytesIO(); img.save(buf, "PNG"); icon_data = buf.getvalue()
            temp_mod = "temp_modded.ipa"
            with zipfile.ZipFile(ipa_in, 'r') as zin:
                with zipfile.ZipFile(temp_mod, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
                    c = [n for n in zin.namelist() if n.endswith("Info.plist") and "Payload/" in n]; c.sort(key=len); info_path = c[0] if c else None
                    app_folder = os.path.dirname(info_path) if info_path else ""
                    for item in zin.infolist():
                        if icon_data and "AppIcon" in item.filename and item.filename.endswith(".png"): continue
                        if item.filename == info_path:
                            try:
                                pl = plistlib.loads(zin.read(item))
                                pl['CFBundleIdentifier'] = new_id; pl['CFBundleDisplayName'] = new_name; pl['CFBundleName'] = new_name
                                if icon_data:
                                    if 'CFBundleIcons' in pl: del pl['CFBundleIcons'] 
                                    if 'CFBundleIconFiles' in pl: del pl['CFBundleIconFiles']
                                    pl['CFBundleIconFiles'] = ["IconV50"]; pl['CFBundleIcons'] = {'CFBundlePrimaryIcon': {'CFBundleIconFiles': ["IconV50"],'CFBundleIconName': "IconV50"}}
                                zout.writestr(item, plistlib.dumps(pl))
                            except: zout.writestr(item, zin.read(item))
                        else: zout.writestr(item, zin.read(item))
                    if icon_data and app_folder: zout.writestr(f"{app_folder}/IconV50.png", icon_data)
            
            p12, prov, pw = self.p12_path.get(), self.prov_path.get(), self.p12_pass.get()
            zsign = resource_path("zsign.exe")
            if not os.path.exists(zsign): raise Exception("Không tìm thấy zsign.exe")
            cmd = f'"{zsign}" -k "{p12}" -p "{pw}" -m "{prov}" -o "{ipa_out}" -z 9 -f "{temp_mod}"'
            subprocess.run(cmd, shell=True)
            if os.path.exists(temp_mod): os.remove(temp_mod)
            return True
        except Exception as e: print(e); return False

    def create_link4sub(self, title, subtitle, note, dest_url):
        if not self.db_l4s: return dest_url
        self.log("🔗 Đang tạo Link4Sub...")
        try:
            def enc(s): return base64.b64encode(urllib.parse.quote(s).encode()).decode()[::-1]
            payload = {"title": title, "subtitle": subtitle, "note": note, "destUrl": enc(dest_url), "type": "link", "active": False, "createdAt": datetime.datetime.now().isoformat(), "views": 0, "tasks": {}, "order": int(time.time())}
            doc_ref = self.db_l4s.collection('artifacts').document('link4sub-pro').collection('public').document('data').collection('links').add(payload)
            return f"{LINK4SUB_BASE_URL}?id={doc_ref[1].id}"
        except Exception as e: return dest_url

    def upload_to_admin(self, name, desc, url, icon, category, badge):
        if not self.db_admin: return
        self.log("☁️ Sync Firebase Admin...")
        try:
            doc_data = {"type":category, "name":name, "desc":desc, "url":url, "icon":icon, "badge":badge, "status":"hidden", "tag":"fire", "updatedAt":datetime.datetime.now().isoformat(), "downloads":0, "order":int(time.time())}
            self.db_admin.collection("apps").add(doc_data)
            messagebox.showinfo("Thành Công", "Đã Upload & Sync Web!")
        except Exception as e: self.log(f"Lỗi Admin: {e}")

    def upload_release(self, path, name):
        """Hàm phụ trợ để upload file nặng lên Release"""
        h = {"Authorization": f"token {self.token_var.get()}"}
        r = requests.get(f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{TAG_RELEASE}", headers=h).json()
        if 'id' not in r: r = requests.post(f"https://api.github.com/repos/{OWNER}/{REPO}/releases", headers=h, json={"tag_name": TAG_RELEASE}).json()
        
        up_url = f"https://uploads.github.com/repos/{OWNER}/{REPO}/releases/{r['id']}/assets?name={name}"
        with open(path, "rb") as f:
            rp = requests.post(up_url, headers={"Authorization": f"token {self.token_var.get()}", "Content-Type": "application/octet-stream"}, data=f)
        return f"https://github.com/{OWNER}/{REPO}/releases/download/{TAG_RELEASE}/{name}" if rp.ok else None

    # ==========================================
    # LOGIC CHÍNH: HYBRID (GIT PUSH + AUTO SIZE)
    # ==========================================
    def start_thread(self): threading.Thread(target=self.run, daemon=True).start()
    
    def run(self):
        ipa = self.ipa_path.get()
        if not ipa: return self.log("❌ Chưa chọn IPA")
        self.btn_run.configure(state="disabled", text="ĐANG XỬ LÝ...")
        
        try:
            work_ipa = ipa
            final_id = self.bundle_id.get(); final_name = self.app_name.get()
            clean_name = os.path.basename(ipa).replace(" ", "_"); clean_name = clean_name if clean_name.endswith(".ipa") else clean_name+".ipa"
            out_ipa = "signed.ipa"; icon_url = "https://placehold.co/100"
            
            # 1. SIGN NẾU CẦN
            if self.operation_mode.get() == 1:
                self.log("🔧 Đang Sign App...")
                # Nếu không chọn icon thì giữ icon gốc
                icon_arg = self.icon_path.get() if (self.use_custom_icon.get() and self.icon_path.get()) else None
                if self.modify_and_sign(work_ipa, out_ipa, icon_arg, final_id, final_name):
                    work_ipa = out_ipa

            # 2. XỬ LÝ ICON
            # Ưu tiên icon user chọn, nếu không thì extract
            icon_to_use = None
            if self.use_custom_icon.get() and self.icon_path.get(): icon_to_use = self.icon_path.get()
            else:
                self.log("🖼️ Trích xuất icon...")
                extracted = self.extract_icon_from_ipa(work_ipa)
                if extracted: icon_to_use = extracted

            # Copy icon vào thư mục local để Git Push luôn
            if icon_to_use:
                icon_name = f"icon_{int(time.time())}.png"
                dest_icon = os.path.join(LOCAL_IPA_DIR, icon_name)
                shutil.copy2(icon_to_use, dest_icon)
                icon_url = f"https://{DOMAIN}/{LOCAL_IPA_DIR}/{icon_name}"

            # 3. KIỂM TRA DUNG LƯỢNG & UPLOAD IPA
            size_mb = os.path.getsize(work_ipa) / (1024*1024)
            self.log(f"📦 Dung lượng: {size_mb:.2f} MB")
            final_dl_link = ""

            if size_mb < 98: # File Nhẹ -> Copy vào thư mục -> Git Push
                self.log("📂 File NHẸ: Copy vào thư mục Local...")
                dest_ipa = os.path.join(LOCAL_IPA_DIR, clean_name)
                shutil.copy2(work_ipa, dest_ipa)
                final_dl_link = f"https://{DOMAIN}/{LOCAL_IPA_DIR}/{clean_name}"
            else: # File Nặng -> Upload Release -> Git Push Plist
                self.log("🚀 File NẶNG: Upload lên GitHub Releases...")
                final_dl_link = self.upload_release(work_ipa, clean_name)
                if not final_dl_link: raise Exception("Lỗi Upload Release")

            # 4. TẠO PLIST
            self.log("📝 Tạo file Plist...")
            assets = [
                {'kind':'software-package', 'url':final_dl_link},
                {'kind':'display-image', 'url':icon_url},
                {'kind':'full-size-image', 'url':icon_url}
            ]
            pl_content = {'items':[{'assets':assets, 'metadata':{'bundle-identifier':final_id, 'bundle-version':self.version.get(), 'kind':'software', 'title':final_name}}]}
            plist_fn = self.plist_name.get().strip() or clean_name.replace(".ipa", "")
            dest_plist = os.path.join(LOCAL_PLIST_DIR, f"{plist_fn}.plist")
            with open(dest_plist, 'wb') as f: plistlib.dump(pl_content, f)

            # 5. GIT PUSH
            self.log("☁️ Đẩy Code lên GitHub...")
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", f"Auto Up: {final_name}"], capture_output=True)
            push = subprocess.run(["git", "push", "origin", "master:main", "-f"], capture_output=True, text=True, encoding="utf-8")
            
            if push.returncode != 0:
                print(push.stderr) # In lỗi ra console nếu có
                if "too large" in push.stderr: raise Exception("Vẫn dính lỗi file nặng! Hãy chạy lệnh reset git.")

            # 6. LINK FINAL & SYNC
            raw_url = f"https://{DOMAIN}/{LOCAL_PLIST_DIR}/{plist_fn}.plist"
            install_link = f"itms-services://?action=download-manifest&url={raw_url}"
            
            # Link4Sub
            final_url_to_use = install_link
            if self.use_link4sub.get():
                final_url_to_use = self.create_link4sub(self.l4s_title.get(), self.l4s_subtitle.get(), self.l4s_note.get(), install_link)
            
            self.final_link.set(final_url_to_use)
            
            # Firebase Admin
            if self.sync_web.get():
                name_w = self.web_custom_name.get().strip() if (self.use_custom_web_name.get() and self.web_custom_name.get().strip()) else final_name
                self.upload_to_admin(name_w, self.app_desc.get(), final_url_to_use, icon_url, self.app_type.get(), self.app_badge.get())

            self.log("✅ XONG!")
            messagebox.showinfo("OK", "Đã xong!")
            
            # Dọn dẹp
            if os.path.exists("signed.ipa"): os.remove("signed.ipa")
            if os.path.exists("temp_extracted_icon.png"): os.remove("temp_extracted_icon.png")

        except Exception as e: self.log(f"Lỗi: {e}"); messagebox.showerror("Lỗi", str(e))
        finally: self.btn_run.configure(state="normal", text="TIẾN HÀNH UPLOAD")

if __name__ == "__main__":
    app = ThaiSonV50()
    app.mainloop()