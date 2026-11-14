"""UNG DUNG PHAT HIEN XAM NHAP MANG - Streamlit.
Chay: streamlit run app/app.py   (tu thu muc goc du an, da kich hoat .venv)"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import altair as alt
import joblib
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
import ids_pipeline  # noqa: F401,E402  (can de nap mo hinh)
import ui as gd  # noqa: E402
from export import EXCEL_MAX, bang_xuat, csv_bytes, excel_bytes, ten_file  # noqa: E402
from report_pdf import tao_pdf  # noqa: E402
from validation import (KQ_BINH_THUONG, KQ_TAN_CONG, KQ_THIEU, ap_nguong, bang_theo_nhan,  # noqa: E402
                        danh_gia_voi_nhan, doc_csv, kiem_tra, phan_tram, tinh_xac_suat)

MAU = {KQ_TAN_CONG: gd.MAU_TAN_CONG, KQ_BINH_THUONG: gd.MAU_BINH_THUONG, KQ_THIEU: gd.MAU_THIEU}
CSV_TAO_NGAY = 200_000   # file xuat nho hon muc nay thi tao CSV ngay; lon hon thi bam nut "Tao file CSV"

st.set_page_config(page_title="ML phát hiện nguy cơ an ninh mạng", page_icon="🛡️", layout="wide")
st.markdown(gd.CSS, unsafe_allow_html=True)


@st.cache_resource
def nap_mo_hinh():
    b = joblib.load(ROOT / "models" / "final_model.joblib")
    lock = ROOT / "models" / "test_lock.json"
    b["test"] = json.loads(lock.read_text(encoding="utf-8"))["ket_qua"] if lock.exists() else None
    return b


def html(x):
    st.markdown(x, unsafe_allow_html=True)


def bieu_do(chart, h):
    return (chart.properties(height=h, background="transparent")
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor=gd.MAU_CHU_PHU, titleColor=gd.MAU_CHU_PHU, gridColor=gd.MAU_VIEN,
                            domainColor=gd.MAU_VIEN, tickColor=gd.MAU_VIEN, labelFont="IBM Plex Sans",
                            titleFont="IBM Plex Sans", titleFontWeight=500))


try:
    MH = nap_mo_hinh()
except Exception as e:
    st.error(f"Không nạp được mô hình (models/final_model.joblib). Hãy chạy lại Giai đoạn 5. Chi tiết: {e}")
    st.stop()

# ---------------- Thanh ben: cai dat ----------------
with st.sidebar:
    st.markdown("### Cài đặt phát hiện")
    nguong = st.slider("Ngưỡng cảnh báo", 0.05, 0.95, float(round(MH["threshold"], 2)), 0.01,
                       help="Luồng có xác suất tấn công từ ngưỡng này trở lên sẽ bị đánh dấu là Tấn công.")
    html(gd.dong_ho_nguong(nguong, MH["threshold"]))
    st.markdown(f'<p class="ghi-chu">Mặc định {MH["threshold"]:.3f}, được chọn trên tập validation. '
                'Hạ ngưỡng để bắt được nhiều tấn công hơn, đổi lại có thể báo nhầm nhiều hơn.</p>',
                unsafe_allow_html=True)
    if abs(nguong - MH["threshold"]) > 0.006:
        st.warning(f"Đang dùng ngưỡng {nguong:.2f}, khác mặc định.")
    st.divider()
    st.markdown("### Định dạng file")
    st.markdown(f'<p class="ghi-chu">File CSV cần đủ {len(MH["input_features"])} cột đặc trưng của CICFlowMeter. '
                'Tên cột không phân biệt hoa thường hay khoảng trắng. Cột <code>Label</code> là tùy chọn, '
                'nếu có thì ứng dụng so sánh thêm với nhãn thực tế.</p>', unsafe_allow_html=True)
    with st.expander("Xem danh sách cột"):
        st.code("\n".join(MH["input_features"]), language=None)
    st.download_button("Tải file mẫu chỉ có dòng tiêu đề",
                       (",".join(MH["input_features"]) + "\n").encode("utf-8-sig"),
                       "header_template.csv", "text/csv", use_container_width=True)

# ---------------- Dau trang ----------------
_gs = st.session_state.get("giam_sat")
html(gd.dau_trang(MH["model_name"], MH["test"], MH["threshold"], dang_giam_sat=bool(_gs and _gs.dang_chay)))
CHE_DO = ["Phân tích file CSV", "Giám sát trực tiếp (thử nghiệm)"]
# Trong Docker (bien moi truong IDS_DOCKER=1): container khong bat duoc goi tin cua may that -> tat giam sat truc tiep
TRONG_DOCKER = os.environ.get("IDS_DOCKER") == "1"
try:
    che_do = st.segmented_control("Chế độ", CHE_DO, default=CHE_DO[0], label_visibility="collapsed")
except AttributeError:
    che_do = st.radio("Chế độ", CHE_DO, horizontal=True, label_visibility="collapsed")
che_do = che_do or CHE_DO[0]
if _gs is not None and _gs.dang_chay and che_do == CHE_DO[0]:
    st.info("Chế độ giám sát trực tiếp vẫn đang chạy ở nền. Chuyển sang tab đó để xem hoặc dừng lại.")



def che_do_file():
    # ---- 1. Tai du lieu ----
    html(gd.buoc(1, "Tải dữ liệu", "file CSV, tối đa 1 GB"))
    tep = st.file_uploader("Chọn hoặc kéo thả file CSV vào đây", type=["csv"], label_visibility="collapsed")
    if tep is None:
        st.session_state.pop("phan_tich", None)   # giai phong bo nho khi bo file
        st.session_state.pop("excel", None)
        st.session_state.pop("csv", None)
        st.session_state.pop("pdf", None)
        html(gd.trang_chua_co_file(len(MH["input_features"])))
        st.stop()

    # ---- 2. Kiem tra ----
    html(gd.buoc(2, "Kiểm tra dữ liệu", tep.name))
    # Doc, kiem tra va tinh xac suat CHI MOT LAN cho moi file. Cac lan tai lai giao dien sau do
    # (doi bo loc, doi nguong, bat tat nut) dung lai ket qua da luu, khong tinh lai.
    khoa_file = (tep.name, tep.size, getattr(tep, "file_id", None))
    bn = st.session_state.get("phan_tich")
    if bn is None or bn["khoa"] != khoa_file:
        st.session_state.pop("phan_tich", None)
        st.session_state.pop("excel", None)
        st.session_state.pop("csv", None)
        st.session_state.pop("pdf", None)
        with st.spinner("Đang đọc và kiểm tra file..."):
            df, loi_doc = doc_csv(tep)
            kt = kiem_tra(df, MH["input_features"]) if not loi_doc else None
        xs = None
        if kt is not None and kt["ok"]:
            with st.spinner("Đang phân tích các luồng mạng..."):
                xs = tinh_xac_suat(MH["pipeline"], kt["X"], kt["hop_le"])
        bn = {"khoa": khoa_file, "df": df, "loi_doc": loi_doc, "kt": kt, "xs": xs}
        st.session_state["phan_tich"] = bn
    df, loi_doc, kt, xs = bn["df"], bn["loi_doc"], bn["kt"], bn["xs"]
    if loi_doc:
        html(gd.danh_sach_kiem_tra([("loi", loi_doc)]))
        st.stop()
    muc = [("ok", f"Đọc được {kt['thong_ke']['so_dong']:,} dòng và {kt['thong_ke']['so_cot']:,} cột.")]
    if kt["ok"] or not any("Thiếu" in l and "cột" in l for l in kt["loi"]):
        muc.append(("ok", f"Có đủ {len(MH['input_features'])} cột mà mô hình cần."))
    muc += [("cb", w) for w in kt["canh_bao"]] + [("loi", l) for l in kt["loi"]]
    if kt["ok"]:
        muc.append(("ok", f"Sẵn sàng phân tích {kt['thong_ke']['so_dong_hop_le']:,} dòng."
                    + (" File có cột Label, sẽ so sánh với nhãn thực tế." if kt["nhan"] is not None else "")))
    html(gd.danh_sach_kiem_tra(muc))
    if not kt["ok"]:
        st.stop()

    # ---- 3. Phat hien ----
    html(gd.buoc(3, "Phát hiện tấn công", f"mô hình {MH['model_name']}"))
    kq = ap_nguong(xs, nguong)   # doi nguong chi can so sanh lai, rat nhanh
    kq.insert(0, "Dong", range(1, len(kq) + 1))
    kq["Ly_do"] = kt["ly_do"]
    if kt["nhan"] is not None:
        kq["Nhan_thuc_te"] = kt["nhan"].values
    dem = kq["Ket_qua"].value_counts().reindex(list(MAU), fill_value=0)
    tong = len(kq)
    html(gd.dai_phan_quyet(int(dem[KQ_TAN_CONG]), int(dem[KQ_BINH_THUONG]), int(dem[KQ_THIEU]), nguong))
    if dem[KQ_TAN_CONG] == 0:
        st.success(f"Không phát hiện luồng tấn công nào ở ngưỡng {nguong:.2f}. "
                   "Có thể hạ ngưỡng ở thanh bên nếu muốn soát kỹ hơn.")
    st.write("")

    # Thanh chon che do xem ket qua: nut lon co bieu tuong (thay cho st.tabs de trinh bay noi bat, ro la bam duoc)
    tabs = [":material/table_rows: Chi tiết từng luồng", ":material/bar_chart: Phân bố xác suất"] + (
        [":material/fact_check: So với nhãn thực tế"] if kt["nhan"] is not None else [])
    with st.container(key="xem_kq"):
        xem = st.segmented_control("Xem kết quả", tabs, default=tabs[0], key=f"che_do_xem_{len(tabs)}",
                                   label_visibility="collapsed", width="stretch") or tabs[0]
    if xem not in tabs:
        xem = tabs[0]

    if xem == tabs[0]:
        f1, f2, f3 = st.columns([2, 1, 1])
        chon = f1.multiselect("Hiển thị kết quả", list(MAU), default=[KQ_TAN_CONG, KQ_THIEU] if dem[KQ_TAN_CONG]
                              else list(MAU))
        xs_min = f2.number_input("Xác suất tấn công từ", 0.0, 1.0, 0.0, 0.05)
        sap_xep = f3.selectbox("Sắp xếp", ["Xác suất giảm dần", "Theo thứ tự trong file", "Xác suất tăng dần"])
        v = kq[kq["Ket_qua"].isin(chon)]
        if xs_min > 0:
            v = v[v["Xac_suat_tan_cong"].fillna(-1) >= xs_min]
        if sap_xep != "Theo thứ tự trong file":
            v = v.sort_values("Xac_suat_tan_cong", ascending=sap_xep.endswith("tăng dần"), na_position="last")
        hien = v.head(10000).rename(columns={"Dong": "Dòng", "Xac_suat_tan_cong": "Xác suất tấn công",
                                             "Ket_qua": "Kết quả", "Ly_do": "Lý do", "Nhan_thuc_te": "Nhãn thực tế"})
        _to = {KQ_TAN_CONG: f"color:#ff8f8f;background-color:rgba(239,91,91,.16);font-weight:600",
               KQ_BINH_THUONG: f"color:#7fe0cf;background-color:rgba(63,185,166,.10)",
               KQ_THIEU: f"color:{gd.MAU_MO};background-color:rgba(125,138,163,.10)"}
        st.dataframe(hien.style.map(lambda x: _to.get(x, ""), subset=["Kết quả"]),
                     use_container_width=True, hide_index=True, height=420,
                     column_config={"Xác suất tấn công": st.column_config.ProgressColumn(
                         format="%.4f", min_value=0.0, max_value=1.0)})
        html(f'<p class="ghi-chu">{min(len(v), 10000):,} trên {len(v):,} dòng phù hợp đang hiển thị. '
             'File xuất ra ở bước 4 luôn có đầy đủ.</p>')

    if xem == tabs[1]:
        xs = kq.loc[kq["Ket_qua"] != KQ_THIEU, ["Xac_suat_tan_cong", "Ket_qua"]]
        # Tu dem theo 20 khoang roi chong tay, de moi nhom co mau chuyen sac rieng
        canh = np.linspace(0, 1, 21)
        khoang = np.clip(np.digitize(xs["Xac_suat_tan_cong"].to_numpy(), canh) - 1, 0, 19)
        dem_k = (pd.DataFrame({"k": khoang, "kq": xs["Ket_qua"].to_numpy()})
                 .groupby(["k", "kq"]).size().unstack(fill_value=0)
                 .reindex(index=range(20), columns=[KQ_BINH_THUONG, KQ_TAN_CONG], fill_value=0))
        hang = []
        for k in range(20):
            bt_, tc_ = int(dem_k.loc[k, KQ_BINH_THUONG]), int(dem_k.loc[k, KQ_TAN_CONG])
            for ten, y0, y1 in ((KQ_BINH_THUONG, 0, bt_), (KQ_TAN_CONG, bt_, bt_ + tc_)):
                if y1 > y0:
                    hang.append({"tu": canh[k], "den": canh[k + 1], "y0": y0, "y1": y1, "So_luong": y1 - y0,
                                 "Ket_qua": ten, "Khoang": f"{canh[k]:.2f}–{canh[k + 1]:.2f}"})
        dk = pd.DataFrame(hang)
        def lop(ten, mau_dam, mau_sang):
            return alt.Chart(dk).transform_filter(alt.datum.Ket_qua == ten).mark_rect(
                cornerRadiusTopLeft=4, cornerRadiusTopRight=4, stroke=gd.MAU_NEN, strokeWidth=1.5,
                color=alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0,
                                   stops=[alt.GradientStop(color=mau_dam, offset=0),
                                          alt.GradientStop(color=mau_sang, offset=1)])).encode(
                x=alt.X("tu:Q", title="Xác suất tấn công", scale=alt.Scale(domain=[0, 1])), x2="den:Q",
                y=alt.Y("y1:Q", title="Số luồng (thang log)", scale=alt.Scale(type="symlog")), y2="y0:Q",
                opacity=alt.condition(chon_hover, alt.value(1), alt.value(.55)),
                tooltip=[alt.Tooltip("Khoang:N", title="Khoảng xác suất"), alt.Tooltip("Ket_qua:N", title="Kết quả"),
                         alt.Tooltip("So_luong:Q", title="Số luồng", format=",")])
        chon_hover = alt.selection_point(on="pointerover", fields=["Khoang"], empty=True, clear="pointerout")
        vung = alt.Chart(pd.DataFrame({"a": [nguong], "b": [1.0]})).mark_rect(
            color=gd.MAU_TAN_CONG, opacity=.07).encode(x="a:Q", x2="b:Q")
        rule = alt.Chart(pd.DataFrame({"x": [nguong]})).mark_rule(color=gd.MAU_NHAN, strokeDash=[6, 4],
                                                                   strokeWidth=2).encode(x="x:Q")
        nhan_nguong = alt.Chart(pd.DataFrame({"x": [nguong], "t": [f"ngưỡng {nguong:.2f}"]})).mark_text(
            align="left", dx=6, dy=-6, color=gd.MAU_NHAN, fontWeight=600, font="IBM Plex Sans").encode(
            x="x:Q", y=alt.value(12), text="t:N")
        hist = (vung + lop(KQ_BINH_THUONG, "#1f6f63", "#5fe0c8").add_params(chon_hover)
                + lop(KQ_TAN_CONG, "#8f2a2a", "#ff8a8a"))
        st.altair_chart(bieu_do(hist + rule + nhan_nguong, 320), use_container_width=True)
        html(f'<p class="ghi-chu">Vạch vàng là ngưỡng cảnh báo {nguong:.2f}; vùng đỏ nhạt bên phải là vùng bị đánh dấu Tấn công. Rê chuột lên cột để xem số luồng. Hầu hết các luồng nằm sát hai đầu 0 và 1, '
             'nghĩa là mô hình rất chắc chắn. Các luồng ở giữa là những trường hợp nên xem lại.</p>')

    if kt["nhan"] is not None:
        if xem == tabs[2]:
            dg = danh_gia_voi_nhan(kq["Nhan_thuc_te"], kq["Ket_qua"])
            if dg is None:
                st.info("Không có dòng nào dùng được để so sánh.")
            else:
                co_tc, co_bt = dg["TP"] + dg["FN"] > 0, dg["TN"] + dg["FP"] > 0
                X_, D_, V_ = gd.MAU_BINH_THUONG, gd.MAU_TAN_CONG, gd.MAU_NHAN
                html(gd.dai_so_lieu([("Accuracy", phan_tram(dg["Accuracy"]), "dự đoán đúng", dg["Accuracy"], V_),
                                     ("Precision", phan_tram(dg["Precision"]), "cảnh báo đúng", dg["Precision"], V_),
                                     ("Recall", phan_tram(dg["Recall"]), "tấn công bắt được", dg["Recall"], X_),
                                     ("F1", f"{dg['F1']:.4f}" if co_tc else "—", "cân bằng P và R",
                                      dg["F1"] if co_tc else None, V_),
                                     ("FPR", phan_tram(dg["FPR"], 3), "báo động nhầm", None, D_),
                                     ("FNR", phan_tram(dg["FNR"], 3), "bỏ sót tấn công", None, D_)]))
                if not co_tc:
                    html('<p class="ghi-chu">File không có dòng tấn công nào theo nhãn thực tế, nên Recall, '
                         'F1 và FNR không tính được (hiện "—"). Precision chỉ tính được khi có cảnh báo.</p>')
                if not co_bt:
                    html('<p class="ghi-chu">File không có dòng Benign nào theo nhãn thực tế, nên FPR '
                         'không tính được (hiện "—").</p>')
                st.markdown("**Ma trận nhầm lẫn**")
                html(gd.ma_tran(dg["TN"], dg["FP"], dg["FN"], dg["TP"]))
                st.write("")
                # Bang theo nhan: chiem ca chieu ngang, khong gioi han chieu cao -> thay het cot va het dong
                st.markdown("**Theo từng loại nhãn trong file**")
                b = bang_theo_nhan(kq["Nhan_thuc_te"], kq["Ket_qua"])
                html(gd.bang([("Nhãn", ""), ("Loại", "mo"), ("Số dòng", "so"), ("Đoán tấn công", "so"),
                              ("Đoán bình thường", "so"), ("Thiếu dữ liệu", "so"), ("Tỉ lệ đúng", "html")],
                             [[r.Nhan, r.Loai, f"{r.So_dong:,}", f"{r.Tan_cong:,}", f"{r.Binh_thuong:,}",
                               f"{r.Khong_du:,}", gd.thanh_ti_le(r.Ti_le_dung)] for r in b.itertuples()]
                             ).replace('<div class="bang">', '<div class="bang" style="max-height:none">', 1))
                html('<p class="ghi-chu">Tỉ lệ đúng: với Benign là phần được đoán Bình thường; với nhãn '
                     'tấn công là phần bị bắt là Tấn công. Không tính dòng thiếu dữ liệu.</p>')
                html(f'<p class="ghi-chu">Tính trên {dg["so_dong"]:,} dòng, không gồm dòng thiếu dữ liệu và nhãn '
                     '"Attempted". Benign được tính là bình thường, mọi nhãn khác là tấn công.</p>')

    # ---- 4. Xuat ket qua ----
    html(gd.buoc(4, "Xuất kết quả"))
    chi_tan_cong = st.toggle("Chỉ xuất các luồng bị đánh dấu Tấn công")
    so_dong_xuat = int(dem[KQ_TAN_CONG]) if chi_tan_cong else len(kq)
    ten = ten_file(tep.name, chi_tan_cong, duoi="")[:-1]
    x1, x2, x3 = st.columns(3)
    # File CSV chi tao MOT LAN cho moi (file, nguong, lua chon) roi luu lai; bam nut khac khong tao lai.
    khoa_csv = (khoa_file, round(nguong, 4), chi_tan_cong)
    luu = st.session_state.get("csv")
    if luu is None or luu[0] != khoa_csv:
        luu = None
        tao = so_dong_xuat <= CSV_TAO_NGAY or x1.button(
            f"Tạo file CSV ({so_dong_xuat:,} dòng)", type="primary", use_container_width=True,
            help="File lớn nên chỉ tạo khi bạn cần. Có thể mất vài chục giây.")
        if tao:
            with st.spinner(f"Đang tạo file CSV ({so_dong_xuat:,} dòng)..."):
                noi_dung, _ = csv_bytes(bang_xuat(df, kq, chi_tan_cong))
            st.session_state["csv"] = luu = (khoa_csv, noi_dung, f"{ten}.csv")
            if so_dong_xuat > CSV_TAO_NGAY:
                st.rerun()
    if luu is not None:
        x1.download_button(f"Tải file CSV ({so_dong_xuat:,} dòng, {len(luu[1]) / 2**20:,.1f} MB)", luu[1],
                           luu[2], "text/csv", type="primary", use_container_width=True)
    if so_dong_xuat <= EXCEL_MAX:
        khoa = (khoa_file, round(nguong, 4), chi_tan_cong)
        luu_x = st.session_state.get("excel")
        if luu_x is not None and luu_x[0] == khoa:
            x2.download_button(f"Tải file Excel ({len(luu_x[1]) / 2**20:,.1f} MB)", luu_x[1], luu_x[2],
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
        elif x2.button(f"Tạo file Excel ({so_dong_xuat:,} dòng)", use_container_width=True,
                       help="Khoảng 0,3 giây cho mỗi 1.000 dòng."):
            tom_tat = [("Mô hình", MH["model_name"]), ("Ngưỡng cảnh báo", round(nguong, 4)),
                       ("Ngưỡng mặc định", round(MH["threshold"], 4)),
                       ("Thời điểm phân tích", f"{datetime.now():%Y-%m-%d %H:%M:%S}"),
                       ("File gốc", tep.name), ("Số dòng trong file gốc", len(kq)),
                       ("Chỉ xuất luồng Tấn công", "Có" if chi_tan_cong else "Không"),
                       ("Số dòng trong file này", so_dong_xuat),
                       ("Tấn công", int(dem[KQ_TAN_CONG])), ("Bình thường", int(dem[KQ_BINH_THUONG])),
                       ("Không đủ dữ liệu", int(dem[KQ_THIEU])),
                       ("Ghi chú", "Ô trống ở cột Xac_suat_tan_cong là dòng thiếu dữ liệu, không dự đoán. "
                                   "Chữ 'inf' là giá trị vô cực có trong file gốc.")]
            with st.spinner(f"Đang tạo file Excel ({so_dong_xuat:,} dòng)..."):
                data = excel_bytes(bang_xuat(df, kq, chi_tan_cong), tom_tat)
            st.session_state["excel"] = (khoa, data, ten_file(tep.name, chi_tan_cong, "xlsx"))
            st.rerun()
    else:
        x2.info(f"Excel chỉ hỗ trợ tối đa {EXCEL_MAX:,} dòng trong ứng dụng này. Hãy dùng CSV, "
                "hoặc bật “Chỉ xuất các luồng bị đánh dấu Tấn công”.")
    # ---- Bao cao PDF: tom tat 2-4 trang de nop/gui, khong chua toan bo du lieu ----
    khoa_pdf = (khoa_file, round(nguong, 4))
    luu_p = st.session_state.get("pdf")
    if luu_p is not None and luu_p[0] == khoa_pdf:
        x3.download_button(f"Tải báo cáo PDF ({len(luu_p[1]) / 2**10:,.0f} KB)", luu_p[1], luu_p[2],
                           "application/pdf", use_container_width=True)
    elif x3.button("Tạo báo cáo PDF", use_container_width=True,
                   help="Tóm tắt kết quả 2–4 trang: kết luận, biểu đồ, top 20 luồng đáng ngờ, chỉ số nếu có nhãn."):
        thong_tin = [("File gốc", tep.name), ("Thời điểm phân tích", f"{datetime.now():%Y-%m-%d %H:%M:%S}"),
                     ("Mô hình", MH["model_name"]),
                     ("Ngưỡng cảnh báo", f"{nguong:.3f} (mặc định {MH['threshold']:.3f})"),
                     ("Số dòng / số cột", f"{len(kq):,} / {df.shape[1]:,}")]
        dg_pdf = bn_pdf = None
        if kt["nhan"] is not None:
            dg_pdf = danh_gia_voi_nhan(kq["Nhan_thuc_te"], kq["Ket_qua"])
            bn_pdf = bang_theo_nhan(kq["Nhan_thuc_te"], kq["Ket_qua"])
        with st.spinner("Đang tạo báo cáo PDF..."):
            data = tao_pdf(thong_tin, df, kq, nguong, dg_pdf, bn_pdf)
        st.session_state["pdf"] = (khoa_pdf, data, ten_file(tep.name, False, "pdf").replace("results_", "report_", 1))
        st.rerun()
    html('<p class="ghi-chu">Mở bằng Excel trên máy dùng định dạng số Việt Nam: hãy dùng <b>file Excel</b>. '
         'File CSV dùng dấu chấm thập phân, nên nếu nhấp đúp mở bằng Excel, các số như 0.999999 có thể '
         'bị đọc thành 999999. CSV vẫn đúng khi mở bằng ứng dụng này, Python hay các công cụ phân tích.</p>')

if che_do == CHE_DO[0]:
    che_do_file()
elif TRONG_DOCKER:
    # Giao dien giu nguyen nhu tren may; chi rieng giam sat truc tiep khong chay duoc trong container
    html(gd.buoc(1, "Giám sát trực tiếp", "không khả dụng trong Docker"))
    html(gd.danh_sach_kiem_tra([
        ("cb", "Ứng dụng đang chạy trong Docker. Container là một máy ảo nhỏ, tách biệt với card Wi-Fi và dây mạng "
               "của máy tính, nên không bắt được gói tin thật để giám sát."),
        ("ok", "Chế độ Phân tích file CSV vẫn dùng đầy đủ: kiểm tra dữ liệu, phát hiện tấn công, xuất CSV, Excel, PDF."),
        ("ok", "Muốn dùng giám sát trực tiếp: chạy ứng dụng thẳng trên Windows bằng lệnh streamlit run app\\app.py "
               "(xem mục Chạy ứng dụng trong README)."),
    ]))
    html(gd.radar([], [], False, 0))
else:
    import live_view
    live_view.hien_thi(MH, nguong, html, bieu_do, MAU)
