"""A1 - Kiem thu tu dong cho buoc NHAP CSV va KIEM TRA DU LIEU (app/validation.py).
Chay: pytest tests/test_validation.py -v"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from validation import KQ_THIEU, doc_csv, kiem_tra  # noqa: E402

FEAT = json.loads((ROOT / "models" / "feature_cols.json").read_text(encoding="utf-8"))


# ---------- Du lieu mau ----------
def bang_hop_le(n=20, nhan=True, seed=0):
    """Bang du 82 cot, toan so duong, khong loi."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.integers(1, 1000, size=(n, len(FEAT))).astype(float), columns=FEAT)
    df["Protocol"] = 6
    if nhan:
        df["Label"] = ["Benign"] * (n - 5) + ["DDoS"] * 5
    return df


def sang_csv(df, **kw):
    return df.to_csv(index=False, **kw).encode("utf-8")


def doc_va_kiem_tra(raw):
    df, loi = doc_csv(raw)
    assert loi is None, loi
    return kiem_tra(df, FEAT)


# ---------- 1. Doc file ----------
def test_file_hop_le():
    kq = doc_va_kiem_tra(sang_csv(bang_hop_le()))
    assert kq["ok"] and not kq["loi"] and not kq["canh_bao"]
    assert kq["thong_ke"]["so_dong_hop_le"] == 20


@pytest.mark.parametrize("raw", [b"", b"   \n\n  "])
def test_file_rong(raw):
    df, loi = doc_csv(raw)
    assert df is None and "rỗng" in loi


def test_chi_co_dong_tieu_de():
    df, loi = doc_csv((",".join(FEAT) + "\n").encode())
    assert df is None and "chỉ có dòng tiêu đề" in loi


def test_file_nhi_phan_khong_phai_csv():
    df, loi = doc_csv(b"PK\x03\x04\x00\x00" + bytes(range(256)) * 4)
    assert df is None and "không phải dạng văn bản" in loi


def test_vuot_gioi_han_dung_luong():
    df, loi = doc_csv(sang_csv(bang_hop_le()), gioi_han_mb=0)
    assert df is None and "quá lớn" in loi


@pytest.mark.parametrize("dau,ten", [(";", "chấm phẩy"), ("\t", "Tab"), ("|", "gạch đứng")])
def test_tu_nhan_dang_dau_phan_cach(dau, ten):
    kq = doc_va_kiem_tra(sang_csv(bang_hop_le(), sep=dau))
    assert kq["ok"]
    assert any(ten in w for w in kq["canh_bao"])


def test_file_bang_ma_latin1():
    df = bang_hop_le()
    df["Label"] = "Bénign"
    df, loi = doc_csv(df.to_csv(index=False).encode("latin-1"))
    assert loi is None and len(df) == 20


# ---------- 2. Cot ----------
def test_thieu_cot_bao_ro_ten_cot():
    kq = doc_va_kiem_tra(sang_csv(bang_hop_le().drop(columns=["Flow Duration", "Protocol"])))
    assert not kq["ok"]
    assert "Thiếu 2/82" in kq["loi"][0] and "Flow Duration" in kq["loi"][0] and "Protocol" in kq["loi"][0]


def test_cot_thua_bi_bo_qua():
    df = bang_hop_le()
    df["Src IP"] = "10.0.0.1"
    kq = doc_va_kiem_tra(sang_csv(df))
    assert kq["ok"] and any("Bỏ qua 1 cột" in w and "Src IP" in w for w in kq["canh_bao"])
    assert "Src IP" not in kq["X"].columns


def test_ten_cot_viet_khac_kieu_van_nhan_dung():
    df = bang_hop_le()
    df.columns = ["  " + c.lower().replace(" ", "_") + " " for c in df.columns]
    kq = doc_va_kiem_tra(sang_csv(df))
    assert kq["ok"] and list(kq["X"].columns) == FEAT


def test_cot_lap_ten():
    df = bang_hop_le()
    df.insert(1, "flow_duration", 1.0)          # trung voi "Flow Duration" khi so khop
    kq = doc_va_kiem_tra(sang_csv(df))
    assert kq["ok"] and any("lặp tên" in w for w in kq["canh_bao"])


# ---------- 3. Gia tri ----------
def test_o_chua_chu():
    df = bang_hop_le()
    df = df.astype({"Flow Duration": object})
    df.loc[0, "Flow Duration"] = "abc"
    kq = doc_va_kiem_tra(sang_csv(df))
    assert kq["ok"] and not kq["hop_le"][0] and kq["hop_le"][1:].all()
    assert kq["thong_ke"]["loi_theo_cot"]["Flow Duration"]["khong_phai_so"] == 1
    assert "Flow Duration" in kq["ly_do"][0]


def test_o_vo_cuc():
    df = bang_hop_le()
    df.loc[2, "Flow Bytes/s"] = np.inf
    df.loc[3, "Flow Bytes/s"] = -np.inf
    kq = doc_va_kiem_tra(sang_csv(df))
    assert kq["thong_ke"]["loi_theo_cot"]["Flow Bytes/s"]["vo_cuc"] == 2
    assert (~kq["hop_le"]).sum() == 2


def test_o_trong():
    df = bang_hop_le()
    df.loc[4, "Protocol"] = np.nan
    kq = doc_va_kiem_tra(sang_csv(df))
    assert kq["thong_ke"]["loi_theo_cot"]["Protocol"]["trong"] == 1 and not kq["hop_le"][4]


def test_thong_ke_loi_theo_cot_xep_cot_nhieu_loi_truoc():
    df = bang_hop_le()
    df.loc[0:4, "Flow IAT Max"] = np.nan
    df.loc[5, "Protocol"] = np.nan
    kq = doc_va_kiem_tra(sang_csv(df))
    dong = next(w for w in kq["canh_bao"] if "Các cột có lỗi nhiều nhất" in w)
    assert dong.index("Flow IAT Max") < dong.index("Protocol")


def test_toan_bo_dong_loi():
    df = bang_hop_le()
    df["Flow Duration"] = np.nan
    kq = doc_va_kiem_tra(sang_csv(df))
    assert not kq["ok"] and "Không còn dòng nào" in kq["loi"][0]


def test_dong_trung_lap_van_du_doan():
    df = pd.concat([bang_hop_le(), bang_hop_le().head(3)], ignore_index=True)
    kq = doc_va_kiem_tra(sang_csv(df))
    assert kq["ok"] and kq["thong_ke"]["so_dong_trung"] == 3 and kq["hop_le"].all()


# ---------- 4. Cot nhan (Label) ----------
def test_co_cot_label():
    kq = doc_va_kiem_tra(sang_csv(bang_hop_le(nhan=True)))
    assert kq["nhan"] is not None and (kq["nhan"] == "DDoS").sum() == 5


def test_khong_co_cot_label():
    kq = doc_va_kiem_tra(sang_csv(bang_hop_le(nhan=False)))
    assert kq["ok"] and kq["nhan"] is None


def test_cot_label_khong_bao_gio_lot_vao_du_lieu_mo_hinh():
    kq = doc_va_kiem_tra(sang_csv(bang_hop_le(nhan=True)))
    assert list(kq["X"].columns) == FEAT and "Label" not in kq["X"].columns


def test_x_giong_het_du_co_hay_khong_co_label():
    a = doc_va_kiem_tra(sang_csv(bang_hop_le(nhan=True)))["X"]
    b = doc_va_kiem_tra(sang_csv(bang_hop_le(nhan=False)))["X"]
    pd.testing.assert_frame_equal(a, b)


# ---------- 5. File mau that cua du an ----------
@pytest.mark.parametrize("ten,co_nhan", [("demo_labeled.csv", True), ("demo_unlabeled.csv", False)])
def test_file_mau_cua_du_an(ten, co_nhan):
    f = ROOT / "data" / "samples" / ten
    if not f.exists():
        pytest.skip("Chua co file mau (chay src/s08_make_samples.py)")
    df, loi = doc_csv(str(f))
    kq = kiem_tra(df, FEAT)
    assert loi is None and kq["ok"] and (kq["nhan"] is not None) == co_nhan
    assert kq["thong_ke"]["so_dong_hop_le"] == len(df)
