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

# --- CONFIG CỦA BẠN ---
DOMAIN = "sharechungchi.com"
OWNER = "VieCertP12"
REPO = "pageipa"
TOKEN_DEFAULT = "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" 
TAG_RELEASE = "esignipa"
LINK4SUB_BASE_URL = f"https://{DOMAIN}/link4sub/"

# Thư mục local
LOCAL_IPA_DIR = "ipa"
LOCAL_PLIST_DIR = "esignplist"

# Check thư viện
try: import firebase_admin; from firebase_admin import credentials, firestore; FIREBASE_AVAILABLE = True
except: FIREBASE_AVAILABLE = False
try: from cryptography.hazmat.primitives.serialization import pkcs12; from cryptography.hazmat.backends import default_backend; CRYPTO_AVAILABLE = True
except: CRYPTO_AVAILABLE = False

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class ThaiSonV61_FixName(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Tool V61 - Tên File Có Số (Timestamp)")
        self.geometry("1100x850")
        
        # Variables
        self.token_var = ctk.StringVar(value=TOKEN_DEFAULT)
        self.operation_mode = ctk.IntVar(value=0)
        self.ipa_path = ctk.StringVar()
        self.status_msg = ctk.StringVar(value="Sẵn sàng.")
        self.final_link = ctk.StringVar()
        
        # App Info
        self.app_name = ctk.StringVar(); self.bundle_id = ctk.StringVar(); self.version = ctk.StringVar(value="1.0")
        self.plist_name = ctk.StringVar(); self.icon_path = ctk.StringVar(); self.use_custom_icon = ctk.BooleanVar(value=False)
        
        # Cert
        self.p12_path = ctk.StringVar(); self.prov_path = ctk.StringVar(); self.p12_pass = ctk.StringVar()
        self.cert_status_str = ctk.StringVar(value="Waiting...")
        
        # Web Config
        self.use_link4sub = ctk.BooleanVar(value=True); self.l4s_title = ctk.StringVar(value="Tải App"); self.l4s_subtitle = ctk.StringVar(value="...")
        self.l4s_note = ctk.StringVar(value="")
        self.sync_web = ctk.BooleanVar(value=True); self.app_desc = ctk.StringVar(value=""); self.app_type = ctk.StringVar(value="esign"); self.app_badge = ctk.StringVar(value="")
        self.use_custom_web_name = ctk.BooleanVar(value=False); self.web_custom_name = ctk.StringVar(value="")
        
        self.db_admin = None; self.db_l4s = None
        threading.Thread(target=self.connect_db, daemon=True).start()
        
        if not os.path.exists(LOCAL_IPA_DIR): os.makedirs(LOCAL_IPA_DIR)
        if not os.path.exists(LOCAL_PLIST_DIR): os.makedirs(LOCAL_PLIST_DIR)
        
        self.setup_ui()

    def connect_db(self):
        if not FIREBASE_AVAILABLE: return
        try:
            if os.path.exists(resource_path("firebase_key.json")): self.db_admin = firestore.client(app=firebase_admin.initialize_app(credentials.Certificate(resource_path("firebase_key.json")), name="app_admin"))
            if os.path.exists(resource_path("link4sub_key.json")): self.db_l4s = firestore.client(app=firebase_admin.initialize_app(credentials.Certificate(resource_path("link4sub_key.json")), name="app_l4s"))
        except: pass

    # --- UI (GIỮ NGUYÊN) ---
    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        sf = ctk.CTkFrame(self, width=220, corner_radius=0); sf.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(sf, text="TOOL V61\nTIMESTAMP MODE", font=("Arial",20,"bold"), text_color="#007AFF").pack(pady=30)
        f_tk = ctk.CTkFrame(sf, fg_color="transparent"); f_tk.pack(fill="x", padx=10)
        ctk.CTkEntry(f_tk, textvariable=self.token_var, show="•").pack(fill="x")
        ctk.CTkLabel(sf, textvariable=self.status_msg, font=("Arial",11), text_color="#555", wraplength=180).pack(side="bottom", pady=20)
        
        mf = ctk.CTkScrollableFrame(self, fg_color="transparent"); mf.grid(row=0, column=1, sticky="nsew", padx=20, pady=10)
        
        self.sec(mf, "1. FILE & CHẾ ĐỘ")
        c1 = self.card(mf)
        fm = ctk.CTkFrame(c1, fg_color="transparent"); fm.pack(fill="x", pady=5)
        ctk.CTkRadioButton(fm, text="Giữ nguyên", variable=self.operation_mode, value=0, command=self.toggle_ui).pack(side="left", padx=20)
        ctk.CTkRadioButton(fm, text="Mod & Sign", variable=self.operation_mode, value=1, command=self.toggle_ui).pack(side="left", padx=20)
        ff = ctk.CTkFrame(c1, fg_color="#F2F2F7"); ff.pack(fill="x", padx=10, pady=10)
        ctk.CTkEntry(ff, textvariable=self.ipa_path, height=35, border_width=0, fg_color="transparent", placeholder_text="Chọn IPA...").pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(ff, text="CHỌN", width=80, command=self.browse_ipa).pack(side="right", padx=5)

        self.sec(mf, "2. THÔNG TIN")
        ci = self.card(mf)
        fi = ctk.CTkFrame(ci, fg_color="transparent"); fi.pack(fill="x")
        self.input(fi, "Tên App:", self.app_name, 0, 0); self.input(fi, "Version:", self.version, 0, 1)
        self.input(fi, "BundleID:", self.bundle_id, 1, 0); self.input(fi, "Plist:", self.plist_name, 1, 1)
        fic = ctk.CTkFrame(ci, fg_color="transparent"); fic.pack(fill="x", pady=5, padx=10)
        self.chk_icon = ctk.CTkCheckBox(fic, text="Thay Icon", variable=self.use_custom_icon, command=self.toggle_icon); self.chk_icon.pack(side="left")
        self.btn_icon = ctk.CTkButton(fic, text="Chọn Ảnh...", width=80, command=self.browse_icon, state="disabled"); self.btn_icon.pack(side="left", padx=10)

        self.box_cert = ctk.CTkFrame(mf, fg_color="white")
        ctk.CTkLabel(self.box_cert, text="CẤU HÌNH SIGN", font=("Arial",12,"bold")).pack(anchor="w", padx=15, pady=10)
        fp = ctk.CTkFrame(self.box_cert, fg_color="transparent"); fp.pack(fill="x", padx=15)
        ctk.CTkEntry(fp, textvariable=self.p12_pass, placeholder_text="Pass P12...").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(fp, text="Chọn P12", width=80, command=lambda:self.browse(self.p12_path,"P12","*.p12")).pack(side="left", padx=5)
        ctk.CTkButton(fp, text="Chọn Prov", width=80, command=lambda:self.browse(self.prov_path,"Prov","*.mobileprovision")).pack(side="left", padx=5)
        self.btn_zip = ctk.CTkButton(self.box_cert, text="NHẬP TỪ ZIP", command=self.import_zip); self.btn_zip.pack(pady=5)

        self.sec(mf, "3. CẤU HÌNH WEB")
        ca = self.card(mf)
        ctk.CTkSwitch(ca, text="Link4Sub", variable=self.use_link4sub, command=self.toggle_ui).pack(anchor="w", padx=10)
        self.box_l4s = ctk.CTkFrame(ca); ctk.CTkEntry(self.box_l4s, textvariable=self.l4s_title).pack(fill="x")
        ctk.CTkSwitch(ca, text="Sync Admin", variable=self.sync_web, command=self.toggle_ui).pack(anchor="w", padx=10)
        self.box_web = ctk.CTkFrame(ca); ctk.CTkEntry(self.box_web, textvariable=self.app_desc).pack(fill="x")

        self.btn_run = ctk.CTkButton(mf, text="TIẾN HÀNH UPLOAD", height=45, font=("Arial",14,"bold"), fg_color="#34C759", command=self.start_thread)
        self.btn_run.pack(fill="x", pady=20)
        fr = ctk.CTkFrame(mf, fg_color="white"); fr.pack(fill="x")
        ctk.CTkEntry(fr, textvariable=self.final_link, state="readonly", justify="center").pack(side="left", fill="x", expand=True, padx=10, pady=10)
        ctk.CTkButton(fr, text="Copy", width=60, command=lambda: [self.clipboard_clear(), self.clipboard_append(self.final_link.get())]).pack(side="right", padx=5)

        self.toggle_ui()

    # --- HELPERS ---
    def sec(self, p, t): ctk.CTkLabel(p, text=t, font=("Arial",13,"bold"), text_color="#888", anchor="w").pack(fill="x", pady=(20,5))
    def card(self, p): f=ctk.CTkFrame(p, fg_color="white"); f.pack(fill="x", pady=5, ipadx=5, ipady=5); return f
    def input(self, p, l, v, r, c): f=ctk.CTkFrame(p, fg_color="transparent"); f.grid(row=r, column=c, sticky="ew", padx=5, pady=5); p.grid_columnconfigure(c, weight=1); ctk.CTkLabel(f, text=l).pack(anchor="w"); ctk.CTkEntry(f, textvariable=v).pack(fill="x")
    def browse(self, v, t, e): 
        f=filedialog.askopenfilename(filetypes=[(t,e)])
        if f: v.set(f)
    def browse_icon(self): self.browse(self.icon_path, "Img", "*.png;*.jpg")
    def browse_ipa(self):
        f = filedialog.askopenfilename(filetypes=[("IPA", "*.ipa")])
        if f:
            self.ipa_path.set(f); self.plist_name.set(os.path.splitext(os.path.basename(f))[0].replace(" ", "_"))
            threading.Thread(target=self.analyze_ipa, args=(f,), daemon=True).start()
    def analyze_ipa(self, path):
        try:
            with zipfile.ZipFile(path, 'r') as z:
                c=[n for n in z.namelist() if n.endswith("Info.plist") and "Payload/" in n]; c.sort(key=len)
                if c:
                    d=plistlib.loads(z.read(c[0]))
                    self.app_name.set(d.get("CFBundleDisplayName") or d.get("CFBundleName") or "App")
                    self.bundle_id.set(d.get("CFBundleIdentifier") or "com.app")
                    self.version.set(d.get("CFBundleShortVersionString") or "1.0")
        except: pass
    
    def toggle_ui(self):
        self.box_cert.pack(fill="x", pady=10, after=self.card_info) if self.operation_mode.get()==1 else self.box_cert.pack_forget()
        self.box_l4s.pack(fill="x", padx=10) if self.use_link4sub.get() else self.box_l4s.pack_forget()
        self.box_web.pack(fill="x", padx=10) if self.sync_web.get() else self.box_web.pack_forget()
        self.chk_icon.configure(state="normal" if self.operation_mode.get()==1 else "disabled")
        self.btn_icon.configure(state="normal" if self.use_custom_icon.get() and self.operation_mode.get()==1 else "disabled")
    def toggle_icon(self): self.btn_icon.configure(state="normal" if self.use_custom_icon.get() else "disabled")
    def log(self, s): self.status_msg.set(s)
    
    def import_zip(self):
        z = filedialog.askopenfilename(filetypes=[("Zip", "*.zip")])
        if not z: return
        try:
            d = resource_path("temp_cert"); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
            with zipfile.ZipFile(z, 'r') as zi: zi.extractall(d)
            for r,_,fs in os.walk(d):
                for f in fs:
                    if f.endswith(".p12"): self.p12_path.set(os.path.join(r,f))
                    if f.endswith(".mobileprovision"): self.prov_path.set(os.path.join(r,f))
            self.log("Đã nhập Zip!")
        except: self.log("Lỗi Zip")

    def extract_icon(self, ipa):
        try:
            with zipfile.ZipFile(ipa, 'r') as z:
                l = [n for n in z.namelist() if "AppIcon" in n and n.endswith(".png")]
                if not l: l = [n for n in z.namelist() if n.endswith(".png") and "Payload" in n]
                if l:
                    d = z.read(l[0]); p="temp_icon.png"
                    with open(p, "wb") as f: f.write(d)
                    return p
        except: pass
        return None
    
    def sign_app(self, ipa, out):
        zsign = resource_path("zsign.exe")
        if not os.path.exists(zsign): return False
        cmd = f'"{zsign}" -k "{self.p12_path.get()}" -p "{self.p12_pass.get()}" -m "{self.prov_path.get()}" -o "{out}" -z 9 "{ipa}"'
        subprocess.run(cmd, shell=True)
        return os.path.exists(out)

    def upload_release(self, path, name):
        h = {"Authorization": f"token {self.token_var.get()}"}
        r = requests.get(f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{TAG_RELEASE}", headers=h).json()
        if 'id' not in r: r = requests.post(f"https://api.github.com/repos/{OWNER}/{REPO}/releases", headers=h, json={"tag_name": TAG_RELEASE}).json()
        up = f"https://uploads.github.com/repos/{OWNER}/{REPO}/releases/{r['id']}/assets?name={name}"
        with open(path, "rb") as f:
            rp = requests.post(up, headers={"Authorization": f"token {self.token_var.get()}", "Content-Type": "application/octet-stream"}, data=f)
        return f"https://github.com/{OWNER}/{REPO}/releases/download/{TAG_RELEASE}/{name}" if rp.ok else None

    # ==========================================
    # LOGIC MỚI: TÊN FILE CÓ SỐ (TIMESTAMP)
    # ==========================================
    def start_thread(self): threading.Thread(target=self.run, daemon=True).start()
    
    def run(self):
        ipa = self.ipa_path.get()
        if not ipa: return self.log("❌ Chưa chọn IPA")
        self.btn_run.configure(state="disabled", text="ĐANG XỬ LÝ...")
        
        try:
            work_ipa = ipa
            
            # --- ĐẶT TÊN CHUẨN CÓ SỐ (TIMESTAMP) ---
            timestamp = int(time.time())
            raw_name = os.path.basename(ipa).replace(" ", "_")
            if not raw_name.endswith(".ipa"): raw_name += ".ipa"
            
            # Tên file cuối cùng: 1768638..._TenApp.ipa
            final_filename = f"{timestamp}_{raw_name}"
            
            self.log(f"📝 Tên file mới: {final_filename}")

            out_ipa = "signed.ipa"; icon_url = "https://placehold.co/100"

            # 1. SIGN NẾU CẦN
            if self.operation_mode.get() == 1:
                self.log("🔧 Đang Sign App...")
                if self.sign_app(ipa, out_ipa): work_ipa = out_ipa

            # 2. XỬ LÝ ICON
            icon_src = self.icon_path.get() if (self.use_custom_icon.get() and self.icon_path.get()) else self.extract_icon(work_ipa)
            if icon_src:
                inm = f"icon_{timestamp}.png"
                shutil.copy2(icon_src, os.path.join(LOCAL_IPA_DIR, inm))
                icon_url = f"https://{DOMAIN}/{LOCAL_IPA_DIR}/{inm}"

            # 3. KIỂM TRA DUNG LƯỢNG & COPY
            size_mb = os.path.getsize(work_ipa) / (1024*1024)
            self.log(f"📦 Dung lượng: {size_mb:.2f} MB")
            final_dl_link = ""

            if size_mb < 98: 
                # < 98MB: Copy vào thư mục với TÊN MỚI (có số)
                self.log(f"📂 Đang copy vào folder ipa...")
                dest_ipa = os.path.join(LOCAL_IPA_DIR, final_filename)
                shutil.copy2(work_ipa, dest_ipa)
                
                # Tạo link dựa trên TÊN MỚI
                final_dl_link = f"https://{DOMAIN}/{LOCAL_IPA_DIR}/{final_filename}"
            else:
                # > 98MB: Up Release với TÊN MỚI
                self.log("🚀 File NẶNG: Up Release...")
                final_dl_link = self.upload_release(work_ipa, final_filename)
                if not final_dl_link: raise Exception("Lỗi Upload Release")

            # 4. TẠO PLIST
            self.log("📝 Tạo Plist...")
            assets = [
                {'kind':'software-package', 'url':final_dl_link}, # Link đã có timestamp
                {'kind':'display-image', 'url':icon_url},
                {'kind':'full-size-image', 'url':icon_url}
            ]
            pl_content = {'items':[{'assets':assets, 'metadata':{'bundle-identifier':self.bundle_id.get(), 'bundle-version':self.version.get(), 'kind':'software', 'title':self.app_name.get()}}]}
            
            # Tên file Plist
            pfn = self.plist_name.get().strip() or raw_name.replace(".ipa","") # Plist giữ tên gọn cũng được, hoặc thêm số tùy bạn
            with open(os.path.join(LOCAL_PLIST_DIR, f"{pfn}.plist"), "wb") as f: plistlib.dump(pl_content, f)

            # 5. GIT PUSH
            self.log("☁️ Đẩy GitHub...")
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", f"App: {self.app_name.get()} ({timestamp})"], capture_output=True)
            push = subprocess.run(["git", "push", "origin", "master:main", "-f"], capture_output=True, text=True, encoding="utf-8")
            if push.returncode != 0 and "too large" in push.stderr: raise Exception("Lỗi Git: Dính file nặng cũ! Hãy Reset Git.")

            # 6. KẾT QUẢ
            install = f"itms-services://?action=download-manifest&url=https://{DOMAIN}/{LOCAL_PLIST_DIR}/{pfn}.plist"
            if self.use_link4sub.get() and self.db_l4s:
                enc = base64.b64encode(urllib.parse.quote(install).encode()).decode()[::-1]
                ref = self.db_l4s.collection('artifacts').document('link4sub-pro').collection('public').document('data').collection('links').add({"title":self.l4s_title.get(),"destUrl":enc,"type":"link","active":False,"order":int(time.time())})
                install = f"https://{DOMAIN}/link4sub/?id={ref[1].id}"
            
            if self.sync_web.get() and self.db_admin:
                self.db_admin.collection("apps").add({"type":self.app_type.get(),"name":self.app_name.get(),"url":install,"icon":icon_url,"status":"hidden","updatedAt":datetime.datetime.now().isoformat(),"order":int(time.time())})

            self.final_link.set(install)
            self.log("✅ XONG! (Đã đặt tên chuẩn)")
            messagebox.showinfo("OK", f"Đã xong!\nTên file: {final_filename}")
            
            if os.path.exists("signed.ipa"): os.remove("signed.ipa")
            if os.path.exists("temp_icon.png"): os.remove("temp_icon.png")

        except Exception as e: self.log(f"Lỗi: {e}"); messagebox.showerror("Lỗi", str(e))
        finally: self.btn_run.configure(state="normal", text="TIẾN HÀNH UPLOAD")

if __name__ == "__main__":
    app = ThaiSonV61_FixName()
    app.mainloop()