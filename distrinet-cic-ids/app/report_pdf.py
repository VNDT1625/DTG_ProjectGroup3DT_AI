"""B2 - BAO CAO PDF cho mot lan phan tich file CSV.
Noi dung: thong tin lan chay, ket luan, bieu do phan bo xac suat, top 20 luong dang ngo,
(neu file co cot Label) chi so + ma tran nham lan + bang theo nhan, va ghi chu cach doc.
Font: DejaVu Sans di kem matplotlib (co du dau tieng Viet, khong can cai them font)."""
import io
from pathlib import Path

import numpy as np
import pandas as pd

from validation import KQ_BINH_THUONG, KQ_TAN_CONG, KQ_THIEU, phan_tram

MAU_TC, MAU_BT, MAU_THIEU = "#D64545", "#2A9D8F", "#9AA3AE"
MAU_NHAN, MAU_CHU, MAU_PHU, MAU_VIEN, MAU_NEN = "#E0A030", "#1B2433", "#5B6577", "#D9DEE7", "#F4F6FA"
COT_TOP = ["Protocol", "Flow Duration", "Total Fwd Packets", "Total Backward Packets"]
SO_TOP = 20
_FONT = None


def _dang_ky_font():
    """Dang ky DejaVu Sans (thuong + dam) tu thu muc font cua matplotlib. Tra ve (ten, ten_dam)."""
    global _FONT
    if _FONT:
        return _FONT
    import matplotlib
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    thu_muc = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    pdfmetrics.registerFont(TTFont("VN", str(thu_muc / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("VN-B", str(thu_muc / "DejaVuSans-Bold.ttf")))
    from reportlab.lib.fonts import addMapping
    addMapping("VN", 0, 0, "VN"); addMapping("VN", 1, 0, "VN-B")
    addMapping("VN", 0, 1, "VN"); addMapping("VN", 1, 1, "VN-B")
    _FONT = ("VN", "VN-B")
    return _FONT


def _bieu_do_xac_suat(xs, ket_qua, nguong):
    """Bieu do cot chong: so luong theo khoang xac suat (thang log), vach ngang la nguong. Tra ve PNG bytes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "DejaVu Sans"
    bins = np.linspace(0, 1, 21)
    fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=200)
    tc = xs[ket_qua == KQ_TAN_CONG]
    bt = xs[ket_qua == KQ_BINH_THUONG]
    ax.hist([bt, tc], bins=bins, stacked=True, color=[MAU_BT, MAU_TC], label=["Bình thường", "Tấn công"],
            edgecolor="white", linewidth=0.8)
    ax.set_yscale("symlog", linthresh=1)
    ax.axvline(nguong, color=MAU_NHAN, linestyle="--", linewidth=1.6)
    ax.text(nguong, 1.02, f"ngưỡng {nguong:.2f}", color="#9A6A10", fontsize=7.5, va="bottom", ha="center",
            transform=ax.get_xaxis_transform())
    ax.set_xlabel("Xác suất tấn công", fontsize=8, color=MAU_PHU)
    ax.set_ylabel("Số luồng (thang log)", fontsize=8, color=MAU_PHU)
    ax.set_xlim(0, 1)
    ax.tick_params(labelsize=7, colors=MAU_PHU)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MAU_VIEN)
    ax.grid(axis="y", color=MAU_VIEN, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.legend(fontsize=7.5, frameon=False, loc="lower left", ncol=2, bbox_to_anchor=(0, 1.0), borderaxespad=0.2)
    fig.tight_layout()
    b = io.BytesIO()
    fig.savefig(b, format="png")
    plt.close(fig)
    return b.getvalue()


def _so(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if isinstance(v, (float, np.floating)):
        if np.isinf(v):
            return "inf"
        return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.4g}"
    return f"{v:,}" if isinstance(v, (int, np.integer)) else str(v)


def tao_pdf(thong_tin, df, kq, nguong, dg=None, bang_nhan=None):
    """thong_tin: list (nhan, gia_tri) cho bang dau trang.
    df: du lieu goc; kq: bang ket qua cung thu tu (Ket_qua, Xac_suat_tan_cong, tuy chon Dong, Nhan_thuc_te).
    dg: ket qua danh_gia_voi_nhan (hoac None); bang_nhan: ket qua bang_theo_nhan (hoac None). Tra ve PDF bytes."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.graphics.shapes import Drawing, Rect
    from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)
    f, fb = _dang_ky_font()
    C = colors.HexColor
    st = {
        "tieu_de": ParagraphStyle("td", fontName=fb, fontSize=17, leading=21, textColor=C(MAU_CHU)),
        "phu": ParagraphStyle("ph", fontName=f, fontSize=9, leading=12, textColor=C(MAU_PHU)),
        "muc": ParagraphStyle("mu", fontName=fb, fontSize=11.5, leading=15, textColor=C(MAU_CHU),
                              spaceBefore=10, spaceAfter=5),
        "than": ParagraphStyle("th", fontName=f, fontSize=9.2, leading=13.5, textColor=C(MAU_CHU),
                               alignment=TA_LEFT),
        "ket_luan": ParagraphStyle("kl", fontName=fb, fontSize=12.5, leading=17, textColor=C(MAU_CHU)),
        "o": ParagraphStyle("o", fontName=f, fontSize=7.8, leading=10, textColor=C(MAU_CHU)),
    }
    rong = A4[0] - 36 * mm

    def bang(du_lieu, do_rong, cot_so=(), dong_dau=True, co_chu=8):
        if dong_dau:   # tieu de cot dai thi tu xuong dong, khong de chu de len nhau
            du_lieu = [[Paragraph(f"<b>{h}</b>", ParagraphStyle(
                "h", fontName=fb, fontSize=co_chu - 0.4, leading=co_chu + 1.6, textColor=C(MAU_PHU),
                alignment=2 if j in cot_so else 0)) if isinstance(h, str) else h
                for j, h in enumerate(du_lieu[0])]] + list(du_lieu[1:])
        t = Table(du_lieu, colWidths=do_rong, repeatRows=1 if dong_dau else 0, hAlign="LEFT")
        kieu = [("FONT", (0, 0), (-1, -1), f, co_chu), ("TEXTCOLOR", (0, 0), (-1, -1), C(MAU_CHU)),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, C(MAU_VIEN)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        if dong_dau:
            kieu += [("FONT", (0, 0), (-1, 0), fb, co_chu), ("BACKGROUND", (0, 0), (-1, 0), C(MAU_NEN)),
                     ("TEXTCOLOR", (0, 0), (-1, 0), C(MAU_PHU))]
        for c in cot_so:
            kieu.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
        t.setStyle(TableStyle(kieu))
        return t

    ket_qua = kq["Ket_qua"].to_numpy()
    xs = kq["Xac_suat_tan_cong"].to_numpy(dtype=float)
    n = len(kq)
    dem = {k: int((ket_qua == k).sum()) for k in (KQ_TAN_CONG, KQ_BINH_THUONG, KQ_THIEU)}
    co_kq = dem[KQ_TAN_CONG] + dem[KQ_BINH_THUONG]
    p = []

    # ---- Dau trang ----
    p += [Paragraph("Báo cáo phát hiện xâm nhập mạng", st["tieu_de"]),
          Paragraph("Ứng dụng Machine Learning vào hệ thống phát hiện nguy cơ an ninh mạng", st["phu"]),
          Spacer(1, 6)]
    tt = bang([[Paragraph(str(a), st["phu"]), Paragraph(str(b), st["than"])] for a, b in thong_tin],
              [45 * mm, rong - 45 * mm], dong_dau=False)
    p.append(tt)

    # ---- 1. Ket luan ----
    p.append(Paragraph("1. Kết luận", st["muc"]))
    if dem[KQ_TAN_CONG]:
        cau = (f"Phát hiện <font color='{MAU_TC}'>{dem[KQ_TAN_CONG]:,} luồng tấn công</font> trên {co_kq:,} "
               f"luồng được phân tích ({dem[KQ_TAN_CONG] / max(co_kq, 1) * 100:.2f}%).")
    else:
        cau = f"Không phát hiện luồng tấn công nào trong {co_kq:,} luồng được phân tích, ở ngưỡng {nguong:.2f}."
    p.append(Paragraph(cau, st["ket_luan"]))
    p.append(Spacer(1, 6))
    d = Drawing(rong, 9)
    x = 0.0
    for k, mau in ((KQ_TAN_CONG, MAU_TC), (KQ_BINH_THUONG, MAU_BT), (KQ_THIEU, MAU_THIEU)):
        w = rong * dem[k] / max(n, 1)
        if w > 0:
            d.add(Rect(x, 0, max(w - 1.5, 0.6), 9, fillColor=C(mau), strokeColor=None))
        x += w
    p += [d, Spacer(1, 5)]
    o = [[Paragraph(f"<font color='{m}'>■</font> {k}", st["than"]),
          Paragraph(f"<b>{dem[k]:,}</b>", st["than"]),
          Paragraph(f"{dem[k] / max(n, 1) * 100:.2f}%", st["phu"])]
         for k, m in ((KQ_TAN_CONG, MAU_TC), (KQ_BINH_THUONG, MAU_BT), (KQ_THIEU, MAU_THIEU))]
    p.append(bang(o, [55 * mm, 35 * mm, 30 * mm], dong_dau=False))
    if dem[KQ_THIEU]:
        p.append(Paragraph(f"{dem[KQ_THIEU]:,} dòng có ô trống, ô chữ hoặc giá trị vô cực nên không được dự đoán.",
                           st["phu"]))

    # ---- 2. Bieu do ----
    if co_kq:
        p.append(Paragraph("2. Phân bố xác suất tấn công", st["muc"]))
        hop = ~np.isnan(xs)
        anh = _bieu_do_xac_suat(xs[hop], ket_qua[hop], nguong)
        p.append(Image(io.BytesIO(anh), width=rong, height=rong * 2.6 / 7.2))
        p.append(Paragraph("Luồng có xác suất từ ngưỡng trở lên bị đánh dấu Tấn công. Phần lớn luồng nằm sát 0 "
                           "hoặc 1 nghĩa là mô hình chắc chắn; các luồng ở giữa nên được xem lại.", st["phu"]))

    # ---- 3. Top luong dang ngo ----
    p.append(Paragraph(f"3. Top {SO_TOP} luồng đáng ngờ nhất", st["muc"]))
    dong_so = kq["Dong"].to_numpy() if "Dong" in kq else np.arange(1, n + 1)
    vi_tri = np.flatnonzero(ket_qua == KQ_TAN_CONG)
    if len(vi_tri) == 0:
        p.append(Paragraph("Không có luồng nào bị đánh dấu Tấn công.", st["than"]))
    else:
        vi_tri = vi_tri[np.argsort(-xs[vi_tri], kind="stable")][:SO_TOP]
        cot = [c for c in COT_TOP if c in df.columns]
        co_nhan = "Nhan_thuc_te" in kq
        dau = ["Dòng", "Xác suất"] + cot + (["Nhãn thực tế"] if co_nhan else [])
        dl = [dau]
        for i in vi_tri:
            dl.append([f"{int(dong_so[i]):,}", f"{xs[i]:.4f}"] + [_so(df[c].iloc[i]) for c in cot]
                      + ([Paragraph(str(kq["Nhan_thuc_te"].iloc[i]), st["o"])] if co_nhan else []))
        w_nhan = 38 * mm if co_nhan else 0
        w_con = (rong - 14 * mm - 17 * mm - w_nhan) / max(len(cot), 1)
        p.append(bang(dl, [14 * mm, 17 * mm] + [w_con] * len(cot) + ([w_nhan] if co_nhan else []),
                      cot_so=range(0, 2 + len(cot)), co_chu=7.8))
        if dem[KQ_TAN_CONG] > SO_TOP:
            p.append(Paragraph(f"Danh sách đầy đủ {dem[KQ_TAN_CONG]:,} luồng có trong file CSV/Excel xuất từ "
                               "ứng dụng.", st["phu"]))

    # ---- 4. So voi nhan thuc te ----
    if dg is not None:
        p.append(Paragraph("4. So với nhãn thực tế trong file", st["muc"]))
        co_tc, co_bt = dg["TP"] + dg["FN"] > 0, dg["TN"] + dg["FP"] > 0
        cs = [("Accuracy", phan_tram(dg["Accuracy"])), ("Precision", phan_tram(dg["Precision"])),
              ("Recall", phan_tram(dg["Recall"])), ("F1", f"{dg['F1']:.4f}" if co_tc else "—"),
              ("FPR", phan_tram(dg["FPR"], 3)), ("FNR", phan_tram(dg["FNR"], 3))]
        p.append(bang([[a for a, _ in cs], [b for _, b in cs]], [rong / 6] * 6, cot_so=range(6), co_chu=9))
        p.append(Spacer(1, 3))
        p.append(Paragraph("Precision: cảnh báo đúng. Recall: tấn công bắt được. FPR: báo động nhầm trên luồng "
                           "bình thường. FNR: tấn công bị bỏ sót. \"—\" là không tính được do file thiếu loại "
                           "nhãn tương ứng.", st["phu"]))
        p.append(Spacer(1, 6))
        mt = bang([["", "Dự đoán bình thường", "Dự đoán tấn công"],
                   ["Thực tế bình thường", f"{dg['TN']:,}", f"{dg['FP']:,}"],
                   ["Thực tế tấn công", f"{dg['FN']:,}", f"{dg['TP']:,}"]],
                  [40 * mm, 35 * mm, 35 * mm], cot_so=(1, 2))
        p.append(KeepTogether([Paragraph("Ma trận nhầm lẫn", st["than"]), Spacer(1, 3), mt]))
        if bang_nhan is not None and len(bang_nhan):
            dl = [["Nhãn", "Loại", "Số dòng", "Đoán tấn công", "Đoán bình thường", "Thiếu dữ liệu", "Tỉ lệ đúng"]]
            for r in bang_nhan.itertuples():
                dl.append([Paragraph(str(r.Nhan), st["o"]), r.Loai, f"{r.So_dong:,}", f"{r.Tan_cong:,}",
                           f"{r.Binh_thuong:,}", f"{r.Khong_du:,}", phan_tram(r.Ti_le_dung)])
            p += [Spacer(1, 8), Paragraph("Theo từng loại nhãn", st["than"]), Spacer(1, 3),
                  bang(dl, [44 * mm, 30 * mm, 18 * mm, 22 * mm, 24 * mm, 19 * mm, rong - 157 * mm],
                       cot_so=range(2, 7), co_chu=7.8)]
        p.append(Spacer(1, 3))
        p.append(Paragraph(f"Tính trên {dg['so_dong']:,} dòng, không gồm dòng thiếu dữ liệu và nhãn \"Attempted\". "
                           "Benign được tính là bình thường, mọi nhãn khác là tấn công.", st["phu"]))

    # ---- Ghi chu ----
    ghi_chu = [Paragraph(f"{5 if dg is not None else 4}. Ghi chú khi đọc kết quả", st["muc"])]
    for g in ("Mô hình học từ bộ dữ liệu CIC-IDS2017 (bản sửa lỗi của Distrinet). Kết quả đáng tin nhất khi "
              "file được tạo bằng CICFlowMeter với cùng cách tính đặc trưng.",
              "Tấn công kiểu mới mà mô hình chưa từng gặp có thể bị bỏ sót. Thí nghiệm chia theo ngày trong "
              "đề tài cho thấy ngưỡng mặc định bắt kém các tấn công chưa gặp; ngưỡng thấp hơn bắt được nhiều "
              "hơn nhưng báo nhầm nhiều hơn.",
              "Dòng thiếu dữ liệu (ô trống, chữ, vô cực) không được dự đoán và không tính vào các chỉ số.",
              "Báo cáo này hỗ trợ ra quyết định, không thay thế việc kiểm tra của người phụ trách an ninh mạng."):
        ghi_chu.append(Paragraph("• " + g, st["than"]))
    p.append(KeepTogether(ghi_chu))

    ten_file = next((str(b) for a, b in thong_tin if "File" in str(a)), "")

    def chan_trang(canvas, doc):
        canvas.saveState()
        canvas.setFont(f, 7.5)
        canvas.setFillColor(C(MAU_PHU))
        canvas.drawString(18 * mm, 10 * mm, f"Báo cáo phát hiện xâm nhập mạng · {ten_file}"[:110])
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Trang {doc.page}")
        canvas.setStrokeColor(C(MAU_NHAN))
        canvas.setLineWidth(2)
        canvas.line(18 * mm, A4[1] - 12 * mm, 40 * mm, A4[1] - 12 * mm)
        canvas.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=17 * mm,
                            bottomMargin=17 * mm, title="Báo cáo phát hiện xâm nhập mạng",
                            author="Ứng dụng phát hiện xâm nhập mạng")
    doc.build(p, onFirstPage=chan_trang, onLaterPages=chan_trang)
    return buf.getvalue()
