"""Doc, KIEM TRA va DU DOAN cho ung dung. Tach rieng khoi giao dien de kiem thu tu dong duoc.
Nguyen tac: ung dung CHI AP DUNG day chuyen da hoc tren train, KHONG hoc lai gi tu file nguoi dung."""
import io
import re
import numpy as np
import pandas as pd

KQ_TAN_CONG, KQ_BINH_THUONG, KQ_THIEU = "Tấn công", "Bình thường", "Không đủ dữ liệu"
GIOI_HAN_MB = 1024                       # dung luong toi da cua file CSV
TEN_DAU_PHAN_CACH = {",": "dấu phẩy (,)", ";": "dấu chấm phẩy (;)", "\t": "dấu Tab", "|": "dấu gạch đứng (|)"}


def chuan_hoa_ten(ten):
    """So khop ten cot khong phan biet hoa/thuong, khoang trang, gach duoi: 'flow_duration' == 'Flow Duration'."""
    return re.sub(r"[\s_]+", "", str(ten)).lower()


def _doan_dau_phan_cach(dong_dau):
    """Chon dau phan cach xuat hien nhieu nhat o dong tieu de (mac dinh dau phay)."""
    dem = {d: dong_dau.count(d) for d in TEN_DAU_PHAN_CACH}
    tot = max(dem, key=dem.get)
    return tot if dem[tot] > 0 else ","


def doc_csv(nguon, gioi_han_mb=GIOI_HAN_MB):
    """Doc file CSV. Tra ve (DataFrame, None) neu doc duoc, hoac (None, thong_bao_loi).
    Ghi chu cho nguoi dung (vd: da tu nhan dang dau phan cach) nam o df.attrs['ghi_chu']."""
    if hasattr(nguon, "getvalue"):
        raw = nguon.getvalue()
    elif isinstance(nguon, (bytes, bytearray)):
        raw = bytes(nguon)
    else:
        with open(nguon, "rb") as f:
            raw = f.read()
    if len(raw) > gioi_han_mb * 1024 * 1024:
        return None, (f"File quá lớn: {len(raw) / 2**20:,.0f} MB, vượt giới hạn {gioi_han_mb:,} MB. "
                      "Hãy chia file thành nhiều phần nhỏ hơn.")
    if len(raw.strip()) == 0:
        return None, "File rỗng: không có nội dung nào."
    if b"\x00" in raw[:4096]:
        return None, ("File không phải dạng văn bản CSV (có thể là file Excel hoặc file nén bị đổi đuôi). "
                      "Hãy mở bằng Excel và lưu lại dạng 'CSV UTF-8'.")
    df, dau = None, ","
    for enc in ("utf-8-sig", "latin-1"):
        try:
            dong_dau = raw.decode(enc).splitlines()[0]
            dau = _doan_dau_phan_cach(dong_dau)
            df = pd.read_csv(io.BytesIO(raw), low_memory=False, encoding=enc, sep=dau)
            break
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            return None, "File rỗng: không có dòng tiêu đề hoặc dữ liệu."
        except pd.errors.ParserError as e:
            return None, f"Không đọc được file dạng CSV (số cột giữa các dòng không khớp): {str(e)[:200]}"
    if df is None:
        return None, "Không đọc được file: bảng mã ký tự không hợp lệ. Hãy lưu lại file dạng 'CSV UTF-8'."
    if len(df) == 0:
        return None, "File chỉ có dòng tiêu đề, không có dòng dữ liệu nào."
    df.attrs["ghi_chu"] = ([f"Đã tự nhận dạng file dùng {TEN_DAU_PHAN_CACH[dau]} để phân cách cột."]
                           if dau != "," else [])
    return df, None


def kiem_tra(df, input_features):
    """Kiem tra du lieu nguoi dung. Tra ve dict:
    ok, loi[], canh_bao[], X (dung thu tu cot mo hinh), hop_le (mask dong du dieu kien du doan),
    ly_do (Series ly do cho dong khong hop le), nhan (Series hoac None), thong_ke{} (gom loi_theo_cot)."""
    kq = {"ok": False, "loi": [], "canh_bao": list(df.attrs.get("ghi_chu", [])), "X": None, "hop_le": None,
          "ly_do": None, "nhan": None, "thong_ke": {"so_dong": len(df), "so_cot": df.shape[1]}}

    # 1. Ten cot: bo khoang trang thua; so khop linh hoat
    df = df.rename(columns=lambda c: str(c).strip())
    ban_do = {}
    for c in df.columns:
        k = chuan_hoa_ten(c)
        if k in ban_do:
            kq["canh_bao"].append(f"Cột bị lặp tên: '{ban_do[k]}' và '{c}'. Dùng cột xuất hiện trước.")
        else:
            ban_do[k] = c
    thieu = [f for f in input_features if chuan_hoa_ten(f) not in ban_do]
    if thieu:
        kq["loi"].append(f"Thiếu {len(thieu)}/{len(input_features)} cột mà mô hình cần: " + ", ".join(thieu))
        return kq

    # 2. Cot nhan (neu co) va cot thua. Cot nhan KHONG BAO GIO duoc dua vao X.
    cot_nhan = ban_do.get("label")
    if cot_nhan is not None:
        kq["nhan"] = df[cot_nhan].fillna("").astype(str).str.strip()
    can = {chuan_hoa_ten(f) for f in input_features} | {"label"}
    thua = [c for c in df.columns if chuan_hoa_ten(c) not in can]
    if thua:
        kq["canh_bao"].append(f"Bỏ qua {len(thua)} cột không dùng đến: " + ", ".join(map(str, thua[:15]))
                              + (" ..." if len(thua) > 15 else ""))

    # 3. Lay dung cac cot, dung thu tu, ep ve so; dem loi theo tung cot
    X = pd.DataFrame({f: df[ban_do[chuan_hoa_ten(f)]] for f in input_features})
    loi_theo_cot = {}
    for c in X.columns:
        trong_goc = X[c].isna()
        so = pd.to_numeric(X[c], errors="coerce")
        chu = int((~trong_goc & so.isna()).sum())
        v = so.to_numpy(dtype="float64")
        inf = int(np.isinf(v).sum())
        trong = int(trong_goc.sum())
        X[c] = so.replace([np.inf, -np.inf], np.nan)
        if chu or inf or trong:
            loi_theo_cot[c] = {"khong_phai_so": chu, "vo_cuc": inf, "trong": trong}
    khong_phai_so = sum(d["khong_phai_so"] for d in loi_theo_cot.values())
    so_vo_cuc = sum(d["vo_cuc"] for d in loi_theo_cot.values())
    so_o_trong = sum(d["trong"] for d in loi_theo_cot.values())
    if khong_phai_so:
        kq["canh_bao"].append(f"Có {khong_phai_so:,} ô chứa chữ/ký tự không phải số → coi như ô trống.")
    if so_vo_cuc:
        kq["canh_bao"].append(f"Có {so_vo_cuc:,} ô chứa giá trị vô cực (inf).")
    if so_o_trong:
        kq["canh_bao"].append(f"Có {so_o_trong:,} ô trống.")
    if loi_theo_cot:
        top = sorted(loi_theo_cot.items(), key=lambda kv: -sum(kv[1].values()))[:5]
        mo_ta = []
        for c, d in top:
            phan = [f"{d['khong_phai_so']:,} ô chữ" if d["khong_phai_so"] else "",
                    f"{d['vo_cuc']:,} ô vô cực" if d["vo_cuc"] else "",
                    f"{d['trong']:,} ô trống" if d["trong"] else ""]
            mo_ta.append(f"{c} ({', '.join(p for p in phan if p)})")
        kq["canh_bao"].append(f"Các cột có lỗi nhiều nhất ({len(loi_theo_cot)} cột có lỗi): " + "; ".join(mo_ta))

    # 4. Cach 1: dong co o trong/vo cuc/chu -> KHONG du doan, danh dau "Khong du du lieu"
    thieu_mask = X.isna()
    hop_le = ~thieu_mask.any(axis=1)
    ly_do = pd.Series("", index=X.index, dtype=object)
    if (~hop_le).any():
        # Xu ly ca bang mot lan (nhanh voi file lon): lay toi da 3 ten cot loi dau tien cua moi dong
        B = thieu_mask.to_numpy()[~hop_le.to_numpy()]
        dem = B.sum(axis=1)
        dau = np.argsort(~B, axis=1, kind="stable")[:, :3]
        ten = np.asarray(X.columns)[dau]
        ly_do[~hop_le] = ["Thiếu/lỗi ở: " + ", ".join(ten[i, :min(d, 3)]) + (" ..." if d > 3 else "")
                          for i, d in enumerate(dem)]
        kq["canh_bao"].append(f"{(~hop_le).sum():,} dòng có ô trống/lỗi/vô cực → đánh dấu '{KQ_THIEU}', "
                              f"không dự đoán.")

    so_trung = int(X.duplicated().sum())
    if so_trung:
        kq["canh_bao"].append(f"Có {so_trung:,} dòng trùng lặp hoàn toàn (vẫn dự đoán bình thường).")
    kq["thong_ke"].update(so_dong_hop_le=int(hop_le.sum()), so_dong_thieu=int((~hop_le).sum()),
                          so_o_khong_phai_so=khong_phai_so, so_o_vo_cuc=so_vo_cuc,
                          so_o_trong=so_o_trong, so_dong_trung=so_trung, loi_theo_cot=loi_theo_cot)
    if hop_le.sum() == 0:
        kq["loi"].append("Không còn dòng nào đủ dữ liệu để dự đoán.")
        return kq

    kq.update(ok=True, X=X, hop_le=hop_le, ly_do=ly_do)
    return kq


def tinh_xac_suat(pipeline, X, hop_le):
    """Phan cham (cham): chi tinh xac suat tan cong tren dong hop le; dong loi la NaN.
    Tach rieng de ung dung chi tinh MOT LAN cho moi file, doi nguong khong can tinh lai."""
    xs = pd.Series(np.nan, index=X.index, dtype="float64")
    if hop_le.any():
        xs[hop_le] = pipeline.predict_proba(X[hop_le])[:, 1]
    return xs


def ap_nguong(xs, nguong):
    """Phan nhanh: tu xac suat + nguong -> DataFrame: Xac_suat_tan_cong, Ket_qua."""
    kq = pd.Series(KQ_THIEU, index=xs.index, dtype=object)
    co = xs.notna()
    kq[co] = np.where(xs[co] >= nguong, KQ_TAN_CONG, KQ_BINH_THUONG)
    return pd.DataFrame({"Xac_suat_tan_cong": xs, "Ket_qua": kq})


def du_doan(pipeline, X, hop_le, nguong):
    """Chi du doan tren dong hop le. Tra ve DataFrame: Xac_suat_tan_cong, Ket_qua."""
    return ap_nguong(tinh_xac_suat(pipeline, X, hop_le), nguong)


def phan_tram(x, so_le=2):
    """Dinh dang ti le cho giao dien; khong tinh duoc (NaN) thi hien '—'."""
    return "—" if x is None or x != x else f"{x * 100:.{so_le}f}%"


def bang_theo_nhan(nhan, ket_qua):
    """Bang theo tung nhan trong file: so dong, so du doan moi loai, ti le du doan dung.
    Benign dung khi du doan Binh thuong; nhan tan cong dung khi du doan Tan cong.
    Nhan 'Attempted' khong tinh ti le (khong thuoc bai toan); dong thieu du lieu khong tinh vao ti le."""
    n = nhan.fillna("").astype(str).str.strip()
    d = pd.DataFrame({"Nhan": n.values, "Ket_qua": np.asarray(ket_qua)})
    bang = pd.crosstab(d["Nhan"], d["Ket_qua"]).reindex(columns=[KQ_TAN_CONG, KQ_BINH_THUONG, KQ_THIEU],
                                                         fill_value=0)
    bang.columns = ["Tan_cong", "Binh_thuong", "Khong_du"]
    bang.insert(0, "So_dong", bang.sum(axis=1))
    la_benign = bang.index.str.lower() == "benign"
    la_attempted = bang.index.str.contains("attempted", case=False)
    bang.insert(0, "Loai", np.where(la_attempted, "Bỏ qua (Attempted)",
                                    np.where(la_benign, "Bình thường", "Tấn công")))
    dung = np.where(la_benign, bang["Binh_thuong"], bang["Tan_cong"])
    co_kq = bang["Tan_cong"] + bang["Binh_thuong"]
    bang["Ti_le_dung"] = np.where((co_kq > 0) & ~la_attempted, dung / co_kq.where(co_kq > 0, 1), np.nan)
    thu_tu = np.select([la_benign, la_attempted], [0, 2], 1)
    bang = bang.assign(_t=thu_tu).sort_values(["_t", "So_dong"], ascending=[True, False]).drop(columns="_t")
    return bang.reset_index()


def danh_gia_voi_nhan(nhan, ket_qua):
    """Neu file co cot Label: so sanh voi du doan. Bo dong 'Attempted' va dong khong du du lieu."""
    n = nhan.str.strip()
    dung_duoc = (~n.str.contains("attempted", case=False)) & (ket_qua != KQ_THIEU)
    if dung_duoc.sum() == 0:
        return None
    y = (n[dung_duoc].str.lower() != "benign").astype(int)
    p = (ket_qua[dung_duoc] == KQ_TAN_CONG).astype(int)
    tp = int(((y == 1) & (p == 1)).sum()); fp = int(((y == 0) & (p == 1)).sum())
    fn = int(((y == 1) & (p == 0)).sum()); tn = int(((y == 0) & (p == 0)).sum())
    tong = tp + fp + fn + tn
    return {"so_dong": tong, "Accuracy": (tp + tn) / tong,
            "Precision": tp / (tp + fp) if tp + fp else float("nan"),
            "Recall": tp / (tp + fn) if tp + fn else float("nan"),
            "F1": 2 * tp / (2 * tp + fp + fn) if tp else 0.0,
            "FPR": fp / (fp + tn) if fp + tn else float("nan"),
            "FNR": fn / (fn + tp) if fn + tp else float("nan"),
            "TP": tp, "FP": fp, "FN": fn, "TN": tn}
