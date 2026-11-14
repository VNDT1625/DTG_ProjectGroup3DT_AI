"""Giao dien che do GIAM SAT TRUC TIEP (thu nghiem)."""
import time
from datetime import datetime

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import ui as gd
from live_monitor import GiamSat, danh_sach_card, kiem_tra_moi_truong
from validation import KQ_BINH_THUONG, KQ_TAN_CONG, KQ_THIEU

TZ = datetime.now().astimezone().tzinfo


def _gan_nhan(df, nguong):
    xs = df["Xac_suat_tan_cong"]
    return np.where(xs.isna(), KQ_THIEU, np.where(xs >= nguong, KQ_TAN_CONG, KQ_BINH_THUONG))


def _gio(ts_series, fmt="%H:%M:%S"):
    return pd.to_datetime(ts_series, unit="s", utc=True).dt.tz_convert(TZ).dt.strftime(fmt)


@st.cache_data(ttl=30, show_spinner=False)
def _cac_card(cach_bat):
    return danh_sach_card(cach_bat)


def _radar(kq, nguong, dang_chay):
    """Radar: moi cham la mot luong vua danh gia. Goc theo dia chi dich, khoang cach theo nguon (co dinh
    cho cung mot cap may), cham do la luong bi danh dau Tan cong."""
    import zlib
    if kq.empty:
        return gd.radar([], [], dang_chay, 0)
    v = kq.sort_values("Ket_thuc").tail(60)
    tc = (v["Xac_suat_tan_cong"].fillna(0) >= nguong).to_numpy()
    diem = [(zlib.crc32(str(d).encode()) % 360, 0.22 + 0.74 * (zlib.crc32(str(n).encode()) % 1000) / 1000, bool(t))
            for d, n, t in zip(v["Dich"], v["Nguon"], tc)]
    moi = v.iloc[::-1].head(7)
    nhat_ky = [(g, f"{n} → {d} {gt}", float(p) if p == p else 0.0, bool(float(p) >= nguong) if p == p else False)
               for g, n, d, gt, p in zip(_gio(moi["Ket_thuc"]), moi["Nguon"], moi["Dich"], moi["Giao_thuc"],
                                         moi["Xac_suat_tan_cong"])]
    return gd.radar(diem, nhat_ky, dang_chay, int(tc.sum()))


def _ve(gs, nguong, html, bieu_do, MAU):
    s = gs.anh_chup()
    if s["loi"]:
        html(gd.danh_sach_kiem_tra([("loi", s["loi"])]))
    t0 = s["t_bat_dau"]
    chay = int(((s["t_dung"] or time.time()) - t0)) if t0 else 0
    kq = s["ket_qua"]
    toc_do = f"{s['so_goi'] / chay:,.0f} gói/giây" if chay else ""
    html(gd.dai_so_lieu([("Gói tin đã bắt", f"{s['so_goi']:,}", toc_do),
                         ("Luồng đang mở", f"{s['dang_mo']:,}", "chờ kết thúc để đánh giá"),
                         ("Luồng đã đánh giá", f"{len(kq):,}", ""),
                         ("Thời gian chạy", f"{chay // 60:02d}:{chay % 60:02d}",
                          "đang chạy" if s["dang_chay"] else "đã dừng")]))
    html(_radar(kq, nguong, s["dang_chay"]))
    if kq.empty:
        html('<p class="ghi-chu">Đang chờ luồng đầu tiên kết thúc. Một luồng được đánh giá khi kết nối đóng lại '
             'hoặc sau 15 giây không có gói tin mới. Mở vài trang web để tạo lưu lượng.</p>')
        return
    kq = kq.copy()
    kq["Ket_qua"] = _gan_nhan(kq, nguong)
    dem = pd.Series(kq["Ket_qua"]).value_counts().reindex(list(MAU), fill_value=0)
    html(gd.dai_phan_quyet(int(dem[KQ_TAN_CONG]), int(dem[KQ_BINH_THUONG]), int(dem[KQ_THIEU]), nguong,
                           "Đã đánh giá"))

    # ---- Dong thoi gian: so luong moi 10 giay, vung xep chong ----
    html('<div class="tieu-de-nho">Số luồng theo thời gian</div>')
    tl = kq[["Ket_thuc", "Ket_qua"]].copy()
    tl["Thoi_diem"] = pd.to_datetime((tl["Ket_thuc"] // 10) * 10, unit="s", utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
    luoi = pd.MultiIndex.from_product([sorted(tl["Thoi_diem"].unique()), list(MAU)], names=["Thoi_diem", "Ket_qua"])
    tl = tl.groupby(["Thoi_diem", "Ket_qua"]).size().reindex(luoi, fill_value=0).reset_index(name="So_luong")
    chart = alt.Chart(tl).mark_area(interpolate="monotone", opacity=0.85, line={"strokeWidth": 1.5}).encode(
        x=alt.X("Thoi_diem:T", title=None, axis=alt.Axis(format="%H:%M:%S", labelAngle=0, tickCount=6)),
        y=alt.Y("So_luong:Q", title="Luồng mỗi 10 giây", stack=True),
        color=alt.Color("Ket_qua:N", scale=alt.Scale(domain=list(MAU), range=list(MAU.values())),
                        legend=alt.Legend(title=None, orient="top-left", labelColor=gd.MAU_CHU_PHU, symbolType="circle")),
        order=alt.Order("Ket_qua:N", sort="descending"),
        tooltip=[alt.Tooltip("Thoi_diem:T", title="Thời điểm", format="%H:%M:%S"),
                 alt.Tooltip("Ket_qua:N", title="Kết quả"), alt.Tooltip("So_luong:Q", title="Số luồng")])
    st.altair_chart(bieu_do(chart, 200), use_container_width=True)

    # ---- Tom tat theo nguon -> dich ----
    canh_bao = kq[kq["Ket_qua"] == KQ_TAN_CONG]
    html('<div class="tieu-de-nho">Cảnh báo gộp theo nguồn và đích</div>')
    if canh_bao.empty:
        html('<p class="ghi-chu">Chưa có luồng nào bị đánh dấu Tấn công.</p>')
    else:
        cb = canh_bao.assign(IP_nguon=canh_bao["Nguon"].str.rsplit(":", n=1).str[0])
        g = (cb.groupby(["IP_nguon", "Dich", "Giao_thuc"])
             .agg(So_luong=("Dich", "size"), Xs=("Xac_suat_tan_cong", "mean"), Cuoi=("Ket_thuc", "max"))
             .reset_index().sort_values(["So_luong", "Cuoi"], ascending=False).head(15))
        g["Gio"] = _gio(g["Cuoi"])
        html(gd.bang([("IP nguồn", ""), ("Đích", ""), ("Giao thức", "mo"), ("Số luồng", "so"),
                      ("Xác suất trung bình", "html"), ("Lần cuối", "mo")],
                     [[r.IP_nguon, r.Dich, r.Giao_thuc, f"{r.So_luong:,}", gd.thanh_xac_suat(r.Xs), r.Gio]
                      for r in g.itertuples()]))

    # ---- Luong gan nhat ----
    tat_ca = st.toggle("Hiện cả luồng bình thường", key="tt_tat_ca")
    v = kq if tat_ca else canh_bao
    v = v.sort_values("Ket_thuc", ascending=False).head(100)
    html(f'<div class="tieu-de-nho">{"Luồng gần nhất" if tat_ca else "Luồng bị đánh dấu Tấn công gần nhất"}</div>')
    if v.empty:
        html('<p class="ghi-chu">Không có luồng nào để hiển thị.</p>')
        return
    html(gd.bang([("Thời điểm", "mo"), ("Kết quả", "html"), ("Xác suất tấn công", "html"), ("Nguồn", ""),
                  ("Đích", ""), ("Giao thức", "mo"), ("Số gói", "so")],
                 [[t, gd.nhan_ket_qua(k), gd.thanh_xac_suat(p), n, d, gt, f"{sg:,}"]
                  for t, k, p, n, d, gt, sg in zip(_gio(v["Ket_thuc"]), v["Ket_qua"], v["Xac_suat_tan_cong"],
                                                    v["Nguon"], v["Dich"], v["Giao_thuc"], v["So_goi"])]))
    html('<p class="ghi-chu">Hiển thị tối đa 100 luồng mới nhất. Dừng giám sát để xuất toàn bộ.</p>')


def hien_thi(MH, nguong, html, bieu_do, MAU):
    gs = st.session_state.get("giam_sat")
    dang_chay = gs is not None and gs.dang_chay
    html('<p class="ghi-chu">Chế độ thử nghiệm: bắt gói tin đi qua máy tính này, gom thành luồng và tính đặc trưng '
         'theo cách của CICFlowMeter. Mô hình học trên mạng phòng thí nghiệm năm 2017 nên trên mạng thật có thể '
         'báo nhầm. Chỉ giám sát mạng của bạn hoặc mạng bạn được phép giám sát.</p>')

    html(gd.buoc(1, "Chọn card mạng", "Wi-Fi, dây mạng, hoặc cả hai"))
    ok, huong_dan, cach_bat = kiem_tra_moi_truong()
    if not ok:
        html(gd.danh_sach_kiem_tra([("loi", huong_dan)]))
        return
    try:
        cards = _cac_card(cach_bat)
    except Exception as ex:
        html(gd.danh_sach_kiem_tra([("loi", f"Không liệt kê được card mạng: {ex}")]))
        return
    if not cards:
        html(gd.danh_sach_kiem_tra([("loi", "Không tìm thấy card mạng nào.")]))
        return
    nhan = {c["id"]: c["nhan"] for c in cards}
    mac_dinh = [c["id"] for c in cards if c["co_ip"] and c["loai"] in ("Wi-Fi", "Dây mạng")][:2] or [cards[0]["id"]]
    c0, c1, c2 = st.columns([3, 1, 1], vertical_alignment="bottom")
    chon = c0.multiselect("Card mạng cần giám sát", list(nhan), default=[i for i in mac_dinh if i in nhan],
                          format_func=lambda i: nhan[i], disabled=dang_chay,
                          help="Card đang kết nối có địa chỉ IP. Có thể chọn cùng lúc Wi-Fi và dây mạng.")
    if not dang_chay:
        if c1.button("Bắt đầu", type="primary", disabled=not chon, use_container_width=True):
            gs = GiamSat(MH["pipeline"], MH["input_features"])
            gs.bat_dau(chon, [nhan[i] for i in chon])
            st.session_state["giam_sat"] = gs
            st.rerun()
        if gs is not None and c2.button("Xóa kết quả", use_container_width=True):
            del st.session_state["giam_sat"]
            st.rerun()
    else:
        if c1.button("Dừng", type="primary", use_container_width=True):
            with st.spinner("Đang đánh giá nốt các luồng còn mở..."):
                gs.dung()
            st.rerun()
    html(f'<p class="ghi-chu">{"Đọc gói tin bằng Npcap (IPv4 và IPv6)." if cach_bat == "npcap" else "Đọc gói tin bằng raw socket có sẵn của Windows (chỉ IPv4), không cần cài thêm. Nếu Windows Firewall hỏi quyền, chọn Allow."}</p>')
    if gs is None:
        return

    html(gd.buoc(2, "Theo dõi", them_html=gd.trang_thai(
        gs.dang_chay, ("Đang giám sát " if gs.dang_chay else "Đã dừng, ") + ", ".join(gs.card))))
    st.fragment(run_every=2 if gs.dang_chay else None)(_ve)(gs, nguong, html, bieu_do, MAU)

    html(gd.buoc(3, "Xuất kết quả"))
    if gs.dang_chay:
        html('<p class="ghi-chu">Dừng giám sát để xuất toàn bộ kết quả.</p>')
        return
    kq = gs.anh_chup()["ket_qua"]
    if kq.empty:
        html('<p class="ghi-chu">Không có luồng nào để xuất.</p>')
        return
    kq.insert(0, "Ket_qua", _gan_nhan(kq, nguong))
    for c in ("Bat_dau", "Ket_thuc"):
        kq[c] = _gio(kq[c], "%Y-%m-%d %H:%M:%S.%f")
    ten = f"live_monitor_{datetime.fromtimestamp(gs.t_bat_dau):%Y%m%d_%H%M%S}"
    st.download_button(f"Tải file CSV ({len(kq):,} luồng, kèm 82 đặc trưng)",
                       kq.to_csv(index=False).encode("utf-8-sig"), f"{ten}.csv", "text/csv", type="primary")
