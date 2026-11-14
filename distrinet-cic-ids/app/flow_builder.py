"""GOM GOI TIN THANH LUONG MANG (flow) va TINH 82 DAC TRUNG theo quy uoc cua CIC-IDS2017 (ban Distrinet).
Doc lap voi viec bat goi tin => kiem thu duoc bang goi tin gia lap.

Quy uoc (doi chieu voi thong ke du lieu Distrinet):
- Luong 2 chieu; chieu "di" (Fwd) la chieu cua goi tin DAU TIEN.
- Thoi gian tinh bang micro-giay. Do lon goi = so byte DU LIEU (payload) cua tang giao van.
- Header Length = tong do dai header TCP/UDP. Fwd Seg Size Min = header TCP/UDP nho nhat chieu di.
- Init Win Bytes = cua so TCP cua goi dau tien moi chieu (0 neu khong co).
- ICMP Code/Type = -1 neu khong phai ICMP. Do lech chuan dung cong thuc mau (n-1).
- Luong ket thuc khi: co co RST; hai chieu deu da gui FIN; khong co goi moi trong `idle_timeout` giay;
  hoac ton tai qua `max_age` giay (CICFlowMeter dung 120 giay)."""
import math
from dataclasses import dataclass, field

FIN, SYN, RST, PSH, ACK, URG, ECE, CWR = 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80
ACTIVITY_TIMEOUT_US = 5_000_000  # 5 giay, nhu CICFlowMeter

TEN_DAC_TRUNG = [
    "Protocol", "Flow Duration", "Total Fwd Packets", "Total Backward Packets", "Fwd Packets Length Total",
    "Bwd Packets Length Total", "Fwd Packet Length Max", "Fwd Packet Length Min", "Fwd Packet Length Mean",
    "Fwd Packet Length Std", "Bwd Packet Length Max", "Bwd Packet Length Min", "Bwd Packet Length Mean",
    "Bwd Packet Length Std", "Flow Bytes/s", "Flow Packets/s", "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max",
    "Flow IAT Min", "Fwd IAT Total", "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max", "Fwd IAT Min", "Bwd IAT Total",
    "Bwd IAT Mean", "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min", "Fwd PSH Flags", "Bwd PSH Flags", "Fwd URG Flags",
    "Bwd URG Flags", "Fwd RST Flags", "Bwd RST Flags", "Fwd Header Length", "Bwd Header Length", "Fwd Packets/s",
    "Bwd Packets/s", "Packet Length Min", "Packet Length Max", "Packet Length Mean", "Packet Length Std",
    "Packet Length Variance", "FIN Flag Count", "SYN Flag Count", "RST Flag Count", "PSH Flag Count",
    "ACK Flag Count", "URG Flag Count", "CWR Flag Count", "ECE Flag Count", "Down/Up Ratio", "Avg Packet Size",
    "Avg Fwd Segment Size", "Avg Bwd Segment Size", "Fwd Avg Bytes/Bulk", "Fwd Avg Packets/Bulk",
    "Fwd Avg Bulk Rate", "Bwd Avg Bytes/Bulk", "Bwd Avg Packets/Bulk", "Bwd Avg Bulk Rate", "Subflow Fwd Packets",
    "Subflow Fwd Bytes", "Subflow Bwd Packets", "Subflow Bwd Bytes", "Init Fwd Win Bytes", "Init Bwd Win Bytes",
    "Fwd Act Data Packets", "Fwd Seg Size Min", "Active Mean", "Active Std", "Active Max", "Active Min",
    "Idle Mean", "Idle Std", "Idle Max", "Idle Min", "ICMP Code", "ICMP Type", "Total TCP Flow Time"]


@dataclass
class GoiTin:
    """Thong tin toi thieu cua 1 goi tin (tach ra tu goi that o module bat goi)."""
    ts: float          # giay (epoch)
    src: str
    dst: str
    sport: int
    dport: int
    proto: int         # 6=TCP, 17=UDP, 1=ICMP, 58=ICMPv6...
    hdr: int           # do dai header TCP/UDP (byte)
    payload: int       # so byte du lieu tang giao van
    flags: int = 0     # co TCP
    win: int = 0       # cua so TCP
    icmp_type: int = -1
    icmp_code: int = -1


def _tk(v):
    """(mean, std mau, max, min) cua danh sach; rong -> 0."""
    n = len(v)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    m = sum(v) / n
    s = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1)) if n > 1 else 0.0
    return m, s, float(max(v)), float(min(v))


def _iat(ts):
    return [(b - a) * 1e6 for a, b in zip(ts, ts[1:])]


@dataclass
class Luong:
    khoa: tuple
    src: str
    dst: str
    sport: int
    dport: int
    proto: int
    t_dau: float
    t_cuoi: float = 0.0
    f_len: list = field(default_factory=list)
    b_len: list = field(default_factory=list)
    f_ts: list = field(default_factory=list)
    b_ts: list = field(default_factory=list)
    all_ts: list = field(default_factory=list)
    f_hdr: list = field(default_factory=list)
    b_hdr: list = field(default_factory=list)
    co: dict = field(default_factory=lambda: {k: 0 for k in
                                              ("FIN", "SYN", "RST", "PSH", "ACK", "URG", "ECE", "CWR",
                                               "fPSH", "bPSH", "fURG", "bURG", "fRST", "bRST")})
    fin_f: bool = False
    fin_b: bool = False
    win_f: int = 0
    win_b: int = 0
    icmp_type: int = -1
    icmp_code: int = -1
    ket_thuc: bool = False

    def them(self, g: GoiTin):
        di = (g.src, g.sport) == (self.src, self.sport)
        self.t_cuoi = g.ts
        self.all_ts.append(g.ts)
        if di:
            if not self.f_len and self.proto == 6:
                self.win_f = g.win
            self.f_len.append(g.payload); self.f_ts.append(g.ts); self.f_hdr.append(g.hdr)
        else:
            if not self.b_len and self.proto == 6:
                self.win_b = g.win
            self.b_len.append(g.payload); self.b_ts.append(g.ts); self.b_hdr.append(g.hdr)
        if g.proto == 6:
            for ten, bit in (("FIN", FIN), ("SYN", SYN), ("RST", RST), ("PSH", PSH), ("ACK", ACK),
                             ("URG", URG), ("ECE", ECE), ("CWR", CWR)):
                if g.flags & bit:
                    self.co[ten] += 1
            p = "f" if di else "b"
            for ten, bit in (("PSH", PSH), ("URG", URG), ("RST", RST)):
                if g.flags & bit:
                    self.co[p + ten] += 1
            if g.flags & FIN:
                if di:
                    self.fin_f = True
                else:
                    self.fin_b = True
            if g.flags & RST or (self.fin_f and self.fin_b):
                self.ket_thuc = True
        if g.icmp_type >= 0 and self.icmp_type < 0:
            self.icmp_type, self.icmp_code = g.icmp_type, g.icmp_code

    def dac_trung(self):
        dur = max((self.t_cuoi - self.t_dau) * 1e6, 1.0)   # micro-giay, toi thieu 1 (nhu du lieu goc)
        dur_s = dur / 1e6
        nf, nb = len(self.f_len), len(self.b_len)
        tat_ca = self.f_len + self.b_len
        fm, fs, fmx, fmn = _tk(self.f_len)
        bm, bs, bmx, bmn = _tk(self.b_len)
        am, as_, amx, amn = _tk(tat_ca)
        flow_iat, f_iat, b_iat = _iat(self.all_ts), _iat(self.f_ts), _iat(self.b_ts)
        fi = _tk(flow_iat); ffi = _tk(f_iat); bbi = _tk(b_iat)
        # Active / Idle (nguong 5 giay)
        active, idle = [], []
        bat_dau = truoc = self.all_ts[0] * 1e6
        for t in self.all_ts[1:]:
            t *= 1e6
            if t - truoc > ACTIVITY_TIMEOUT_US:
                if truoc - bat_dau > 0:
                    active.append(truoc - bat_dau)
                idle.append(t - truoc)
                bat_dau = t
            truoc = t
        ac, idl = _tk(active), _tk(idle)
        tong_byte = sum(tat_ca)
        d = {
            "Protocol": self.proto, "Flow Duration": dur, "Total Fwd Packets": nf, "Total Backward Packets": nb,
            "Fwd Packets Length Total": sum(self.f_len), "Bwd Packets Length Total": sum(self.b_len),
            "Fwd Packet Length Max": fmx, "Fwd Packet Length Min": fmn, "Fwd Packet Length Mean": fm,
            "Fwd Packet Length Std": fs, "Bwd Packet Length Max": bmx, "Bwd Packet Length Min": bmn,
            "Bwd Packet Length Mean": bm, "Bwd Packet Length Std": bs,
            "Flow Bytes/s": tong_byte / dur_s, "Flow Packets/s": (nf + nb) / dur_s,
            "Flow IAT Mean": fi[0], "Flow IAT Std": fi[1], "Flow IAT Max": fi[2], "Flow IAT Min": fi[3],
            "Fwd IAT Total": sum(f_iat), "Fwd IAT Mean": ffi[0], "Fwd IAT Std": ffi[1], "Fwd IAT Max": ffi[2],
            "Fwd IAT Min": ffi[3], "Bwd IAT Total": sum(b_iat), "Bwd IAT Mean": bbi[0], "Bwd IAT Std": bbi[1],
            "Bwd IAT Max": bbi[2], "Bwd IAT Min": bbi[3],
            "Fwd PSH Flags": self.co["fPSH"], "Bwd PSH Flags": self.co["bPSH"], "Fwd URG Flags": self.co["fURG"],
            "Bwd URG Flags": self.co["bURG"], "Fwd RST Flags": self.co["fRST"], "Bwd RST Flags": self.co["bRST"],
            "Fwd Header Length": sum(self.f_hdr), "Bwd Header Length": sum(self.b_hdr),
            "Fwd Packets/s": nf / dur_s, "Bwd Packets/s": nb / dur_s,
            "Packet Length Min": amn, "Packet Length Max": amx, "Packet Length Mean": am,
            "Packet Length Std": as_, "Packet Length Variance": as_ ** 2,
            "FIN Flag Count": self.co["FIN"], "SYN Flag Count": self.co["SYN"], "RST Flag Count": self.co["RST"],
            "PSH Flag Count": self.co["PSH"], "ACK Flag Count": self.co["ACK"], "URG Flag Count": self.co["URG"],
            "CWR Flag Count": self.co["CWR"], "ECE Flag Count": self.co["ECE"],
            "Down/Up Ratio": nb / nf if nf else 0.0, "Avg Packet Size": am,
            "Avg Fwd Segment Size": fm, "Avg Bwd Segment Size": bm,
            # Cac dac trung "bulk" gan nhu luon = 0 trong du lieu va KHONG nam trong 30 dac trung mo hinh dung
            "Fwd Avg Bytes/Bulk": 0, "Fwd Avg Packets/Bulk": 0, "Fwd Avg Bulk Rate": 0,
            "Bwd Avg Bytes/Bulk": 0, "Bwd Avg Packets/Bulk": 0, "Bwd Avg Bulk Rate": 0,
            # Subflow: xap xi (khong nam trong 30 dac trung mo hinh dung)
            "Subflow Fwd Packets": 0, "Subflow Fwd Bytes": int(fm // 2) if nf else 0,
            "Subflow Bwd Packets": 0, "Subflow Bwd Bytes": int(bm // 2) if nb else 0,
            "Init Fwd Win Bytes": self.win_f, "Init Bwd Win Bytes": self.win_b,
            "Fwd Act Data Packets": sum(1 for x in self.f_len if x > 0),
            "Fwd Seg Size Min": min(self.f_hdr) if self.f_hdr else 0,
            "Active Mean": ac[0], "Active Std": ac[1], "Active Max": ac[2], "Active Min": ac[3],
            "Idle Mean": idl[0], "Idle Std": idl[1], "Idle Max": idl[2], "Idle Min": idl[3],
            "ICMP Code": self.icmp_code, "ICMP Type": self.icmp_type,
            "Total TCP Flow Time": dur if self.proto == 6 else 0,
        }
        return d

    def thong_tin(self):
        return {"Bat_dau": self.t_dau, "Ket_thuc": self.t_cuoi, "Nguon": f"{self.src}:{self.sport}",
                "Dich": f"{self.dst}:{self.dport}",
                "Giao_thuc": {6: "TCP", 17: "UDP", 1: "ICMP", 58: "ICMPv6"}.get(self.proto, str(self.proto)),
                "So_goi": len(self.f_len) + len(self.b_len)}


class BangLuong:
    """Bang cac luong dang mo. Them goi -> lay ra cac luong da ket thuc."""
    def __init__(self, idle_timeout=15.0, max_age=120.0):
        self.idle_timeout, self.max_age = idle_timeout, max_age
        self.dang_mo, self.xong = {}, []

    @staticmethod
    def _khoa(g):
        a, b = (g.src, g.sport), (g.dst, g.dport)
        return (g.proto,) + (a + b if a <= b else b + a)

    def them(self, g: GoiTin):
        k = self._khoa(g)
        l = self.dang_mo.get(k)
        if l is not None and g.ts - l.t_cuoi > self.idle_timeout:   # luong cu da "nguoi"
            self.xong.append(self.dang_mo.pop(k)); l = None
        if l is None:
            l = Luong(k, g.src, g.dst, g.sport, g.dport, g.proto, t_dau=g.ts)
            self.dang_mo[k] = l
        l.them(g)
        if l.ket_thuc or g.ts - l.t_dau >= self.max_age:
            self.xong.append(self.dang_mo.pop(k))

    def lay_luong_xong(self, bay_gio, tat_ca=False):
        """Tra ve cac luong da ket thuc (va dong cac luong qua han). tat_ca=True: dong het (khi dung)."""
        for k in list(self.dang_mo):
            l = self.dang_mo[k]
            if tat_ca or bay_gio - l.t_cuoi > self.idle_timeout or bay_gio - l.t_dau >= self.max_age:
                self.xong.append(self.dang_mo.pop(k))
        out, self.xong = self.xong, []
        return out
