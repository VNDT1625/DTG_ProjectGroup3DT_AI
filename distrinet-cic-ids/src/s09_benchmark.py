"""A2 - DO HIEU NANG cua ung dung voi file lon: 100 nghin, 500 nghin, 1 trieu dong.
Tao file CSV lon bang cach lay mau co lap lai tu data/samples/demo_unlabeled.csv, them 1% dong loi (vo cuc),
roi do thoi gian va bo nho dinh cua tung buoc: doc CSV -> kiem tra -> du doan -> xuat CSV.
Xuat CSV duoc do KHONG bat do bo nho (cong cu do bo nho lam cham viec ghi CSV ~5 lan),
voi 2 cach ghi: pyarrow (ung dung dung mac dinh) va pandas (cach cu, de so sanh).
Ket qua: reports/s09_benchmark.csv, logs/s09_benchmark.txt"""
import io
import sys
import time
import tracemalloc
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
import ids_pipeline  # noqa: F401,E402
from export import bang_xuat, csv_bytes  # noqa: E402
from validation import doc_csv, du_doan, kiem_tra  # noqa: E402

KICH_THUOC = [100_000, 500_000, 1_000_000]
lines = []
def out(s=""):
    print(s, flush=True); lines.append(str(s))


def do(ham):
    """Chay ham, tra ve (ket qua, so giay, bo nho dinh MB)."""
    tracemalloc.start()
    t0 = time.perf_counter()
    kq = ham()
    giay = time.perf_counter() - t0
    _, dinh = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return kq, giay, dinh / 2**20


mh = joblib.load(ROOT / "models" / "final_model.joblib")
goc = pd.read_csv(ROOT / "data" / "samples" / "demo_unlabeled.csv")
out(f"Mo hinh: {mh['model_name']} | file goc: {len(goc):,} dong x {goc.shape[1]} cot")
rng = np.random.default_rng(42)
rows = []
for n in KICH_THUOC:
    df = goc.sample(n=n, replace=True, random_state=42).reset_index(drop=True)
    loi = rng.choice(n, size=n // 100, replace=False)
    df.loc[loi, "Flow Bytes/s"] = np.inf
    raw = df.to_csv(index=False).encode("utf-8")
    del df
    out(f"\n--- {n:,} dong | file CSV {len(raw) / 2**20:,.0f} MB ---")
    (doc, _), t_doc, m_doc = do(lambda: doc_csv(raw))
    kt, t_kt, m_kt = do(lambda: kiem_tra(doc, mh["input_features"]))
    kq, t_dd, m_dd = do(lambda: du_doan(mh["pipeline"], kt["X"], kt["hop_le"], mh["threshold"]))
    def thoi_gian(ham):
        t0 = time.perf_counter(); kq_ = ham(); return kq_, time.perf_counter() - t0
    bx, t_bx = thoi_gian(lambda: bang_xuat(doc, kq))
    (b_pa, cach), t_pa = thoi_gian(lambda: csv_bytes(bx, "tu_dong"))
    (b_pd, _), t_pd = thoi_gian(lambda: csv_bytes(bx, "pandas"))
    assert len(kq) == n and (kq["Ket_qua"] == "Không đủ dữ liệu").sum() == n // 100
    t_x = t_bx + t_pa
    tong = t_doc + t_kt + t_dd + t_x
    out(f"  Doc CSV    {t_doc:7.1f} s   bo nho dinh {m_doc:7,.0f} MB")
    out(f"  Kiem tra   {t_kt:7.1f} s   bo nho dinh {m_kt:7,.0f} MB")
    out(f"  Du doan    {t_dd:7.1f} s   bo nho dinh {m_dd:7,.0f} MB")
    out(f"  Xuat CSV   {t_x:7.1f} s   (cach {cach}; ghep bang {t_bx:.1f} s)")
    out(f"  Xuat CSV bang pandas (cach cu, de so sanh): {t_bx + t_pd:.1f} s")
    out(f"  TONG       {tong:7.1f} s   | {n / tong:,.0f} dong/giay")
    rows.append({"So_dong": n, "Dung_luong_MB": round(len(raw) / 2**20), "Doc_CSV_s": round(t_doc, 2),
                 "Kiem_tra_s": round(t_kt, 2), "Du_doan_s": round(t_dd, 2), "Xuat_CSV_s": round(t_x, 2),
                 "Cach_xuat": cach, "Xuat_CSV_pandas_s": round(t_bx + t_pd, 2),
                 "Tong_s": round(tong, 2), "Dong_moi_giay": round(n / tong),
                 "Bo_nho_dinh_lon_nhat_MB": round(max(m_doc, m_kt, m_dd))})
    del raw, doc, kt, kq, bx, b_pa, b_pd

pd.DataFrame(rows).to_csv(ROOT / "reports" / "s09_benchmark.csv", index=False, encoding="utf-8-sig")
out("\nDa luu: reports/s09_benchmark.csv")
(ROOT / "logs" / "s09_benchmark.txt").write_text("\n".join(lines), encoding="utf-8")
