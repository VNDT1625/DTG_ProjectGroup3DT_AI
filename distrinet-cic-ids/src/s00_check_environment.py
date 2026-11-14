"""Buoc 0: kiem tra moi truong va du lieu tho. Ghi ket qua vao logs/s00_environment.txt"""
import sys, platform, os, importlib, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
LOG = ROOT / "logs" / "s00_environment.txt"
LOG.parent.mkdir(exist_ok=True)
lines = []
def out(s=""):
    print(s); lines.append(str(s))

out(f"Python: {sys.version}")
out(f"He dieu hanh: {platform.platform()}")
out(f"So nhan CPU: {os.cpu_count()}")
try:
    import ctypes
    class M(ctypes.Structure):
        _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                    ("avail", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong),
                    ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong)]
    m = M(); m.l = ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    out(f"RAM: {m.total/2**30:.1f} GB (con trong {m.avail/2**30:.1f} GB)")
except Exception as e:
    out(f"RAM: khong doc duoc ({e})")

out("\n[THU VIEN]")
ok = True
for name in ["pandas", "numpy", "pyarrow", "sklearn", "imblearn", "lightgbm", "streamlit", "openpyxl", "matplotlib", "joblib", "pytest"]:
    try:
        mod = importlib.import_module(name)
        out(f"  OK   {name} {getattr(mod, '__version__', '')}")
    except Exception as e:
        ok = False
        out(f"  THIEU {name}: {e}")

out("\n[DU LIEU TRONG data/raw]")
files = sorted(RAW.rglob("*.parquet"))
if not files:
    out("  KHONG CO FILE .parquet NAO")
hashes = {}
for f in files:
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    hashes[str(f.relative_to(ROOT))] = h.hexdigest()
    out(f"  {f.relative_to(RAW)}  {f.stat().st_size/2**20:.1f} MB  sha256={h.hexdigest()[:16]}...")
if hashes:
    (ROOT / "data" / "raw_hashes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    out("  Da luu dau van tay (hash) vao data/raw_hashes.json")

out("\nKET LUAN: " + ("MOI TRUONG OK" if ok and files else "CON THIEU - xem ben tren"))
LOG.write_text("\n".join(lines), encoding="utf-8")
