# === AUTO-INSTALL LIBRARIES ===
import sys
import subprocess
import importlib

REQUIRED_PACKAGES = {
    "requests": "requests",
    "httpx": "httpx",
    "PIL": "Pillow",
    "pyscreenshot": "pyscreenshot",
    "psutil": "psutil"
}

def auto_install():
    missing = []
    for module, package in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)
    if missing:
        print(f"[*] Đang cài đặt thư viện cần thiết: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet"] + missing)
            print("[+] Đã cài đặt thành công!")
        except Exception as e:
            print(f"[-] Không thể cài đặt tự động: {e}. Vui lòng chạy lệnh: pip install {' '.join(missing)}")

auto_install()

# === IMPORTS ===
import os
import json
import time
import re
import platform
import threading
import psutil
import sqlite3
import shutil
import datetime
import requests
import base64
import logging
import copy
from concurrent.futures import ThreadPoolExecutor

# ── CONFIG PATHS ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH          = os.path.join(BASE_DIR, "multi_configs.json")
WEBHOOK_CONFIG_PATH  = os.path.join(BASE_DIR, "webhook_config.json")
PREFIX_CONFIG_PATH   = os.path.join(BASE_DIR, "package_prefix_config.json")
ACTIVITY_CONFIG_PATH = os.path.join(BASE_DIR, "activity_config.json")
AUTOEXEC_CONFIG_PATH = os.path.join(BASE_DIR, "autoexec_config.json")
ADB_CONFIG_PATH      = os.path.join(BASE_DIR, "adb_config.json")

IS_ANDROID = os.path.exists("/data/data/com.termux")
IS_WINDOWS = platform.system() == "Windows"

# Thiết lập hệ thống Logger ghi nhật ký hoạt động
logging.basicConfig(
    filename=os.path.join(BASE_DIR, "app.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

# Kích hoạt hỗ trợ mã ANSI trên hệ điều hành Windows
if IS_WINDOWS:
    try:
        os.system('')
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  MÀU SẮC & ĐỊNH DẠNG ANSI
# ══════════════════════════════════════════════════════════════════════════════
class C:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    # Tổ hợp màu chuyên dụng cho UI mới
    H1 = BOLD + MAGENTA
    H2 = BOLD + CYAN
    SUC = BOLD + GREEN
    WRN = BOLD + YELLOW
    ERR = BOLD + RED
    TXT = WHITE
    BG_DARK = '\033[48;5;235m'

# ══════════════════════════════════════════════════════════════════════════════
#  UTILS
# ══════════════════════════════════════════════════════════════════════════════
class Utils:
    COMMON_EMULATOR_PORTS = [
        5555,   # LDPlayer mặc định, BlueStacks, Nox, Cổng Android tiêu chuẩn
        5557,   # LDPlayer (Instance 2)
        5559,   # LDPlayer (Instance 3)
        62001,  # NoxPlayer mặc định (Instance 1)
        62025,  # NoxPlayer (Instance 2)
        62026,  # NoxPlayer (Instance 3)
        21503,  # MEmu Player mặc định
        26868,  # SmartGaga
        16384,  # MuMu Player mặc định
    ]

    @staticmethod
    def run_cmd(cmd, shell=True, capture=True, timeout=12):
        try:
            r = subprocess.run(cmd, shell=shell, capture_output=capture,
                               text=True, timeout=timeout)
            return r.stdout.strip() if capture else ""
        except subprocess.TimeoutExpired:
            logging.warning(f"Lệnh thực thi hết thời gian chờ (Timeout): {cmd}")
            return ""
        except Exception as e:
            logging.error(f"Lỗi thực thi lệnh {cmd}: {e}")
            return ""

    @staticmethod
    def clear_screen():
        os.system('cls' if IS_WINDOWS else 'clear')

    # ── Bảo mật Cookie ──
    @staticmethod
    def obfuscate_cookie(cookie_str):
        if not cookie_str:
            return ""
        try:
            return base64.b64encode(cookie_str.encode("utf-8")).decode("utf-8")[::-1]
        except Exception as e:
            logging.error(f"Không thể xáo trộn Cookie: {e}")
            return cookie_str

    @staticmethod
    def deobfuscate_cookie(obfuscated_str):
        if not obfuscated_str:
            return ""
        try:
            if not obfuscated_str.startswith(".ROBLOSECURITY=") and not obfuscated_str.startswith("_|"):
                decoded = base64.b64decode(obfuscated_str[::-1].encode("utf-8")).decode("utf-8")
                return decoded
            return obfuscated_str
        except Exception:
            return obfuscated_str

    # ── Config helpers ──
    @staticmethod
    def save_json(path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"{C.ERR}[-] Không thể lưu cấu hình tại {path}: {e}{C.RESET}")
            logging.error(f"Không thể lưu cấu hình JSON tại {path}: {e}")

    @staticmethod
    def load_json(path, default=None):
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Lỗi nạp tệp JSON {path}: {e}")
            return default

    # Multi configs (Lưu trữ và phục hồi kèm mã hóa cookie)
    @staticmethod
    def save_multi_configs(configs):
        saved_configs = copy.deepcopy(configs)
        for pkg, cfg in saved_configs.items():
            if "cookie" in cfg and cfg["cookie"]:
                cfg["cookie"] = Utils.obfuscate_cookie(cfg["cookie"])
        Utils.save_json(CONFIG_PATH, saved_configs)

    @staticmethod
    def load_multi_configs():
        configs = Utils.load_json(CONFIG_PATH, {})
        for pkg, cfg in configs.items():
            if "cookie" in cfg and cfg["cookie"]:
                cfg["cookie"] = Utils.deobfuscate_cookie(cfg["cookie"])
        return configs

    # Webhook
    @staticmethod
    def save_webhook_config(config):
        Utils.save_json(WEBHOOK_CONFIG_PATH, config)

    @staticmethod
    def load_webhook_config():
        cfg = Utils.load_json(WEBHOOK_CONFIG_PATH, None)
        if cfg and "enabled" not in cfg:
            cfg["enabled"] = True
        return cfg

    # Package prefix
    @staticmethod
    def save_package_prefix(prefix):
        Utils.save_json(PREFIX_CONFIG_PATH, {"prefix": prefix})

    @staticmethod
    def load_package_prefix():
        cfg = Utils.load_json(PREFIX_CONFIG_PATH, {})
        return cfg.get("prefix", "com.roblox")

    # Activity
    @staticmethod
    def save_activity_config(activity):
        Utils.save_json(ACTIVITY_CONFIG_PATH, {"activity": activity})

    @staticmethod
    def load_activity_config():
        cfg = Utils.load_json(ACTIVITY_CONFIG_PATH, {})
        return cfg.get("activity", None)

    # ADB Settings helpers
    @staticmethod
    def load_adb_path():
        cfg = Utils.load_json(ADB_CONFIG_PATH, {})
        return cfg.get("adb_path", "adb")

    @staticmethod
    def save_adb_path(path):
        Utils.save_json(ADB_CONFIG_PATH, {"adb_path": path})

    # ── Platform Prevent Sleep ──
    @staticmethod
    def enable_wake_lock():
        if IS_ANDROID:
            subprocess.Popen(["termux-wake-lock"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        elif IS_WINDOWS:
            try:
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000002)
            except Exception:
                pass

    # ── Roblox Process Management ──
    @staticmethod
    def kill_roblox_pc():
        if not IS_WINDOWS:
            return
        killed = False
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] in ("RobloxPlayerBeta.exe", "WindowsUniversal.exe"):
                    proc.kill()
                    killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if killed:
            print(f"{C.WRN}[*] Đã tắt tiến trình Roblox cũ đang chạy trên PC.{C.RESET}")
            time.sleep(2)

    # ── ADB Integrations ──
    @staticmethod
    def get_adb_devices_detailed():
        """Trả về danh sách thiết bị kèm theo trạng thái chi tiết."""
        adb_path = Utils.load_adb_path()
        out = Utils.run_cmd(f'"{adb_path}" devices')
        devices = []
        if not out:
            return devices
            
        lines = out.splitlines()
        raw_list = []
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                raw_list.append({"serial": parts[0], "state": parts[1]})

        emulators = {}
        ips = {}
        other_devices = []

        for dev in raw_list:
            serial = dev["serial"]
            if serial.startswith("emulator-"):
                try:
                    port = int(serial.split("-")[1])
                    emulators[port] = dev
                except ValueError:
                    other_devices.append(dev)
            elif "127.0.0.1:" in serial or "localhost:" in serial:
                try:
                    port = int(serial.split(":")[1])
                    ips[port] = dev
                except ValueError:
                    other_devices.append(dev)
            else:
                other_devices.append(dev)

        to_remove_emu_ports = set()
        for emu_port in emulators.keys():
            if (emu_port + 1) in ips:
                to_remove_emu_ports.add(emu_port)
            elif emu_port in ips:
                to_remove_emu_ports.add(emu_port)

        final_list = []
        for emu_port, dev_info in emulators.items():
            if emu_port not in to_remove_emu_ports:
                final_list.append(dev_info)
        for ip_port, dev_info in ips.items():
            final_list.append(dev_info)
        final_list.extend(other_devices)

        return final_list

    @staticmethod
    def get_adb_devices():
        """Tương thích ngược cho các tính năng cũ."""
        detailed = Utils.get_adb_devices_detailed()
        return [d["serial"] for d in detailed if d["state"] == "device"]

    @staticmethod
    def connect_adb_device(addr):
        adb_path = Utils.load_adb_path()
        return Utils.run_cmd(f'"{adb_path}" connect {addr}')

    @staticmethod
    def pair_adb_device(addr, pairing_code):
        adb_path = Utils.load_adb_path()
        return Utils.run_cmd(f'"{adb_path}" pair {addr} {pairing_code}')

    @staticmethod
    def restart_adb_server():
        adb_path = Utils.load_adb_path()
        Utils.run_cmd(f'"{adb_path}" kill-server')
        time.sleep(1)
        Utils.run_cmd(f'"{adb_path}" start-server')

    @staticmethod
    def detect_roblox_packages_adb(serial):
        adb_path = Utils.load_adb_path()
        prefix = Utils.load_package_prefix()
        out = Utils.run_cmd(f'"{adb_path}" -s {serial} shell pm list packages')
        packages = {}
        if not out:
            return packages
        pattern = re.compile(rf"package:({re.escape(prefix)}[^\s]*)")
        for line in out.splitlines():
            m = pattern.search(line)
            if m:
                pkg = m.group(1)
                if pkg == f"{prefix}.client":
                    display = "Roblox Quốc tế"
                elif pkg == f"{prefix}.client.vnggames":
                    display = "Roblox VNG"
                else:
                    display = f"Roblox Custom ({pkg})"
                packages[pkg] = {"packageName": pkg, "displayName": display}
        return packages

    @staticmethod
    def get_roblox_cookie_adb(serial, package_name):
        adb_path = Utils.load_adb_path()
        sdcard_temp = f"/sdcard/cookies_{int(time.time())}.db"
        local_temp = os.path.join(BASE_DIR, f"temp_cookies_{serial.replace(':', '_')}.db")
        
        # Copy file Cookies trong app_webview ra thư mục chung
        Utils.run_cmd(f'"{adb_path}" -s {serial} shell "su -c \'cp /data/data/{package_name}/app_webview/Default/Cookies {sdcard_temp}\'"')
        Utils.run_cmd(f'"{adb_path}" -s {serial} shell "su -c \'chmod 777 {sdcard_temp}\'"')
        
        # Kéo file về máy chủ để đọc cơ sở dữ liệu
        Utils.run_cmd(f'"{adb_path}" -s {serial} pull "{sdcard_temp}" "{local_temp}"')
        Utils.run_cmd(f'"{adb_path}" -s {serial} shell rm "{sdcard_temp}"')
        
        cookie_val = None
        if os.path.exists(local_temp):
            try:
                conn = sqlite3.connect(local_temp)
                cur = conn.cursor()
                cur.execute("SELECT value FROM cookies WHERE name='.ROBLOSECURITY' LIMIT 1")
                row = cur.fetchone()
                if row:
                    val = row[0]
                    if not val.startswith("_"):
                        val = "_" + val
                    cookie_val = f".ROBLOSECURITY={val}"
                conn.close()
            except Exception as e:
                logging.error(f"Lỗi đọc Cookie từ SQLite giả lập: {e}")
            finally:
                try:
                    os.remove(local_temp)
                except Exception:
                    pass
        return cookie_val

    # ── Android/PC Package Detection (Local Termux) ──
    @staticmethod
    def detect_all_roblox_packages():
        packages = {}
        if not IS_ANDROID:
            return packages

        prefix = Utils.load_package_prefix()
        methods = [
            "unset LD_PRELOAD LD_LIBRARY_PATH; pm list packages",
            "unset LD_PRELOAD LD_LIBRARY_PATH; cmd package list packages",
            "pm list packages",
            "cmd package list packages",
        ]
        result = ""
        for method in methods:
            out = Utils.run_cmd(method)
            if out and "package:" in out:
                result = out
                break

        if not result:
            return packages

        pattern = re.compile(rf"package:({re.escape(prefix)}[^\s]*)")
        for line in result.splitlines():
            m = pattern.search(line)
            if m:
                pkg = m.group(1)
                if pkg == f"{prefix}.client":
                    display = "Roblox Quốc tế"
                elif pkg == f"{prefix}.client.vnggames":
                    display = "Roblox VNG"
                else:
                    display = f"Roblox Custom ({pkg})"
                packages[pkg] = {"packageName": pkg, "displayName": display}
        return packages

    @staticmethod
    def get_roblox_cookie(package_name):
        if not IS_ANDROID:
            return None
        cookies_path = f"/data/data/{package_name}/app_webview/Default/Cookies"
        sdcard_path  = f"/sdcard/cookies_temp_{int(time.time()*1000)}.db"
        try:
            try:
                shutil.copy2(cookies_path, sdcard_path)
            except Exception:
                Utils.run_cmd(f"su -c \"cp '{cookies_path}' '{sdcard_path}'\"")

            conn = sqlite3.connect(sdcard_path)
            cur  = conn.cursor()
            cur.execute("SELECT value FROM cookies WHERE name='.ROBLOSECURITY' LIMIT 1")
            row = cur.fetchone()
            conn.close()
            try:
                os.remove(sdcard_path)
            except Exception:
                pass
            if not row:
                return None
            val = row[0]
            if not val.startswith("_"):
                val = "_" + val
            return f".ROBLOSECURITY={val}"
        except Exception as e:
            print(f"{C.ERR}[-] Lỗi lấy cookie {package_name}: {e}{C.RESET}")
            logging.error(f"Lỗi lấy cookie {package_name}: {e}")
            return None

    # ── Launch Engine ──
    @staticmethod
    def launch(place_id, link_code, package_name, mode="local", adb_serial=None):
        url = (f"roblox://placeID={place_id}&linkCode={link_code}"
               if link_code else f"roblox://placeID={place_id}")
        
        logging.info(f"Yêu cầu khởi chạy Map: {place_id}, Chế độ: {mode}, Thiết bị: {adb_serial}")

        if mode == "adb" and adb_serial:
            adb_path = Utils.load_adb_path()
            activity = Utils.load_activity_config() or "com.roblox.client.ActivityProtocolLaunch"
            # Tắt tiến trình cũ một cách sạch sẽ
            Utils.run_cmd(f'"{adb_path}" -s {adb_serial} shell am force-stop {package_name}')
            time.sleep(1.5)
            # Khởi chạy ứng dụng mới qua ADB
            launch_cmd = f'"{adb_path}" -s {adb_serial} shell am start -n {package_name}/{activity} -a android.intent.action.VIEW -d \\"{url}\\" --activity-clear-top'
            Utils.run_cmd(launch_cmd)
            return

        if IS_WINDOWS:
            Utils.kill_roblox_pc()
            try:
                os.startfile(url)
            except Exception as e:
                print(f"{C.ERR}[-] Lỗi khi khởi chạy Roblox trên Windows: {e}{C.RESET}")
                logging.error(f"Khởi chạy Roblox PC thất bại: {e}")
            return

        if IS_ANDROID:
            activity = Utils.load_activity_config()
            prefix   = Utils.load_package_prefix()
            if not activity:
                activity = f"{prefix}.client.ActivityProtocolLaunch"

            cmd = (f"am start -n {package_name}/{activity} "
                   f"-a android.intent.action.VIEW -d \"{url}\" --activity-clear-top")
            Utils.run_cmd(cmd)

    @staticmethod
    def validate_package_integrity(configs):
        if not configs:
            return False, "Không có cấu hình nào được thiết lập!"
        
        for pkg, cfg in configs.items():
            for field in ("username", "userId", "placeId", "delaySec"):
                if not cfg.get(field):
                    return False, f"Cấu hình {pkg} bị thiếu thông tin bắt buộc: {field}"
        return True, "Hợp lệ"

    # ── Network ──
    @staticmethod
    def curl_pastebin_visits():
        try:
            r = requests.get("https://pastebin.com/Q9yk1GNq", timeout=5,
                             headers={"User-Agent": "Mozilla/5.0"})
            m = re.search(r'<div class="visits"[^>]*>\s*([\d,.]+)\s*</div>', r.text)
            if m:
                return m.group(1).replace(",", "")
        except Exception:
            pass
        return None

    @staticmethod
    def mask(text):
        if not text or text == "Unknown":
            return str(text)
        s = str(text)
        if len(s) <= 4:
            return s
        return "*" * (len(s) - 4) + s[-4:]

    # ── Screenshot ──
    @staticmethod
    def take_screenshot(mode="local", adb_serial=None):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(BASE_DIR, f"screenshot_{ts}.png")

        if mode == "adb" and adb_serial:
            adb_path = Utils.load_adb_path()
            remote_path = f"/sdcard/screencap_{ts}.png"
            try:
                Utils.run_cmd(f'"{adb_path}" -s {adb_serial} shell screencap -p {remote_path}')
                Utils.run_cmd(f'"{adb_path}" -s {adb_serial} pull {remote_path} "{filepath}"')
                Utils.run_cmd(f'"{adb_path}" -s {adb_serial} shell rm {remote_path}')
                if os.path.exists(filepath):
                    return filepath
            except Exception as e:
                logging.error(f"Lỗi chụp ảnh thiết bị ADB {adb_serial}: {e}")

        if IS_ANDROID:
            try:
                data = Utils.run_cmd('su -c "screencap -p"')
                if data:
                    with open(filepath, "wb") as f:
                        f.write(data.encode("latin1"))
                    return filepath
            except Exception as e:
                logging.error(f"Lỗi chụp ảnh nội bộ Android: {e}")
        if IS_WINDOWS:
            try:
                import pyscreenshot as ImageGrab
                img = ImageGrab.grab()
                img.save(filepath)
                return filepath
            except Exception as e:
                logging.error(f"Lỗi chụp ảnh màn hình PC Windows: {e}")
        
        txt = os.path.join(BASE_DIR, f"system_info_{ts}.txt")
        info = {
            "platform": platform.platform(),
            "python":   sys.version,
            "cpu":      psutil.cpu_percent(),
            "ram_total_mb": psutil.virtual_memory().total // (1024**2),
            "ram_free_mb":  psutil.virtual_memory().available // (1024**2),
            "timestamp": datetime.datetime.now().isoformat(),
        }
        with open(txt, "w") as f:
            for k, v in info.items():
                f.write(f"{k}: {v}\n")
        return txt

    @staticmethod
    def delete_file(path):
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    @staticmethod
    def send_webhook_embed(url, embed, screenshot_path=None):
        try:
            payload = {"embeds": [embed]}
            if screenshot_path and os.path.exists(screenshot_path):
                ext = os.path.splitext(screenshot_path)[1].lower()
                ctype = "image/png" if ext == ".png" else "text/plain"
                with open(screenshot_path, "rb") as f:
                    data = f.read()
                files = {"file": (os.path.basename(screenshot_path), data, ctype)}
                requests.post(url, data={"payload_json": json.dumps(payload)},
                              files=files, timeout=15)
            else:
                requests.post(url, json=payload,
                              headers={"Content-Type": "application/json"}, timeout=15)
            if screenshot_path:
                threading.Timer(5.0, Utils.delete_file, args=[screenshot_path]).start()
        except Exception as e:
            print(f"{C.ERR}[-] Lỗi gửi webhook: {e}{C.RESET}")
            logging.error(f"Gửi dữ liệu tới Discord Webhook thất bại: {e}")

    @staticmethod
    def get_system_stats():
        cpu = psutil.cpu_percent(interval=0)
        vm  = psutil.virtual_memory()
        total_gb = vm.total / (1024**3)
        used_gb  = (vm.total - vm.available) / (1024**3)
        return {
            "cpuUsage": f"{cpu:.1f}",
            "ramUsage": f"{used_gb:.2f}GB/{total_gb:.2f}GB",
        }


# ══════════════════════════════════════════════════════════════════════════════
#  ROBLOX API
# ══════════════════════════════════════════════════════════════════════════════
class RobloxUser:
    def __init__(self, username=None, user_id=None, cookie=None):
        self.username = username
        self.user_id  = user_id
        self.cookie   = cookie
        self._headers = {
            "Cookie":     cookie or "",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
            "Accept":     "application/json",
        }

    def fetch_authenticated_user(self):
        try:
            r = requests.get("https://users.roblox.com/v1/users/authenticated",
                             headers=self._headers, timeout=10)
            data = r.json()
            self.username = data.get("name")
            self.user_id  = data.get("id")
            return self.user_id
        except Exception as e:
            logging.error(f"Xác thực API người dùng Roblox thất bại: {e}")
            return None

    def get_presence(self):
        targets = [
            "https://presence.roproxy.com/v1/presence/users",
            "https://presence.rbxproxy.com/v1/presence/users",
            "https://presence.ro.place/v1/presence/users",
            "https://presence.roblox.com/v1/presence/users"
        ]
        
        for url in targets:
            try:
                r = requests.post(
                    url,
                    json={"userIds": [self.user_id]},
                    headers=self._headers,
                    timeout=8,
                )
                if r.status_code == 200:
                    presences = r.json().get("userPresences", [])
                    return presences[0] if presences else None
                elif r.status_code == 401:
                    return {"error": "Unauthorized", "message": "Cookie het hieu luc"}
            except Exception:
                continue
                
        return {"error": "RateLimit", "message": "Tat ca proxy bi gioi han tan suat"}


# ══════════════════════════════════════════════════════════════════════════════
#  STATUS HANDLER
# ══════════════════════════════════════════════════════════════════════════════
class StatusHandler:
    def __init__(self):
        self.consecutive_offline_ticks = 0
        self.max_ticks_before_rejoin = 1

    def analyze_presence(self, presence, target_place_id):
        if not presence:
            return {
                "status": "Loi Ket Noi",
                "info": "Khong nhan dien tin hieu",
                "color": C.ERR,
                "shouldLaunch": False
            }

        if isinstance(presence, dict) and "error" in presence:
            err_type = presence["error"]
            if err_type == "RateLimit":
                return {
                    "status": "Rate Limited",
                    "info": "Proxy gioi han, ngung quet",
                    "color": C.WRN,
                    "shouldLaunch": False
                }
            elif err_type == "Unauthorized":
                return {
                    "status": "Cookie Het Han",
                    "info": "Phien dang nhap ket thuc",
                    "color": C.ERR,
                    "shouldLaunch": False
                }
            else:
                return {
                    "status": "Loi API",
                    "info": f"{presence.get('message', 'Ngoai le ket noi')}",
                    "color": C.ERR,
                    "shouldLaunch": False
                }

        t = presence.get("userPresenceType")
        if t is None:
            return {
                "status": "Khong Du Lieu",
                "info": "Du lieu API trong",
                "color": C.GRAY,
                "shouldLaunch": False
            }

        # ĐANG TRONG GAME (type = 2)
        if t == 2:
            root = presence.get("rootPlaceId")
            if not root or str(root) != str(target_place_id):
                self.consecutive_offline_ticks += 1
                if self.consecutive_offline_ticks >= self.max_ticks_before_rejoin:
                    self.consecutive_offline_ticks = 0
                    return {
                        "status": "Sai Ban Do",
                        "info": f"Treo nham game ({root}) -> Rejoin!",
                        "color": C.WRN,
                        "shouldLaunch": True
                    }
                return {
                    "status": "Sai Ban Do (Cho)",
                    "info": f"Cho xac minh lai ({self.consecutive_offline_ticks}/{self.max_ticks_before_rejoin})",
                    "color": C.WRN,
                    "shouldLaunch": False
                }
            
            self.consecutive_offline_ticks = 0
            return {
                "status": "Treo Game OK",
                "info": "Hoat dong on dinh tai ban do",
                "color": C.SUC,
                "shouldLaunch": False
            }

        # OFFLINE (type = 0) hoặc ONLINE LOBBY (type = 1)
        self.consecutive_offline_ticks += 1
        state_label = "Sanh Cho" if t == 1 else "Ngoai Tuyen"
        color_label = C.WRN if t == 1 else C.ERR

        if self.consecutive_offline_ticks >= self.max_ticks_before_rejoin:
            self.consecutive_offline_ticks = 0
            return {
                "status": state_label,
                "info": "Mat ket noi -> Dang Rejoin!",
                "color": color_label,
                "shouldLaunch": True
            }

        return {
            "status": f"{state_label} (Cho)",
            "info": f"Cho xac nhan lai ({self.consecutive_offline_ticks}/{self.max_ticks_before_rejoin})",
            "color": color_label,
            "shouldLaunch": False
        }


# ══════════════════════════════════════════════════════════════════════════════
#  AUTOEXEC MANAGER
# ══════════════════════════════════════════════════════════════════════════════
EXECUTORS = {
    "Delta (Android/ADB)":    "/storage/emulated/0/Delta/Autoexecute/text.txt",
    "Ronix (Android/ADB)":    "/storage/emulated/0/RonixExploit/autoexec/text.txt",
    "Codex (Android/ADB)":    "/storage/emulated/0/Codex/Autoexec/text.txt",
    "Arceus X (Android/ADB)": "/storage/emulated/0/Arceus X/Autoexec/text.txt",
    "Solara (PC)":            os.path.expandvars(r"%LocalAppData%\Solara\autoexec\text.txt"),
    "Wave (PC)":              os.path.expandvars(r"%LocalAppData%\Wave\autoexec\text.txt"),
    "Celery (PC)":            os.path.expandvars(r"%appdata%\Celery\autoexec\text.txt"),
}

class AutoexecManager:
    def load_config(self):
        return Utils.load_json(AUTOEXEC_CONFIG_PATH, None)

    def save_config(self, config):
        Utils.save_json(AUTOEXEC_CONFIG_PATH, config)

    def write_to_executor(self, executor_name, script):
        path = EXECUTORS.get(executor_name)
        if not path:
            config = self.load_config()
            if config and config.get("executor") == executor_name:
                path = config.get("path")
            else:
                return False
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(script)
            return True
        except Exception as e:
            print(f"{C.ERR}[-] Lỗi ghi đè tệp autoexec: {e}{C.RESET}")
            logging.error(f"Ghi đè file autoexec nội bộ thất bại: {e}")
            return False

    def write_to_executor_adb(self, serial, executor_name, script):
        path = EXECUTORS.get(executor_name)
        if not path:
            return False
        if "storage" not in path and "sdcard" not in path:
            return False
            
        adb_path = Utils.load_adb_path()
        local_temp = os.path.join(BASE_DIR, "temp_autoexec.txt")
        try:
            with open(local_temp, "w", encoding="utf-8") as f:
                f.write(script)
            
            dir_name = os.path.dirname(path)
            Utils.run_cmd(f'"{adb_path}" -s {serial} shell mkdir -p "{dir_name}"')
            Utils.run_cmd(f'"{adb_path}" -s {serial} push "{local_temp}" "{path}"')
            return True
        except Exception as e:
            print(f"{C.ERR}[-] Lỗi đồng bộ Autoexec qua giả lập ADB {serial}: {e}{C.RESET}")
            logging.error(f"Đồng bộ autoexec qua ADB {serial} lỗi: {e}")
            return False
        finally:
            if os.path.exists(local_temp):
                os.remove(local_temp)

    def check_and_fix(self, config, instances=None):
        if not config or not config.get("script"):
            return
        script = config["script"]
        executor = config["executor"]

        path = config.get("path")
        if path and os.path.exists(os.path.dirname(path)):
            try:
                current = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
                if current.strip() != script.strip():
                    self.write_to_executor(executor, script)
            except Exception:
                pass

        if instances:
            for inst in instances:
                cfg = inst["config"]
                if cfg.get("mode") == "adb" and cfg.get("adb_serial"):
                    self.write_to_executor_adb(cfg["adb_serial"], executor, script)


# ══════════════════════════════════════════════════════════════════════════════
#  WEBHOOK MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class WebhookManager:
    def send_status_webhook(self, instances, start_time, system_stats=None):
        cfg = Utils.load_webhook_config()
        if not cfg or not cfg.get("enabled"):
            return
        stats = system_stats or Utils.get_system_stats()
        elapsed = time.time() - start_time
        h = int(elapsed // 3600)
        m = int((elapsed % 3600) // 60)
        s = int(elapsed % 60)
        active = sum(1 for i in instances if "Treo Game" in i.get("status", ""))
        
        pkg_list = "\n".join(
            f"{i['packageName'].split('.')[-1] if '.' in i['packageName'] else i['packageName']} ({i['config'].get('mode', 'local').upper()}): {i.get('status', 'Unknown')}" 
            for i in instances
        )
        
        embed = {
            "title": "🖥️ Rbl Rejoin - Báo Cáo Giám Sát Thiết Bị",
            "color": 0x32CD32,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "fields": [
                {"name": "🖥️ CPU", "value": f"{stats['cpuUsage']}%", "inline": True},
                {"name": "💾 RAM", "value": stats["ramUsage"], "inline": True},
                {"name": "⏱️ Thời gian chạy", "value": f"{h}h {m}m {s}s", "inline": True},
                {"name": "📦 Số tài khoản treo", "value": f"{active}/{len(instances)}", "inline": True},
                {"name": "📋 Chi tiết tài khoản", "value": pkg_list[:1024] or "—", "inline": False},
            ],
            "footer": {"text": "Rbl Rejoin Tool - CLI Version with ADB"},
        }
        
        screenshot = None
        if instances and instances[0]['config'].get("mode") == "adb":
            screenshot = Utils.take_screenshot(mode="adb", adb_serial=instances[0]['config'].get("adb_serial"))
        else:
            screenshot = Utils.take_screenshot()
            
        Utils.send_webhook_embed(cfg["url"], embed, screenshot)


# ══════════════════════════════════════════════════════════════════════════════
#  GAMES DATA
# ══════════════════════════════════════════════════════════════════════════════
GAMES = {
    "1":  ("126884695634066",  "Grow-a-Garden"),
    "2":  ("2753915549",       "Blox-Fruits"),
    "3":  ("6284583030",       "Pet-Simulator-X"),
    "4":  ("126244816328678",  "DIG"),
    "5":  ("116495829188952",  "Dead-Rails-Alpha"),
    "6":  ("8737602449",       "PLS-DONATE"),
    "7":  ("920587237",        "Adopt Me!"),
    "8":  ("79546208627805",   "99 Night In The Forests"),
    "9":  ("109983668079237",  "Steal-a-Brainrot"),
    "10": ("127742093697776",  "Plants-Vs-Brainrots"),
    "11": ("121864768012064",  "Fish-It"),
    "12": ("16732694052",      "Fisch"),
}


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN CLI APPLICATION
# ══════════════════════════════════════════════════════════════════════════════
class AppCLI:
    def __init__(self):
        self._running = False
        self._instances = []
        self._start_time = time.time()
        self._visits = "Đang tải..."
        self.executor = ThreadPoolExecutor(max_workers=8) # Quản lý cụm luồng tối ưu tài nguyên
        
        threading.Thread(target=self._load_visits, daemon=True).start()

    def _load_visits(self):
        v = Utils.curl_pastebin_visits()
        if v:
            self._visits = v

    def render_header(self):
        print(f"{C.RED}  ⚡──────────────────────────────────────────────────────────────────────────⚡{C.RESET}")
        print(f"  {C.H1}  ██████╗ ██████╗ ██╗         ██████╗ ███████╗    ██╗ ██████╗ ██╗███╗   ██╗")
        print(f"  {C.H1}  ██╔══██╗██╔══██╗██║         ██╔══██╗██╔════╝    ██║██╔═══██╗██║████╗  ██║")
        print(f"  {C.H2}  ██████╔╝██████╔╝██║         ██████╔╝█████╗      ██║██║   ██║██║██╔██╗ ██║")
        print(f"  {C.H2}  ██╔══██╗██╔══██╗██║         ██╔══██╗██╔══╝ ██   ██║██║   ██║██║██║╚██╗██║")
        print(f"  {C.CYAN}  ██║  ██║██████╔╝███████╗    ██║  ██║███████╗╚█████╔╝╚██████╔╝██║██║ ╚████║")
        print(f"  {C.CYAN}  ╚═╝  ╚═╝╚═════╝ ╚══════╝    ╚═╝  ╚═╝╚══════╝ ╚════╝  ╚═════╝ ╚═╝╚═╝  ╚═══╝")
        print(f"  {C.GRAY}        ───────────────── PHIÊN BẢN GIÁM SÁT ĐA LUỒNG ADB ─────────────────{C.RESET}")

    def render_system_info(self):
        stats = Utils.get_system_stats()
        print(f"  {C.GRAY}╭──────────────────────────────────────────────────────────────────────────╮{C.RESET}")
        print(f"    {C.TXT}📱 Lượt chạy: {C.SUC}{self._visits:<10}{C.RESET} | {C.TXT}💻 OS: {C.BLUE}{platform.system()} {platform.release()[:18]:<18}{C.RESET}")
        print(f"    {C.TXT}⚙️ ADB Path: {C.CYAN}{Utils.load_adb_path()[:25]:<25}{C.RESET} | {C.TXT}🧠 Tài nguyên: {C.WRN}CPU {stats['cpuUsage']}%{C.RESET} - {C.WRN}RAM {stats['ramUsage']}{C.RESET}")
        print(f"  {C.GRAY}╰──────────────────────────────────────────────────────────────────────────╯{C.RESET}")

    def run(self):
        Utils.enable_wake_lock()
        while True:
            Utils.clear_screen()
            self.render_header()
            self.render_system_info()

            # Danh sách chức năng phẳng tối giản theo yêu cầu người dùng
            print(f"  {C.GRAY}──────────────────────────────────────────────────────────────────────────{C.RESET}")
            print(f"   {C.SUC}[1]{C.TXT} Bắt đầu Auto Rejoin (Kích hoạt tất cả cấu hình)")
            print(f"   {C.SUC}[2]{C.TXT} Tự động quét & Thiết lập cấu hình (Hỗ trợ ADB / Local Root)")
            print(f"   {C.CYAN}[3]{C.TXT} Thêm tài khoản thủ công (Manual Profile Configuration)")
            print(f"   {C.CYAN}[4]{C.TXT} Quản lý tài khoản (Xem chi tiết / Chỉnh sửa thông tin / Xóa)")
            print(f"   {C.CYAN}[5]{C.TXT} Quản lý kết nối ADB (Quét IP / Ghép nối các thiết bị giả lập)")
            print(f"   {C.BLUE}[6]{C.TXT} Điều chỉnh Package Prefix định dạng gói Roblox")
            print(f"   {C.BLUE}[7]{C.TXT} Cấu hình Class Activity khởi chạy tùy chọn (Custom Class)")
            print(f"   {C.BLUE}[8]{C.TXT} Thiết lập liên kết Discord Webhook (Gửi báo cáo / Chụp màn hình)")
            print(f"   {C.BLUE}[9]{C.TXT} Cấu hình đồng bộ tệp tin Autoexec Script")
            print(f"   {C.ERR}[10]{C.TXT} Đóng hệ thống & Thoát chương trình")
            print(f"  {C.GRAY}──────────────────────────────────────────────────────────────────────────{C.RESET}")
            
            choice = input(f"\n  {C.H2}👉 Nhập lựa chọn thực thi (1-10): {C.RESET}").strip()
            
            if choice == "1":
                self.start_rejoin()
            elif choice == "2":
                self.setup_packages_dialog()
            elif choice == "3":
                self.add_manual_config()
            elif choice == "4":
                self.manage_configs()
            elif choice == "5":
                self.manage_adb_settings()
            elif choice == "6":
                self.change_prefix()
            elif choice == "7":
                self.change_activity()
            elif choice == "8":
                self.manage_webhook()
            elif choice == "9":
                self.manage_autoexec()
            elif choice == "10":
                print(f"\n  {C.SUC}[+] Đang dọn dẹp và tắt chương trình an toàn. Hẹn gặp lại!{C.RESET}")
                self.executor.shutdown(wait=False)
                break
            else:
                input(f"\n  {C.ERR}[!] Lựa chọn không hợp lệ. Nhấn Enter để tiếp tục...{C.RESET}")

    # ── Chức năng 1: Bắt đầu Auto Rejoin ─────────────────────────────────────
    def start_rejoin(self):
        configs = Utils.load_multi_configs()
        if not configs:
            print(f"\n  {C.ERR}[-] Thất bại: Bạn chưa tạo tài khoản nào trong hệ thống.{C.RESET}")
            input("\n  Nhấn Enter để quay lại...")
            return

        ok, msg = Utils.validate_package_integrity(configs)
        if not ok:
            print(f"\n  {C.WRN}[!] Cảnh báo lỗi cấu hình: {msg}{C.RESET}")
            confirm = input("  Vẫn tiếp tục khởi chạy? (y/n): ").strip().lower()
            if confirm != 'y':
                return

        pkg_names = list(configs.keys())

        print(f"\n  {C.H2}📋 [ DANH SÁCH TÀI KHOẢN HIỆN HÀNH ]{C.RESET}")
        print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
        for i, pkg in enumerate(pkg_names, 1):
            cfg = configs[pkg]
            mode = cfg.get("mode", "local").upper()
            serial_info = f" | Dev: {cfg.get('adb_serial')}" if mode == "ADB" else ""
            print(f"   {C.CYAN}[{i}]{C.TXT} [{mode}{serial_info}] Profile: {pkg[:20]:<20} - User: {C.SUC}{Utils.mask(cfg.get('username')):<14}{C.RESET}")
        print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")

        print(f"\n  {C.TXT}Nhập số thứ tự hồ sơ muốn chạy (Ví dụ: 1,2 hoặc nhấn {C.SUC}Enter{C.TXT} để chọn toàn bộ):")
        sel_input = input(f"  {C.H2}👉 Nhập cấu hình: {C.RESET}").strip()
        
        selected_indexes = []
        if not sel_input:
            selected_indexes = list(range(len(pkg_names)))
        else:
            try:
                selected_indexes = [int(x.strip()) - 1 for x in sel_input.split(",") if x.strip()]
            except ValueError:
                print(f"  {C.ERR}[-] Định dạng dữ liệu nhập không chính xác.{C.RESET}")
                input("\n  Nhấn Enter để tiếp tục...")
                return

        selected_pkgs = []
        for idx in selected_indexes:
            if 0 <= idx < len(pkg_names):
                selected_pkgs.append(pkg_names[idx])

        if not selected_pkgs:
            print(f"  {C.ERR}[-] Không tìm thấy tài khoản thích hợp nào.{C.RESET}")
            input("\n  Nhấn Enter để tiếp tục...")
            return

        self._instances = []
        self._running = True
        self._start_time = time.time()

        for pkg in selected_pkgs:
            cfg = configs[pkg]
            cookie = cfg.get("cookie")
            
            # Đồng bộ Cookie mới tự động qua ADB nếu thiết bị hoạt động
            if cfg.get("mode") == "adb" and cfg.get("adb_serial"):
                fresh_cookie = Utils.get_roblox_cookie_adb(cfg["adb_serial"], cfg["packageName"])
                if fresh_cookie:
                    cookie = fresh_cookie

            user = RobloxUser(cfg["username"], cfg["userId"], cookie)
            self._instances.append({
                "packageName":      pkg,
                "config":           cfg,
                "user":             user,
                "statusHandler":    StatusHandler(),
                "status":           "Cho Quet",
                "statusColor":      C.CYAN,
                "info":             "Chuan bi quet...",
                "countdownSeconds": 0,
                "lastCheck":        0,
                "is_checking":      False
            })
            print(f"  {C.SUC}[+] Liên kết thành công tiến trình: {pkg}{C.RESET}")

        print(f"\n  {C.SUC}[+] Hệ thống giám sát bắt đầu hoạt động. Nhấn Ctrl+C để thoát về Menu chính.{C.RESET}")
        time.sleep(1)

        try:
            self._run_loop()
        except KeyboardInterrupt:
            self._running = False
            self._instances = []
            print(f"\n  {C.WRN}[-] Đã dừng hoạt động Auto Rejoin.{C.RESET}")
            input("\n  Nhấn Enter để quay lại...")

    def _threaded_presence_check(self, inst, active_adb_serials):
        cfg = inst["config"]
        try:
            if cfg.get("mode") == "adb" and cfg.get("adb_serial"):
                serial = cfg["adb_serial"]
                if serial not in active_adb_serials and ":" in serial:
                    Utils.connect_adb_device(serial)

            presence = inst["user"].get_presence()
            analysis = inst["statusHandler"].analyze_presence(presence, cfg["placeId"])
            
            if analysis["shouldLaunch"]:
                Utils.launch(
                    place_id=cfg["placeId"], 
                    link_code=cfg.get("linkCode"), 
                    package_name=cfg["packageName"],
                    mode=cfg.get("mode", "local"),
                    adb_serial=cfg.get("adb_serial")
                )
            
            inst["status"]      = analysis["status"]
            inst["statusColor"] = analysis["color"]
            inst["info"]        = analysis["info"]
            inst["lastCheck"]   = time.time()
        except Exception as ex:
            inst["status"]      = "Loi Luong"
            inst["statusColor"] = C.ERR
            inst["info"]        = f"Ngoai le: {str(ex)[:15]}"
            logging.error(f"Lỗi kiểm tra hoạt động của luồng {cfg.get('username')}: {ex}")
        finally:
            inst["is_checking"] = False

    def _run_loop(self):
        wm = WebhookManager()
        ae = AutoexecManager()
        ae_cfg = ae.load_config()
        next_ae_check = time.time() + 5
        wh_counter = 0

        cached_stats = Utils.get_system_stats()
        next_stats_check = 0

        cached_adb_devices = []
        next_adb_check = 0

        Utils.clear_screen()

        border_top = f"  {C.H2}╭" + "─" * 105 + "╮"
        border_mid = f"  {C.H2}├" + "─" * 105 + "┤"
        border_bot = f"  {C.H2}╰" + "─" * 105 + "╯"

        while self._running:
            sys.stdout.write("\033[H")
            sys.stdout.flush()

            now = time.time()

            if now >= next_stats_check:
                cached_stats = Utils.get_system_stats()
                next_stats_check = now + 3

            if now >= next_adb_check:
                def update_adb_list():
                    nonlocal cached_adb_devices
                    cached_adb_devices = Utils.get_adb_devices()
                self.executor.submit(update_adb_list)
                next_adb_check = now + 10

            if ae_cfg and now >= next_ae_check:
                ae.check_and_fix(ae_cfg, self._instances)
                next_ae_check = now + 15 * 60

            elapsed = int(now - self._start_time)
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)
            
            lines_buffer = []
            lines_buffer.append(border_top)
            
            title_text = " BẢNG GIÁM SÁT TRẠNG THÁI HOẠT ĐỘNG (DASHBOARD ACTIVE - MULTI-THREADED)"
            lines_buffer.append(f"  │{C.H1}{title_text:<105}{C.H2}│")
            lines_buffer.append(border_mid)
            
            stats_text = f" Uptime: {h:02d}h {m:02d}m {s:02d}s  │  CPU: {cached_stats['cpuUsage']}%  │  RAM: {cached_stats['ramUsage']}"
            lines_buffer.append(f"  │ {C.TXT}{stats_text:<104}{C.H2}│")
            lines_buffer.append(border_mid)
            
            h1, h2, h3, h4, h5, h6 = "HỒ SƠ / ACC", "MODE", "USER", "TRẠNG THÁI", "COUNTDOWN", "LOG CHI TIẾT"
            lines_buffer.append(f"  │ {C.H2}{h1:<18} │ {h2:<6} │ {h3:<14} │ {h4:<16} │ {h5:<10} │ {h6:<24} │")
            lines_buffer.append(border_mid)

            for inst in self._instances:
                cfg       = inst["config"]
                delay_ms  = cfg["delaySec"]
                elapsed_check = now - inst["lastCheck"]
                time_left = max(0, delay_ms - elapsed_check)
                inst["countdownSeconds"] = int(time_left)

                if elapsed_check >= delay_ms and not inst["is_checking"]:
                    inst["is_checking"] = True
                    inst["status"] = "Dang K.Tra..."
                    inst["statusColor"] = C.YELLOW
                    self.executor.submit(self._threaded_presence_check, inst, cached_adb_devices)

                short_pkg = inst["packageName"].split(".")[-1] if "." in inst["packageName"] else inst["packageName"]
                user_mask = Utils.mask(cfg.get("username", "Unknown"))
                cd_str    = f"{inst['countdownSeconds']}s"

                c1 = short_pkg[:18].ljust(18)
                c2 = cfg.get("mode", "local").upper()[:6].ljust(6)
                c3 = user_mask[:14].ljust(14)
                c4 = inst["status"][:16].ljust(16)
                c5 = cd_str[:10].ljust(10)
                c6 = inst["info"][:24].ljust(24)

                lines_buffer.append(
                    f"  │ {C.TXT}{c1} │ {C.CYAN}{c2}{C.TXT} │ {C.WHITE}{c3}{C.TXT} │ {inst['statusColor']}{c4}{C.TXT} │ {C.WRN}{c5}{C.TXT} │ {C.GRAY}{c6}{C.H2} │"
                )

            lines_buffer.append(border_bot)
            lines_buffer.append(f"  {C.WRN}[*] Hệ thống đang chạy liên tục. Nhấn Ctrl+C để quay lại trình điều khiển.{C.RESET}")

            print("\n".join(lines_buffer))
            sys.stdout.write("\033[J")
            sys.stdout.flush()

            wh_cfg = Utils.load_webhook_config()
            if wh_cfg and wh_cfg.get("enabled"):
                interval_s = wh_cfg["intervalMinutes"] * 60
                if wh_counter > 0 and wh_counter % interval_s == 0:
                    self.executor.submit(wm.send_status_webhook, self._instances, self._start_time, cached_stats)
            wh_counter += 1
            time.sleep(1)

    # ── Chức năng 2: Quét & Thiết lập Packages tự động ───────────────────────
    def setup_packages_dialog(self):
        Utils.clear_screen()
        print(f"  {C.H2}📦 [ TỰ ĐỘNG KHỞI TẠO VÀ THIẾT LẬP HỒ SƠ ]{C.RESET}")
        print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
        print("  Chọn phương thức quét ứng dụng Roblox trên thiết bị của bạn:")
        print(f"   {C.CYAN}[1]{C.TXT} Quét thông qua giả lập đang trực tuyến (Giao thức ADB)")
        print(f"   {C.CYAN}[2]{C.TXT} Quét nội bộ (Hỗ trợ trực tiếp trên thiết bị Android/Termux Root)")
        print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
        
        m_choice = input(f"\n  {C.H2}👉 Nhập lựa chọn quét (1-2): {C.RESET}").strip()
        configs = Utils.load_multi_configs()

        if m_choice == "1":
            devices = Utils.get_adb_devices()
            if not devices:
                print(f"\n  {C.ERR}[-] Không tìm thấy cổng kết nối ADB nào hoạt động!{C.RESET}")
                print("  [*] Hãy kết nối thiết bị của bạn trước tại Mục cài đặt ADB (Số 5).")
                input("\n  Nhấn Enter để quay lại...")
                return
            
            print(f"\n  {C.H2}Chọn thiết bị mục tiêu:{C.RESET}")
            print(f"  {C.SUC}[0]{C.TXT} Quét ĐỒNG LOẠT tất cả các thiết bị hoạt động")
            for idx, dev in enumerate(devices, 1):
                print(f"  {C.CYAN}[{idx}]{C.TXT} Thiết bị IP/Serial: {C.WHITE}{dev}{C.RESET}")
            
            target_devices = []
            try:
                dev_input = input(f"\n  {C.H2}👉 Nhập số thứ tự thiết bị (hoặc nhập 0): {C.RESET}").strip()
                if dev_input == "0":
                    target_devices = devices
                else:
                    dev_idx = int(dev_input) - 1
                    if 0 <= dev_idx < len(devices):
                        target_devices = [devices[dev_idx]]
                    else:
                        print(f"  {C.ERR}[-] Lựa chọn nằm ngoài vùng dữ liệu.{C.RESET}")
                        input("\n  Nhấn Enter để quay lại...")
                        return
            except Exception:
                print(f"  {C.ERR}[-] Dữ liệu nhập không hợp lệ.{C.RESET}")
                input("\n  Nhấn Enter để quay lại...")
                return

            detected_accounts = []
            for serial in target_devices:
                print(f"\n  {C.CYAN}[*] Đang quét danh sách package Roblox trên thiết bị {serial}...{C.RESET}")
                pkgs = Utils.detect_roblox_packages_adb(serial)
                if not pkgs:
                    print(f"  {C.ERR}[-] Không tìm thấy gói ứng dụng Roblox nào trên {serial}.{C.RESET}")
                    continue
                
                for pkg in pkgs:
                    print(f"  [*] Đang trích xuất cookie từ gói {pkg} trên {serial}...")
                    cookie = Utils.get_roblox_cookie_adb(serial, pkg)
                    if not cookie:
                        print(f"  {C.ERR}[-] Không thể lấy cookie an toàn từ ứng dụng.{C.RESET}")
                        continue
                    
                    user = RobloxUser(cookie=cookie)
                    uid = user.fetch_authenticated_user()
                    if not uid:
                        print(f"  {C.ERR}[-] Lỗi xác minh tài khoản từ cookie thu được.{C.RESET}")
                        continue
                    
                    detected_accounts.append({
                        "serial": serial,
                        "package": pkg,
                        "displayName": pkgs[pkg]["displayName"],
                        "username": user.username,
                        "userId": uid,
                        "cookie": cookie
                    })

            if not detected_accounts:
                print(f"\n  {C.ERR}[-] Thất bại: Không lấy được tài khoản hợp lệ nào từ thiết bị chỉ định.{C.RESET}")
                input("\n  Nhấn Enter để quay lại...")
                return

            print(f"\n  {C.SUC}[+] Hoàn tất! Phát hiện thành công {len(detected_accounts)} tài khoản.{C.RESET}")
            for i, acc in enumerate(detected_accounts, 1):
                print(f"  {i}. Thiết bị: {acc['serial']} | Gói: {acc['package']} | User: {C.CYAN}{acc['username']}{C.RESET}")
            
            apply_all = input(f"\n  {C.H2}👉 Bạn có muốn áp dụng CÙNG MỘT CẤU HÌNH game cho mọi tài khoản không? (y/n): {C.RESET}").strip().lower()
            
            global_place_id = ""
            global_game_name = ""
            global_link_code = None
            global_delay = 30
            
            if apply_all == 'y':
                print(f"\n  {C.H2}--- THIẾT LẬP CẤU HÌNH CHUNG ---{C.RESET}")
                for k, v in GAMES.items():
                    print(f"  [{k}] {v[1]} (PlaceID: {v[0]})")
                print("  [C] Nhập PlaceID tùy chỉnh bên ngoài")
                
                game_sel = input(" Nhập lựa chọn game: ").strip()
                if game_sel in GAMES:
                    global_place_id, global_game_name = GAMES[game_sel]
                else:
                    global_place_id = input(" Nhập PlaceID tùy chỉnh: ").strip()
                    global_game_name = input(" Nhập tên Game hiển thị: ").strip() or "Custom"
                
                if global_place_id:
                    global_link_code = input(" Nhập Link Private Server (Không có -> Nhấn Enter): ").strip() or None
                    try:
                        delay_in = input(" Nhập thời gian giãn cách quét (Mặc định 30s): ").strip()
                        global_delay = int(delay_in) if delay_in else 30
                        if not 15 <= global_delay <= 120:
                            global_delay = 30
                    except ValueError:
                        global_delay = 30
            
            for acc in detected_accounts:
                profile_key = f"{acc['package']}_{acc['serial'].replace('.', '_').replace(':', '_')}"
                
                if apply_all == 'y' and global_place_id:
                    place_id = global_place_id
                    game_name = global_game_name
                    link_code = global_link_code
                    delay = global_delay
                else:
                    print(f"\n  {C.H2}--- Cấu hình game riêng cho tài khoản: {C.SUC}{acc['username']}{C.H2} ({acc['serial']}) ---{C.RESET}")
                    for k, v in GAMES.items():
                        print(f"  [{k}] {v[1]} (PlaceID: {v[0]})")
                    print("  [C] Nhập PlaceID tùy chỉnh bên ngoài")
                    
                    game_sel = input(" Nhập lựa chọn game: ").strip()
                    place_id = ""
                    game_name = "Custom"
                    if game_sel in GAMES:
                        place_id, game_name = GAMES[game_sel]
                    else:
                        place_id = input(" Nhập PlaceID tùy chỉnh: ").strip()
                        game_name = input(" Nhập tên Game hiển thị: ").strip() or "Custom"
                    
                    if not place_id:
                        print(f"  {C.WRN}[-] Bỏ qua tài khoản này.{C.RESET}")
                        continue
                        
                    link_code = input(" Nhập Link Private Server (Không có -> Nhấn Enter): ").strip() or None
                    try:
                        delay_in = input(" Nhập thời gian giãn cách quét (Mặc định 30s): ").strip()
                        delay = int(delay_in) if delay_in else 30
                        if not 15 <= delay <= 120:
                            delay = 30
                    except ValueError:
                        delay = 30
                
                configs[profile_key] = {
                    "username":    acc["username"],
                    "userId":      acc["userId"],
                    "placeId":     place_id,
                    "gameName":    game_name,
                    "linkCode":    link_code,
                    "delaySec":    delay,
                    "packageName": acc["package"],
                    "mode":        "adb",
                    "adb_serial":  acc["serial"],
                    "cookie":      acc["cookie"]
                }
                print(f"  {C.SUC}[+] Đã lưu cấu hình hoạt động: {profile_key}{C.RESET}")
                
            Utils.save_multi_configs(configs)
            print(f"\n  {C.SUC}[+] Hoàn tất lưu trữ cấu hình qua ADB!{C.RESET}")
            input("\n  Nhấn Enter để quay lại...")
            
        else:
            if not IS_ANDROID:
                print(f"\n  {C.ERR}[-] Thiết bị cục bộ hiện tại không phải hệ điều hành Android (Termux)!{C.RESET}")
                input("\n  Nhấn Enter để quay lại...")
                return
            print("  [*] Đang quét các gói cài đặt Roblox cục bộ trên thiết bị...")
            pkgs = Utils.detect_all_roblox_packages()

            if not pkgs:
                print(f"\n  {C.ERR}[-] Không tìm thấy gói cài đặt nào trong phân vùng.{C.RESET}")
                input("\n  Nhấn Enter để quay lại...")
                return

            pkg_list = list(pkgs.keys())
            for i, pkg in enumerate(pkg_list, 1):
                print(f"  {C.CYAN}[{i}]{C.TXT} {pkgs[pkg]['displayName']} ({pkg})")

            print(f"\n  {C.TXT}Nhập số thứ tự của Package muốn chọn (Ví dụ: 1, 2 hoặc Enter để chọn hết):")
            sel_input = input(f"  {C.H2}👉 Lựa chọn: {C.RESET}").strip()
            selected_pkgs = []
            if not sel_input:
                selected_pkgs = pkg_list
            else:
                try:
                    selected_pkgs = [pkg_list[int(x.strip()) - 1] for x in sel_input.split(",") if x.strip()]
                except (ValueError, IndexError):
                    print(f"  {C.ERR}[-] Tùy chọn không hợp lệ.{C.RESET}")
                    input("\n  Nhấn Enter để tiếp tục...")
                    return

            for pkg in selected_pkgs:
                print(f"\n  [*] Đang thực thi trích xuất cookie từ: {pkg}...")
                cookie = Utils.get_roblox_cookie(pkg)

                if not cookie:
                    print(f"  {C.ERR}[-] Thất bại: Không lấy được thông tin từ bộ nhớ {pkg}. Đảm bảo đã bật ROOT.{C.RESET}")
                    continue

                user = RobloxUser(cookie=cookie)
                uid = user.fetch_authenticated_user()
                if not uid:
                    print(f"  {C.ERR}[-] Không thể xác thực phiên đăng nhập hiện thời.{C.RESET}")
                    continue

                print(f"  {C.SUC}[+] Xác thực thành công tài khoản: {user.username} (ID: {uid}){C.RESET}")
                
                print(f"\n  {C.H2}--- CHỌN GAME MUỐN THIẾT LẬP ---{C.RESET}")
                for k, v in GAMES.items():
                    print(f"  [{k}] {v[1]} (PlaceID: {v[0]})")
                print("  [C] Nhập PlaceID tùy chỉnh bên ngoài")
                
                game_sel = input(" Nhập lựa chọn game: ").strip()
                place_id = ""
                game_name = "Custom"
                if game_sel in GAMES:
                    place_id, game_name = GAMES[game_sel]
                else:
                    place_id = input(" Nhập PlaceID tùy chỉnh: ").strip()
                    game_name = input(" Nhập tên Game hiển thị: ").strip() or "Custom"

                if not place_id:
                    print(f"  {C.WRN}[-] Bỏ qua gói tài khoản hiện thời.{C.RESET}")
                    continue

                link_code = input(" Nhập Link Private Server (Không có -> Nhấn Enter): ").strip() or None
                
                try:
                    delay = int(input(" Thời gian giãn cách kiểm tra trạng thái (Mặc định 30s): ").strip() or "30")
                    if not 15 <= delay <= 120:
                        delay = 30
                except ValueError:
                    delay = 30

                profile_key = pkg
                configs[profile_key] = {
                    "username":    user.username,
                    "userId":      uid,
                    "placeId":     place_id,
                    "gameName":    game_name,
                    "linkCode":    link_code,
                    "delaySec":    delay,
                    "packageName": pkg,
                    "mode":        "local",
                    "adb_serial":  None,
                    "cookie":      cookie
                }
                print(f"  {C.SUC}[+] Đã lưu cấu hình thành công cho hồ sơ {profile_key}{C.RESET}")

            Utils.save_multi_configs(configs)
            print(f"\n  {C.SUC}[+] Đã lưu toàn bộ cơ sở dữ liệu cấu hình!{C.RESET}")
            input("\n  Nhấn Enter để tiếp tục...")

    # ── Chức năng 3: Thêm cấu hình thủ công ───────────────────────────────────
    def add_manual_config(self):
        Utils.clear_screen()
        print(f"  {C.H2}🆕 [ TẠO HỒ SƠ TÀI KHOẢN THỦ CÔNG ]{C.RESET}")
        print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
        print("  Chọn cơ chế hoạt động cho hồ sơ tài khoản:")
        print(f"   {C.CYAN}[1]{C.TXT} Chạy cục bộ trực tiếp trên PC/Thiết bị cầm tay (Local)")
        print(f"   {C.CYAN}[2]{C.TXT} Điều hành từ xa thông qua liên kết thiết bị (ADB)")
        print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
        m_sel = input(f"\n  {C.H2}👉 Nhập tùy chọn (1-2): {C.RESET}").strip()
        
        mode = "adb" if m_sel == "2" else "local"
        adb_serial = None
        
        if mode == "adb":
            devices = Utils.get_adb_devices()
            if devices:
                print(f"\n  Chọn thiết bị ADB đang trực tuyến:")
                for idx, dev in enumerate(devices, 1):
                    print(f"  [{idx}] {dev}")
                try:
                    dev_idx = int(input(" Lựa chọn thiết bị: ").strip()) - 1
                    adb_serial = devices[dev_idx]
                except Exception:
                    pass
            if not adb_serial:
                adb_serial = input("\n Nhập IP/Serial thủ công của cổng ADB: ").strip()

        default_profile = "com.roblox.client"
        pkg = input(f" Nhập Tên Hồ Sơ / Package Name (Mặc định: {default_profile}): ").strip() or default_profile
        
        username = input(" Tên tài khoản (Username Roblox): ").strip()
        user_id = input(" Mã số tài khoản (User ID Roblox): ").strip()
        
        print(f" Nhập Cookie (.ROBLOSECURITY dùng để trích xuất dữ liệu sâu của API - Nếu có):")
        cookie_input = input(" > ").strip()
        cookie = None
        if cookie_input:
            if not cookie_input.startswith(".ROBLOSECURITY="):
                if cookie_input.startswith("_|"):
                    cookie = f".ROBLOSECURITY={cookie_input}"
                else:
                    cookie = cookie_input
            else:
                cookie = cookie_input

        print(f"\n  {C.H2}--- CHỌN GAME TREO ---{C.RESET}")
        for k, v in GAMES.items():
            print(f"  [{k}] {v[1]} (PlaceID: {v[0]})")
        print("  [C] Nhập PlaceID tùy chỉnh")
        
        game_sel = input(" Chọn loại game: ").strip()
        place_id = ""
        game_name = "Custom"
        if game_sel in GAMES:
            place_id, game_name = GAMES[game_sel]
        else:
            place_id = input(" Nhập PlaceID tùy chỉnh: ").strip()
            game_name = input(" Nhập tên Game hiển thị: ").strip() or "Custom"

        if not place_id or not username or not user_id:
            print(f"  {C.ERR}[-] Thất bại: Không thể bỏ trống các tham số cốt lõi.{C.RESET}")
            input("\n  Nhấn Enter để quay lại...")
            return

        link_code = input(" Nhập Link Private Server (Nếu không có -> Nhấn Enter): ").strip() or None
        
        try:
            delay = int(input(" Thời gian quét kiểm tra (Giây, Mặc định 30s): ").strip() or "30")
            if not 15 <= delay <= 120:
                delay = 30
        except ValueError:
            delay = 30

        configs = Utils.load_multi_configs()
        
        profile_name = f"{pkg}_{adb_serial.replace(':', '_')}" if adb_serial else pkg
        configs[profile_name] = {
            "username":    username,
            "userId":      user_id,
            "placeId":     place_id,
            "gameName":    game_name,
            "linkCode":    link_code,
            "delaySec":    delay,
            "packageName": pkg,
            "mode":        mode,
            "adb_serial":  adb_serial,
            "cookie":      cookie
        }
        Utils.save_multi_configs(configs)
        print(f"\n  {C.SUC}[+] Đã thiết lập thành công hồ sơ {profile_name}!{C.RESET}")
        input("\n  Nhấn Enter để tiếp tục...")

    # ── Chức năng 4: Xem / Chỉnh sửa / Xóa danh sách cấu hình ─────────────────
    def manage_configs(self):
        while True:
            Utils.clear_screen()
            configs = Utils.load_multi_configs()
            
            print(f"  {C.H2}📋 [ DANH SÁCH TẤT CẢ HỒ SƠ LƯU TRỮ ]{C.RESET}")
            print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
            if not configs:
                print(f"  [-] Hệ thống hiện trống cấu hình tài khoản.")
                print(f"   {C.SUC}[1]{C.TXT} Khởi tạo hồ sơ mới")
                print(f"   [2] Quay về trang chủ")
                print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
                opt = input(f"  {C.H2}👉 Nhập lựa chọn: {C.RESET}").strip()
                if opt == "1":
                    self.add_manual_config()
                    continue
                else:
                    break

            pkg_list = list(configs.keys())
            for idx, pkg in enumerate(pkg_list, 1):
                cfg = configs[pkg]
                mode_str = cfg.get("mode", "local").upper()
                serial_info = f" | Dev: {cfg.get('adb_serial')}" if cfg.get("adb_serial") else ""
                
                print(f"   {C.CYAN}[{idx}]{C.RESET} Hồ sơ: {C.BOLD}{pkg}{C.RESET} ({C.CYAN}{mode_str}{serial_info}{C.RESET})")
                print(f"      ▸ Username: {Utils.mask(cfg['username'])} (ID: {Utils.mask(cfg['userId'])})")
                print(f"      ▸ Bản đồ:   {cfg['gameName']} (ID: {cfg['placeId']})")
                print(f"      ▸ Quét:     {cfg['delaySec']}s | Private Link: {'Có' if cfg.get('linkCode') else 'Không'}")
                print(f"      ▸ Cookie:   {'Đã nhập ✓' if cfg.get('cookie') else 'Trống ✗'}")
                print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")

            print("  Lựa chọn hành động:")
            print(f"    {C.CYAN}[STT]{C.TXT} Nhập số thứ tự của tài khoản để sửa hoặc xóa")
            print(f"    {C.ERR}[C]{C.TXT} Xóa toàn bộ danh sách cấu hình đang lưu trữ")
            print(f"    {C.TXT}[B] Quay lại trang chủ")
            act = input(f"\n  {C.H2}👉 Nhập hành động: {C.RESET}").strip().lower()

            if act == 'b':
                break
            elif act == 'c':
                confirm = input(f"  {C.ERR}[!] Bạn có đồng ý xóa toàn bộ cấu hình? (y/n): {C.RESET}").strip().lower()
                if confirm == 'y':
                    Utils.save_multi_configs({})
                    print("  [+] Đã dọn sạch cơ sở dữ liệu cấu hình.")
                    time.sleep(1)
            else:
                try:
                    idx = int(act) - 1
                    if 0 <= idx < len(pkg_list):
                        target_pkg = pkg_list[idx]
                        self.edit_single_config(target_pkg, configs)
                except ValueError:
                    pass

    def edit_single_config(self, pkg, configs):
        cfg = configs[pkg]
        Utils.clear_screen()
        print(f"  {C.H2}⚙️ [ CHỈNH SỬA CẤU HÌNH TÀI KHOẢN: {pkg[:20]}... ]{C.RESET}")
        print(f"  {C.GRAY}(Nhấn Enter để bỏ qua / Giữ lại giá trị thiết lập ban đầu){C.RESET}")
        print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}\n")
        
        place_id = input(f" Place ID mới (Hiện hành: {cfg['placeId']}): ").strip() or cfg['placeId']
        game_name = input(f" Tên game hiển thị mới (Hiện hành: {cfg['gameName']}): ").strip() or cfg['gameName']
        
        raw_link = input(f" Nhập Link Private mới (Nhập 'del' để gỡ bỏ hoàn toàn): ").strip()
        if raw_link.lower() == 'del':
            link_code = None
        elif raw_link:
            link_code = raw_link
        else:
            link_code = cfg.get("linkCode")

        raw_cookie = input(" Nhập Cookie mới (Nhập 'del' để gỡ bỏ): ").strip()
        if raw_cookie.lower() == 'del':
            cookie = None
        elif raw_cookie:
            if not raw_cookie.startswith(".ROBLOSECURITY="):
                cookie = f".ROBLOSECURITY={raw_cookie}" if raw_cookie.startswith("_|") else raw_cookie
            else:
                cookie = raw_cookie
        else:
            cookie = cfg.get("cookie")

        try:
            delay_in = input(f" Thời gian giãn cách quét mới (Hiện hành: {cfg['delaySec']}s): ").strip()
            delay = int(delay_in) if delay_in else cfg['delaySec']
            if not 15 <= delay <= 120:
                delay = cfg['delaySec']
        except ValueError:
            delay = cfg['delaySec']

        configs[pkg].update({
            "placeId": place_id,
            "gameName": game_name,
            "linkCode": link_code,
            "delaySec": delay,
            "cookie": cookie
        })
        
        print(f"\n    {C.SUC}[1]{C.TXT} Lưu tất cả thay đổi cấu hình")
        print(f"    {C.ERR}[2]{C.TXT} XÓA tài khoản hiện hành khỏi hệ thống")
        print(f"    {C.TXT}[3] Hủy bỏ và quay lại")
        op = input(f"\n  {C.H2}👉 Chọn hành động: {C.RESET}").strip()
        if op == "1":
            Utils.save_multi_configs(configs)
            print(f"  {C.SUC}[+] Cập nhật dữ liệu thành công.{C.RESET}")
        elif op == "2":
            del configs[pkg]
            Utils.save_multi_configs(configs)
            print(f"  {C.WRN}[-] Đã xóa thành công hồ sơ.{C.RESET}")
        
        time.sleep(1)

    # ── Chức năng 5: Cấu hình cài đặt ADB & Quét Thiết bị Giả lập ────────────────
    def manage_adb_settings(self):
        while True:
            Utils.clear_screen()
            adb_path = Utils.load_adb_path()
            devices_info = Utils.get_adb_devices_detailed()
            
            print(f"  {C.H2}⚙️ [ CẤU HÌNH LIÊN KẾT TRÌNH GIẢ LẬP / THIẾT BỊ (ADB) ]{C.RESET}")
            print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
            print(f"  Đường dẫn ADB hiện tại: {C.CYAN}{adb_path}{C.RESET}")
            print(f"  Danh sách thiết bị kết nối:")
            
            if devices_info:
                for idx, dev in enumerate(devices_info, 1):
                    state = dev["state"]
                    if state == "device":
                        status_str = f"{C.SUC}[Trực tuyến - Sẵn sàng]{C.RESET}"
                    elif state == "unauthorized":
                        status_str = f"{C.WRN}[Chờ xác nhận trên màn hình thiết bị]{C.RESET}"
                    elif state == "offline":
                        status_str = f"{C.ERR}[Mất kết nối - Offline]{C.RESET}"
                    else:
                        status_str = f"{C.GRAY}[Trạng thái: {state}]{C.RESET}"
                        
                    print(f"   {C.CYAN}[{idx}]{C.TXT} {dev['serial']:<22} {status_str}")
            else:
                print(f"   {C.ERR}[-] Không tìm thấy thiết bị ADB nào đang trực tuyến!{C.RESET}")
                
            print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
            print(f"   {C.SUC}[1]{C.TXT} Tự động quét và kết nối giả lập (Auto-detect Ports)")
            print(f"   {C.SUC}[2]{C.TXT} Kết nối thủ công bằng IP/Cổng (Ví dụ: 127.0.0.1:5555)")
            print(f"   {C.SUC}[3]{C.TXT} Ghép nối thiết bị không dây mới (ADB Pair - Android 11+)")
            print(f"   {C.CYAN}[4]{C.TXT} Khởi động lại ADB Server (Sửa lỗi treo/nghẽn kết nối)")
            print(f"   {C.CYAN}[5]{C.TXT} Thay đổi đường dẫn tệp thực thi ADB")
            print(f"   {C.BLUE}[6]{C.TXT} Quét và làm mới danh sách")
            print(f"   [7] Quay lại Menu chính")
            print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
            
            opt = input(f"\n  {C.H2}👉 Nhập lựa chọn thực thi: {C.RESET}").strip()

            if opt == "1":
                print(f"\n  [*] Đang chạy quét tự động qua các cổng giả lập thông dụng...")
                connected_count = 0
                for port in Utils.COMMON_EMULATOR_PORTS:
                    addr = f"127.0.0.1:{port}"
                    if any(d["serial"] == addr and d["state"] == "device" for d in devices_info):
                        continue
                    
                    sys.stdout.write(f"    ▸ Thử kết nối {addr}... ")
                    sys.stdout.flush()
                    res = Utils.connect_adb_device(addr)
                    if "connected to" in res.lower():
                        print(f"{C.SUC}Thành công!{C.RESET}")
                        connected_count += 1
                    else:
                        print(f"{C.GRAY}Không phát hiện{C.RESET}")
                
                print(f"\n  {C.SUC}[+] Quá trình hoàn tất. Đã kết nối thêm {connected_count} cổng giả lập mới.{C.RESET}")
                time.sleep(2)
                
            elif opt == "2":
                addr = input("\n  Nhập địa chỉ IP và Cổng (Ví dụ: 127.0.0.1:62001): ").strip()
                if addr:
                    print(f"  [*] Đang gửi yêu cầu kết nối tới {addr}...")
                    res = Utils.connect_adb_device(addr)
                    print(f"  [Kết quả] {res}")
                input("\n  Nhấn Enter để tiếp tục...")
                
            elif opt == "3":
                addr = input("\n  Nhập IP và Cổng ghép nối (Ví dụ: 192.168.1.50:39811): ").strip()
                code = input("  Nhập mã pin ghép nối (Pairing Code): ").strip()
                if addr and code:
                    print(f"  [*] Đang thực hiện ghép nối bảo mật...")
                    res = Utils.pair_adb_device(addr, code)
                    print(f"  [Kết quả] {res}")
                input("\n  Nhấn Enter để tiếp tục...")
                
            elif opt == "4":
                print(f"\n  [*] Đang khởi động lại trình máy chủ ADB (kill & restart)...")
                Utils.restart_adb_server()
                print(f"  {C.SUC}[+] Khởi động thành công ADB Server!{C.RESET}")
                time.sleep(1.5)
                
            elif opt == "5":
                print("\n  Nhập đường dẫn tuyệt đối dẫn đến tệp tin thực thi adb.")
                print("  Ví dụ: C:\\Program Files\\Nox\\bin\\adb.exe")
                new_path = input("  Đường dẫn mới: ").strip()
                if new_path:
                    new_path = new_path.strip('"').strip("'")
                    Utils.save_adb_path(new_path)
                    print(f"  {C.SUC}[+] Lưu đường dẫn ADB mới thành công!{C.RESET}")
                time.sleep(1.5)
                
            elif opt == "6":
                print("  [*] Đang nạp lại dữ liệu...")
                time.sleep(0.5)
                
            elif opt == "7":
                break

    # ── Chức năng 6: Thay đổi Package Prefix (Chỉ cho Android/ADB) ─────────────
    def change_prefix(self):
        Utils.clear_screen()
        curr = Utils.load_package_prefix()
        print(f"  {C.H2}🏷️ [ ĐỊNH DẠNG PACKAGE PREFIX ]{C.RESET}")
        print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
        print(f"  Định dạng Package Prefix hiện hành: {C.CYAN}{curr}{C.RESET}")
        print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
        new_prefix = input("  Nhập định dạng Prefix mới (Hoặc nhấn Enter để bỏ qua): ").strip()
        if new_prefix:
            Utils.save_package_prefix(new_prefix)
            print(f"  {C.SUC}[+] Thay đổi thành công: {new_prefix}{C.RESET}")
        time.sleep(1)

    # ── Chức năng 7: Thay đổi Activity Custom (Chỉ cho Android/ADB) ────────────
    def change_activity(self):
        Utils.clear_screen()
        curr = Utils.load_activity_config() or "(Mặc định: com.roblox.client.ActivityProtocolLaunch)"
        print(f"  {C.H2}🔧 [ CẤU HÌNH CUSTOM ACTIVITY LAUNCH ]{C.RESET}")
        print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
        print(f"  Class Activity đang sử dụng:")
        print(f"  {C.CYAN}{curr}{C.RESET}")
        print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
        new_act = input("  Nhập tên Class mới (Nhấn Enter để đặt lại mặc định): ").strip()
        if new_act:
            Utils.save_activity_config(new_act)
            print(f"  {C.SUC}[+] Cập nhật thành công Class: {new_act}{C.RESET}")
        else:
            Utils.save_activity_config(None)
            print(f"  {C.SUC}[+] Đã đặt lại cấu hình Class khởi chạy mặc định.{C.RESET}")
        time.sleep(1)

    # ── Chức năng 8: Thiết lập Webhook Discord ──────────────────────────────
    def manage_webhook(self):
        while True:
            Utils.clear_screen()
            cfg = Utils.load_webhook_config()
            print(f"  {C.H2}🔔 [ KẾT NỐI DISCORD WEBHOOK LOGGING ]{C.RESET}")
            print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
            if cfg:
                status_str = f"{C.SUC}[ĐANG HOẠT ĐỘNG]{C.RESET}" if cfg.get("enabled") else f"{C.ERR}[NGỪNG HOẠT ĐỘNG]{C.RESET}"
                print(f"  Trạng thái hoạt động: {status_str}")
                print(f"  URL: {C.CYAN}{cfg.get('url')[:60]}...{C.RESET}")
                print(f"  Tần suất gửi thông báo: {C.WRN}Mỗi {cfg.get('intervalMinutes')} phút{C.RESET}")
            else:
                print(f"  [-] Hệ thống hiện chưa có kết nối webhook nào.")
            print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
            print(f"   {C.CYAN}[1]{C.TXT} Thiết lập mới hoặc Thay thế địa chỉ Discord Webhook URL")
            print(f"   {C.CYAN}[2]{C.TXT} Chuyển đổi trạng thái sử dụng (Bật / Tắt)")
            print(f"   {C.CYAN}[3]{C.TXT} Thực hiện gửi thử nghiệm tin nhắn mẫu (Kèm chụp màn hình)")
            print(f"   {C.ERR}[4]{C.TXT} Gỡ bỏ hoàn toàn liên kết Webhook hiện hành")
            print(f"   [5] Quay lại trang chủ")
            print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
            opt = input(f"\n  {C.H2}👉 Nhập lựa chọn: {C.RESET}").strip()

            if opt == "1":
                url = input(" Nhập địa chỉ liên kết Discord Webhook URL: ").strip()
                if not url or "discord.com/api/webhooks/" not in url:
                    print(f"  {C.ERR}[-] Đường dẫn liên kết Discord Webhook không chính xác!{C.RESET}")
                    time.sleep(1.5)
                    continue
                try:
                    mins = int(input(" Thời gian giãn cách gửi báo cáo định kỳ (Phút, Mặc định 30): ").strip() or "30")
                    if not 5 <= mins <= 180:
                        mins = 30
                except ValueError:
                    mins = 30
                
                Utils.save_webhook_config({"url": url, "intervalMinutes": mins, "enabled": True})
                print(f"  {C.SUC}[+] Thiết lập kết nối thành công.{C.RESET}")
                time.sleep(1)
            elif opt == "2":
                if cfg:
                    cfg["enabled"] = not cfg.get("enabled", True)
                    Utils.save_webhook_config(cfg)
                    print(f"  {C.SUC}[+] Trạng thái chuyển đổi thành công: {'BẬT' if cfg['enabled'] else 'TẮT'}{C.RESET}")
                else:
                    print(f"  {C.ERR}[-] Không có cấu hình Webhook nào hoạt động.{C.RESET}")
                time.sleep(1)
            elif opt == "3":
                if cfg:
                    print("  [*] Đang chụp màn hình hệ thống và truyền tải dữ liệu đến Discord...")
                    embed = {
                        "title": "🧪 Thử Nghiệm Kết Nối - Rbl Rejoin CLI",
                        "color": 0x00BFFF,
                        "description": "Tín hiệu hoạt động tốt! Webhook đã được cấu hình thành công.",
                        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    }
                    screenshot = Utils.take_screenshot()
                    self.executor.submit(Utils.send_webhook_embed, cfg["url"], embed, screenshot)
                    print(f"  {C.SUC}[+] Gửi tín hiệu thành công!{C.RESET}")
                else:
                    print(f"  {C.ERR}[-] Không tìm thấy cấu hình kết nối Webhook nào.{C.RESET}")
                time.sleep(1.5)
            elif opt == "4":
                if input(" Bạn có chắc muốn xóa cấu hình Webhook? (y/n): ").strip().lower() == "y":
                    Utils.save_webhook_config(None)
                    print(f"  {C.WRN}[-] Đã xóa cấu hình.{C.RESET}")
                time.sleep(1)
            elif opt == "5":
                break

    # ── Chức năng 9: Thiết lập Autoexec Script (Cả Android & PC) ───────────────
    def manage_autoexec(self):
        mgr = AutoexecManager()
        while True:
            Utils.clear_screen()
            cfg = mgr.load_config()
            print(f"  {C.H2}📝 [ CẤU HÌNH ĐỒNG BỘ AUTOEXEC SCRIPT ]{C.RESET}")
            print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
            if cfg:
                print(f"  Trình thực thi hỗ trợ: {C.CYAN}{cfg.get('executor')}{C.RESET}")
                print(f"  File liên kết đích:   {C.WHITE}{cfg.get('path')}{C.RESET}")
                short_script = cfg.get('script', '').replace('\n', ' ')[:45]
                print(f"  Script tóm tắt:       {C.GRAY}{short_script}...{C.RESET}")
            else:
                print(f"  [-] Hệ thống hiện chưa được cấu hình kịch bản Autoexec nào.")
            print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
            print(f"   {C.CYAN}[1]{C.TXT} Thiết lập mới hoặc Sửa đổi tệp cấu hình Autoexec Script")
            print(f"   {C.CYAN}[2]{C.TXT} Hiển thị chi tiết nội dung tệp Script đang đồng bộ")
            print(f"   {C.ERR}[3]{C.TXT} Hủy bỏ liên kết & Xóa tệp đồng bộ kịch bản")
            print(f"   [4] Quay lại trang chủ")
            print(f"  {C.GRAY}────────────────────────────────────────────────────────────────────────{C.RESET}")
            opt = input(f"\n  {C.H2}👉 Nhập lựa chọn: {C.RESET}").strip()

            if opt == "1":
                print(f"\n  {C.H2}Lựa chọn Executor hỗ trợ:{C.RESET}")
                exec_names = list(EXECUTORS.keys())
                for i, name in enumerate(exec_names, 1):
                    print(f"  {C.CYAN}[{i}]{C.TXT} {name} (Đường dẫn: {EXECUTORS[name]})")
                print(f"  {C.CYAN}[{len(exec_names) + 1}]{C.TXT} Đặt đường dẫn tùy biến riêng (Custom Path)")
                
                try:
                    choice_idx = int(input(" Lựa chọn: ").strip())
                    if choice_idx == len(exec_names) + 1:
                        executor = "Custom Path"
                        custom_path = input(" Nhập đường dẫn tệp tuyệt đối (.txt): ").strip()
                        if not custom_path:
                            print(f"  {C.ERR}[-] Đường dẫn không hợp lệ. Hủy bỏ.{C.RESET}")
                            time.sleep(1)
                            continue
                    else:
                        executor = exec_names[choice_idx - 1]
                        custom_path = EXECUTORS[executor]
                except (ValueError, IndexError):
                    print(f"  {C.ERR}[-] Tùy chọn không hợp lệ.{C.RESET}")
                    time.sleep(1)
                    continue

                print(f"\n Nhập đoạn mã Script Lua cần thực thi (Kết thúc ghi bằng dòng nhập có từ {C.ERR}__END__{C.RESET}):")
                lines = []
                while True:
                    line = input()
                    if line.strip() == "__END__":
                        break
                    lines.append(line)
                script = "\n".join(lines).strip()

                if not script:
                    print(f"  {C.ERR}[-] Nội dung rỗng. Hủy bỏ thao tác.{C.RESET}")
                    time.sleep(1)
                    continue

                new_cfg = {
                    "executor": executor,
                    "script": script,
                    "path": custom_path
                }
                mgr.save_config(new_cfg)
                print(f"  {C.SUC}[+] Thiết lập hoàn tất! Kịch bản sẽ tự động đồng bộ khi quá trình Rejoin diễn ra.{C.RESET}")
                time.sleep(2)
            elif opt == "2":
                if cfg:
                    Utils.clear_screen()
                    print(f"  {C.H2}--- NỘI DUNG MÃ NGUỒN SCRIPT HOẠT ĐỘNG ---{C.RESET}")
                    print(cfg.get('script'))
                    print(f"  {C.H2}──────────────────────────────────────────────────────────────────────────{C.RESET}")
                    input("  Nhấn phím Enter để tiếp tục quay lại...")
                else:
                    print(f"  {C.ERR}[-] Chưa cấu hình kịch bản nào để hiển thị.{C.RESET}")
                    time.sleep(1)
            elif opt == "3":
                if input(" Bạn chắc chắn muốn xóa cấu hình Autoexec? (y/n): ").strip().lower() == "y":
                    mgr.save_config(None)
                    print(f"  {C.WRN}[-] Đã dọn sạch kịch bản.{C.RESET}")
                time.sleep(1)
            elif opt == "4":
                break


# === ENTRY POINT ===
if __name__ == "__main__":
    cli = AppCLI()
    cli.run()