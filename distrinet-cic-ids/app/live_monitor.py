"""GIAM SAT MANG TRUC TIEP (thu nghiem): bat goi tin tren 1 hoac nhieu card mang (Wi-Fi, day mang),
gom thanh luong, tinh dac trung, va cho mo hinh danh gia moi vai giay.

Hai cach bat goi tin, ung dung tu chon:
- "raw": raw socket co san cua Windows. KHONG can cai them gi, nhung can chay cmd bang quyen Administrator.
  Chi doc duoc goi IPv4.
- "npcap": dung scapy + Npcap neu may da cai (doc duoc ca IPv6, khong can quyen Administrator).
Chi giam sat mang cua ban hoac mang ban duoc phep giam sat."""
import json
import platform
import socket
import struct
import subprocess
import threading
import time
from collections import deque

import pandas as pd

from validation import kiem_tra
from flow_builder import TEN_DAC_TRUNG, BangLuong, GoiTin

TOI_DA_LUU = 50_000
LA_WINDOWS = platform.system() == "Windows"


# ======================= Kiem tra moi truong =======================
def _co_npcap():
    try:
        from scapy.all import conf
        return bool(conf.use_pcap) if LA_WINDOWS else True
    except Exception:
        return False


def _la_admin():
    if not LA_WINDOWS:
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def kiem_tra_moi_truong():
    """Tra ve (ok, thong_bao, cach_bat) voi cach_bat in {'npcap', 'raw', None}."""
    if _co_npcap():
        return True, "", "npcap"
    if not LA_WINDOWS:
        return False, "Chế độ này được thiết kế cho Windows.", None
    if not _la_admin():
        return False, ("Cần quyền Administrator để đọc gói tin bằng raw socket của Windows. Tắt ứng dụng, "
                       "bấm phím Windows, gõ cmd, bấm chuột phải vào Command Prompt, chọn "
                       "\"Run as administrator\", rồi chạy lại các lệnh khởi động ứng dụng."), None
    return True, "", "raw"


# ======================= Liet ke card mang =======================
def _loai_card(ten):
    t = (ten or "").lower()
    if any(k in t for k in ("wi-fi", "wifi", "wireless", "802.11", "wlan")):
        return "Wi-Fi"
    if any(k in t for k in ("ethernet", "gbe", "lan")):
        return "Dây mạng"
    if "loopback" in t:
        return "Loopback"
    return "Khác"


def _card_raw():
    """Card IPv4 tren Windows qua PowerShell (InterfaceAlias: 'Wi-Fi', 'Ethernet', ...)."""
    out = []
    try:
        lenh = ("Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -ne '127.0.0.1'} | "
                "Select-Object InterfaceAlias,IPAddress | ConvertTo-Json -Compress")
        r = subprocess.run(["powershell", "-NoProfile", "-Command", lenh], capture_output=True, text=True,
                           timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        ds = json.loads(r.stdout or "[]")
        ds = [ds] if isinstance(ds, dict) else ds
        for d in ds:
            out.append((d.get("InterfaceAlias", ""), d.get("IPAddress", "")))
    except Exception:
        pass
    if not out:   # du phong: chi co dia chi IP, khong co ten card
        try:
            ips = {a[4][0] for a in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}
            out = [("Card mạng", ip) for ip in sorted(ips) if not ip.startswith("127.")]
        except Exception:
            pass
    cards = []
    for ten, ip in out:
        loai = _loai_card(ten)
        if loai == "Loopback" or not ip:
            continue
        cards.append({"id": f"raw:{ip}", "nhan": f"{loai}: {ten} ({ip})", "loai": loai,
                      "co_ip": not ip.startswith("169.254")})
    return cards


def _card_npcap():
    from scapy.all import conf
    cards = []
    for i in conf.ifaces.values():
        mo_ta = getattr(i, "description", "") or getattr(i, "name", "")
        ip = getattr(i, "ip", "") or ""
        loai = _loai_card(mo_ta + " " + str(getattr(i, "name", "")))
        if loai == "Loopback":
            continue
        cards.append({"id": f"npcap:{i.name}", "nhan": f"{loai}: {mo_ta}" + (f" ({ip})" if ip else " (chưa có IP)"),
                      "loai": loai, "co_ip": bool(ip and not ip.startswith("169.254"))})
    return cards


def danh_sach_card(cach_bat):
    cards = _card_npcap() if cach_bat == "npcap" else _card_raw()
    cards.sort(key=lambda c: (not c["co_ip"], c["loai"] not in ("Wi-Fi", "Dây mạng"), c["nhan"]))
    return cards


# ======================= Tach goi tin =======================
def tach_ipv4(b, ts):
    """Byte cua goi IPv4 (bat dau tu IP header) -> GoiTin. Dung cho raw socket."""
    if len(b) < 20 or (b[0] >> 4) != 4:
        return None
    ihl = (b[0] & 0x0F) * 4
    tong = struct.unpack("!H", b[2:4])[0]
    if tong == 0 or tong > len(b):          # Windows co the bao 0 voi goi lon (TSO)
        tong = len(b)
    proto = b[9]
    src, dst = socket.inet_ntoa(b[12:16]), socket.inet_ntoa(b[16:20])
    tai = max(tong - ihl, 0)
    l4 = b[ihl:]
    if proto == 6 and len(l4) >= 20:
        sport, dport = struct.unpack("!HH", l4[:4])
        hdr = (l4[12] >> 4) * 4 or 20
        flags = l4[13]
        win = struct.unpack("!H", l4[14:16])[0]
        return GoiTin(ts, src, dst, sport, dport, 6, hdr, max(tai - hdr, 0), flags, win)
    if proto == 17 and len(l4) >= 8:
        sport, dport = struct.unpack("!HH", l4[:4])
        return GoiTin(ts, src, dst, sport, dport, 17, 8, max(tai - 8, 0))
    if proto == 1 and len(l4) >= 2:
        return GoiTin(ts, src, dst, 0, 0, 1, 8, max(tai - 8, 0), icmp_type=l4[0], icmp_code=l4[1])
    return GoiTin(ts, src, dst, 0, 0, proto, 0, tai)


def tach_goi_scapy(pkt):
    """Goi tin scapy -> GoiTin (dung khi co Npcap)."""
    from scapy.layers.inet import ICMP, IP, TCP, UDP
    from scapy.layers.inet6 import IPv6
    ts = float(pkt.time)
    if IP in pkt:
        ip = pkt[IP]
        src, dst, proto = ip.src, ip.dst, int(ip.proto)
        tai = ip.len - ip.ihl * 4 if ip.len else len(ip.payload)
    elif IPv6 in pkt:
        ip = pkt[IPv6]
        src, dst, proto = ip.src, ip.dst, int(ip.nh)
        tai = ip.plen if ip.plen else len(ip.payload)
    else:
        return None
    if TCP in pkt:
        t = pkt[TCP]
        hdr = int(t.dataofs or 5) * 4
        return GoiTin(ts, src, dst, int(t.sport), int(t.dport), 6, hdr, max(tai - hdr, 0), int(t.flags), int(t.window))
    if UDP in pkt:
        u = pkt[UDP]
        return GoiTin(ts, src, dst, int(u.sport), int(u.dport), 17, 8, max(tai - 8, 0))
    if ICMP in pkt:
        c = pkt[ICMP]
        return GoiTin(ts, src, dst, 0, 0, 1, 8, max(tai - 8, 0), icmp_type=int(c.type), icmp_code=int(c.code))
    if proto == 58:
        pl = ip.payload
        return GoiTin(ts, src, dst, 0, 0, 58, 8, max(tai - 8, 0),
                      icmp_type=int(getattr(pl, "type", -1)), icmp_code=int(getattr(pl, "code", -1)))
    return GoiTin(ts, src, dst, 0, 0, proto, 0, max(tai, 0))


# ======================= Bo bat goi bang raw socket (Windows) =======================
class BatRaw:
    """Doc moi goi IPv4 di/den 1 dia chi IP cua may (che do SIO_RCVALL cua Windows)."""
    def __init__(self, ip, nhan_goi):
        self.ip, self.nhan_goi = ip, nhan_goi
        self.dang_chay = False
        self.loi = None
        self.s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
        self.s.bind((ip, 0))
        self.s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        self.s.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
        self.s.settimeout(1.0)
        self.t = threading.Thread(target=self._chay, daemon=True)

    def start(self):
        self.dang_chay = True
        self.t.start()

    def _chay(self):
        while self.dang_chay:
            try:
                b = self.s.recv(65535)
            except socket.timeout:
                continue
            except OSError as e:
                if self.dang_chay:
                    self.loi = str(e)
                break
            self.nhan_goi(tach_ipv4(b, time.time()))

    def stop(self):
        self.dang_chay = False
        try:
            self.s.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
        except Exception:
            pass
        try:
            self.s.close()
        except Exception:
            pass


# ======================= Dieu phoi giam sat =======================
class GiamSat:
    def __init__(self, pipeline, input_features, idle_timeout=15.0, chu_ky=2.0):
        assert list(input_features) == TEN_DAC_TRUNG, "Ten dac trung khong khop voi mo hinh"
        self.pipeline, self.features = pipeline, list(input_features)
        self.bang = BangLuong(idle_timeout=idle_timeout)
        self.chu_ky = chu_ky
        self.khoa = threading.Lock()
        self.ket_qua = deque(maxlen=TOI_DA_LUU)
        self.so_goi = 0
        self.so_goi_bo_qua = 0
        self.loi = None
        self.dang_chay = False
        self.t_bat_dau = None
        self.t_dung = None
        self.card = []
        self.cach_bat = None
        self._bo_bat = []
        self._luong_xu_ly = None

    def _nhan_goi(self, g):
        with self.khoa:
            if g is None:
                self.so_goi_bo_qua += 1
                return
            self.so_goi += 1
            self.bang.them(g)

    def _nhan_goi_scapy(self, pkt):
        try:
            g = tach_goi_scapy(pkt)
        except Exception:
            g = None
        self._nhan_goi(g)

    def bat_dau(self, card_ids, nhan_card):
        self.card = nhan_card
        self.loi, self.dang_chay, self.t_bat_dau, self.t_dung = None, True, time.time(), None
        try:
            if all(c.startswith("npcap:") for c in card_ids):
                from scapy.all import AsyncSniffer
                self.cach_bat = "npcap"
                ten = [c.split(":", 1)[1] for c in card_ids]
                sn = AsyncSniffer(iface=ten if len(ten) > 1 else ten[0], prn=self._nhan_goi_scapy,
                                  store=False, filter="ip or ip6")
                sn.start()
                self._bo_bat = [sn]
            else:
                self.cach_bat = "raw"
                self._bo_bat = [BatRaw(c.split(":", 1)[1], self._nhan_goi) for c in card_ids]
                for b in self._bo_bat:
                    b.start()
            time.sleep(0.5)
        except PermissionError:
            self.dang_chay = False
            self.loi = "Không có quyền đọc gói tin. Hãy chạy cmd bằng quyền Administrator (Run as administrator)."
            self._dung_bo_bat()
            return False
        except Exception as e:
            self.dang_chay = False
            self.loi = f"Không bắt được gói tin: {e}"
            self._dung_bo_bat()
            return False
        self._luong_xu_ly = threading.Thread(target=self._vong_lap, daemon=True)
        self._luong_xu_ly.start()
        return True

    def _dung_bo_bat(self):
        for b in self._bo_bat:
            try:
                b.stop()
            except Exception:
                pass
        self._bo_bat = []

    def dung(self):
        self._dung_bo_bat()
        self.dang_chay, self.t_dung = False, time.time()
        self._xu_ly(time.time(), tat_ca=True)

    def _vong_lap(self):
        while self.dang_chay:
            time.sleep(self.chu_ky)
            for b in self._bo_bat:
                if getattr(b, "loi", None):
                    self.loi = f"Bộ bắt gói tin báo lỗi: {b.loi}"
            try:
                self._xu_ly(time.time())
            except Exception as e:
                self.loi = f"Lỗi khi đánh giá luồng: {e}"

    def _xu_ly(self, bay_gio, tat_ca=False):
        with self.khoa:
            luong = self.bang.lay_luong_xong(bay_gio, tat_ca=tat_ca)
        if not luong:
            return
        df = pd.DataFrame([l.dac_trung() for l in luong], columns=self.features)
        kt = kiem_tra(df, self.features)          # Cach 1: dong co o trong/vo cuc -> khong du doan
        xs = pd.Series(float("nan"), index=df.index)
        ly_do = pd.Series("", index=df.index, dtype=object)
        if kt["ok"]:
            hl = kt["hop_le"]
            if hl.any():
                xs[hl] = self.pipeline.predict_proba(kt["X"][hl])[:, 1]
            ly_do = kt["ly_do"]
        else:
            ly_do[:] = "Dữ liệu luồng có ô trống hoặc giá trị vô cực"
        ban_ghi = []
        for i, l in enumerate(luong):
            r = l.thong_tin()
            r["Xac_suat_tan_cong"] = float(xs.iloc[i])
            r["Ly_do"] = ly_do.iloc[i]
            r.update(df.iloc[i].to_dict())
            ban_ghi.append(r)
        with self.khoa:
            self.ket_qua.extend(ban_ghi)

    def anh_chup(self):
        with self.khoa:
            return {"so_goi": self.so_goi, "bo_qua": self.so_goi_bo_qua, "dang_mo": len(self.bang.dang_mo),
                    "ket_qua": pd.DataFrame(list(self.ket_qua)), "loi": self.loi, "dang_chay": self.dang_chay,
                    "t_bat_dau": self.t_bat_dau, "t_dung": self.t_dung, "card": list(self.card),
                    "cach_bat": self.cach_bat}
