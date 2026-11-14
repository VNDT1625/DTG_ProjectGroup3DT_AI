"""A3 - Kiem thu cho phan GIAO DIEN KET QUA (dashboard).
Kiem tra cac ham ma giao dien dung, va 3 truong hop: co tan cong, khong co tan cong, toan dong loi.
Chay: pytest tests/test_dashboard.py -v"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
from validation import (KQ_BINH_THUONG, KQ_TAN_CONG, KQ_THIEU, ap_nguong, bang_theo_nhan,  # noqa: E402
                        danh_gia_voi_nhan, doc_csv, du_doan, kiem_tra, phan_tram, tinh_xac_suat)

FEAT = json.loads((ROOT / "models" / "feature_cols.json").read_text(encoding="utf-8"))
MAU = ROOT / "data" / "samples"


@pytest.fixture(scope="module")
def mo_hinh():
    joblib = pytest.importorskip("joblib")
    pytest.importorskip("xgboost")
    import ids_pipeline  # noqa: F401
    return joblib.load(ROOT / "models" / "final_model.joblib")


def doc(ten):
    f = MAU / ten
    if not f.exists():
        pytest.skip(f"Chua co {ten} (chay src/s08_make_samples.py va src/s10_make_dashboard_cases.py)")
    df, loi = doc_csv(str(f))
    assert loi is None
    return df


# ---------- Cac ham nho ----------
def test_phan_tram():
    assert phan_tram(0.5) == "50.00%"
    assert phan_tram(0.00044, 3) == "0.044%"
    assert phan_tram(float("nan")) == "—" and phan_tram(None) == "—"


def test_ap_nguong():
    xs = pd.Series([0.1, 0.5, 0.9, np.nan])
    kq = ap_nguong(xs, 0.5)
    assert list(kq["Ket_qua"]) == [KQ_BINH_THUONG, KQ_TAN_CONG, KQ_TAN_CONG, KQ_THIEU]
    assert list(ap_nguong(xs, 0.95)["Ket_qua"]) == [KQ_BINH_THUONG] * 3 + [KQ_THIEU]


def test_bang_theo_nhan():
    nhan = pd.Series(["Benign", "Benign", "Benign", "DDoS", "DDoS", "Botnet", "Attempted-x", "Benign"])
    kq = pd.Series([KQ_BINH_THUONG, KQ_BINH_THUONG, KQ_TAN_CONG, KQ_TAN_CONG, KQ_BINH_THUONG,
                    KQ_THIEU, KQ_TAN_CONG, KQ_THIEU])
    b = bang_theo_nhan(nhan, kq).set_index("Nhan")
    assert list(b.index) == ["Benign", "DDoS", "Botnet", "Attempted-x"]      # Benign dau, Attempted cuoi
    assert b.loc["Benign", "So_dong"] == 4 and b.loc["Benign", "Khong_du"] == 1
    assert b.loc["Benign", "Ti_le_dung"] == pytest.approx(2 / 3)               # khong tinh dong thieu
    assert b.loc["DDoS", "Ti_le_dung"] == pytest.approx(0.5)
    assert np.isnan(b.loc["Botnet", "Ti_le_dung"])                             # chi co dong thieu
    assert np.isnan(b.loc["Attempted-x", "Ti_le_dung"]) and b.loc["Attempted-x", "Loai"].startswith("Bỏ qua")
    assert b["So_dong"].sum() == len(nhan)


def test_tinh_mot_lan_doi_nguong_giong_tinh_lai(mo_hinh):
    """Giao dien chi tinh xac suat 1 lan roi doi nguong: ket qua phai giong het tinh lai tu dau."""
    kt = kiem_tra(doc("demo_labeled.csv"), FEAT)
    xs = tinh_xac_suat(mo_hinh["pipeline"], kt["X"], kt["hop_le"])
    for ng in (0.2, mo_hinh["threshold"], 0.9):
        pd.testing.assert_frame_equal(ap_nguong(xs, ng), du_doan(mo_hinh["pipeline"], kt["X"], kt["hop_le"], ng))


# ---------- 3 truong hop ----------
def test_truong_hop_co_tan_cong(mo_hinh):
    df = doc("demo_labeled.csv")
    kt = kiem_tra(df, FEAT)
    kq = ap_nguong(tinh_xac_suat(mo_hinh["pipeline"], kt["X"], kt["hop_le"]), mo_hinh["threshold"])
    assert (kq["Ket_qua"] == KQ_TAN_CONG).sum() > 1000
    b = bang_theo_nhan(kt["nhan"], kq["Ket_qua"])
    assert len(b) == df["Label"].nunique() and b["So_dong"].sum() == len(df)
    assert b.loc[b["Nhan"] == "Benign", "Ti_le_dung"].item() >= 0.995


def test_truong_hop_khong_co_tan_cong(mo_hinh):
    df = doc("case_no_attack.csv")
    kt = kiem_tra(df, FEAT)
    assert kt["ok"]
    kq = ap_nguong(tinh_xac_suat(mo_hinh["pipeline"], kt["X"], kt["hop_le"]), mo_hinh["threshold"])
    assert (kq["Ket_qua"] == KQ_TAN_CONG).mean() <= 0.005        # gan nhu khong bao nham
    dg = danh_gia_voi_nhan(kt["nhan"], kq["Ket_qua"])
    assert np.isnan(dg["Recall"]) and np.isnan(dg["FNR"])          # giao dien hien "—"
    assert phan_tram(dg["Recall"]) == "—"


def test_truong_hop_toan_dong_loi():
    df = doc("case_all_invalid.csv")
    kt = kiem_tra(df, FEAT)
    assert not kt["ok"]
    assert any("Không còn dòng nào đủ dữ liệu" in l for l in kt["loi"])
    assert kt["thong_ke"]["so_dong_thieu"] == len(df)
    assert any("Flow Bytes/s" in c for c in kt["canh_bao"])       # chi ro cot bi loi
