import sys, datetime as dt, calendar, copy
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_MARKER_STYLE, XL_LABEL_POSITION, XL_TICK_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree
import data as Dt

MODE, OUT = sys.argv[1], sys.argv[2]
EX = MODE == "example"
FONT = "맑은 고딕"
def rgb(h): return RGBColor.from_string(h)
NAVY, BLUE, LIGHT, DARK, GRAY, LINE = rgb("0C447C"), rgb("185FA5"), rgb("E6F1FB"), rgb("2C2C2A"), rgb("5F5E5A"), rgb("B4B2A9")
WHITE, RED, ORANGE = rgb("FFFFFF"), rgb("C00000"), rgb("E46C0A")
PLAN_C, DONE_C, DELAY_C = rgb("BDD7EE"), rgb("185FA5"), rgb("E06666")
SIG = {"지연": ("F8D7DA", "C00000"), "주의": ("FFF3CD", "9C6500"), "정상": ("D4EDDA", "1E7B34"), "완료": ("D6E4F0", "0C447C")}

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BL = prs.slide_layouts[6]
PAGE = [0]

# ---------------- helpers ----------------
def para(tf, text, size, color, bold=False, align=PP_ALIGN.LEFT, first=False, space=0):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align; p.space_before = Pt(space)
    r = p.add_run(); r.text = text
    f = r.font; f.name, f.size, f.bold, f.color.rgb = FONT, Pt(size), bold, color
    return p

def textbox(slide, x, y, w, h, anchor=None):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.02)
    if anchor: tf.vertical_anchor = anchor
    return tf

def new_slide(title, notes=None):
    s = prs.slides.add_slide(BL); PAGE[0] += 1
    tf = textbox(s, Inches(0.4), Inches(0.25), Inches(12.53), Inches(0.95), MSO_ANCHOR.MIDDLE)
    lines = title if isinstance(title, list) else [title]
    for i, ln in enumerate(lines):
        para(tf, ln, 18, DARK, bold=True, align=PP_ALIGN.CENTER, first=(i == 0))
    ln = s.shapes.add_connector(1, Inches(0.4), Inches(1.3), Inches(12.93), Inches(1.3))
    ln.line.color.rgb = LINE; ln.line.width = Pt(0.75)
    pg = textbox(s, Inches(12.2), Inches(7.12), Inches(0.75), Inches(0.3))
    para(pg, str(PAGE[0]), 9, GRAY, align=PP_ALIGN.RIGHT, first=True)
    if notes: s.notes_slide.notes_text_frame.text = notes
    return s

def heading(slide, x, y, w, text):
    hb = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, Inches(0.45))
    hb.adjustments[0] = 0.15
    hb.fill.solid(); hb.fill.fore_color.rgb = LIGHT
    hb.line.color.rgb = BLUE; hb.line.width = Pt(0.75)
    tf = hb.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(tf, text, 14, NAVY, bold=True, align=PP_ALIGN.CENTER, first=True)

def sub3(slide, x, y, w, sub, detail=None, result=None, h=Inches(0.8)):
    tf = textbox(slide, x, y, w, h)
    para(tf, sub, 12, DARK, bold=True, first=True)
    if detail: para(tf, detail, 11, GRAY, space=2)
    if result: para(tf, result if result.startswith("—>") else "—> " + result, 11, BLUE, space=1)
    return tf

def vbox(slide, x, y, w, h, label):
    vb = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    vb.fill.background(); vb.line.color.rgb = LINE; vb.line.width = Pt(0.75)
    vb.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    t = vb.text_frame; t.word_wrap = True; t.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(t, "[그림] " + label, 9, GRAY, align=PP_ALIGN.CENTER, first=True)

def box(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE):
    b = slide.shapes.add_shape(shape, x, y, w, h)
    if fill is None: b.fill.background()
    else: b.fill.solid(); b.fill.fore_color.rgb = fill
    if line is None: b.line.fill.background()
    else: b.line.color.rgb = line; b.line.width = Pt(0.75)
    b.shadow.inherit = False
    tf = b.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.02)
    return b

def table(slide, x, y, w, colw, rows, row_h=0.36, font=10, hdr_fill=NAVY, aligns=None):
    nr, nc = len(rows), len(rows[0])
    gs = slide.shapes.add_table(nr, nc, x, y, w, Inches(row_h * nr))
    tbl = gs.table
    tblPr = gs._element.graphic.graphicData.tbl.tblPr
    tblPr.set("bandRow", "0"); tblPr.set("firstRow", "1")
    tot = sum(colw)
    for j, cw in enumerate(colw): tbl.columns[j].width = int(w * cw / tot)
    for i in range(nr):
        tbl.rows[i].height = Inches(row_h)
        for j in range(nc):
            c = tbl.cell(i, j); v = rows[i][j]
            c.margin_left = c.margin_right = Inches(0.04); c.margin_top = c.margin_bottom = Inches(0.01)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = c.text_frame; tf.word_wrap = True
            txt = "" if v is None else str(v)
            al = PP_ALIGN.CENTER
            if aligns and i > 0 and aligns[j] == "l": al = PP_ALIGN.LEFT
            p = tf.paragraphs[0]; p.alignment = al
            r = p.add_run(); r.text = txt
            r.font.name = FONT; r.font.size = Pt(font)
            c.fill.solid()
            if i == 0:
                c.fill.fore_color.rgb = hdr_fill; r.font.bold = True; r.font.color.rgb = WHITE
            else:
                c.fill.fore_color.rgb = WHITE; r.font.color.rgb = DARK
    return tbl

def set_cell(tbl, i, j, fill=None, color=None, bold=None, text=None, size=None):
    c = tbl.cell(i, j)
    if fill is not None: c.fill.solid(); c.fill.fore_color.rgb = fill if isinstance(fill, RGBColor) else rgb(fill)
    r = c.text_frame.paragraphs[0].runs
    if text is not None:
        if r: r[0].text = text
    for run in c.text_frame.paragraphs[0].runs:
        if color is not None: run.font.color.rgb = color if isinstance(color, RGBColor) else rgb(color)
        if bold is not None: run.font.bold = bold
        if size is not None: run.font.size = Pt(size)

def sig_cell(tbl, i, j, sig):
    if sig in SIG:
        set_cell(tbl, i, j, fill=SIG[sig][0], color=SIG[sig][1], bold=True)

def style_chart(ch, size=9, legend=True):
    ch.font.name = FONT; ch.font.size = Pt(size); ch.font.color.rgb = GRAY
    ch.has_legend = legend
    if legend:
        ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(size)

def chart_title(ch, text, size=11):
    ch.has_title = True
    tf = ch.chart_title.text_frame; tf.text = text
    r = tf.paragraphs[0].runs[0]; r.font.size = Pt(size); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = DARK

def tick_skip(ch, n):
    cat = ch._chartSpace.find(".//" + qn("c:catAx"))
    el = etree.SubElement(cat, qn("c:tickLblSkip")); el.set("val", str(n))
    nm = cat.find(qn("c:noMultiLvlLbl"))
    if nm is not None: nm.addprevious(el)

def axis_max(ch):
    va = ch._chartSpace.find(".//" + qn("c:valAx"))
    va.find(qn("c:crosses")).set("val", "max")

def fmt(v):
    if v is None or v == "": return ""
    if isinstance(v, float):
        if abs(v) < 1: return f"{v:.2f}".rstrip("0").rstrip(".") if v else "0"
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)

def signal(it):
    if it["status"] == "완료": return "완료"
    if Dt.BASE_DATE > it["end"]: return "지연"
    dur = (it["end"] - it["start"]).days
    plan = max(0, min(1, (Dt.BASE_DATE - it["start"]).days / dur))
    return "주의" if it["prog"] < plan - 0.15 else "정상"

ITEMS = Dt.ITEMS
for it in ITEMS: it["sig"] = signal(it)
cnt = {k: sum(1 for it in ITEMS if it["sig"] == k) for k in SIG}
avg_ach = sum(min(it["ach"], 1.5) for it in ITEMS) / len(ITEMS)
W = Dt.CUR_WEEK
BD = Dt.BASE_DATE.strftime("%Y.%m.%d")

def kpi_chart(slide, x, y, w, h, it, title=None, size=9, placeholder=False):
    cd = CategoryChartData()
    cd.categories = [f"W{n:02d}" for n in range(1, 53)]
    if placeholder:
        tgt = [round(100 - 50 * n / 51, 1) for n in range(52)]
        act = [round(100 - 30 * n / 51 + (3 if n % 3 else -2), 1) if n < 12 else None for n in range(52)]
        ttl = title or "[KPI명] (단위, ↓)"
    else:
        sw, ew = Dt.week_of(it["start"]), Dt.week_of(it["end"])
        tgt = []
        for n in range(1, 53):
            ws = Dt.wk_start(n)
            if ws + dt.timedelta(days=6) < it["start"]: tgt.append(None)
            elif ws >= it["end"]: tgt.append(it["target"])
            else: tgt.append(round(it["base"] + (it["target"] - it["base"]) * (ws - it["start"]).days / (it["end"] - it["start"]).days, 3))
        act = [it["actuals"].get(n) for n in range(1, 53)]
        ttl = title or f'{it["id"]} {it["kpi"]} ({it["unit"]}, {it["dir"]})'
    cd.add_series("목표", tgt); cd.add_series("실적", act)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, x, y, w, h, cd)
    ch = gf.chart; style_chart(ch, size); chart_title(ch, ttl, size + 1)
    s0, s1 = ch.plots[0].series
    s0.format.line.color.rgb = rgb("9E9E9E"); s0.format.line.dash_style = MSO_LINE_DASH_STYLE.DASH; s0.format.line.width = Pt(1.5)
    s0.marker.style = XL_MARKER_STYLE.NONE; s0.smooth = False
    s1.format.line.color.rgb = BLUE; s1.format.line.width = Pt(2); s1.smooth = False
    s1.marker.style = XL_MARKER_STYLE.CIRCLE; s1.marker.size = 4
    s1.marker.format.fill.solid(); s1.marker.format.fill.fore_color.rgb = BLUE; s1.marker.format.line.color.rgb = BLUE
    va = ch.value_axis; va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("E5E5E5"); va.format.line.fill.background()
    va.tick_labels.font.size = Pt(size - 1)
    ca = ch.category_axis; ca.tick_labels.font.size = Pt(size - 1); ca.format.line.color.rgb = LINE
    tick_skip(ch, 8)
    return ch

# =====================================================================
# 1. 표지
# =====================================================================
s = prs.slides.add_slide(BL); PAGE[0] += 1
b = box(s, Inches(0), Inches(0), prs.slide_width, prs.slide_height, NAVY)
tf = textbox(s, Inches(1.0), Inches(2.3), Inches(11.33), Inches(1.6), MSO_ANCHOR.MIDDLE)
para(tf, "2027 Stack Layer Defect 개선" if EX else "20OO Stack Layer Defect 개선", 32, WHITE, bold=True, align=PP_ALIGN.CENTER, first=True)
para(tf, "Action Item 추진 계획 및 현황", 32, WHITE, bold=True, align=PP_ALIGN.CENTER, space=4)
tf = textbox(s, Inches(1.0), Inches(4.3), Inches(11.33), Inches(1.0), MSO_ANCHOR.TOP)
para(tf, f"{BD} 기준 (W{W:02d})" if EX else "20OO.OO.OO 기준 (WOO)", 16, rgb("CADCFC"), align=PP_ALIGN.CENTER, first=True)
para(tf, "Stack Layer 모듈  |  모듈장 OOO", 14, rgb("CADCFC"), align=PP_ALIGN.CENTER, space=6)
s.notes_slide.notes_text_frame.text = "표지. 기준일/주차는 매 보고 시 갱신."

# =====================================================================
# 2. 요약
# =====================================================================
s = new_slide("stack layer 7개 step action item 9건 선정 —> 정/부 담당 weekly F/U 로 KPI 성과화" if EX
              else "[불합리 요약] —> [action] 으로 [결과/목표]",
              "요약 장표. 추진 배경 / 추진 내용 / 현재 현황 숫자 3개만 강조. 숫자는 Excel Dashboard 기준으로 갱신.")
cards = [("추진 배경", "850 ppm" if EX else "OO", "edge_cr 불량률 (전년 대비 2.1배)" if EX else "[핵심 불량 지표 / 증가율]",
          "step별 defect F/U 기준 상이 : 연간 지속 관리 체계 미연계" if EX else "[관리 체계 불합리]"),
         ("추진 내용", "9 건" if EX else "OO 건", "7개 step action item · 정/부 담당 지정" if EX else "[과제 수 / step 수]",
          "weekly·bi-weekly 보고 : 주차별 KPI 실적 입력·추적" if EX else "[보고 주기 / 추적 방식]"),
         ("현재 현황 (W22)" if EX else "현재 현황", f"{avg_ach*100:.0f} %" if EX else "OO %", "평균 목표 달성률" if EX else "평균 목표 달성률",
          f"정상 {cnt['정상']} · 주의 {cnt['주의']} · 지연 {cnt['지연']} · 완료 {cnt['완료']}" if EX else "정상 O · 주의 O · 지연 O · 완료 O")]
cw, gap = Inches(3.9), Inches(0.42)
for j, (h, big, l1, l2) in enumerate(cards):
    x = Inches(0.4) + (cw + gap) * j
    heading(s, x, Inches(1.75), cw, h)
    b = box(s, x, Inches(2.4), cw, Inches(3.3), rgb("F7FAFD"), rgb("D6E4F0"), MSO_SHAPE.ROUNDED_RECTANGLE); b.adjustments[0] = 0.05
    tf = textbox(s, x + Inches(0.2), Inches(2.7), cw - Inches(0.4), Inches(1.4), MSO_ANCHOR.MIDDLE)
    para(tf, big, 44, BLUE, bold=True, align=PP_ALIGN.CENTER, first=True)
    tf = textbox(s, x + Inches(0.2), Inches(4.3), cw - Inches(0.4), Inches(1.8))
    para(tf, l1, 14, DARK, bold=True, align=PP_ALIGN.CENTER, first=True)
    para(tf, l2, 11, GRAY, align=PP_ALIGN.CENTER, space=8)

# =====================================================================
# 3. 추진 체계
# =====================================================================
s = new_slide("stack layer step별 핵심 defect 1:1 과제화 —> 정/부 담당 · 주차별 KPI 추적으로 연간 F/U 체계 운영" if EX
              else "[step별 과제 선정 기준] —> [운영 체계]",
              "좌측은 step별 과제 map, 우측은 운영 방식. 과제 선정 회의 결과로 좌측 map 을 갱신.")
LX, RX, HW = Inches(0.4), Inches(0.4) + Inches(6.1) + Inches(0.33), Inches(6.1)
heading(s, LX, Inches(1.5), HW, "stack layer step별 action item map")
heading(s, RX, Inches(1.5), HW, "운영 방안 : 보고 주기 · R&R · 수치화")
steps = Dt.STEPS
top, rh = Inches(2.1), Inches(0.6)
for k, st in enumerate(steps):
    y = top + rh * k
    b = box(s, LX, y + Inches(0.06), Inches(1.9), rh - Inches(0.12), NAVY if st != "공통" else GRAY, shape=MSO_SHAPE.CHEVRON if st != "공통" else MSO_SHAPE.ROUNDED_RECTANGLE)
    para(b.text_frame, st if EX else (st if st == "공통" else f"S{k+1} [step명]"), 10, WHITE, bold=True, align=PP_ALIGN.CENTER, first=True)
    its = [it for it in ITEMS if it["step"] == st] if EX else []
    tf = textbox(s, LX + Inches(2.0), y + Inches(0.04), HW - Inches(2.0), rh - Inches(0.08), MSO_ANCHOR.MIDDLE)
    if its:
        for q, it in enumerate(its):
            p = para(tf, f'{it["id"]}  ', 10, BLUE, bold=True, first=(q == 0))
            r = p.add_run(); r.text = f'{it["title"]}  ({it["owner"]}/{it["sub"]})'
            r.font.name = FONT; r.font.size = Pt(10); r.font.color.rgb = DARK
    else:
        para(tf, "AI-OO  [과제명]  (정 OO / 부 OO)" if not EX else "-", 10, GRAY, first=True)
    if k < len(steps) - 1:
        ln = s.shapes.add_connector(1, LX + Inches(2.0), y + rh, LX + HW, y + rh); ln.line.color.rgb = rgb("E5E5E5"); ln.line.width = Pt(0.5)
ry = Inches(2.1)
subs = [("1. 보고 주기 : 우선순위·변화 속도 기준 이원화", "상 우선순위·주 단위 변동 KPI : weekly / 그 외 : bi-weekly", "주차별 실적 누적 : 보고 시점 무관 동일 기준 추적"),
        ("2. R&R : 과제별 정/부 담당 지정", "정 = KPI 입력·대책 실행 / 부 = 대체 보고·데이터 검증", "담당 공백 시에도 F/U 연속성 유지"),
        ("3. 수치화 : baseline → 목표 → 주차 실적 → 달성률", "달성률 = (현재-baseline)÷(목표-baseline) : ↓/↑ 공통", "연말 baseline 대비 개선율로 성과 정량화")]
for q, (a, d, r) in enumerate(subs):
    sub3(s, RX, ry + Inches(0.88) * q, HW, a, d, r)
fy = Inches(5.0)
flow = ["주차 실적 입력\n(담당 정/부)", "달성률·신호등\n자동 산출", "weekly 보고\n(모듈장)", "주의·지연 과제\n대책 재수립"]
fw, fg = Inches(1.35), Inches(0.23)
for q, t in enumerate(flow):
    x = RX + (fw + fg) * q
    b = box(s, x, fy, fw, Inches(0.85), LIGHT if q < 3 else rgb("FFF3CD"), BLUE if q < 3 else rgb("E0A800"), MSO_SHAPE.ROUNDED_RECTANGLE)
    for z, line in enumerate(t.split("\n")):
        para(b.text_frame, line, 10, NAVY, bold=(z == 0), align=PP_ALIGN.CENTER, first=(z == 0))
    if q < 3:
        a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + fw + Inches(0.03), fy + Inches(0.33), fg - Inches(0.06), Inches(0.2))
        a.fill.solid(); a.fill.fore_color.rgb = LINE; a.line.fill.background()
tf = textbox(s, RX, fy + Inches(1.0), HW, Inches(0.9))
para(tf, "※ 운영 tool : Excel tracker (Action_Master · Weekly_KPI · Gantt · Dashboard) 1개 파일로 연간 운영", 10, GRAY, first=True)
para(tf, "※ 분기 1회 : 목표 재설정 / 과제 추가·drop 검토 (변경 이력 비고 기록)", 10, GRAY, space=3)

# =====================================================================
# 4. 총괄표
# =====================================================================
s = new_slide(f"action item {len(ITEMS)}건 총괄 —> 정상 {cnt['정상']} · 주의 {cnt['주의']} · 지연 {cnt['지연']} · 완료 {cnt['완료']} (W{W:02d} 기준)" if EX
              else "action item OO건 총괄 —> 정상 O · 주의 O · 지연 O · 완료 O (WOO 기준)",
              "총괄표. 행 추가/삭제는 표 우클릭 → 삽입/삭제. 신호 칸 색상은 범례 기준으로 셀 음영 변경.")
hdrs = ["No", "Step", "과제명", "KPI (단위)", "방향", "Baseline", "목표", f"현재\n(W{W:02d})" if EX else "현재", "달성률", "담당\n정 / 부", "완료\n목표", "신호"]
rows = [hdrs]
if EX:
    for it in ITEMS:
        rows.append([it["id"], it["step"], it["title"], f'{it["kpi"]} ({it["unit"]})', it["dir"], fmt(it["base"]), fmt(it["target"]),
                     fmt(it["current"]), f'{it["ach"]*100:.0f}%', f'{it["owner"]} / {it["sub"]}', it["end"].strftime("%m/%d"), it["sig"]])
else:
    rows.append(["AI-01", "S5 [step명]", "[defect] 불량률 저감", "[KPI] (ppm)", "↓", "OO", "OO", "OO", "OO%", "OO / OO", "MM/DD", "정상"])
    for k in range(2, 11): rows.append([f"AI-{k:02d}", "", "", "", "", "", "", "", "", "", "", ""])
tbl = table(s, Inches(0.4), Inches(1.55), Inches(12.53), [0.65, 1.55, 3.6, 1.9, 0.5, 0.8, 0.7, 0.75, 0.75, 1.15, 0.7, 0.65], rows,
            row_h=0.44 if EX else 0.42, font=10, aligns=["c", "c", "l", "c", "c", "c", "c", "c", "c", "c", "c", "c"])
for i in range(1, len(rows)):
    sig_cell(tbl, i, 11, rows[i][11])
    if rows[i][8]: set_cell(tbl, i, 8, bold=True, color=BLUE)
lg = textbox(s, Inches(0.4), Inches(6.85), Inches(12.0), Inches(0.3))
para(lg, "※ 신호 : 완료 / 정상 / 주의 (실제 진척 < 계획 진척 -15%p) / 지연 (완료 목표일 경과 미완료)   ·   달성률 = (현재-Baseline)÷(목표-Baseline)", 9, GRAY, first=True)

# =====================================================================
# 5. Gantt (표)
# =====================================================================
s = new_slide("연간 추진 일정 (Gantt) —> 계획 대비 진척 구간·milestone 월 단위 관리" if EX else "연간 추진 일정 (Gantt) —> [요약 메시지]",
              "표 기반 간트. 셀 음영으로 막대 표현 : 연파랑=계획, 진파랑=진척, 빨강=지연. ◆=milestone(흰색 완료/빨강 예정). 셀 색은 직접 바꿔서 수정.")
months = [f"{m}월" for m in range(1, 13)]
hdrs = ["No", "과제명", "정 / 부"] + months + ["진척", "신호"]
rows = [hdrs]
gitems = ITEMS if EX else []
for it in gitems:
    rows.append([it["id"], it["title"], f'{it["owner"]}/{it["sub"]}'] + [""] * 12 + [f'{it["prog"]*100:.0f}%', it["sig"]])
if not EX:
    rows.append(["AI-01", "[과제명]", "OO/OO"] + [""] * 12 + ["OO%", "정상"])
    for k in range(2, 11): rows.append([f"AI-{k:02d}", "", ""] + [""] * 12 + ["", ""])
colw = [0.6, 3.0, 1.0] + [0.6] * 12 + [0.55, 0.6]
tbl = table(s, Inches(0.4), Inches(1.55), Inches(12.53), colw, rows, row_h=0.46 if EX else 0.42, font=9,
            aligns=["c", "l"] + ["c"] * 16)
cm = Dt.BASE_DATE.month if EX else None
for j in range(3, 15):
    if EX and j - 2 == cm: set_cell(tbl, 0, j, fill=ORANGE)
for i, it in enumerate(gitems, start=1):
    done_until = it["start"] + dt.timedelta(days=(it["end"] - it["start"]).days * it["prog"])
    for m in range(1, 13):
        ms0 = dt.date(Dt.YEAR, m, 1); ms1 = dt.date(Dt.YEAR, m, calendar.monthrange(Dt.YEAR, m)[1])
        j = 2 + m
        inplan = ms1 >= it["start"] and ms0 <= it["end"]
        fill = None
        if inplan:
            fill = DONE_C if ms0 <= done_until else PLAN_C
            if it["sig"] == "지연" and fill == PLAN_C: fill = DELAY_C
        if it["sig"] == "지연" and ms0 > it["end"] and ms0 <= Dt.BASE_DATE: fill = DELAY_C
        if fill is not None: set_cell(tbl, i, j, fill=fill)
        mss = [x for x in Dt.MILESTONES if x["id"] == it["id"] and ms0 <= x["plan"] <= ms1]
        if mss:
            done = all(x["actual"] for x in mss)
            set_cell(tbl, i, j, text="◆" * len(mss), color=WHITE if (done and fill == DONE_C) else RED, bold=True, size=9)
    sig_cell(tbl, i, 16, it["sig"])
if not EX:
    for m, f in [(1, DONE_C), (2, DONE_C), (3, PLAN_C), (4, PLAN_C), (5, PLAN_C)]: set_cell(tbl, 1, 2 + m, fill=f)
    set_cell(tbl, 1, 4, text="◆", color=WHITE, bold=True); set_cell(tbl, 1, 7, text="◆", color=RED, bold=True)
    sig_cell(tbl, 1, 16, "정상")
ly = Inches(6.9)
lx = Inches(0.4)
for lab, c in [("계획", PLAN_C), ("진척", DONE_C), ("지연", DELAY_C)]:
    box(s, lx, ly + Inches(0.06), Inches(0.3), Inches(0.16), c)
    t = textbox(s, lx + Inches(0.33), ly, Inches(0.7), Inches(0.3)); para(t, lab, 9, GRAY, first=True)
    lx += Inches(1.0)
t = textbox(s, lx, ly, Inches(9), Inches(0.3))
para(t, ("◆ milestone (흰색 = 완료, 빨강 = 예정/미완료)   ·   주황 = 기준월   ·   주 단위 상세는 Excel Gantt 시트 참조"), 9, GRAY, first=True)

# =====================================================================
# 6. Gantt (차트)
# =====================================================================
s = new_slide("연간 추진 일정 (차트형) —> 시작~완료 주차 기준 진척 / 잔여 구간 시각화" if EX else "연간 추진 일정 (차트형) —> [요약 메시지]",
              "차트형 간트 (차트 우클릭 → 데이터 편집으로 주차 수정). 시작 = 투명 막대, 진척/잔여 = 주 단위.")
cd = CategoryChartData()
if EX:
    cats = [f'{it["id"]} {it["title"][:18]}{"…" if len(it["title"]) > 18 else ""}' for it in ITEMS]
    st = [Dt.week_of(it["start"]) - 1 for it in ITEMS]
    du = [Dt.week_of(it["end"]) - Dt.week_of(it["start"]) + 1 for it in ITEMS]
    dn = [round(d * it["prog"], 1) for d, it in zip(du, ITEMS)]
    rm = [round(d - x, 1) for d, x in zip(du, dn)]
else:
    cats = [f"AI-{k:02d} [과제명]" for k in range(1, 7)]
    st = [0, 2, 4, 8, 0, 12]; du = [30, 20, 36, 24, 52, 20]
    dn = [12, 8, 6, 2, 10, 0]; rm = [d - x for d, x in zip(du, dn)]
cd.categories = cats
cd.add_series(" ", st); cd.add_series("진척", dn); cd.add_series("잔여", rm)
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_STACKED, Inches(0.4), Inches(1.5), Inches(12.53), Inches(5.35), cd)
ch = gf.chart; style_chart(ch, 10)
pl = ch.plots[0]; pl.gap_width = 45; pl.overlap = 100
s0, s1, s2 = pl.series
s0.format.fill.background(); s0.format.line.fill.background()
s1.format.fill.solid(); s1.format.fill.fore_color.rgb = DONE_C
s2.format.fill.solid(); s2.format.fill.fore_color.rgb = PLAN_C
ch.category_axis.reverse_order = True
ch.category_axis.tick_labels.font.size = Pt(10); ch.category_axis.tick_labels.font.color.rgb = DARK
va = ch.value_axis; va.minimum_scale = 0; va.maximum_scale = 52; va.major_unit = 4
va.tick_labels.number_format = '"W"0'; va.tick_labels.number_format_is_linked = False
va.has_major_gridlines = True; va.major_gridlines.format.line.color.rgb = rgb("E5E5E5")
axis_max(ch)
if EX:
    t = textbox(s, Inches(9.6), Inches(1.45), Inches(3.3), Inches(0.3))
    para(t, f"기준 W{W:02d} ({BD})", 10, ORANGE, bold=True, align=PP_ALIGN.RIGHT, first=True)

# =====================================================================
# 7. KPI 추이
# =====================================================================
s = new_slide("주요 KPI 주차별 목표 vs 실적 —> edge_cr·chipping 개선 추세, die crack·void σ 목표 대비 지연" if EX
              else "주요 KPI 주차별 목표 vs 실적 추이 —> [요약 메시지]",
              "차트 우클릭 → 데이터 편집 → 실적 행에 주차별 값 붙여넣기 (Excel Weekly_KPI 시트 행 복사). 점선 = 목표 glide path.")
sel = [ITEMS[i] for i in (0, 1, 2, 3, 4, 6)]
cw, chh = Inches(4.05), Inches(2.6)
for q, it in enumerate(sel):
    x = Inches(0.4) + (cw + Inches(0.19)) * (q % 3)
    y = Inches(1.55) + (chh + Inches(0.2)) * (q // 3)
    kpi_chart(s, x, y, cw, chh, it, placeholder=not EX,
              title=None if EX else f"AI-0{q+1} [KPI명] (단위, ↓/↑)")

# =====================================================================
# 8. 과제 상세 : AI-01 torque F/U
# =====================================================================
it1 = ITEMS[0]
tq = Dt.TQ_LOTS; ts = Dt.TQ_SPEC
n_in = sum(1 for l in tq if min(l["t"]) >= ts["lsl"] and max(l["t"]) <= ts["usl"])
n3 = sum(1 for l in tq if l["eq"] == "#3")
n_cyc = sum(1 for l in tq if l["gap"] > ts["cycle_hr"])
if EX:
    s = new_slide(["AI-01 edge_cr 대응 torque 관리 중이나 불량 lot 87.5% torque 규격 내",
                   "—> #3 호기 head 평탄도 등 추가 인자 검증 진행 (Stack팀 협업)"],
                  "edge_cr 의 원인 공정 관리 인자(torque)가 실제 불량 lot 에서 정상이었는지 연계 검증한 결과. 관리 기준 내 불량이 대부분이므로 torque 단독 관리로는 개선 한계 → 추가 인자 검증. 타팀 관리 미흡이 아니라 관리 항목 확장 관점으로 설명.")
    heading(s, LX, Inches(1.5), HW, "edge_cr 현황 및 torque 관리 연계 검증")
    heading(s, RX, Inches(1.5), HW, "추가 인자 검증 및 F/U 계획")
    sub3(s, LX, Inches(2.05), HW, f"1. edge_cr 불량률 850 → {it1['current']} ppm (W{W:02d}, 달성률 {it1['ach']*100:.0f}%)",
         f"stack torque 관리 기준 운영 : {ts['lsl']}~{ts['usl']} {ts['unit']}", "목표 300 ppm 대비 개선 속도 부족")
    kpi_chart(s, LX, Inches(2.9), HW, Inches(1.95), it1, title="edge_cr 불량률 (ppm) : 목표 vs 실적", size=8)
    sub3(s, LX, Inches(4.95), HW, f"2. 불량 lot {len(tq)}건 torque 이력 연계 : {n_in}건 규격 내",
         "작업 시점 직전 torque 실측값 연계 : 불량 lot 평균 2.42 N·m", "torque 단독 관리로 edge_cr 개선 한계 추정")
    # stat callouts
    for q, (big, lab, col) in enumerate([(f"{n_in/len(tq)*100:.1f}%", f"규격 내 ({n_in}/{len(tq)})", BLUE),
                                         (f"{len(tq)-n_in}건", "규격 이탈", RED), ("1.51", "양품 torque Cpk", NAVY)]):
        x = LX + Inches(2.03) * q
        b = box(s, x, Inches(5.8), Inches(1.9), Inches(1.2), rgb("F7FAFD"), rgb("D6E4F0"), MSO_SHAPE.ROUNDED_RECTANGLE); b.adjustments[0] = 0.08
        para(b.text_frame, big, 24, col, bold=True, align=PP_ALIGN.CENTER, first=True)
        para(b.text_frame, lab, 10, GRAY, align=PP_ALIGN.CENTER)
    sub3(s, RX, Inches(2.05), HW, f"1. 설비 #3 호기 편중 : {n3}/{len(tq)}건 ({n3/len(tq)*100:.0f}%)",
         "torque 정상 범위 내 발생 : head 평탄도 차이 추정", "Stack팀 협업 평탄도 측정 → edge_cr 상관 분석 (W24)")
    cd = CategoryChartData(); cd.categories = Dt.EQUIP
    cd.add_series("불량 lot", [sum(1 for l in tq if l["eq"] == e) for e in Dt.EQUIP])
    cd.add_series("torque 규격 이탈", [sum(1 for l in tq if l["eq"] == e and (min(l["t"]) < ts["lsl"] or max(l["t"]) > ts["usl"])) for e in Dt.EQUIP])
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, RX, Inches(2.9), HW, Inches(1.95), cd)
    ch = gf.chart; style_chart(ch, 8); chart_title(ch, "설비별 불량 lot / torque 규격 이탈 (건)", 9)
    pl = ch.plots[0]; pl.gap_width = 60; pl.has_data_labels = True
    pl.data_labels.font.size = Pt(8); pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    pl.series[0].format.fill.solid(); pl.series[0].format.fill.fore_color.rgb = BLUE
    pl.series[1].format.fill.solid(); pl.series[1].format.fill.fore_color.rgb = RED
    ch.value_axis.has_major_gridlines = False; ch.value_axis.visible = False
    sub3(s, RX, Inches(4.95), HW, f"2. torque 측정→작업 gap 기준({ts['cycle_hr']}hr) 초과 {n_cyc}건",
         "측정 주기 내 torque 변동 미반영 가능성 : 주기 기준 재검토", "측정 주기 단축 + 평탄도 관리 항목 편입 협의")
    rows = [["구분", "현재 관리", "검증 결과", "개선(안)"],
            ["torque", "2.0~3.0 N·m", "불량 lot 87.5% 규격 내", "기준 유지 + 주기 단축"],
            ["head 평탄도", "관리 항목 외", "#3 호기 편중 (58%)", "관리 항목 편입 검토"],
            ["측정 주기", "8 hr", f"gap 초과 {n_cyc}건", "4 hr / interlock 검토"]]
    tb = table(s, RX, Inches(5.8), HW, [1.1, 1.2, 1.7, 1.6], rows, row_h=0.3, font=9)
else:
    s = new_slide(["[과제 No] [defect] 대응 [관리 인자] 관리 중이나 불량 lot OO% 기준 내",
                   "—> [추가 인자] 검증 진행"], "deep-dive 과제 상세 템플릿 : 관리 인자 실효성 검증 (Excel Torque_FU 시트 결과 반영)")
    heading(s, LX, Inches(1.5), HW, "[defect] 현황 및 [관리 인자] 연계 검증")
    heading(s, RX, Inches(1.5), HW, "추가 인자 검증 및 F/U 계획")
    for X, pairs in [(LX, [("1. [defect] 불량률 OO → OO ppm (달성률 OO%)", "[관리 인자] 관리 기준 : OO~OO [단위]", "목표 OO 대비 [현황]", "KPI 목표 vs 실적 trend"),
                           ("2. 불량 lot OO건 [관리 인자] 이력 연계 : OO건 기준 내", "작업 시점 직전 실측값 연계 : 불량 lot 평균 OO", "[판단]", "기준 내 비율 / 이탈 건수 / Cpk")]),
                     (RX, [("1. [추가 인자] : OO/OO건 (OO%)", "[현상] : [원인 추정]", "[협업 부서] [검증 계획] (WOO)", "설비/head별 불량 건수"),
                           ("2. [관리 기준] 개선 필요 항목 OO건", "[부연] : [부연]", "[개선안]", "현재 관리 / 검증 결과 / 개선(안) 표")])]:
        for q, (a, d, r, v) in enumerate(pairs):
            y = Inches(2.05) + Inches(2.9) * q
            sub3(s, X, y, HW, a, d, r)
            vbox(s, X, y + Inches(0.85), HW, Inches(1.95), v)

# =====================================================================
# 9. 과제 상세 : mean 감소 (일반형)
# =====================================================================
it2 = ITEMS[1]
if EX:
    s = new_slide(["AI-02 BG 후 edge chipping size mean 12.5µm : 후속 dicing crack 연계 risk",
                   f"—> dressing 주기 최적화로 mean {it2['current']}µm (-{(1-it2['current']/it2['base'])*100:.0f}%) 개선 중"],
                  "mean 값 감소형 과제 예시. 주차별 mean 을 계속 입력해 추세 추적, baseline 대비 개선율로 성과화.")
    heading(s, LX, Inches(1.5), HW, "chipping size 현황 및 원인")
    heading(s, RX, Inches(1.5), HW, "개선 action 및 효과")
    sub3(s, LX, Inches(2.05), HW, "1. chipping size mean 12.5µm : 목표 8.0µm",
         "edge chipping : 후속 dicing die crack 연계 risk", "주차별 mean 추적 지표로 KPI 설정")
    kpi_chart(s, LX, Inches(2.9), HW, Inches(1.95), it2, title="chipping size mean (µm) : 목표 vs 실적", size=8)
    sub3(s, LX, Inches(4.95), HW, "2. wheel 마모 주기 대비 dressing 주기 미연계",
         "dressing 300 wafer 주기 : 후반부 chipping size 증가", "dressing 주기·wheel 교체 기준 수치화 필요")
    vbox(s, LX, Inches(5.8), HW, Inches(1.2), "dressing 후 wafer 순번별 chipping size (사진/그래프 삽입)")
    sub3(s, RX, Inches(2.05), HW, "1. dressing 주기 300 → 200 wafer 적용 (W10~)",
         f"mean 12.5 → {it2['current']}µm : 산포 동반 감소", f"목표 달성률 {it2['ach']*100:.0f}% (W{W:02d})")
    cd = CategoryChartData(); cd.categories = ["Baseline", f"현재 (W{W:02d})", "목표"]
    cd.add_series("chipping mean (µm)", [it2["base"], it2["current"], it2["target"]])
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, RX, Inches(2.9), HW, Inches(1.95), cd)
    ch = gf.chart; style_chart(ch, 9, legend=False); chart_title(ch, "chipping size mean (µm)", 9)
    pl = ch.plots[0]; pl.gap_width = 90; pl.has_data_labels = True; pl.data_labels.font.size = Pt(9); pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    pl.vary_by_categories = False
    ser = pl.series[0]; ser.format.fill.solid(); ser.format.fill.fore_color.rgb = BLUE
    for k, c in enumerate(["9E9E9E", "185FA5", "1E7B34"]):
        pt = ser.points[k]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(c)
    ch.value_axis.visible = False; ch.value_axis.has_major_gridlines = False; ch.value_axis.minimum_scale = 0
    sub3(s, RX, Inches(4.95), HW, "2. wheel 교체 기준 수치화 : 잔량 기준 도입 (W24~)",
         "교체 주기 시간 기준 → 잔량·chipping 연동 기준", "목표 8.0µm 달성 후 SOP 반영 (AI-08 연계)")
    rows = [["단계", "내용", "일정", "상태"], ["①", "dressing 주기 최적화", "W06~W12", "완료"],
            ["②", "wheel 교체 기준 수치화", "W24~W28", "진행"], ["③", "효과 검증 · SOP 반영", "W29~W31", "예정"]]
    tb = table(s, RX, Inches(5.8), HW, [0.6, 2.6, 1.3, 1.0], rows, row_h=0.3, font=9)
    set_cell(tb, 1, 3, fill="D6E4F0", color="0C447C", bold=True); set_cell(tb, 2, 3, fill="D4EDDA", color="1E7B34", bold=True)
else:
    s = new_slide(["[과제 No] [불합리 : 현상 · 수치]", "—> [action] 으로 [KPI] OO → OO 개선"], "일반 과제 상세 템플릿 (좌 : 현황·원인 / 우 : action·효과)")
    heading(s, LX, Inches(1.5), HW, "[중제목 : 현황 및 원인]")
    heading(s, RX, Inches(1.5), HW, "[중제목 : 개선 action 및 효과]")
    for X, pairs in [(LX, [("1. [KPI] OO [단위] : 목표 OO", "[부연] : [부연]", "[결과/상황]", "KPI 목표 vs 실적 trend"),
                           ("2. [원인] ", "[부연] : [부연]", "[결과/상황]", "원인 분석 자료 (map / box plot / 사진)")]),
                     (RX, [("1. [action 1] 적용 (WOO~)", "[KPI] OO → OO : [부연]", "목표 달성률 OO%", "Baseline / 현재 / 목표 비교"),
                           ("2. [action 2] (WOO~)", "[부연] : [부연]", "[향후 계획]", "단계별 일정 표")])]:
        for q, (a, d, r, v) in enumerate(pairs):
            y = Inches(2.05) + Inches(2.9) * q
            sub3(s, X, y, HW, a, d, r)
            vbox(s, X, y + Inches(0.85), HW, Inches(1.95), v)

# =====================================================================
# 10. 주간 진척 현황
# =====================================================================
s = new_slide(f"W{W:02d} 주간 진척 현황 —> 지연 1건 (AI-06 6월 2주 완료 예정), 주의 3건 대책 일정 재수립" if EX
              else "WOO 주간 진척 현황 —> [지연·주의 과제 요약]",
              "Excel Weekly_Report 시트의 해당 주차 행을 복사해 갱신. 이슈/지원요청은 팀장님 의사결정 필요 항목 위주로.")
rows = [["No", "과제명", "정", f"KPI\n(W{W:02d})" if EX else "KPI\n(WOO)", "금주 실적", "차주 계획", "이슈 / 지원 요청", "신호"]]
if EX:
    rep = {r[0]: r for r in Dt.REPORTS if r[1] == W}
    for it in ITEMS:
        r = rep.get(it["id"])
        if r is None:
            r = (it["id"], W, "효과 유지 확인 : 온도 편차 1.3℃ 수준 유지", "월 1회 monitoring 전환", "-")
        rows.append([it["id"], it["title"], it["owner"], f'{fmt(it["current"])} {it["unit"]}', r[2], r[3], r[4], it["sig"]])
else:
    rows.append(["AI-01", "[과제명]", "OO", "OO [단위]", "[금주 실적 : 수치 포함]", "[차주 계획]", "[이슈 / 지원 요청]", "정상"])
    for k in range(2, 11): rows.append([f"AI-{k:02d}", "", "", "", "", "", "", ""])
tbl = table(s, Inches(0.4), Inches(1.5), Inches(12.53), [0.6, 2.5, 0.6, 0.9, 3.1, 2.4, 2.2, 0.6], rows, row_h=0.5 if EX else 0.44, font=9,
            aligns=["c", "l", "c", "c", "l", "l", "l", "c"])
for i in range(1, len(rows)):
    sig_cell(tbl, i, 7, rows[i][7])
    if rows[i][6] and rows[i][6] != "-": set_cell(tbl, i, 6, color=RED)

# =====================================================================
# 11. 성과 요약
# =====================================================================
s = new_slide(f"W{W:02d} 기준 평균 목표 달성률 {avg_ach*100:.0f}% —> 연말 목표 달성 위해 주의·지연 {cnt['주의']+cnt['지연']}건 집중 관리" if EX
              else "WOO 기준 평균 목표 달성률 OO% —> [연말 목표 / 집중 관리 과제]",
              "성과 요약. 연말 보고 시 현재 → 최종 실적으로 바꾸고, 개선율(%)과 효과(yld %p, loss 금액)를 추가.")
heading(s, LX, Inches(1.5), HW, "과제별 목표 달성률")
heading(s, RX, Inches(1.5), HW, "baseline 대비 개선 실적")
cd = CategoryChartData()
if EX:
    cd.categories = [f'{it["id"]} {it["kpi"]}' for it in ITEMS]
    cd.add_series("달성률", [round(it["ach"], 3) for it in ITEMS])
else:
    cd.categories = [f"AI-{k:02d} [KPI]" for k in range(1, 9)]
    cd.add_series("달성률", [0.5, 0.4, 0.3, 0.6, 0.2, 0.7, 0.5, 1.0])
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, LX, Inches(2.1), HW, Inches(4.9), cd)
ch = gf.chart; style_chart(ch, 9, legend=False); ch.has_title = False
pl = ch.plots[0]; pl.gap_width = 50; pl.has_data_labels = True
pl.data_labels.number_format = "0%"; pl.data_labels.number_format_is_linked = False; pl.data_labels.font.size = Pt(9)
pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
pl.series[0].format.fill.solid(); pl.series[0].format.fill.fore_color.rgb = BLUE
if EX:
    for k, it in enumerate(ITEMS):
        if it["sig"] in ("지연", "주의"):
            p = pl.series[0].points[k]; p.format.fill.solid(); p.format.fill.fore_color.rgb = rgb("F4A6A6" if it["sig"] == "지연" else "F2C14E")
        if it["sig"] == "완료":
            p = pl.series[0].points[k]; p.format.fill.solid(); p.format.fill.fore_color.rgb = rgb("1E7B34")
ch.category_axis.reverse_order = True; axis_max(ch); ch.category_axis.tick_labels.font.size = Pt(9); ch.category_axis.tick_labels.font.color.rgb = DARK
va = ch.value_axis; va.minimum_scale = 0; va.maximum_scale = 1.2; va.major_unit = 0.2
va.tick_labels.number_format = "0%"; va.tick_labels.number_format_is_linked = False
va.has_major_gridlines = True; va.major_gridlines.format.line.color.rgb = rgb("E5E5E5")
rows = [["No", "KPI (단위)", "Baseline", "현재", "목표", "개선율"]]
if EX:
    for it in ITEMS:
        imp = (it["current"] - it["base"]) / abs(it["base"]) if it["base"] else None
        if it["dir"] == "↓" and imp is not None: imp = -imp
        rows.append([it["id"], f'{it["kpi"]} ({it["unit"]})', fmt(it["base"]), fmt(it["current"]), fmt(it["target"]),
                     f"{imp*100:+.0f}%" if imp is not None else "+3건"])
else:
    rows.append(["AI-01", "[KPI] (단위)", "OO", "OO", "OO", "OO%"])
    for k in range(2, 9): rows.append([f"AI-{k:02d}", "", "", "", "", ""])
tbl = table(s, RX, Inches(2.1), HW, [0.7, 2.3, 0.9, 0.8, 0.8, 0.9], rows, row_h=0.42 if EX else 0.44, font=9, aligns=["c", "l", "c", "c", "c", "c"])
for i in range(1, len(rows)): set_cell(tbl, i, 5, color=rgb("1E7B34"), bold=True)
t = textbox(s, RX, Inches(6.45), HW, Inches(0.55))
para(t, "※ 개선율 = baseline 대비 개선 방향 변화율 (↓ 과제 : 감소율, ↑ 과제 : 증가율)", 9, GRAY, first=True)
para(t, "※ 연말 : 최종 실적 + 효과 환산 (yld %p, loss 금액) 추가", 9, GRAY)

# =====================================================================
# 12. Appendix
# =====================================================================
s = new_slide("[Appendix] 운영 rule : 상태 · 신호 정의 및 보고 프로세스", "운영 rule. 킥오프 미팅에서 합의 후 고정.")
heading(s, LX, Inches(1.5), HW, "신호 / 상태 정의")
heading(s, RX, Inches(1.5), HW, "보고 · 입력 rule")
rows = [["신호", "판정 기준", "조치"],
        ["완료", "상태 = 완료 (효과 검증·표준화 완료)", "월 1회 효과 유지 monitoring"],
        ["정상", "실제 진척 ≥ 계획 진척 -15%p", "계획대로 진행"],
        ["주의", "실제 진척 < 계획 진척 -15%p", "차주 보고 시 만회 계획 제시"],
        ["지연", "완료 목표일 경과 + 미완료", "원인·신규 완료일 보고, 모듈장 review"],
        ["보류/Drop", "우선순위 변경 · 효과 미미", "분기 review 시 사유 기록"]]
tbl = table(s, LX, Inches(2.1), HW, [1.0, 2.7, 2.4], rows, row_h=0.5, font=10, aligns=["c", "l", "l"])
for i, k in enumerate(["완료", "정상", "주의", "지연"], start=1): sig_cell(tbl, i, 0, k)
t = textbox(s, LX, Inches(5.3), HW, Inches(1.5))
para(t, "※ 계획 진척 = (기준일 - 시작일) ÷ (완료 목표일 - 시작일)", 10, GRAY, first=True)
para(t, "※ 주의 기준 15%p 는 Excel 설정 시트에서 변경 가능", 10, GRAY, space=3)
para(t, "※ 목표 변경 시 비고에 '변경일 / 변경 전 → 후 / 사유' 기록", 10, GRAY, space=3)
subs = [("1. 입력 : 담당(정) 매주 목요일까지", "Weekly_KPI 실적 · Master 진척/상태 · Weekly_Report 1행", "부 담당 : 정 담당 부재 시 대체 입력"),
        ("2. 보고 : weekly 금요일 / bi-weekly 격주 금요일", "총괄표 · 간트 · KPI 추이 · 주간 진척 장표 갱신", "주의·지연 과제 우선 보고"),
        ("3. review : 분기 1회 과제 재검토", "목표 재설정 · 과제 추가 / drop · 담당 조정", "연말 baseline 대비 개선율로 성과 정리")]
for q, (a, d, r) in enumerate(subs):
    sub3(s, RX, Inches(2.1) + Inches(0.95) * q, HW, a, d, r)

prs.save(OUT)

# thumbnail
import subprocess, tempfile, os, zipfile, shutil, glob
d = tempfile.mkdtemp()
try:
    subprocess.run([sys.executable, "/root/.claude/skills/synced/5296dd1d-8ee1-4968-870b-206aa46652b6_42df8ede-18d5-4e97-9ed9-3d81346ba374/pptx/scripts/office/soffice.py",
                    "--headless", "--convert-to", "pdf", "--outdir", d, OUT], capture_output=True, timeout=180)
    pdf = glob.glob(os.path.join(d, "*.pdf"))
    if pdf:
        subprocess.run(["pdftoppm", "-jpeg", "-r", "30", "-f", "1", "-l", "1", "-singlefile", pdf[0], os.path.join(d, "t")])
        thumb = open(os.path.join(d, "t.jpg"), "rb").read()
        tmp = OUT + ".tmp"
        with zipfile.ZipFile(OUT) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
            for itm in zi.infolist():
                zo.writestr(itm, thumb if itm.filename == "docProps/thumbnail.jpeg" else zi.read(itm.filename))
        shutil.move(tmp, OUT)
finally:
    shutil.rmtree(d, ignore_errors=True)
print("saved", OUT)
