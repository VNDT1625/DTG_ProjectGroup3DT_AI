"""Phan giao dien: mau sac, font, va cac khoi HTML dung chung cho app.py va live_view.py."""
import html as _h

MAU_NEN, MAU_KHUNG, MAU_KHUNG_2, MAU_VIEN = "#121a2b", "#18223a", "#1e2a47", "#2a3858"
MAU_CHU, MAU_CHU_PHU, MAU_MO = "#e6ebf2", "#aab4c8", "#7d8aa3"
MAU_NHAN = "#f2b33d"
MAU_TAN_CONG, MAU_BINH_THUONG, MAU_THIEU = "#ef5b5b", "#3fb9a6", "#7d8aa3"
MAU_THEO_KQ = {"Tấn công": MAU_TAN_CONG, "Bình thường": MAU_BINH_THUONG, "Không đủ dữ liệu": MAU_THIEU}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@500;600&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, textarea, select, [data-testid="stWidgetLabel"] {{
  font-family: 'IBM Plex Sans', system-ui, 'Segoe UI', sans-serif;
}}
[data-testid="stAppViewContainer"] {{
  background:
    radial-gradient(900px 420px at 12% -8%, rgba(242,179,61,.07), transparent 60%),
    radial-gradient(700px 380px at 100% 0%, rgba(63,185,166,.05), transparent 60%),
    radial-gradient(rgba(125,138,163,.10) 1px, transparent 1.2px) 0 0 / 22px 22px,
    {MAU_NEN};
}}
.block-container {{ padding-top: 1.25rem; padding-bottom: 4rem; max-width: 1200px; }}
[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stToolbar"] {{ right: .5rem; }}
[data-testid="stSidebar"] {{ background: {MAU_KHUNG}; border-right: 1px solid {MAU_VIEN}; }}
[data-testid="stSidebar"] h3 {{ font-size: 1rem; font-weight: 600; margin-top: .5rem; }}
:focus-visible {{ outline: 2px solid {MAU_NHAN} !important; outline-offset: 2px; }}

/* ---- Dau trang: dai tin hieu ---- */
.hero {{ position:relative; overflow:hidden; border:1px solid {MAU_VIEN}; border-radius:20px; margin-bottom:1.25rem;
  background: radial-gradient(120% 160% at 0% 0%, rgba(242,179,61,.13), transparent 42%),
              linear-gradient(180deg, {MAU_KHUNG_2} 0%, {MAU_KHUNG} 100%);
  box-shadow: 0 1px 0 rgba(255,255,255,.04) inset, 0 18px 40px -24px rgba(0,0,0,.7); }}
.hero .dong1 {{ display:flex; justify-content:space-between; align-items:center; gap:1rem; flex-wrap:wrap; padding:1.15rem 1.5rem 0; }}
.hero .trai {{ display:flex; align-items:center; gap:1rem; }}
.hero .logo {{ display:grid; place-items:center; width:52px; height:52px; border-radius:14px;
  background: rgba(242,179,61,.08); border:1px solid rgba(242,179,61,.28); }}
.hero h1 {{ font-family:'IBM Plex Sans Condensed', sans-serif; font-size:1.7rem; font-weight:600; letter-spacing:-.01em;
  margin:0; padding:0; color:{MAU_CHU}; line-height:1.1; }}
.hero .phu {{ color:{MAU_CHU_PHU}; font-size:.9rem; margin-top:.25rem; }}
.hero .song {{ display:block; width:100%; height:64px; margin-top:.4rem; }}
.hero .song .nen {{ fill:none; stroke:rgba(242,179,61,.28); stroke-width:1.4; vector-effect:non-scaling-stroke;
  stroke-dasharray:1000; stroke-dashoffset:1000; animation: ve-song 1.8s cubic-bezier(.4,0,.2,1) .1s forwards; }}
.hero .song .xung {{ fill:none; stroke:{MAU_NHAN}; stroke-width:2.4; stroke-linecap:round; vector-effect:non-scaling-stroke;
  stroke-dasharray:55 945; stroke-dashoffset:1000; opacity:0; filter: drop-shadow(0 0 6px rgba(242,179,61,.9));
  animation: chay-xung 6.5s linear 1.9s infinite; }}
.hero .song .xung.do {{ stroke:{MAU_TAN_CONG}; filter: drop-shadow(0 0 6px rgba(239,91,91,.9)); animation-duration:3.2s; }}
@keyframes ve-song {{ to {{ stroke-dashoffset:0; }} }}
@keyframes chay-xung {{ 0% {{ stroke-dashoffset:1000; opacity:0; }} 4% {{ opacity:1; }} 92% {{ opacity:1; }} 100% {{ stroke-dashoffset:0; opacity:0; }} }}
.hero .chi-so {{ display:grid; grid-template-columns:repeat(var(--n), minmax(0,1fr)); border-top:1px solid {MAU_VIEN};
  background: rgba(14,20,36,.35); }}
.hero .chi-so > div {{ padding:.7rem 1.5rem .8rem; border-left:1px solid {MAU_VIEN};
  opacity:0; animation: hien .6s ease-out forwards; }}
.hero .chi-so > div:first-child {{ border-left:none; }}
.hero .chi-so > div:nth-child(1) {{ animation-delay:.9s; }} .hero .chi-so > div:nth-child(2) {{ animation-delay:1.0s; }}
.hero .chi-so > div:nth-child(3) {{ animation-delay:1.1s; }} .hero .chi-so > div:nth-child(4) {{ animation-delay:1.2s; }}
.hero .chi-so > div:nth-child(5) {{ animation-delay:1.3s; }}
.hero .chi-so span {{ display:block; color:{MAU_MO}; font-size:.78rem; }}
.hero .chi-so b {{ font-family:'IBM Plex Sans Condensed', sans-serif; font-weight:600; font-size:1.25rem; color:{MAU_CHU};
  font-variant-numeric: tabular-nums; }}
@keyframes hien {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
.tt-live.san-sang {{ color:{MAU_CHU_PHU}; }}
.tt-live.san-sang i {{ background:{MAU_BINH_THUONG}; box-shadow:0 0 0 3px rgba(63,185,166,.18); }}
@media (max-width: 720px) {{ .hero .chi-so {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
  .hero .chi-so > div {{ border-left:none; border-top:1px solid {MAU_VIEN}; }} .hero h1 {{ font-size:1.4rem; }} }}

/* ---- Chuyen che do (segmented control) ---- */
[data-testid="stButtonGroup"] {{ margin-bottom: .25rem; }}
[data-testid="stBaseButton-segmented_control"], [data-testid="stBaseButton-segmented_controlActive"] {{
  border-radius: 999px !important; padding: .35rem 1.05rem !important; font-weight: 500; }}
[data-testid="stBaseButton-segmented_controlActive"] {{ background: {MAU_NHAN} !important; color: {MAU_NEN} !important;
  border-color: {MAU_NHAN} !important; }}

/* ---- Tieu de buoc ---- */
.buoc {{ display:flex; align-items:center; gap:.7rem; margin: 2rem 0 .85rem; }}
.buoc .so {{ font-family:'IBM Plex Sans Condensed', sans-serif; font-weight:600; font-size:.95rem; color:{MAU_NEN};
  width:1.9rem; height:1.9rem; border-radius:50%; background:{MAU_NHAN}; display:grid; place-items:center;
  box-shadow: 0 0 0 4px rgba(242,179,61,.14), 0 0 18px rgba(242,179,61,.35); }}
.buoc .ten {{ font-size:1.12rem; font-weight:600; color:{MAU_CHU}; }}
.buoc .mo {{ color:{MAU_MO}; font-size:.88rem; }}
.buoc .gach {{ flex:1; height:1px; margin-left:.4rem;
  background: linear-gradient(90deg, rgba(242,179,61,.45), {MAU_VIEN} 35%, transparent); }}

/* ---- Trang thai truc tiep ---- */
.tt-live {{ display:inline-flex; align-items:center; gap:.5rem; padding:.25rem .75rem; border-radius:999px;
  font-size:.85rem; font-weight:500; border:1px solid {MAU_VIEN}; color:{MAU_CHU_PHU}; }}
.tt-live i {{ width:.55rem; height:.55rem; border-radius:50%; background:{MAU_MO}; display:inline-block; }}
.tt-live.on {{ color:{MAU_CHU}; border-color: rgba(239,91,91,.45); background: rgba(239,91,91,.08); }}
.tt-live.on i {{ background:{MAU_TAN_CONG}; animation: nhip 1.6s ease-out infinite; }}
@keyframes nhip {{ 0% {{ box-shadow:0 0 0 0 rgba(239,91,91,.6); }} 100% {{ box-shadow:0 0 0 .55rem rgba(239,91,91,0); }} }}
@media (prefers-reduced-motion: reduce) {{
  .tt-live.on i, .hero .song .xung {{ animation:none !important; opacity:0; }}
  .hero .song .nen {{ animation:none !important; stroke-dashoffset:0; }}
  .hero .chi-so > div, .pq .o, .pq .thanh span {{ animation:none !important; opacity:1; transform:none; }}
}}
.buoc .tt-live.on i {{ animation:none; }}

/* ---- Danh sach kiem tra ---- */
.kt {{ list-style:none; padding:0; margin:0; border:1px solid {MAU_VIEN}; border-radius:12px; overflow:hidden; background:{MAU_KHUNG}; }}
.kt li {{ display:flex; gap:.75rem; align-items:flex-start; padding:.6rem 1rem; border-top:1px solid {MAU_VIEN};
  color:{MAU_CHU}; font-size:.92rem; margin:0; }}
.kt li:first-child {{ border-top:none; }}
.kt .i {{ flex:none; width:1.3rem; height:1.3rem; border-radius:50%; display:grid; place-items:center; font-size:.75rem; font-weight:600; margin-top:.05rem; }}
.kt .ok .i {{ background:rgba(63,185,166,.16); color:{MAU_BINH_THUONG}; }}
.kt .cb .i {{ background:rgba(242,179,61,.16); color:{MAU_NHAN}; }}
.kt .loi .i {{ background:rgba(239,91,91,.16); color:{MAU_TAN_CONG}; }}

/* ---- Dai so lieu ---- */
.sl {{ display:grid; grid-template-columns: repeat(var(--n), minmax(0,1fr)); border:1px solid {MAU_VIEN};
  border-radius:12px; background:{MAU_KHUNG}; margin-bottom: 1rem; }}
.sl > div {{ padding: .85rem 1.1rem; border-left:1px solid {MAU_VIEN}; }}
.sl > div:first-child {{ border-left:none; }}
.sl .t {{ color:{MAU_MO}; font-size:.8rem; }}
.sl .n {{ font-family:'IBM Plex Sans Condensed', sans-serif; font-weight:600; font-size:1.65rem; color:{MAU_CHU}; line-height:1.2; font-variant-numeric: tabular-nums; }}
.sl .p {{ color:{MAU_CHU_PHU}; font-size:.8rem; }}

/* ---- Dai phan quyet ---- */
.pq {{ position:relative; overflow:hidden; background:{MAU_KHUNG}; border:1px solid {MAU_VIEN}; border-radius:18px;
  padding:1.4rem 1.6rem 1.3rem; }}
.pq.co-tc {{ border-color: rgba(239,91,91,.40);
  background: radial-gradient(90% 140% at 0% 100%, rgba(239,91,91,.10), transparent 55%), {MAU_KHUNG}; }}
.pq.an-toan {{ border-color: rgba(63,185,166,.40);
  background: radial-gradient(90% 140% at 0% 100%, rgba(63,185,166,.10), transparent 55%), {MAU_KHUNG}; }}
.pq .tong {{ display:flex; justify-content:space-between; flex-wrap:wrap; gap:.5rem; color:{MAU_CHU_PHU}; font-size:.9rem; margin-bottom:.85rem; }}
.pq .tong b {{ color:{MAU_CHU}; font-weight:500; }}
.pq .thanh {{ display:flex; height:14px; border-radius:999px; overflow:hidden; gap:3px; background:{MAU_NEN}; }}
.pq .thanh span {{ display:block; min-width:4px; border-radius:999px; transform-origin:left center;
  animation: mo-thanh .9s cubic-bezier(.2,.8,.2,1) both; }}
.pq .thanh span:nth-child(2) {{ animation-delay:.15s; }} .pq .thanh span:nth-child(3) {{ animation-delay:.3s; }}
@keyframes mo-thanh {{ from {{ transform:scaleX(0); opacity:.3; }} to {{ transform:scaleX(1); opacity:1; }} }}
.pq .o {{ animation: hien .5s ease-out both; }}
.pq .o:nth-child(1) {{ animation-delay:.35s; }} .pq .o:nth-child(2) {{ animation-delay:.45s; }} .pq .o:nth-child(3) {{ animation-delay:.55s; }}
.pq .o.tc.co .n {{ color:{MAU_TAN_CONG}; filter: drop-shadow(0 0 14px rgba(239,91,91,.55)); }}
.pq .so-lieu {{ display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:1rem; margin-top:1.1rem; }}
.pq .o .n {{ font-family:'IBM Plex Sans Condensed', sans-serif; font-weight:600; font-size:2.7rem; line-height:1.05; color:{MAU_CHU}; font-variant-numeric: tabular-nums; }}
.pq .o .t {{ display:flex; align-items:center; gap:.45rem; color:{MAU_CHU_PHU}; font-size:.88rem; margin-top:.2rem; }}
.pq .o .t i {{ width:.6rem; height:.6rem; border-radius:3px; display:inline-block; }}

/* ---- Bang tu thiet ke ---- */
.bang {{ border:1px solid {MAU_VIEN}; border-radius:12px; overflow:auto; max-height: 440px; background:{MAU_KHUNG}; }}
.bang table {{ width:100%; border-collapse:collapse; font-size:.88rem; }}
.bang th {{ position:sticky; top:0; background:{MAU_KHUNG_2}; color:{MAU_MO}; font-weight:500; text-align:left;
  padding:.6rem .85rem; border-bottom:1px solid {MAU_VIEN}; white-space:nowrap; z-index:1; }}
.bang td {{ padding:.5rem .85rem; border-bottom:1px solid rgba(42,56,88,.6); color:{MAU_CHU}; white-space:nowrap; }}
.bang tr:last-child td {{ border-bottom:none; }}
.bang tr:hover td {{ background: rgba(255,255,255,.025); }}
.bang .so {{ text-align:right; font-variant-numeric: tabular-nums; }}
.bang .mo {{ color:{MAU_CHU_PHU}; }}
.nhan-kq {{ display:inline-flex; align-items:center; gap:.4rem; padding:.12rem .55rem; border-radius:999px; font-size:.8rem; font-weight:500; }}
.nhan-kq i {{ width:.45rem; height:.45rem; border-radius:50%; display:inline-block; }}
.xs {{ display:flex; align-items:center; gap:.55rem; min-width:150px; }}
.xs .ray {{ flex:1; height:6px; border-radius:999px; background:{MAU_NEN}; overflow:hidden; }}
.xs .ray span {{ display:block; height:100%; border-radius:999px; }}
.xs b {{ font-weight:500; font-variant-numeric: tabular-nums; width:3.2rem; text-align:right; }}

/* ---- Thanh phan Streamlit ---- */
[data-testid="stFileUploaderDropzone"] {{ border:1.5px dashed {MAU_VIEN}; background:{MAU_KHUNG}; border-radius:14px; padding:1.4rem; }}
[data-testid="stFileUploaderDropzone"]:hover {{ border-color:{MAU_NHAN}; background: rgba(242,179,61,.05); }}
[data-testid="stFileUploaderDropzone"] {{ transition: border-color .2s, background .2s; }}
[data-testid="stDataFrame"] {{ border:1px solid {MAU_VIEN}; border-radius:12px; overflow:hidden; }}
.stTabs [role="tablist"] {{ gap:.25rem; border-bottom:1px solid {MAU_VIEN}; }}
.stTabs [data-testid="stTab"] {{ padding:.55rem .95rem; }}
.stDownloadButton button, .stButton button {{ border-radius:10px; font-weight:500; min-height:2.7rem;
  transition: transform .12s ease, box-shadow .2s ease; }}
.stDownloadButton button:active, .stButton button:active {{ transform: translateY(1px) scale(.99); }}
.stDownloadButton button[kind="primary"], .stButton button[kind="primary"] {{
  box-shadow: 0 6px 22px -8px rgba(242,179,61,.65); }}
.stTabs [data-testid="stTab"][aria-selected="true"] {{ color:{MAU_NHAN} !important; }}
[data-testid="stVegaLiteChart"] {{ background:{MAU_KHUNG}; border:1px solid {MAU_VIEN}; border-radius:12px; padding:.75rem .75rem .25rem; }}
.ghi-chu {{ color:{MAU_MO}; font-size:.85rem; line-height:1.5; max-width:80ch; }}
.tieu-de-nho {{ color:{MAU_CHU}; font-weight:600; font-size:.98rem; margin:1.25rem 0 .55rem; }}
@media (max-width: 720px) {{ .pq .so-lieu {{ grid-template-columns:1fr; }} .sl {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
  .sl > div:nth-child(3) {{ border-left:none; }} .sl > div:nth-child(n+3) {{ border-top:1px solid {MAU_VIEN}; }} }}
/* =================== LOP 2: dong bo toan trang theo chu de "tin hieu" =================== */
/* ---- Chuyen che do: ray vien tron, nut dang chon sang vang ---- */
[data-testid="stButtonGroup"] {{ display:inline-flex; padding:5px; gap:4px; border-radius:999px;
  background: rgba(14,20,36,.65); border:1px solid {MAU_VIEN}; box-shadow: inset 0 1px 6px rgba(0,0,0,.35); }}
button[data-variant='segmented_control'] {{ border-radius:999px !important; border:1px solid transparent !important;
  background: transparent !important; color:{MAU_CHU_PHU} !important; padding:.45rem 1.25rem !important;
  font-weight:500 !important; transition: color .2s, background .25s, box-shadow .25s; }}
button[data-variant='segmented_control']:not([data-selected]):hover {{ color:{MAU_CHU} !important;
  background: rgba(255,255,255,.04) !important; }}
button[data-variant='segmented_control'][data-selected] {{ color:#1a1406 !important;
  background: linear-gradient(135deg, #f7c869 0%, {MAU_NHAN} 55%, #e29a22 100%) !important;
  box-shadow: 0 4px 18px -4px rgba(242,179,61,.7), inset 0 1px 0 rgba(255,255,255,.35); }}

/* ---- Tieu de buoc: gach noi ve ra khi buoc xuat hien ---- */
.buoc .gach {{ transform-origin:left; animation: ve-gach .9s cubic-bezier(.4,0,.2,1) both; }}
@keyframes ve-gach {{ from {{ transform:scaleX(0); }} to {{ transform:scaleX(1); }} }}

/* ---- Trang chua co file: quy trinh 4 buoc noi bang mot dai tin hieu ---- */
.qt {{ position:relative; margin-top:1.4rem; padding:1.4rem 1.2rem 1.2rem; border:1px solid {MAU_VIEN}; border-radius:18px;
  background: linear-gradient(180deg, rgba(30,42,71,.55), rgba(24,34,58,.35)); }}
.qt .tieu {{ color:{MAU_CHU_PHU}; font-size:.88rem; margin:0 0 1rem .2rem; }}
.qt .hang {{ position:relative; display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1rem; }}
.qt .day {{ position:absolute; left:12%; right:12%; top:27px; height:2px; background:{MAU_VIEN}; overflow:hidden; border-radius:2px; }}
.qt .day::after {{ content:""; position:absolute; top:0; left:-20%; width:20%; height:100%;
  background: linear-gradient(90deg, transparent, {MAU_NHAN}, transparent); animation: chay-day 3.2s ease-in-out infinite; }}
@keyframes chay-day {{ from {{ left:-20%; }} to {{ left:100%; }} }}
.qt .b {{ position:relative; text-align:center; padding:0 .4rem; animation: noi-len .6s cubic-bezier(.2,.8,.2,1) both; }}
.qt .b:nth-child(2) {{ animation-delay:.08s; }} .qt .b:nth-child(3) {{ animation-delay:.16s; }}
.qt .b:nth-child(4) {{ animation-delay:.24s; }} .qt .b:nth-child(5) {{ animation-delay:.32s; }}
.qt .b .ic {{ width:56px; height:56px; margin:0 auto .7rem; border-radius:16px; display:grid; place-items:center;
  background:{MAU_KHUNG_2}; border:1px solid {MAU_VIEN}; color:{MAU_NHAN}; position:relative; z-index:1;
  box-shadow: 0 10px 24px -14px rgba(0,0,0,.8); }}
.qt .b .ic svg {{ width:26px; height:26px; }}
.qt .b b {{ display:block; color:{MAU_CHU}; font-weight:600; font-size:.95rem; }}
.qt .b span {{ display:block; color:{MAU_MO}; font-size:.82rem; margin-top:.2rem; line-height:1.4; }}
.qt .mau {{ display:flex; flex-wrap:wrap; gap:.5rem; align-items:center; margin-top:1.3rem; padding-top:1rem;
  border-top:1px dashed {MAU_VIEN}; color:{MAU_MO}; font-size:.85rem; }}
.qt .mau code {{ background: rgba(242,179,61,.08); color:#f6cd7a; border:1px solid rgba(242,179,61,.22);
  border-radius:999px; padding:.15rem .65rem; font-size:.8rem; }}
@keyframes noi-len {{ from {{ opacity:0; transform: translateY(10px); }} to {{ opacity:1; transform:none; }} }}
@media (max-width: 720px) {{ .qt .hang {{ grid-template-columns:repeat(2,minmax(0,1fr)); row-gap:1.4rem; }} .qt .day {{ display:none; }} }}

/* ---- Khung tai file: vien sang, quet sang khi re chuot ---- */
[data-testid="stFileUploaderDropzone"] {{ position:relative; overflow:hidden; min-height:110px; padding:1.6rem 1.6rem !important;
  border:1.5px dashed rgba(242,179,61,.35) !important; border-radius:18px !important;
  background: radial-gradient(120% 120% at 50% 0%, rgba(242,179,61,.07), transparent 60%), {MAU_KHUNG} !important; }}
[data-testid="stFileUploaderDropzone"]::after {{ content:""; position:absolute; inset:0; pointer-events:none;
  background: linear-gradient(100deg, transparent 30%, rgba(242,179,61,.10) 50%, transparent 70%);
  transform: translateX(-100%); }}
[data-testid="stFileUploaderDropzone"]:hover {{ border-color:{MAU_NHAN} !important;
  box-shadow: 0 0 0 4px rgba(242,179,61,.08), 0 14px 34px -18px rgba(242,179,61,.5); }}
[data-testid="stFileUploaderDropzone"]:hover::after {{ animation: quet 1.4s ease-in-out infinite; }}
@keyframes quet {{ to {{ transform: translateX(100%); }} }}
[data-testid="stFileUploaderDropzone"] button {{ border-radius:12px !important; border:1px solid rgba(242,179,61,.45) !important;
  color:{MAU_NHAN} !important; background: rgba(242,179,61,.06) !important; }}

/* ---- Danh sach kiem tra: tung dong hien ra, bieu tuong bat len ---- */
.kt li {{ animation: vao .45s cubic-bezier(.2,.8,.2,1) both; }}
.kt li:nth-child(2) {{ animation-delay:.07s; }} .kt li:nth-child(3) {{ animation-delay:.14s; }}
.kt li:nth-child(4) {{ animation-delay:.21s; }} .kt li:nth-child(5) {{ animation-delay:.28s; }}
.kt li:nth-child(n+6) {{ animation-delay:.35s; }}
.kt .i {{ animation: bat .5s cubic-bezier(.3,1.6,.5,1) both; animation-delay:inherit; }}
.kt li.ok {{ box-shadow: inset 3px 0 0 rgba(63,185,166,.65); }}
.kt li.cb {{ box-shadow: inset 3px 0 0 rgba(242,179,61,.75); }}
.kt li.loi {{ box-shadow: inset 3px 0 0 rgba(239,91,91,.8); background: rgba(239,91,91,.05); }}
@keyframes vao {{ from {{ opacity:0; transform: translateX(-8px); }} to {{ opacity:1; transform:none; }} }}
@keyframes bat {{ 0% {{ transform: scale(0); }} 100% {{ transform: scale(1); }} }}

/* ---- Dai phan quyet: nhan ket luan co nhip dap ---- */
.pq .ket-luan {{ display:inline-flex; align-items:center; gap:.5rem; font-weight:600; font-size:.82rem;
  padding:.28rem .8rem; border-radius:999px; margin-bottom:1rem; }}
.pq .ket-luan i {{ width:.55rem; height:.55rem; border-radius:50%; display:inline-block; }}
.pq.co-tc .ket-luan {{ color:#ff9a9a; background: rgba(239,91,91,.12); border:1px solid rgba(239,91,91,.35); }}
.pq.co-tc .ket-luan i {{ background:{MAU_TAN_CONG}; animation: nhip 1.6s ease-out infinite; }}
.pq.an-toan .ket-luan {{ color:#7fe0cf; background: rgba(63,185,166,.12); border:1px solid rgba(63,185,166,.35); }}
.pq.an-toan .ket-luan i {{ background:{MAU_BINH_THUONG}; }}
.pq .thanh {{ height:16px; box-shadow: inset 0 1px 3px rgba(0,0,0,.4); }}
.pq .thanh span {{ position:relative; overflow:hidden; }}
.pq .thanh span::after {{ content:""; position:absolute; inset:0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.35), transparent);
  transform: translateX(-100%); animation: quet 1.2s ease-out 1s 1 both; }}

/* ---- Dai so lieu: vach mau tren dau + thanh ti le chay ra ---- */
.sl {{ overflow:hidden; border-radius:16px; }}
.sl > div {{ position:relative; animation: noi-len .5s cubic-bezier(.2,.8,.2,1) both; }}
.sl > div:nth-child(2) {{ animation-delay:.06s; }} .sl > div:nth-child(3) {{ animation-delay:.12s; }}
.sl > div:nth-child(4) {{ animation-delay:.18s; }} .sl > div:nth-child(5) {{ animation-delay:.24s; }}
.sl > div:nth-child(6) {{ animation-delay:.30s; }}
.sl > div::before {{ content:""; position:absolute; left:1.1rem; right:1.1rem; top:0; height:2px; border-radius:2px;
  background: var(--mau, {MAU_VIEN}); opacity:.85; }}
.sl .ray {{ height:4px; border-radius:999px; background: rgba(14,20,36,.8); margin-top:.55rem; overflow:hidden; }}
.sl .ray span {{ display:block; height:100%; border-radius:999px; background: var(--mau, {MAU_NHAN});
  transform-origin:left; animation: mo-thanh 1.1s cubic-bezier(.2,.8,.2,1) .25s both; }}

/* ---- Tab: dang vien thuoc, tab chon noi len ---- */
.stTabs [role="tablist"] {{ gap:4px; border-bottom:none !important; padding:4px; border-radius:14px;
  background: rgba(14,20,36,.55); border:1px solid {MAU_VIEN} !important; width:fit-content; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none !important; }}
.stTabs [data-testid="stTab"] {{ border-radius:10px !important; padding:.5rem 1rem !important; height:auto !important;
  color:{MAU_CHU_PHU} !important; transition: background .2s, color .2s; }}
.stTabs [data-testid="stTab"]:hover {{ color:{MAU_CHU} !important; background: rgba(255,255,255,.04); }}
.stTabs [data-testid="stTab"][aria-selected="true"] {{ background:{MAU_KHUNG_2} !important; color:{MAU_NHAN} !important;
  box-shadow: 0 1px 0 rgba(255,255,255,.05) inset, 0 6px 16px -10px rgba(0,0,0,.9); }}
.stTabs [data-testid="stTabPanel"] {{ padding-top:1rem; animation: hien .35s ease-out; }}

/* ---- Nut phu: vien sang vang khi re chuot ---- */
.stDownloadButton button[kind="secondary"], .stButton button[kind="secondary"] {{
  background: {MAU_KHUNG} !important; border:1px solid {MAU_VIEN} !important; }}
.stDownloadButton button[kind="secondary"]:hover, .stButton button[kind="secondary"]:hover {{
  border-color: rgba(242,179,61,.6) !important; color:{MAU_NHAN} !important;
  box-shadow: 0 0 0 3px rgba(242,179,61,.08), 0 10px 26px -16px rgba(242,179,61,.6); }}
.stDownloadButton button[kind="primary"], .stButton button[kind="primary"] {{ color:#1a1406 !important;
  background: linear-gradient(135deg, #f7c869 0%, {MAU_NHAN} 55%, #e29a22 100%) !important; border:none !important; }}
.stDownloadButton button[kind="primary"]:hover, .stButton button[kind="primary"]:hover {{
  box-shadow: 0 10px 30px -8px rgba(242,179,61,.85); filter: brightness(1.05); }}

/* ---- Thanh ben ---- */
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, {MAU_KHUNG_2} 0%, {MAU_KHUNG} 40%) !important; }}
[data-testid="stSidebar"] h3 {{ display:flex; align-items:center; gap:.55rem; }}
[data-testid="stSidebar"] h3::before {{ content:""; width:4px; height:1em; border-radius:2px; background:{MAU_NHAN};
  box-shadow: 0 0 10px rgba(242,179,61,.7); }}
[data-baseweb="slider"] [role="slider"] {{ box-shadow: 0 0 0 5px rgba(242,179,61,.18), 0 0 14px rgba(242,179,61,.6) !important; }}

/* ---- Bang du lieu, bieu do, thong bao ---- */
[data-testid="stDataFrame"], [data-testid="stVegaLiteChart"], .bang {{ border-radius:16px !important;
  box-shadow: 0 16px 36px -26px rgba(0,0,0,.9); }}
[data-testid="stAlert"] {{ border-radius:14px; animation: noi-len .4s ease-out both; }}
code {{ border-radius:6px; }}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation-duration:.001s !important; animation-iteration-count:1 !important; transition:none !important; }}
  .hero .song .xung, .qt .day::after {{ display:none; }}
}}
/* =================== LOP 3: hieu ung "trung tam giam sat" =================== */
@property --goc {{ syntax:'<angle>'; inherits:false; initial-value:0deg; }}

/* ---- Nen: cuc quang troi cham phia sau toan trang ---- */
[data-testid="stAppViewContainer"]::before {{ content:""; position:fixed; inset:-25%; pointer-events:none; z-index:0;
  background:
    radial-gradient(38% 32% at 22% 18%, rgba(242,179,61,.10), transparent 70%),
    radial-gradient(34% 30% at 82% 26%, rgba(63,185,166,.09), transparent 70%),
    radial-gradient(40% 34% at 60% 88%, rgba(110,92,230,.08), transparent 70%);
  animation: troi 28s ease-in-out infinite alternate; }}
@keyframes troi {{ 0% {{ transform: translate3d(0,0,0) rotate(0deg); }} 50% {{ transform: translate3d(4%,-3%,0) rotate(6deg); }}
  100% {{ transform: translate3d(-3%,3%,0) rotate(-4deg); }} }}
[data-testid="stAppViewContainer"] > * {{ position:relative; z-index:1; }}

/* ---- Dau trang: mang luoi nut lap lanh, vach quet, logo co vong sang xoay ---- */
.hero {{ isolation:isolate; }}
.hero .mang {{ position:absolute; right:0; top:0; width:58%; height:100%; z-index:-1; opacity:.55;
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 35%); mask-image: linear-gradient(90deg, transparent, #000 35%); }}
.hero .mang line {{ stroke: rgba(170,180,200,.16); stroke-width:1; }}
.hero .mang circle {{ fill:{MAU_CHU_PHU}; animation: lap-lanh 3.6s ease-in-out infinite; }}
.hero .mang circle.v {{ fill:{MAU_NHAN}; }}
@keyframes lap-lanh {{ 0%,100% {{ opacity:.25; }} 50% {{ opacity:1; }} }}
.hero::after {{ content:""; position:absolute; top:0; bottom:0; width:30%; left:-30%; z-index:-1; pointer-events:none;
  background: linear-gradient(90deg, transparent, rgba(242,179,61,.07), transparent);
  animation: quet-hero 9s ease-in-out 2.4s infinite; }}
@keyframes quet-hero {{ 0% {{ left:-30%; }} 45%,100% {{ left:110%; }} }}
.hero .logo {{ position:relative; isolation:isolate; border:none !important; background:none !important; }}
.hero .logo::before {{ content:""; position:absolute; inset:-1.5px; border-radius:15.5px; z-index:-2;
  background: conic-gradient(from var(--goc), rgba(242,179,61,.15) 0 62%, {MAU_NHAN} 80%, rgba(242,179,61,.15) 95%);
  animation: xoay 4.5s linear infinite; }}
.hero .logo::after {{ content:""; position:absolute; inset:0; border-radius:14px; z-index:-1;
  background: radial-gradient(circle at 50% 35%, #2a3352, #1a2238); }}
@keyframes xoay {{ to {{ --goc: 360deg; }} }}
.hero h1 {{ background: linear-gradient(90deg, {MAU_CHU} 0%, {MAU_CHU} 42%, #ffd88a 50%, {MAU_CHU} 58%, {MAU_CHU} 100%);
  background-size: 260% 100%; background-position: 100% 0; -webkit-background-clip:text; background-clip:text;
  -webkit-text-fill-color: transparent; animation: anh-chu 2.4s ease-in-out .5s both; }}
@keyframes anh-chu {{ from {{ background-position: 100% 0; }} to {{ background-position: 0% 0; }} }}

/* ---- So thu tu buoc: vong song lan ra mot lan ---- */
.buoc .so {{ position:relative; }}
.buoc .so::after {{ content:""; position:absolute; inset:-2px; border-radius:50%; border:2px solid {MAU_NHAN};
  animation: song-lan 1.2s ease-out .2s both; }}
@keyframes song-lan {{ from {{ transform:scale(1); opacity:.9; }} to {{ transform:scale(2.1); opacity:0; }} }}

/* ---- So lieu lon: cuon nhu dong ho co ---- */
.cuon-so {{ display:inline-flex; align-items:flex-start; height:1.15em; line-height:1em; overflow:visible; }}
.cuon-so .c {{ display:inline-block; height:1em; overflow:hidden; }}
.cuon-so .c > span {{ display:flex; flex-direction:column; transform: translateY(calc((10 + var(--d)) * -1em));
  animation: cuon 1.6s cubic-bezier(.15,.85,.25,1) both; animation-delay: var(--tre, 0s); }}
.cuon-so .c > span > i {{ font-style:normal; height:1em; line-height:1em; }}
.cuon-so .phay {{ display:inline-block; }}
@keyframes cuon {{ from {{ transform: translateY(0); }} }}
.pq .o .n {{ line-height:1 !important; height:1em; margin-bottom:.25rem; }}

/* ---- Khung ket qua khi co tan cong: vien do tho nhe + vach quet tu tren xuong ---- */
.pq.co-tc {{ animation: canh-bao 3s ease-in-out 1.2s infinite; }}
@keyframes canh-bao {{ 0%,100% {{ box-shadow: 0 0 0 0 rgba(239,91,91,0); }} 50% {{ box-shadow: 0 0 42px -6px rgba(239,91,91,.42); }} }}
.pq.co-tc::before {{ content:""; position:absolute; left:0; right:0; top:-40%; height:40%; pointer-events:none;
  background: linear-gradient(180deg, transparent, rgba(239,91,91,.10) 70%, rgba(239,91,91,.35) 100%);
  border-bottom: 1px solid rgba(239,91,91,.55); animation: quet-doc 4.5s cubic-bezier(.5,0,.5,1) .8s infinite; }}
@keyframes quet-doc {{ 0% {{ top:-40%; opacity:0; }} 10% {{ opacity:1; }} 70% {{ top:100%; opacity:1; }} 71%,100% {{ top:100%; opacity:0; }} }}
.pq.an-toan {{ box-shadow: 0 0 40px -14px rgba(63,185,166,.5); }}
.pq > * {{ position:relative; }}

@media (prefers-reduced-motion: reduce) {{
  [data-testid="stAppViewContainer"]::before, .hero::after, .pq.co-tc::before, .buoc .so::after {{ display:none; }}
  .cuon-so .c > span, .hero .logo::before, .hero h1, .pq.co-tc, .hero .mang circle {{ animation:none !important; }}
}}
/* =================== LOP 4: kinh mo + neon, bang, bieu do, thanh ben, radar =================== */
/* ---- Kinh mo: cac khung trong suot, thay cuc quang troi phia sau ---- */
.hero, .pq, .sl, .kt, .bang, .qt, .mt, .radar-khung, .dong-ho,
[data-testid="stDataFrame"], [data-testid="stVegaLiteChart"], [data-testid="stFileUploaderDropzone"] {{
  background-color: rgba(24,34,58,.52) !important;
  -webkit-backdrop-filter: blur(16px) saturate(150%); backdrop-filter: blur(16px) saturate(150%);
  border-color: rgba(255,255,255,.09) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.06), 0 20px 44px -28px rgba(0,0,0,.95); }}
[data-testid="stAppViewContainer"]::before {{
  background:
    radial-gradient(36% 30% at 18% 16%, rgba(242,179,61,.16), transparent 70%),
    radial-gradient(32% 30% at 84% 22%, rgba(63,185,166,.15), transparent 70%),
    radial-gradient(40% 34% at 62% 86%, rgba(124,92,255,.13), transparent 70%),
    radial-gradient(28% 26% at 10% 80%, rgba(239,91,91,.08), transparent 70%) !important; }}
/* vien neon chay quanh khung dang chu y (khung ket qua) */
.pq::after {{ content:""; position:absolute; inset:0; border-radius:inherit; padding:1px; pointer-events:none;
  background: conic-gradient(from var(--goc), transparent 0 70%, var(--neon, {MAU_NHAN}) 85%, transparent 100%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude; animation: xoay 6s linear infinite; }}
.pq.co-tc {{ --neon: {MAU_TAN_CONG}; }} .pq.an-toan {{ --neon: {MAU_BINH_THUONG}; }}

/* ---- Bieu do, bang du lieu: noi len khi xuat hien ---- */
[data-testid="stVegaLiteChart"], [data-testid="stDataFrame"] {{ animation: noi-len .6s cubic-bezier(.2,.8,.2,1) both; }}
[data-testid="stVegaLiteChart"] {{ padding: 1rem 1rem .4rem !important; }}

/* ---- Ma tran nham lan dang o nhiet ---- */
.mt {{ border:1px solid {MAU_VIEN}; border-radius:18px; padding:1rem 1.1rem 1.1rem; }}
.mt .luoi {{ display:grid; grid-template-columns: 7.5rem 1fr 1fr; gap:8px; }}
.mt .dau {{ color:{MAU_MO}; font-size:.78rem; display:flex; align-items:center; }}
.mt .dau.cot {{ justify-content:center; text-align:center; }}
.mt .o {{ position:relative; border-radius:14px; padding:.9rem 1rem; min-height:92px; overflow:hidden;
  border:1px solid rgba(255,255,255,.06); animation: noi-len .55s cubic-bezier(.2,.8,.2,1) both; }}
.mt .o:nth-of-type(2) {{ animation-delay:.08s; }} .mt .o:nth-of-type(3) {{ animation-delay:.16s; }} .mt .o:nth-of-type(4) {{ animation-delay:.24s; }}
.mt .o.dung {{ background: linear-gradient(135deg, rgba(63,185,166,var(--a)), rgba(63,185,166,calc(var(--a) * .35))); }}
.mt .o.sai {{ background: linear-gradient(135deg, rgba(239,91,91,var(--a)), rgba(239,91,91,calc(var(--a) * .35))); }}
.mt .o .ten {{ font-size:.75rem; color:{MAU_CHU_PHU}; font-weight:600; }}
.mt .o .n {{ font-family:'IBM Plex Sans Condensed',sans-serif; font-weight:600; font-size:1.9rem; color:{MAU_CHU};
  margin-top:.25rem; line-height:1; height:1em; }}
.mt .o .p {{ font-size:.75rem; color:{MAU_CHU_PHU}; margin-top:.35rem; }}
.mt .o.sai.co {{ box-shadow: 0 0 0 1px rgba(239,91,91,.5), 0 0 24px -6px rgba(239,91,91,.6); }}

/* ---- Thanh ti le nho trong bang ---- */
.tl {{ display:flex; align-items:center; gap:.55rem; justify-content:flex-end; min-width:150px; }}
.tl .ray {{ width:90px; height:6px; border-radius:999px; background: rgba(14,20,36,.9); overflow:hidden; }}
.tl .ray span {{ display:block; height:100%; border-radius:999px; transform-origin:left;
  animation: mo-thanh 1s cubic-bezier(.2,.8,.2,1) .2s both; }}
.tl b {{ font-weight:500; font-variant-numeric: tabular-nums; width:4.2rem; text-align:right; }}
.bang tbody tr {{ animation: vao .4s ease-out both; }}
.bang tbody tr:nth-child(2) {{ animation-delay:.03s; }} .bang tbody tr:nth-child(3) {{ animation-delay:.06s; }}
.bang tbody tr:nth-child(4) {{ animation-delay:.09s; }} .bang tbody tr:nth-child(5) {{ animation-delay:.12s; }}
.bang tbody tr:nth-child(n+6) {{ animation-delay:.15s; }}
.bang tr:hover td {{ background: rgba(242,179,61,.05) !important; }}

/* ---- Thanh ben: kinh mo + dong ho nguong ---- */
[data-testid="stSidebar"] {{ background: rgba(18,26,43,.72) !important;
  -webkit-backdrop-filter: blur(18px); backdrop-filter: blur(18px); border-right:1px solid rgba(255,255,255,.07) !important; }}
[data-testid="stSidebar"] [data-testid="stExpander"] {{ border-radius:12px; border:1px solid {MAU_VIEN};
  background: rgba(14,20,36,.4); }}
.dong-ho {{ border:1px solid {MAU_VIEN}; border-radius:18px; padding:.9rem .9rem .7rem; margin:.4rem 0 .6rem; text-align:center; }}
.dong-ho svg {{ width:100%; height:auto; overflow:visible; }}
.dong-ho .cung {{ stroke-dasharray:1000; stroke-dashoffset:1000; animation: ve-song 1.4s cubic-bezier(.4,0,.2,1) forwards; }}
.dong-ho .kim {{ transform-origin: 100px 100px; animation: lac-kim 1.3s cubic-bezier(.3,1.4,.5,1) .2s both; }}
@keyframes lac-kim {{ from {{ transform: rotate(-90deg); }} }}
.dong-ho .gia-tri {{ font-family:'IBM Plex Sans Condensed',sans-serif; font-weight:600; font-size:2rem; color:{MAU_CHU};
  line-height:1; margin-top:.1rem; text-shadow: 0 0 18px rgba(242,179,61,.45); }}
.dong-ho .che-do {{ display:inline-block; margin-top:.4rem; font-size:.78rem; font-weight:600; padding:.18rem .65rem;
  border-radius:999px; }}
.dong-ho .che-do.nhay {{ color:#ff9a9a; background:rgba(239,91,91,.12); border:1px solid rgba(239,91,91,.35); }}
.dong-ho .che-do.can-bang {{ color:#f6cd7a; background:rgba(242,179,61,.12); border:1px solid rgba(242,179,61,.35); }}
.dong-ho .che-do.it-nham {{ color:#7fe0cf; background:rgba(63,185,166,.12); border:1px solid rgba(63,185,166,.35); }}

/* ---- Radar giam sat truc tiep ---- */
.radar-khung {{ display:grid; grid-template-columns: minmax(240px, 330px) 1fr; gap:1.4rem; align-items:center;
  border:1px solid {MAU_VIEN}; border-radius:20px; padding:1.2rem 1.4rem; margin-bottom:1rem; }}
.radar {{ position:relative; width:100%; aspect-ratio:1; border-radius:50%; overflow:hidden;
  background: radial-gradient(circle, rgba(63,185,166,.10) 0%, rgba(14,20,36,.85) 70%);
  box-shadow: 0 0 0 1px rgba(63,185,166,.35), 0 0 40px -10px rgba(63,185,166,.45), inset 0 0 40px rgba(0,0,0,.6); }}
.radar .vong {{ position:absolute; inset:0; border-radius:50%;
  background: repeating-radial-gradient(circle, transparent 0 calc(25% - 1px), rgba(63,185,166,.22) calc(25% - 1px) 25%); }}
.radar .chu-thap {{ position:absolute; inset:0;
  background: linear-gradient(rgba(63,185,166,.18), rgba(63,185,166,.18)) center/1px 100% no-repeat,
              linear-gradient(rgba(63,185,166,.18), rgba(63,185,166,.18)) center/100% 1px no-repeat; }}
.radar .quet {{ position:absolute; inset:0; border-radius:50%;
  background: conic-gradient(from 0deg, transparent 0 300deg, rgba(63,185,166,.05) 320deg, rgba(63,185,166,.55) 359deg, transparent 360deg);
  animation: quay 4s linear infinite; }}
.radar.canh-bao .quet {{ background: conic-gradient(from 0deg, transparent 0 300deg, rgba(239,91,91,.06) 320deg, rgba(239,91,91,.6) 359deg, transparent 360deg); }}
.radar.canh-bao {{ box-shadow: 0 0 0 1px rgba(239,91,91,.45), 0 0 46px -8px rgba(239,91,91,.55), inset 0 0 40px rgba(0,0,0,.6); }}
@keyframes quay {{ to {{ transform: rotate(360deg); }} }}
.radar .cham {{ position:absolute; width:8px; height:8px; margin:-4px 0 0 -4px; border-radius:50%;
  background:{MAU_BINH_THUONG}; box-shadow:0 0 8px {MAU_BINH_THUONG}; animation: cham-mo 4s linear infinite; }}
.radar .cham.tc {{ width:11px; height:11px; margin:-5.5px 0 0 -5.5px; background:{MAU_TAN_CONG}; box-shadow: 0 0 12px {MAU_TAN_CONG}; }}
.radar .cham.tc::after {{ content:""; position:absolute; inset:-3px; border-radius:50%; border:2px solid {MAU_TAN_CONG};
  animation: song-lan 1.6s ease-out infinite; }}
@keyframes cham-mo {{ 0% {{ opacity:1; transform:scale(1.25); }} 70% {{ opacity:.35; transform:scale(1); }} 100% {{ opacity:1; transform:scale(1.25); }} }}
.radar .tam {{ position:absolute; left:50%; top:50%; width:10px; height:10px; margin:-5px; border-radius:50%;
  background:{MAU_NHAN}; box-shadow: 0 0 14px {MAU_NHAN}; }}
.nhat-ky .tieu {{ color:{MAU_CHU_PHU}; font-size:.85rem; margin-bottom:.6rem; display:flex; justify-content:space-between; }}
.nhat-ky ul {{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:6px; }}
.nhat-ky li {{ display:grid; grid-template-columns: 4.6rem 1fr auto; gap:.7rem; align-items:center; padding:.5rem .75rem;
  border-radius:10px; background: rgba(14,20,36,.45); border:1px solid rgba(255,255,255,.05); font-size:.85rem;
  animation: vao .45s cubic-bezier(.2,.8,.2,1) both; margin:0; }}
.nhat-ky li.tc {{ border-color: rgba(239,91,91,.35); background: linear-gradient(90deg, rgba(239,91,91,.14), rgba(14,20,36,.45)); }}
.nhat-ky li .gio {{ color:{MAU_MO}; font-variant-numeric: tabular-nums; }}
.nhat-ky li .dc {{ color:{MAU_CHU}; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.nhat-ky li .xs {{ min-width:0; font-variant-numeric: tabular-nums; font-weight:600; }}
.nhat-ky .trong {{ color:{MAU_MO}; font-size:.88rem; padding:1rem 0; }}
@media (max-width: 760px) {{ .radar-khung {{ grid-template-columns:1fr; }} .radar {{ max-width:300px; margin:auto; }} }}

@media (prefers-reduced-motion: reduce) {{
  .radar .quet, .radar .cham, .radar .cham.tc::after, .pq::after, .dong-ho .kim {{ animation:none !important; }}
}}
/* ---- Tab ket qua: to, ro rang la nut bam duoc ---- */
.stTabs [role="tablist"] {{ gap:8px !important; padding:6px !important; }}
.stTabs [data-testid="stTab"] {{ padding:.7rem 1.35rem !important; border-radius:12px !important; cursor:pointer;
  border:1px solid rgba(255,255,255,.10) !important; background: rgba(30,42,71,.55) !important;
  transition: transform .15s ease, border-color .2s, box-shadow .2s, background .2s; }}
.stTabs [data-testid="stTab"] p {{ font-size:1.05rem !important; font-weight:600 !important; letter-spacing:.005em; }}
.stTabs [data-testid="stTab"]:hover {{ transform: translateY(-2px); border-color: rgba(242,179,61,.55) !important;
  box-shadow: 0 8px 20px -10px rgba(242,179,61,.55); color:{MAU_CHU} !important; }}
.stTabs [data-testid="stTab"][aria-selected="true"] {{ border-color:{MAU_NHAN} !important; color:{MAU_NHAN} !important;
  background: linear-gradient(180deg, rgba(242,179,61,.20), rgba(242,179,61,.07)) !important;
  box-shadow: 0 0 0 3px rgba(242,179,61,.12), 0 10px 26px -12px rgba(242,179,61,.75) !important; }}
.stTabs [data-testid="stTab"][aria-selected="true"] p {{ color:{MAU_NHAN} !important; }}
.hero h1 {{ font-size:1.55rem !important; line-height:1.2 !important; max-width:none; }}
.hero h1 .dong-td {{ display:block; white-space:nowrap; }}
@media (max-width: 900px) {{ .hero h1 .dong-td {{ display:inline; white-space:normal; }} }}
@media (max-width: 720px) {{ .hero h1 {{ font-size:1.2rem !important; }} }}
/* Streamlit 1.67: tab la [data-testid="stTab"] (khong con data-baseweb) */
.stTabs [role="tablist"] {{ display:inline-flex !important; flex-wrap:wrap; }}
.stTabs [data-testid="stTab"] p {{ font-size:1.12rem !important; font-weight:650 !important; }}
.stTabs [data-testid="stTab"] {{ min-height:3rem; }}
.stTabs [data-testid="stTab"]:not([aria-selected="true"]) p {{ color:{MAU_CHU} !important; }}
.stTabs [data-testid="stTab"]:focus-visible {{ outline:2px solid {MAU_NHAN}; outline-offset:2px; }}
/* ---- Thanh chon cach xem ket qua (3 the lon co bieu tuong) ---- */
.st-key-xem_kq {{ margin: .4rem 0 .9rem; }}
.st-key-xem_kq [data-testid="stButtonGroup"] {{ display:flex !important; width:100%; gap:10px; padding:0;
  background:none; border:none; box-shadow:none; }}
.st-key-xem_kq [data-testid="stButtonGroup"] > div {{ display:flex !important; width:100%; gap:10px; flex-wrap:wrap; }}
.st-key-xem_kq button[data-variant='segmented_control'] {{ flex:1 1 0 !important; min-width:190px;
  min-height:3.6rem; padding:.85rem 1.2rem !important; border-radius:16px !important; justify-content:center;
  border:1px solid rgba(255,255,255,.10) !important; background: rgba(24,34,58,.6) !important;
  -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px);
  color:{MAU_CHU} !important; box-shadow: inset 0 1px 0 rgba(255,255,255,.05), 0 10px 26px -20px rgba(0,0,0,.9);
  transition: transform .16s ease, border-color .2s, box-shadow .25s, background .25s !important; }}
.st-key-xem_kq button[data-variant='segmented_control'] p,
.st-key-xem_kq button[data-variant='segmented_control'] div {{ font-size:1.06rem !important; font-weight:600 !important; }}
.st-key-xem_kq button[data-variant='segmented_control'] [data-testid="stIconMaterial"],
.st-key-xem_kq button[data-variant='segmented_control'] span[translate="no"] {{ font-size:1.45rem !important;
  color:{MAU_MO}; margin-right:.35rem; transition: color .2s, transform .2s; }}
.st-key-xem_kq button[data-variant='segmented_control']:not([data-selected]):hover {{ transform: translateY(-2px);
  border-color: rgba(242,179,61,.5) !important; background: rgba(30,42,71,.75) !important;
  box-shadow: 0 14px 30px -18px rgba(242,179,61,.6) !important; }}
.st-key-xem_kq button[data-variant='segmented_control']:not([data-selected]):hover [data-testid="stIconMaterial"],
.st-key-xem_kq button[data-variant='segmented_control']:not([data-selected]):hover span[translate="no"] {{
  color:{MAU_NHAN}; transform: scale(1.12); }}
.st-key-xem_kq button[data-variant='segmented_control'][data-selected] {{ color:#fff3d9 !important;
  border-color: rgba(242,179,61,.85) !important;
  background: linear-gradient(180deg, rgba(242,179,61,.24) 0%, rgba(242,179,61,.08) 100%) !important;
  box-shadow: inset 0 -3px 0 {MAU_NHAN}, 0 0 0 3px rgba(242,179,61,.10), 0 16px 34px -16px rgba(242,179,61,.75) !important; }}
.st-key-xem_kq button[data-variant='segmented_control'][data-selected] [data-testid="stIconMaterial"],
.st-key-xem_kq button[data-variant='segmented_control'][data-selected] span[translate="no"] {{ color:{MAU_NHAN};
  filter: drop-shadow(0 0 6px rgba(242,179,61,.8)); }}
/* ---- The xem ket qua: luon hien du chu, chia deu chieu ngang ---- */
.st-key-xem_kq [data-testid="stElementContainer"], .st-key-xem_kq [data-testid="stButtonGroup"] {{ width:100% !important; }}
.st-key-xem_kq [data-testid="stButtonGroup"] div:has(> button) {{ display:flex !important; width:100% !important;
  flex-wrap:wrap; gap:10px; }}
.st-key-xem_kq button[data-variant='segmented_control'] {{ flex:1 1 auto !important; width:auto !important;
  max-width:none !important; min-width:fit-content !important; padding:.85rem 1.4rem !important; }}
.st-key-xem_kq button[data-variant='segmented_control'] * {{ overflow:visible !important; text-overflow:clip !important;
  white-space:nowrap !important; max-width:none !important; }}
</style>
"""

LOGO = f"""<svg width="40" height="40" viewBox="0 0 44 44" aria-hidden="true">
<path d="M22 3 L38 9 V21 C38 31 31 38 22 41 C13 38 6 31 6 21 V9 Z" fill="rgba(242,179,61,.10)" stroke="{MAU_NHAN}" stroke-width="2.2" stroke-linejoin="round"/>
<path d="M12 23 H17 L19.5 17 L23 29 L26 20 L28 23 H32" fill="none" stroke="{MAU_CHU}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""


def e(x):
    return _h.escape(str(x))


def _duong_song(w=1200, h=64, seed=7):
    """Duong tin hieu kieu may do: phang, thinh thoang co cum xung (giong goi tin di qua)."""
    import random
    r = random.Random(seed)
    y0 = h * 0.55
    d = [f"M0 {y0:.1f}"]
    x = 0.0
    while x < w:
        x += r.uniform(40, 120)
        if x >= w:
            break
        d.append(f"L{x:.1f} {y0:.1f}")
        for _ in range(r.choice([1, 2, 2, 3])):
            cao = r.uniform(.25, .9) * (h * 0.5)
            x += 5; d.append(f"L{x:.1f} {y0 - cao:.1f}")
            x += 6; d.append(f"L{x:.1f} {y0 + cao * .55:.1f}")
            x += 5; d.append(f"L{x:.1f} {y0:.1f}")
    d.append(f"L{w} {y0:.1f}")
    return " ".join(d)


_SONG = _duong_song()


def _mang_luoi(seed=11, w=700, h=190, so_nut=26):
    """Luoi nut mang mo phia sau dau trang: nut lap lanh lech nhip, noi cac nut gan nhau."""
    import random
    r = random.Random(seed)
    nut = [(r.uniform(10, w - 10), r.uniform(10, h - 10)) for _ in range(so_nut)]
    day = []
    for i, (x1, y1) in enumerate(nut):
        gan = sorted(range(len(nut)), key=lambda j: (nut[j][0] - x1) ** 2 + (nut[j][1] - y1) ** 2)[1:3]
        for j in gan:
            if i < j:
                day.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{nut[j][0]:.0f}" y2="{nut[j][1]:.0f}"/>')
    tron = "".join(f'<circle class="{"v" if k % 7 == 0 else ""}" cx="{x:.0f}" cy="{y:.0f}" r="{2.6 if k % 7 == 0 else 1.7}" '
                   f'style="animation-delay:{r.uniform(0, 3.6):.2f}s"/>' for k, (x, y) in enumerate(nut))
    return (f'<svg class="mang" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
            f'{"".join(day)}{tron}</svg>')


_MANG = _mang_luoi()


def so_cuon(n, tre=0.0):
    """So nguyen hien dang dong ho co: moi chu so cuon tu tren xuong toi dung gia tri (chi bang CSS)."""
    chu = f"{int(n):,}"
    phan, k = [], 0
    for ch in chu:
        if ch.isdigit():
            cot = "".join(f"<i>{d % 10}</i>" for d in range(20))
            phan.append(f'<span class="c"><span style="--d:{ch};--tre:{tre + k * 0.07:.2f}s">{cot}</span></span>')
            k += 1
        else:
            phan.append(f'<span class="phay">{ch}</span>')
    return f'<span class="cuon-so" aria-label="{chu}"><span aria-hidden="true" style="display:inline-flex">{"".join(phan)}</span></span>'


def dau_trang(ten_mo_hinh, test, nguong_mac_dinh, dang_giam_sat=False):
    tt = [("Mô hình", ten_mo_hinh), ("Ngưỡng mặc định", f"{nguong_mac_dinh:.3f}")]
    if test:
        fnr = test["FN"] / (test["FN"] + test["TP"]) if test.get("TP") is not None else float("nan")
        tt += [("F1 trên tập test", f"{test['F1']:.4f}"), ("FPR (test)", f"{test['Ty_le_bao_nham_FPR']*100:.3f}%"),
               ("FNR (test)", f"{fnr*100:.3f}%")]
    chi_so = "".join(f'<div><span>{e(a)}</span><b>{e(b)}</b></div>' for a, b in tt)
    trang = ('<span class="tt-live on"><i></i>Đang giám sát mạng</span>' if dang_giam_sat
             else '<span class="tt-live san-sang"><i></i>Sẵn sàng phân tích</span>')
    song = (f'<svg class="song" viewBox="0 0 1200 64" preserveAspectRatio="none" aria-hidden="true">'
            f'<path class="nen" pathLength="1000" d="{_SONG}"/>'
            f'<path class="xung{" do" if dang_giam_sat else ""}" pathLength="1000" d="{_SONG}"/></svg>')
    return (f'<div class="hero">{_MANG}<div class="dong1"><div class="trai"><span class="logo">{LOGO}</span><div>'
            f'<h1><span class="dong-td">Ứng dụng Machine Learning vào</span> <span class="dong-td">hệ thống phát hiện nguy cơ an ninh mạng</span></h1>'
            f'<div class="phu">Mô hình XGBoost trên dữ liệu CIC-IDS2017 (bản sửa lỗi của Distrinet)</div></div></div>'
            f'{trang}</div>{song}<div class="chi-so" style="--n:{len(tt)}">{chi_so}</div></div>')


def buoc(so, ten, mo="", them_html=""):
    return (f'<div class="buoc"><span class="so">{so}</span><span class="ten">{e(ten)}</span>'
            + (f'<span class="mo">{e(mo)}</span>' if mo else "") + them_html + '<span class="gach"></span></div>')


def trang_thai(dang_chay, chu):
    return f'<span class="tt-live{" on" if dang_chay else ""}"><i></i>{e(chu)}</span>'


def danh_sach_kiem_tra(muc):
    """muc: list (loai, noi_dung) voi loai in {'ok','cb','loi'}"""
    ky = {"ok": "✓", "cb": "!", "loi": "✕"}
    return '<ul class="kt">' + "".join(
        f'<li class="{l}"><span class="i">{ky[l]}</span><span>{e(t)}</span></li>' for l, t in muc) + "</ul>"


def dai_so_lieu(muc):
    """muc: list (nhan, gia_tri, phu) hoac (nhan, gia_tri, phu, ti_le 0..1 hoac None, mau)."""
    def o_(m):
        a, b, c = m[:3]
        ti_le = m[3] if len(m) > 3 else None
        mau = m[4] if len(m) > 4 else None
        kieu = f' style="--mau:{mau}"' if mau else ""
        ray = (f'<div class="ray"><span style="width:{max(0.0, min(1.0, ti_le)) * 100:.2f}%"></span></div>'
               if ti_le is not None and ti_le == ti_le else "")
        return (f'<div{kieu}><div class="t">{e(a)}</div><div class="n">{e(b)}</div>'
                + (f'<div class="p">{e(c)}</div>' if c else "") + ray + "</div>")
    o = "".join(o_(m) for m in muc)
    return f'<div class="sl" style="--n:{len(muc)}">{o}</div>'


def dai_phan_quyet(tan_cong, binh_thuong, thieu, nguong, chu_trai="Đã phân tích"):
    tong = tan_cong + binh_thuong + thieu
    t1 = max(tong, 1)
    phan = [(tan_cong, MAU_TAN_CONG, "Tấn công"), (binh_thuong, MAU_BINH_THUONG, "Bình thường"),
            (thieu, MAU_THIEU, "Không đủ dữ liệu")]
    thanh = "".join(f'<span style="flex:{n} 0 0;background:{c}" title="{t}: {n:,}"></span>'
                    for n, c, t in phan if n > 0)
    lop_o = ["tc", "bt", "th"]
    o = "".join(f'<div class="o {lop_o[i]}{" co" if n else ""}"><div class="n">{so_cuon(n, .35 + i * .12)}</div><div class="t">'
                f'<i style="background:{c}"></i>{t}, {n / t1 * 100:.2f}%</div></div>' for i, (n, c, t) in enumerate(phan))
    lop = "co-tc" if tan_cong else ("an-toan" if binh_thuong else "")
    return (f'<div class="pq {lop}" role="img" aria-label="Tấn công {tan_cong}, bình thường {binh_thuong}, '
            f'không đủ dữ liệu {thieu}">'
            + (f'<span class="ket-luan"><i></i>Phát hiện {tan_cong:,} luồng tấn công</span>' if tan_cong else
               ('<span class="ket-luan"><i></i>Không phát hiện tấn công</span>' if binh_thuong else ""))
            + f'<div class="tong"><span>{e(chu_trai)} <b>{tong:,}</b> luồng mạng</span>'
            f'<span>Ngưỡng cảnh báo <b>{nguong:.2f}</b></span></div><div class="thanh">{thanh}</div>'
            f'<div class="so-lieu">{o}</div></div>')


def nhan_ket_qua(kq):
    c = MAU_THEO_KQ.get(kq, MAU_MO)
    return (f'<span class="nhan-kq" style="color:{c};background:{c}1f"><i style="background:{c}"></i>{e(kq)}</span>')


def thanh_xac_suat(p):
    if p != p:  # NaN
        return '<span class="mo">không có</span>'
    c = MAU_TAN_CONG if p >= 0.5 else MAU_BINH_THUONG
    return (f'<div class="xs"><div class="ray"><span style="width:{p*100:.1f}%;background:{c}"></span></div>'
            f'<b>{p:.4f}</b></div>')


def bang(cot, dong):
    """cot: list (ten, kieu) voi kieu in {'', 'so', 'mo', 'html'}; dong: list cac list gia tri."""
    th = "".join(f'<th class="{k if k == "so" else ""}">{e(t)}</th>' for t, k in cot)
    tr = []
    for d in dong:
        o = []
        for (t, k), v in zip(cot, d):
            if k == "html":
                o.append(f"<td>{v}</td>")
            else:
                o.append(f'<td class="{k}">{e(v)}</td>')
        tr.append("<tr>" + "".join(o) + "</tr>")
    return f'<div class="bang"><table><thead><tr>{th}</tr></thead><tbody>{"".join(tr)}</tbody></table></div>'


_IC = {
    "tai": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 15V4m0 0L8 8m4-4 4 4"/><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/></svg>',
    "kt": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="m8.5 12 2.3 2.3L15.5 9.6"/></svg>',
    "dd": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 19 6v5.5c0 4.4-3 7.9-7 9.5-4-1.6-7-5.1-7-9.5V6z"/><path d="M8 12.5h2l1-2.5 2 5 1-2.5h2"/></svg>',
    "xuat": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 14h6M9 17h4"/></svg>',
}


def trang_chua_co_file(so_cot):
    """Man hinh cho khi chua tai file: 4 buoc cua ung dung noi bang mot dai tin hieu chay."""
    b = [("tai", "Tải file CSV", "Kéo thả file luồng mạng từ CICFlowMeter"),
         ("kt", "Kiểm tra dữ liệu", f"Đủ {so_cot} cột, đánh dấu ô trống, chữ, vô cực"),
         ("dd", "Phát hiện tấn công", "XGBoost chấm điểm từng luồng mạng"),
         ("xuat", "Xuất kết quả", "CSV, Excel và báo cáo PDF")]
    the = "".join(f'<div class="b"><div class="ic">{_IC[k]}</div><b>{e(t)}</b><span>{e(m)}</span></div>' for k, t, m in b)
    return ('<div class="qt"><p class="tieu">Ứng dụng làm việc theo 4 bước</p>'
            f'<div class="hang"><div class="day"></div>{the}</div>'
            '<div class="mau">Chưa có file? Thử ngay với file mẫu trong thư mục dự án: '
            '<code>data/samples/demo_labeled.csv</code><code>data/samples/demo_unlabeled.csv</code></div></div>')



# ======================= LOP 4: cac khoi moi =======================
def dong_ho_nguong(nguong, mac_dinh, lo=0.05, hi=0.95):
    """Dong ho nua vong cho nguong canh bao: trai = nhay (bat nhieu), phai = it bao nham."""
    import math
    def diem(v, r):
        g = math.pi * (1 - (v - lo) / (hi - lo))
        return 100 + r * math.cos(g), 100 - r * math.sin(g)
    x1, y1 = diem(lo, 80); x2, y2 = diem(hi, 80)
    goc = -90 + 180 * (nguong - lo) / (hi - lo)
    mx, my = diem(mac_dinh, 92)
    mx2, my2 = diem(mac_dinh, 70)
    vach = "".join(
        f'<line x1="{diem(v, 66)[0]:.1f}" y1="{diem(v, 66)[1]:.1f}" x2="{diem(v, 72)[0]:.1f}" y2="{diem(v, 72)[1]:.1f}" '
        f'stroke="rgba(170,180,200,.35)" stroke-width="1.2"/>' for v in [lo + k * (hi - lo) / 10 for k in range(11)])
    if nguong < 0.35:
        che_do = ('nhay', 'Nhạy: bắt nhiều, dễ báo nhầm')
    elif nguong <= 0.75:
        che_do = ('can-bang', 'Cân bằng')
    else:
        che_do = ('it-nham', 'Ít báo nhầm, dễ bỏ sót')
    return (f'<div class="dong-ho"><svg viewBox="0 0 200 124" aria-hidden="true">'
            f'<defs><linearGradient id="gdh" x1="0" x2="1"><stop offset="0" stop-color="{MAU_TAN_CONG}"/>'
            f'<stop offset=".5" stop-color="{MAU_NHAN}"/><stop offset="1" stop-color="{MAU_BINH_THUONG}"/></linearGradient></defs>'
            f'<path d="M{x1:.1f} {y1:.1f} A80 80 0 0 1 {x2:.1f} {y2:.1f}" fill="none" stroke="rgba(14,20,36,.9)" stroke-width="12" stroke-linecap="round"/>'
            f'<path class="cung" pathLength="1000" d="M{x1:.1f} {y1:.1f} A80 80 0 0 1 {x2:.1f} {y2:.1f}" fill="none" '
            f'stroke="url(#gdh)" stroke-width="12" stroke-linecap="round" style="filter:drop-shadow(0 0 6px rgba(242,179,61,.45))"/>'
            f'{vach}<line x1="{mx:.1f}" y1="{my:.1f}" x2="{mx2:.1f}" y2="{my2:.1f}" stroke="{MAU_CHU}" stroke-width="2" stroke-dasharray="2 2"/>'
            f'<g class="kim"><g transform="rotate({goc:.1f} 100 100)"><path d="M100 30 L104 100 L96 100 Z" fill="{MAU_CHU}"/>'
            f'</g></g><circle cx="100" cy="100" r="7" fill="{MAU_NHAN}" style="filter:drop-shadow(0 0 6px {MAU_NHAN})"/>'
            f'<text x="{x1:.0f}" y="121" fill="{MAU_MO}" font-size="9" text-anchor="middle">nhạy</text>'
            f'<text x="{x2:.0f}" y="121" fill="{MAU_MO}" font-size="9" text-anchor="middle">chặt</text></svg>'
            f'<div class="gia-tri">{nguong:.2f}</div><span class="che-do {che_do[0]}">{e(che_do[1])}</span></div>')


def ma_tran(tn, fp, fn, tp):
    """Ma tran nham lan dang o nhiet: o dung mau xanh, o sai mau do, dam nhat theo ti le trong hang."""
    def o(ten, n, tong_hang, dung, mo):
        a = 0.08 + 0.5 * (n / tong_hang if tong_hang else 0)
        return (f'<div class="o {"dung" if dung else "sai"}{" co" if (not dung and n) else ""}" style="--a:{a:.3f}">'
                f'<div class="ten">{e(ten)}</div><div class="n">{so_cuon(n, .25)}</div>'
                f'<div class="p">{e(mo)}{f" · {n / tong_hang * 100:.2f}%" if tong_hang else ""}</div></div>')
    h0, h1 = tn + fp, fn + tp
    return ('<div class="mt"><div class="luoi">'
            '<span></span><span class="dau cot">Dự đoán bình thường</span><span class="dau cot">Dự đoán tấn công</span>'
            '<span class="dau">Thực tế bình thường</span>'
            + o("TN", tn, h0, True, "đúng là bình thường") + o("FP", fp, h0, False, "báo động nhầm")
            + '<span class="dau">Thực tế tấn công</span>'
            + o("FN", fn, h1, False, "bỏ sót tấn công") + o("TP", tp, h1, True, "bắt đúng tấn công")
            + '</div></div>')


def thanh_ti_le(x):
    """Thanh nho cho cot ti le trong bang: xanh khi >= 99%, vang khi >= 90%, do khi thap hon."""
    if x is None or x != x:
        return '<div class="tl"><b class="mo">—</b></div>'
    mau = MAU_BINH_THUONG if x >= .99 else (MAU_NHAN if x >= .9 else MAU_TAN_CONG)
    return (f'<div class="tl"><div class="ray"><span style="width:{x * 100:.1f}%;background:{mau};'
            f'box-shadow:0 0 8px {mau}"></span></div><b>{x * 100:.2f}%</b></div>')


def radar(diem, nhat_ky, dang_chay, so_tc):
    """diem: list (goc_do, ban_kinh 0..1, la_tan_cong). nhat_ky: list (gio, mo_ta, xac_suat, la_tan_cong).
    Vach quet dung animation-delay am theo dong ho he thong, nen moi lan lam moi (2 giay) van quay lien mach."""
    import math
    import time
    tre = -(time.time() % 4.0)
    cham = []
    for goc, r, tc in diem[-60:]:
        x = 50 + 46 * r * math.cos(math.radians(goc - 90))
        y = 50 + 46 * r * math.sin(math.radians(goc - 90))
        cham.append(f'<span class="cham{" tc" if tc else ""}" style="left:{x:.1f}%;top:{y:.1f}%;'
                    f'animation-delay:{tre + goc / 360 * 4:.2f}s"></span>')
    dong = "".join(
        f'<li class="{"tc" if t else ""}"><span class="gio">{e(g)}</span><span class="dc">{e(m)}</span>'
        f'<span class="xs" style="color:{MAU_TAN_CONG if t else MAU_BINH_THUONG}">{p * 100:.1f}%</span></li>'
        for g, m, p, t in nhat_ky[:7])
    return (f'<div class="radar-khung"><div class="radar{" canh-bao" if so_tc else ""}">'
            f'<div class="vong"></div><div class="chu-thap"></div>'
            f'<div class="quet" style="animation-delay:{tre:.2f}s{"" if dang_chay else ";animation-play-state:paused"}"></div>'
            f'{"".join(cham)}<div class="tam"></div></div>'
            f'<div class="nhat-ky"><div class="tieu"><span>Nhật ký luồng mới nhất</span>'
            f'<span>{"● đang quét" if dang_chay else "đã dừng"}</span></div>'
            + (f'<ul>{dong}</ul>' if dong else '<div class="trong">Chưa có luồng nào được đánh giá.</div>')
            + '</div></div>')
