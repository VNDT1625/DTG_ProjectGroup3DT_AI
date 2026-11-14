"""A2 - Kiem thu tu dong cho buoc DU DOAN, dung MO HINH THAT (models/final_model.joblib).
Chay: pytest tests/test_prediction.py -v"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
from validation import KQ_BINH_THUONG, KQ_TAN_CONG, KQ_THIEU, danh_gia_voi_nhan, doc_csv, du_doan, kiem_tra  # noqa: E402

FEAT = json.loads((ROOT / "models" / "feature_cols.json").read_text(encoding="utf-8"))
MAU = ROOT / "data" / "samples"


@pytest.fixture(scope="module")
def mo_hinh():
    joblib = pytest.importorskip("joblib")
    pytest.importorskip("xgboost")
    import ids_pipeline  # noqa: F401  (can de nap mo hinh)
    return joblib.load(ROOT / "models" / "final_model.joblib")


@pytest.fixture(scope="module")
def mau_co_nhan():
    f = MAU / "demo_labeled.csv"
    if not f.exists():
        pytest.skip("Chua co file mau (chay src/s08_make_samples.py)")
    df, loi = doc_csv(str(f))
    assert loi is None
    return df


def du_doan_file(mh, df, nguong=None):
    kt = kiem_tra(df, mh["input_features"])
    assert kt["ok"], kt["loi"]
    return kt, du_doan(mh["pipeline"], kt["X"], kt["hop_le"], mh["threshold"] if nguong is None else nguong)


# ---------- 1. Mo hinh nap dung ----------
def test_mo_hinh_nap_dung(mo_hinh):
    assert mo_hinh["model_name"] == "XGBoost"
    assert abs(mo_hinh["threshold"] - 0.5703) < 1e-3
    assert mo_hinh["input_features"] == FEAT
    assert len(mo_hinh["selected_features"]) == 30


# ---------- 2. Dinh dang ket qua ----------
def test_dinh_dang_ket_qua(mo_hinh, mau_co_nhan):
    kt, kq = du_doan_file(mo_hinh, mau_co_nhan)
    assert list(kq.columns) == ["Xac_suat_tan_cong", "Ket_qua"]
    assert len(kq) == len(mau_co_nhan) and (kq.index == kt["X"].index).all()
    assert kq["Xac_suat_tan_cong"].between(0, 1).all()
    assert set(kq["Ket_qua"]) <= {KQ_TAN_CONG, KQ_BINH_THUONG}


def test_dong_loi_khong_duoc_du_doan(mo_hinh, mau_co_nhan):
    df = mau_co_nhan.head(50).copy()
    df.loc[[0, 7, 20], "Flow Bytes/s"] = np.inf
    df.loc[[3], "Protocol"] = np.nan
    kt, kq = du_doan_file(mo_hinh, df)
    loi = [0, 3, 7, 20]
    assert (kq.loc[loi, "Ket_qua"] == KQ_THIEU).all() and kq.loc[loi, "Xac_suat_tan_cong"].isna().all()
    con_lai = kq.drop(index=loi)
    assert con_lai["Xac_suat_tan_cong"].notna().all() and (con_lai["Ket_qua"] != KQ_THIEU).all()


def test_nguong_ap_dung_dung_ca_tai_bien(mo_hinh, mau_co_nhan):
    kt, kq = du_doan_file(mo_hinh, mau_co_nhan)
    xs = kq["Xac_suat_tan_cong"]
    nguong = float(xs.iloc[0])                      # dat nguong dung bang xac suat cua dong dau tien
    kq2 = du_doan(mo_hinh["pipeline"], kt["X"], kt["hop_le"], nguong)
    assert kq2["Ket_qua"].iloc[0] == KQ_TAN_CONG    # >= nguong la Tan cong
    assert ((xs >= nguong) == (kq2["Ket_qua"] == KQ_TAN_CONG)).all()


# ---------- 3. Chong ro ri: nhan khong anh huong du doan ----------
def test_ket_qua_giong_het_du_co_hay_khong_co_label(mo_hinh, mau_co_nhan):
    _, a = du_doan_file(mo_hinh, mau_co_nhan)
    _, b = du_doan_file(mo_hinh, mau_co_nhan.drop(columns=["Label"]))
    pd.testing.assert_frame_equal(a, b)


def test_doi_noi_dung_cot_label_khong_doi_du_doan(mo_hinh, mau_co_nhan):
    df = mau_co_nhan.copy()
    df["Label"] = "Benign"                          # gan sai toan bo nhan
    _, a = du_doan_file(mo_hinh, mau_co_nhan)
    _, b = du_doan_file(mo_hinh, df)
    pd.testing.assert_frame_equal(a, b)


def test_ung_dung_khong_hoc_lai_tu_file_nguoi_dung(mo_hinh, mau_co_nhan):
    """Du doan file A, roi du doan mot file B rat khac, roi du doan lai A: ket qua A phai y het."""
    _, truoc = du_doan_file(mo_hinh, mau_co_nhan)
    la = mau_co_nhan.drop(columns=["Label"]).copy()
    la[FEAT] = la[FEAT] * 1000 + 7                   # file B: gia tri lech han
    du_doan_file(mo_hinh, la)
    _, sau = du_doan_file(mo_hinh, mau_co_nhan)
    pd.testing.assert_frame_equal(truoc, sau)


def test_ket_qua_on_dinh_moi_lan_chay(mo_hinh, mau_co_nhan):
    _, a = du_doan_file(mo_hinh, mau_co_nhan)
    _, b = du_doan_file(mo_hinh, mau_co_nhan)
    pd.testing.assert_frame_equal(a, b)


def test_thu_tu_dong_khong_anh_huong(mo_hinh, mau_co_nhan):
    xao = mau_co_nhan.sample(frac=1, random_state=3)
    _, a = du_doan_file(mo_hinh, mau_co_nhan)
    _, b = du_doan_file(mo_hinh, xao)
    pd.testing.assert_frame_equal(a.loc[xao.index], b)


# ---------- 4. Chat luong tren file mau (trich tu tap test) ----------
def test_chat_luong_tren_file_mau(mo_hinh, mau_co_nhan):
    kt, kq = du_doan_file(mo_hinh, mau_co_nhan)
    dg = danh_gia_voi_nhan(kt["nhan"], kq["Ket_qua"])
    assert dg["so_dong"] == len(mau_co_nhan)
    assert dg["Recall"] >= 0.99, dg          # tren tap test: 99,98%
    assert dg["FPR"] <= 0.005, dg            # tren tap test: 0,044%
    assert dg["F1"] >= 0.99, dg


def test_danh_gia_voi_nhan_bo_dong_attempted_va_dong_loi():
    nhan = pd.Series(["Benign", "DDoS", "Attempted-relabel-as-Benign", "Benign", "DoS Hulk"])
    kq = pd.Series([KQ_BINH_THUONG, KQ_TAN_CONG, KQ_TAN_CONG, KQ_THIEU, KQ_BINH_THUONG])
    dg = danh_gia_voi_nhan(nhan, kq)
    assert dg["so_dong"] == 3 and (dg["TP"], dg["FP"], dg["FN"], dg["TN"]) == (1, 0, 1, 1)
    assert dg["FNR"] == 0.5 and dg["FPR"] == 0.0
