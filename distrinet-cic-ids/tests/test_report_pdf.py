"""B2 - Kiem thu BAO CAO PDF: tao duoc file PDF hop le trong cac truong hop
co nhan / khong nhan / khong co tan cong / co dong loi, va noi dung tieng Viet dung.
Chay: pytest tests/test_report_pdf.py -v"""
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
pytest.importorskip("reportlab")
pytest.importorskip("matplotlib")
from report_pdf import tao_pdf  # noqa: E402
from validation import ap_nguong, bang_theo_nhan, danh_gia_voi_nhan  # noqa: E402

FEAT = json.loads((ROOT / "models" / "feature_cols.json").read_text(encoding="utf-8"))
TT = [("File gốc", "thử_nghiệm.csv"), ("Mô hình", "XGBoost"), ("Ngưỡng cảnh báo", "0.570")]


def du_lieu(n=300, co_tan_cong=True, so_loi=3):
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.integers(0, 10_000, (n, len(FEAT))).astype(float), columns=FEAT)
    nhan = np.where(np.arange(n) % 4 == 0, "DDoS", "Benign") if co_tan_cong else np.array(["Benign"] * n)
    xs = np.where(nhan == "Benign", rng.random(n) * 0.1, 0.9 + rng.random(n) * 0.1)
    xs[:so_loi] = np.nan
    kq = ap_nguong(pd.Series(xs), 0.57)
    kq.insert(0, "Dong", range(1, n + 1))
    kq["Nhan_thuc_te"] = nhan
    return df, kq


def so_trang(b):
    return b.count(b"/Type /Page") - b.count(b"/Type /Pages")


def chu_trong_pdf(b):
    pypdf = pytest.importorskip("pypdf")
    return "\n".join(t.extract_text() for t in pypdf.PdfReader(io.BytesIO(b)).pages)


def test_pdf_co_nhan():
    df, kq = du_lieu()
    b = tao_pdf(TT, df, kq, 0.57, danh_gia_voi_nhan(kq["Nhan_thuc_te"], kq["Ket_qua"]),
                bang_theo_nhan(kq["Nhan_thuc_te"], kq["Ket_qua"]))
    assert b.startswith(b"%PDF") and b.rstrip().endswith(b"%%EOF")
    assert 1 <= so_trang(b) <= 5


def test_pdf_khong_nhan_va_khong_tan_cong():
    df, kq = du_lieu(co_tan_cong=False)
    b = tao_pdf(TT, df, kq.drop(columns="Nhan_thuc_te"), 0.57)
    assert b.startswith(b"%PDF") and so_trang(b) >= 1


def test_pdf_toan_dong_loi_khong_vo():
    df, kq = du_lieu(n=10, so_loi=10)
    assert tao_pdf(TT, df, kq, 0.57).startswith(b"%PDF")


def test_pdf_noi_dung_tieng_viet():
    df, kq = du_lieu()
    dg = danh_gia_voi_nhan(kq["Nhan_thuc_te"], kq["Ket_qua"])
    chu = chu_trong_pdf(tao_pdf(TT, df, kq, 0.57, dg, bang_theo_nhan(kq["Nhan_thuc_te"], kq["Ket_qua"])))
    for cum in ("Báo cáo phát hiện xâm nhập mạng", "Kết luận", "Top 20 luồng đáng ngờ nhất",
                "So với nhãn thực tế", "Ma trận nhầm lẫn", "thử_nghiệm.csv", "DDoS"):
        assert cum in chu, cum
    so_tc = int((kq["Ket_qua"] == "Tấn công").sum())
    assert f"{so_tc:,} luồng tấn công" in chu
