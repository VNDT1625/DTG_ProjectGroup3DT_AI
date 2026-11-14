"""A4 - XUAT KET QUA ra file CSV.
Tach khoi app.py de kiem thu duoc va de dung chung cho giao dien, benchmark va Excel.
- bang_xuat : ghep 3 cot ket qua vao TRUOC cac cot goc cua file nguoi dung (khong sua cot goc)
- csv_bytes : tao noi dung file CSV (UTF-8 co BOM de Excel mo dung tieng Viet).
              Dung pyarrow neu co (nhanh hon pandas nhieu lan), loi thi tu dong quay ve pandas.
- ten_file  : ten file xuat co thoi diem tao"""
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from validation import KQ_TAN_CONG

COT_KQ = ["Ket_qua", "Xac_suat_tan_cong", "Ly_do"]
BOM = "﻿".encode("utf-8")


def bang_xuat(df, kq, chi_tan_cong=False):
    """df: du lieu goc nguoi dung tai len; kq: bang ket qua (cung so dong, cung thu tu) co cot
    Ket_qua, Xac_suat_tan_cong va (tuy chon) Ly_do. Tra ve bang de xuat."""
    assert len(df) == len(kq), "Bang ket qua phai cung so dong voi file goc"
    m = (kq["Ket_qua"].to_numpy() == KQ_TAN_CONG) if chi_tan_cong else np.ones(len(kq), bool)
    # Neu file nguoi dung la file ket qua cu (da co 3 cot nay) thi bo cot cu, tranh trung ten
    goc = df.drop(columns=[c for c in COT_KQ if c in df.columns]).iloc[m]
    dau = pd.DataFrame({
        "Ket_qua": kq["Ket_qua"].to_numpy()[m],
        "Xac_suat_tan_cong": kq["Xac_suat_tan_cong"].round(6).to_numpy()[m],
        "Ly_do": (kq["Ly_do"].to_numpy()[m] if "Ly_do" in kq else ""),
    }, index=goc.index)
    return pd.concat([dau, goc], axis=1).reset_index(drop=True)


def _csv_pyarrow(x):
    import pyarrow as pa
    import pyarrow.csv as pacsv
    bang = pa.Table.from_pandas(x, preserve_index=False)
    buf = pa.BufferOutputStream()
    pacsv.write_csv(bang, buf)
    return buf.getvalue().to_pybytes()


def _csv_pandas(x):
    return x.to_csv(index=False).encode("utf-8")


def csv_bytes(x, cach="tu_dong"):
    """Tra ve (noi_dung_bytes, cach_da_dung). cach: 'tu_dong' | 'pyarrow' | 'pandas'."""
    if cach in ("tu_dong", "pyarrow"):
        try:
            return BOM + _csv_pyarrow(x), "pyarrow"
        except Exception:
            if cach == "pyarrow":
                raise
    return BOM + _csv_pandas(x), "pandas"


def ten_file(ten_goc, chi_tan_cong=False, duoi="csv", luc=None):
    luc = luc or datetime.now()
    return (f"results_{Path(ten_goc).stem}" + ("_attacks" if chi_tan_cong else "")
            + f"_{luc:%Y%m%d_%H%M%S}.{duoi}")


# ======================= B1 - XUAT EXCEL (.xlsx) =======================
# File Excel luu so duoi dang SO THAT (khong phai chu), nen mo tren may dinh dang Viet Nam
# van hien dung 0,999999 - khac voi CSV (Excel doc dau cham thanh dau phan cach hang nghin).
EXCEL_MAX = 200_000          # tren muc nay openpyxl rat cham (khoang 0,3 giay / 1.000 dong) va ton RAM
MAU_DO, MAU_XANH, MAU_XAM = "FBD5D5", "D3F2E6", "E5E7EB"


def _gia_tri_excel(x):
    """Chuyen bang sang dang openpyxl ghi duoc: NaN -> o trong, vo cuc -> chu 'inf' / '-inf'
    (Excel khong luu duoc vo cuc va NaN; ghi NaN thang vao se lam hong file)."""
    cot = []
    for c in x.columns:
        s = x[c]
        if pd.api.types.is_float_dtype(s):
            a = s.to_numpy(dtype="float64")
            o = a.astype(object)
            o[np.isnan(a)] = None
            o[np.isposinf(a)] = "inf"
            o[np.isneginf(a)] = "-inf"
        elif pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            o = s.to_numpy().astype(object)
        else:
            o = s.astype(object).where(s.notna(), None).to_numpy()
            o = np.array([None if v is None else (v if isinstance(v, (int, float, str)) else str(v)) for v in o],
                         dtype=object)
        cot.append(o)
    return zip(*cot) if cot else iter(())


def excel_bytes(x, tom_tat):
    """x: bang da qua bang_xuat(); tom_tat: list cac cap (thong tin, gia tri) cho sheet Summary.
    Sheet Results: dong tieu de co dinh + bo loc + do rong cot + to mau cot Ket_qua (to bang
    dinh dang co dieu kien: nhanh, khong phai to tung o). Sheet Summary: thong tin lan chay."""
    if len(x) > EXCEL_MAX:
        raise ValueError(f"Qua {EXCEL_MAX:,} dong, hay xuat CSV hoac chi xuat cac luong Tan cong.")
    import io
    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Results")
    ws.freeze_panes = "B2"                                    # co dinh dong tieu de va cot Ket_qua
    so_cot = x.shape[1]
    cuoi = get_column_letter(max(so_cot, 1))
    for i, c in enumerate(x.columns, start=1):
        rong = {"Ket_qua": 18, "Xac_suat_tan_cong": 19, "Ly_do": 34}.get(c, min(max(len(str(c)) + 3, 11), 32))
        ws.column_dimensions[get_column_letter(i)].width = rong
    ws.auto_filter.ref = f"A1:{cuoi}{len(x) + 1}"
    nen_tieu_de = PatternFill("solid", fgColor="1F2A44")
    dau = []
    for c in x.columns:
        o = WriteOnlyCell(ws, value=str(c))
        o.font = Font(bold=True, color="FFFFFF")
        o.fill = nen_tieu_de
        o.alignment = Alignment(vertical="center")
        dau.append(o)
    ws.append(dau)
    for dong in _gia_tri_excel(x):
        ws.append(dong)
    if len(x) and "Ket_qua" in x.columns:
        vung = f"A2:A{len(x) + 1}"
        for chu, mau in (("Tấn công", MAU_DO), ("Bình thường", MAU_XANH), ("Không đủ dữ liệu", MAU_XAM)):
            ws.conditional_formatting.add(vung, FormulaRule(formula=[f'$A2="{chu}"'],
                                                            fill=PatternFill("solid", bgColor=mau)))

    ws2 = wb.create_sheet("Summary")
    ws2.column_dimensions["A"].width = 30
    ws2.column_dimensions["B"].width = 48
    dau2 = []
    for t in ("Thong_tin", "Gia_tri"):
        o = WriteOnlyCell(ws2, value=t)
        o.font = Font(bold=True, color="FFFFFF")
        o.fill = nen_tieu_de
        dau2.append(o)
    ws2.append(dau2)
    for k, v in tom_tat:
        ws2.append([str(k), v if isinstance(v, (int, float, str)) or v is None else str(v)])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
