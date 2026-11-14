"""A4 - Kiem thu XUAT CSV: so dong, thu tu cot, gia tri goc khong doi, BOM/tieng Viet,
loc "chi tan cong", file ket qua cu tai len lai, va 2 cach ghi (pyarrow / pandas) cho cung noi dung.
Chay: pytest tests/test_export.py -v"""
import io
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
from export import BOM, COT_KQ, bang_xuat, csv_bytes, ten_file  # noqa: E402
from validation import KQ_BINH_THUONG, KQ_TAN_CONG, KQ_THIEU, doc_csv, kiem_tra  # noqa: E402

FEAT = json.loads((ROOT / "models" / "feature_cols.json").read_text(encoding="utf-8"))


@pytest.fixture
def du_lieu():
    """File nho gia lap: 6 dong, co cot Label, 1 o vo cuc, 1 dong loi."""
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.random((6, len(FEAT))) * 1000, columns=FEAT)
    df.loc[2, "Flow Bytes/s"] = np.inf
    df["Label"] = ["Benign", "DDoS", "Benign", "Portscan", "Benign", "DoS Hulk"]
    kq = pd.DataFrame({
        "Ket_qua": [KQ_BINH_THUONG, KQ_TAN_CONG, KQ_THIEU, KQ_TAN_CONG, KQ_BINH_THUONG, KQ_TAN_CONG],
        "Xac_suat_tan_cong": [0.0123456789, 0.99, np.nan, 0.8, 0.1, 0.5703],
        "Ly_do": ["", "", "Thiếu/lỗi ở: Flow Bytes/s", "", "", ""]})
    return df, kq


def doc_lai(b):
    assert b.startswith(BOM)
    return pd.read_csv(io.BytesIO(b), encoding="utf-8-sig")


def test_so_dong_va_thu_tu_cot(du_lieu):
    df, kq = du_lieu
    x = bang_xuat(df, kq)
    assert len(x) == len(df)
    assert list(x.columns) == COT_KQ + list(df.columns)          # 3 cot ket qua dung truoc, cot goc giu thu tu


def test_gia_tri_goc_khong_bi_sua(du_lieu):
    df, kq = du_lieu
    goc = df.copy()
    x = bang_xuat(df, kq)
    pd.testing.assert_frame_equal(x[list(df.columns)], goc.reset_index(drop=True))
    pd.testing.assert_frame_equal(df, goc)                        # khong sua df cua nguoi dung


def test_chi_xuat_tan_cong(du_lieu):
    df, kq = du_lieu
    x = bang_xuat(df, kq, chi_tan_cong=True)
    assert len(x) == 3 and (x["Ket_qua"] == KQ_TAN_CONG).all()
    assert list(x["Label"]) == ["DDoS", "Portscan", "DoS Hulk"]   # dung dong, dung thu tu


def test_file_ket_qua_cu_tai_len_lai(du_lieu):
    """Nguoi dung tai len chinh file da xuat: khong loi, khong trung cot."""
    df, kq = du_lieu
    cu = bang_xuat(df, kq)
    x = bang_xuat(cu, kq)
    assert list(x.columns) == COT_KQ + list(df.columns)


@pytest.mark.parametrize("cach", ["pandas", "pyarrow"])
def test_csv_doc_lai_dung_noi_dung(du_lieu, cach):
    if cach == "pyarrow":
        pytest.importorskip("pyarrow")
    df, kq = du_lieu
    x = bang_xuat(df, kq)
    b, da_dung = csv_bytes(x, cach)
    assert da_dung == cach
    y = doc_lai(b)
    assert list(y.columns) == list(x.columns) and len(y) == len(x)
    assert list(y["Ket_qua"]) == list(x["Ket_qua"])                     # tieng Viet giu nguyen
    assert y.loc[2, "Ly_do"] == "Thiếu/lỗi ở: Flow Bytes/s"
    assert np.isnan(y.loc[2, "Xac_suat_tan_cong"]) and np.isinf(y.loc[2, "Flow Bytes/s"])
    np.testing.assert_allclose(y[FEAT].to_numpy(float), x[FEAT].to_numpy(float), rtol=1e-12)
    assert y.loc[0, "Xac_suat_tan_cong"] == pytest.approx(0.012346)     # lam tron 6 chu so


def test_hai_cach_ghi_cho_cung_noi_dung(du_lieu):
    pytest.importorskip("pyarrow")
    df, kq = du_lieu
    x = bang_xuat(df, kq)
    a, b = doc_lai(csv_bytes(x, "pandas")[0]), doc_lai(csv_bytes(x, "pyarrow")[0])
    pd.testing.assert_frame_equal(a, b, check_exact=False, rtol=1e-12)


def test_file_xuat_tai_len_lai_duoc(du_lieu):
    """File da xuat phai tai len lai ung dung duoc (du cot, dong hop le van hop le)."""
    df, kq = du_lieu
    b, _ = csv_bytes(bang_xuat(df, kq))
    df2, loi = doc_csv(b)
    assert loi is None
    kt = kiem_tra(df2, FEAT)
    assert kt["ok"] and kt["thong_ke"]["so_dong_hop_le"] == 5


def test_ten_file():
    luc = datetime(2026, 11, 14, 6, 30, 5)
    assert ten_file("data/demo labeled.csv", luc=luc) == "results_demo labeled_20261114_063005.csv"
    assert ten_file("x.csv", True, "xlsx", luc) == "results_x_attacks_20261114_063005.xlsx"


# ======================= B1 - Excel =======================
from export import EXCEL_MAX, excel_bytes  # noqa: E402


def mo_excel(b):
    openpyxl = pytest.importorskip("openpyxl")
    return openpyxl.load_workbook(io.BytesIO(b))


def test_excel_cau_truc(du_lieu):
    df, kq = du_lieu
    x = bang_xuat(df, kq)
    wb = mo_excel(excel_bytes(x, [("Mô hình", "XGBoost"), ("Ngưỡng cảnh báo", 0.5703)]))
    assert wb.sheetnames == ["Results", "Summary"]
    ws = wb["Results"]
    assert ws.freeze_panes == "B2"                                       # dong tieu de co dinh
    assert ws.auto_filter.ref == f"A1:{ws.cell(1, x.shape[1]).column_letter}{len(x) + 1}"
    assert [c.value for c in ws[1]] == list(x.columns)
    assert ws.max_row == len(x) + 1
    assert ws.column_dimensions["A"].width == 18
    assert len(list(ws.conditional_formatting)) >= 1                   # to mau cot Ket_qua
    assert list(wb["Summary"].values)[1] == ("Mô hình", "XGBoost")


def test_excel_gia_tri_la_so_that(du_lieu):
    """Diem chinh cua B1: so luu duoi dang SO, khong phai chu -> Excel Viet Nam hien dung."""
    df, kq = du_lieu
    x = bang_xuat(df, kq)
    ws = mo_excel(excel_bytes(x, []))["Results"]
    assert isinstance(ws["B2"].value, float) and ws["B2"].value == pytest.approx(0.012346)
    assert ws["A2"].value == KQ_BINH_THUONG and ws["A3"].value == KQ_TAN_CONG   # tieng Viet giu nguyen
    cot_fb = list(x.columns).index("Flow Bytes/s") + 1
    assert ws["B4"].value is None                                        # dong loi: xac suat trong
    assert ws.cell(4, cot_fb).value == "inf"                             # vo cuc ghi thanh chu
    assert ws.cell(2, cot_fb).value == pytest.approx(x.loc[0, "Flow Bytes/s"])


def test_excel_chi_tan_cong(du_lieu):
    df, kq = du_lieu
    ws = mo_excel(excel_bytes(bang_xuat(df, kq, chi_tan_cong=True), []))["Results"]
    assert ws.max_row == 4 and all(ws.cell(i, 1).value == KQ_TAN_CONG for i in range(2, 5))


def test_excel_qua_gioi_han_bao_loi_ro_rang():
    x = pd.DataFrame({"Ket_qua": [KQ_BINH_THUONG] * (EXCEL_MAX + 1)})
    with pytest.raises(ValueError, match="CSV"):
        excel_bytes(x, [])
