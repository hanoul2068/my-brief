import sys, datetime as dt
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as CL
from openpyxl.formatting.rule import FormulaRule
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.chart import LineChart, BarChart, Reference
from openpyxl.chart.title import Title
from openpyxl.chart.text import Text, RichText
from openpyxl.chart.data_source import StrRef, StrData, StrVal
from openpyxl.comments import Comment
import data as Dt

MODE = sys.argv[1]           # example | blank
OUT = sys.argv[2]
EX = MODE == "example"
ITEMS = Dt.ITEMS if EX else Dt.ITEMS[:1]
NSLOT = 20
FONT = "맑은 고딕"
NAVY, BLUE, LIGHT, GRAYF = "0C447C", "185FA5", "E6F1FB", "F2F2F2"

def F(**k):
    base = dict(name=FONT, size=10); base.update(k); return Font(**base)
thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
HDR_FILL = PatternFill("solid", fgColor=NAVY)
SUB_FILL = PatternFill("solid", fgColor=LIGHT)
CALC_FILL = PatternFill("solid", fgColor=GRAYF)
WHITE = PatternFill("solid", fgColor="FFFFFF")
INP = F(color="0000FF")
CALC = F(color="000000")
LINK = F(color="008000")
CEN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)

wb = Workbook()
def sheet(name, first=False):
    ws = wb.active if first else wb.create_sheet(name)
    ws.title = name
    ws.sheet_view.showGridLines = False
    return ws

def title(ws, text, sub=None, width=12):
    ws["A1"] = text; ws["A1"].font = F(size=16, bold=True, color=NAVY)
    if sub: ws["A2"] = sub; ws["A2"].font = F(size=9, color="5F5E5A")
    ws.row_dimensions[1].height = 28

def hdr(ws, row, col, text, w=None, fill=HDR_FILL, color="FFFFFF"):
    c = ws.cell(row=row, column=col, value=text)
    c.font = F(bold=True, color=color); c.fill = fill; c.alignment = CEN; c.border = BOX
    if w: ws.column_dimensions[CL(col)].width = w
    return c

def put(ws, row, col, val, font=None, fmt=None, fill=None, align=CEN):
    c = ws.cell(row=row, column=col, value=val)
    c.font = font or INP; c.border = BOX; c.alignment = align
    if fmt: c.number_format = fmt
    if fill: c.fill = fill
    return c

# =====================================================================
# 설정
# =====================================================================
README = sheet("README", first=True)
DASH = sheet("Dashboard")
M = sheet("Action_Master")
G = sheet("Gantt")
K = sheet("Weekly_KPI")
KC = sheet("KPI_Chart")
MS = sheet("Milestone")
WR = sheet("Weekly_Report")
TQ = sheet("Torque_FU")
S = sheet("설정")

title(S, "설정 (기준값 · 드롭다운 목록)", "파란 글씨 = 입력/수정 가능. 목록을 바꾸면 각 시트 드롭다운에 바로 반영됩니다.")
hdr(S, 4, 1, "항목", 22); hdr(S, 4, 2, "값", 16)
put(S, 5, 1, "보고 기준일", CALC, align=LEFT)
put(S, 5, 2, Dt.BASE_DATE if EX else "=TODAY()", INP, "yyyy-mm-dd")
S["B5"].comment = Comment("Gantt 기준선, 계획 진척, 지연 판정의 기준. 비워두지 말 것. 템플릿 기본값 =TODAY()", "tracker")
put(S, 6, 1, "1주차(W01) 시작일 (월)", CALC, align=LEFT)
put(S, 6, 2, Dt.W01, INP, "yyyy-mm-dd")
put(S, 7, 1, "현재 주차", CALC, align=LEFT)
put(S, 7, 2, '="W"&TEXT(INT((B5-B6)/7)+1,"00")', CALC, fill=CALC_FILL)
put(S, 8, 1, "주의 판정 기준 (계획-실제 진척)", CALC, align=LEFT)
put(S, 8, 2, 0.15, INP, "0%")
S["B8"].comment = Comment("실제 진척이 계획 진척보다 이 값 이상 낮으면 '주의'. 가정값(모듈장 판단으로 조정)", "tracker")
put(S, 9, 1, "모듈 / 부서", CALC, align=LEFT)
put(S, 9, 2, "Stack Layer", INP)
put(S, 10, 1, "작성자(모듈장)", CALC, align=LEFT)
put(S, 10, 2, "OOO", INP)
LISTS = [("Step", Dt.STEPS), ("Defect / 항목", Dt.DEFECTS), ("담당자", Dt.OWNERS), ("상태", Dt.STATUS),
         ("우선순위", Dt.PRIORITY), ("방향", Dt.DIRECTION), ("보고주기", Dt.CYCLE), ("유관부서", Dt.DEPTS)]
LISTREF = {}
for j, (nm, vals) in enumerate(LISTS):
    col = 4 + j
    hdr(S, 4, col, nm, 20 if j < 3 else 12)
    for i in range(25):
        v = vals[i] if i < len(vals) else None
        put(S, 5 + i, col, v, INP)
    LISTREF[nm] = f"'설정'!${CL(col)}$5:${CL(col)}$29"
S["D31"] = "※ Step 명칭은 예시입니다. 실제 stack layer step 명칭으로 바꿔 쓰세요. 담당자 OO 이름도 실제 이름으로 교체."
S["D31"].font = F(size=9, color="C00000")
S.freeze_panes = "A5"
BASE = "'설정'!$B$5"; W01C = "'설정'!$B$6"; WARN = "'설정'!$B$8"

def dv(ws, ref, rng, allow_blank=True):
    d = DataValidation(type="list", formula1="=" + ref, allow_blank=allow_blank, showErrorMessage=False)
    ws.add_data_validation(d); d.add(rng)

# =====================================================================
# Action_Master
# =====================================================================
title(M, "Action Item Master (연간 과제 총괄)", "파란 글씨 = 입력 · 회색 칸 = 자동 계산(수식, 수정 금지). 과제 1행 = 1 KPI. 행 순서가 Weekly_KPI / Gantt 와 연동됩니다.")
MC = [  # key, header, width, kind, fmt
 ("id", "No", 7, "in", None), ("step", "Step", 16, "in", None), ("defect", "Defect / 항목", 11, "in", None),
 ("title", "과제명", 30, "in", None), ("problem", "문제 정의 (현상·수치)", 30, "in", None),
 ("cause", "원인 (가설/확인)", 28, "in", None), ("action", "대책 (Action)", 30, "in", None),
 ("kpi", "KPI 지표", 16, "in", None), ("unit", "단위", 7, "in", None), ("dir", "방향\n(↓/↑)", 7, "in", None),
 ("base", "Baseline", 9, "in", "General"), ("target", "목표", 9, "in", "General"),
 ("current", "현재 실적\n(자동)", 10, "calc", "General"), ("ach", "목표 달성률\n(자동)", 10, "calc", "0%"),
 ("imp", "개선율\n(자동)", 9, "calc", "0%"), ("owner", "담당(정)", 9, "in", None), ("sub", "담당(부)", 9, "in", None),
 ("dept", "유관부서", 10, "in", None), ("start", "시작일", 11, "in", "yyyy-mm-dd"), ("end", "완료 목표일", 11, "in", "yyyy-mm-dd"),
 ("plan", "계획 진척\n(자동)", 9, "calc", "0%"), ("prog", "실제 진척\n(입력)", 9, "in", "0%"),
 ("status", "상태", 9, "in", None), ("signal", "일정 신호\n(자동)", 9, "calc", None),
 ("prio", "우선\n순위", 6, "in", None), ("cycle", "보고주기", 10, "in", None),
 ("lastwk", "최근 입력\n주차(자동)", 9, "calc", None), ("note", "비고", 24, "in", None),
]
COL = {k: i + 1 for i, (k, *_r) in enumerate(MC)}
def MCL(k): return CL(COL[k])
HR = 4; R0 = 5
for i, (k, h, w, kind, fmt) in enumerate(MC):
    hdr(M, HR, i + 1, h, w, fill=HDR_FILL if kind == "in" else PatternFill("solid", fgColor="5F5E5A"))
M.row_dimensions[HR].height = 34
# Weekly_KPI layout
KR0 = 6; KC0 = 6   # 데이터 첫 행/ 첫 주차 열 (F)
KLAST = CL(KC0 + Dt.NWEEK - 1)  # BE
def krow_t(i): return KR0 + 2 * i
def krow_a(i): return KR0 + 2 * i + 1

for i in range(NSLOT):
    r = R0 + i
    it = ITEMS[i] if i < len(ITEMS) else None
    ar = krow_a(i)
    arng = f"Weekly_KPI!${CL(KC0)}${ar}:${KLAST}${ar}"
    A = lambda k: f"{MCL(k)}{r}"
    calc = {
      "current": f'=IF({A("id")}="","",IFERROR(LOOKUP(2,1/({arng}<>""),{arng}),""))',
      "ach": f'=IF(OR({A("current")}="",{A("base")}="",{A("target")}=""),"",IF({A("target")}={A("base")},"",({A("current")}-{A("base")})/({A("target")}-{A("base")})))',
      "imp": f'=IF(OR({A("current")}="",{A("base")}="",{A("base")}=0),"",IF({A("dir")}="↑",({A("current")}-{A("base")})/ABS({A("base")}),({A("base")}-{A("current")})/ABS({A("base")})))',
      "plan": f'=IF(OR({A("start")}="",{A("end")}=""),"",IF({A("end")}<={A("start")},1,MAX(0,MIN(1,({BASE}-{A("start")})/({A("end")}-{A("start")})))))',
      "signal": f'=IF({A("id")}="","",IF({A("status")}="완료","완료",IF(OR({A("status")}="보류",{A("status")}="Drop"),{A("status")},IF(AND({A("end")}<>"",{BASE}>{A("end")}),"지연",IF(AND({A("plan")}<>"",{A("prog")}<>"",{A("prog")}<{A("plan")}-{WARN}),"주의","정상")))))',
      "lastwk": f'=IF({A("id")}="","",IFERROR(LOOKUP(2,1/({arng}<>""),Weekly_KPI!${CL(KC0)}$5:${KLAST}$5),"-"))',
    }
    for k, h, w, kind, fmt in MC:
        if kind == "calc":
            put(M, r, COL[k], calc[k], CALC, fmt, CALC_FILL)
        else:
            v = None
            if it:
                v = {"title": it["title"], "prog": it["prog"], "owner": it["owner"]}.get(k, it.get(k))
                if k == "note" and EX:
                    v = {"AI-01": "Torque_FU 시트 연계", "AI-06": "완료 목표일 경과 : 6월 2주 완료 예정", "AI-04": "#2 설비 matching 2주 지연"}.get(it["id"])
                if not EX and k == "note": v = "← 예시 행 : 내용 바꿔 쓰거나 삭제"
            put(M, r, COL[k], v, INP, fmt, align=LEFT if k in ("title", "problem", "cause", "action", "note") else CEN)
    M.row_dimensions[r].height = 42
RL = R0 + NSLOT - 1
dv(M, LISTREF["Step"], f"{MCL('step')}{R0}:{MCL('step')}{RL}")
dv(M, LISTREF["Defect / 항목"], f"{MCL('defect')}{R0}:{MCL('defect')}{RL}")
dv(M, LISTREF["담당자"], f"{MCL('owner')}{R0}:{MCL('sub')}{RL}")
dv(M, LISTREF["상태"], f"{MCL('status')}{R0}:{MCL('status')}{RL}")
dv(M, LISTREF["우선순위"], f"{MCL('prio')}{R0}:{MCL('prio')}{RL}")
dv(M, LISTREF["방향"], f"{MCL('dir')}{R0}:{MCL('dir')}{RL}")
dv(M, LISTREF["보고주기"], f"{MCL('cycle')}{R0}:{MCL('cycle')}{RL}")
dv(M, LISTREF["유관부서"], f"{MCL('dept')}{R0}:{MCL('dept')}{RL}")
sig = f"{MCL('signal')}{R0}:{MCL('signal')}{RL}"
for txt, col in [("지연", "F8D7DA"), ("주의", "FFF3CD"), ("정상", "D4EDDA"), ("완료", "D6E4F0")]:
    M.conditional_formatting.add(sig, FormulaRule(formula=[f'{MCL("signal")}{R0}="{txt}"'], fill=PatternFill("solid", fgColor=col), font=Font(bold=True)))
M.freeze_panes = M.cell(row=R0, column=COL["title"] + 1)
M.auto_filter.ref = f"A{HR}:{CL(len(MC))}{RL}"
M[f"A{RL+2}"] = "※ 달성률 = (현재-Baseline)/(목표-Baseline) : ↓/↑ 방향 모두 동일 수식. 개선율 = Baseline 대비 개선 %. 현재 실적 = Weekly_KPI 실적 행의 마지막 입력값."
M[f"A{RL+2}"].font = F(size=9, color="5F5E5A")
M[f"A{RL+3}"] = "※ 일정 신호 : 기준일 > 완료목표일 & 미완료 → 지연 / 실제 진척 < 계획 진척 - 주의기준(설정) → 주의 / 그 외 정상."
M[f"A{RL+3}"].font = F(size=9, color="5F5E5A")

def MREF(k, i, absolute=True):
    return f"Action_Master!${MCL(k)}${R0+i}"

# =====================================================================
# Weekly_KPI
# =====================================================================
title(K, "Weekly KPI 추적 (주차별 목표 / 실적)", "실적 행(파란 글씨)에 주차별 값 입력 · 목표 행은 Baseline→목표 직선 glide path 자동 계산 (필요시 값을 덮어써도 됨) · Bi-weekly 과제는 해당 주차만 입력")
heads = [("No", 7), ("과제명", 28), ("KPI (단위)", 16), ("방향", 5), ("구분", 6)]
for j, (h, w) in enumerate(heads):
    hdr(K, 5, j + 1, h, w); K.merge_cells(start_row=3, start_column=j + 1, end_row=4, end_column=j + 1)
    hdr(K, 3, j + 1, None)
for n in range(1, Dt.NWEEK + 1):
    c = KC0 + n - 1; L = CL(c)
    put(K, 3, c, f'=IF(MONTH({L}4)<>MONTH({L}4-7),MONTH({L}4)&"월","")' if n > 1 else '=MONTH(F4)&"월"', F(bold=True, color=NAVY), fill=SUB_FILL)
    put(K, 4, c, f"={W01C}+7*{n-1}", CALC, "m/d", CALC_FILL)
    hdr(K, 5, c, f"W{n:02d}", 7)
for i in range(NSLOT):
    tr, ar = krow_t(i), krow_a(i)
    it = ITEMS[i] if i < len(ITEMS) else None
    put(K, tr, 1, f'=IF({MREF("id",i)}="","",{MREF("id",i)})', LINK)
    put(K, tr, 2, f'=IF({MREF("title",i)}="","",{MREF("title",i)})', LINK, align=LEFT)
    put(K, tr, 3, f'=IF({MREF("kpi",i)}="","",{MREF("kpi",i)}&" ("&{MREF("unit",i)}&")")', LINK)
    put(K, tr, 4, f'=IF({MREF("dir",i)}="","",{MREF("dir",i)})', LINK)
    for rr in (tr, ar):
        pass
    K.merge_cells(start_row=tr, start_column=1, end_row=ar, end_column=1)
    K.merge_cells(start_row=tr, start_column=2, end_row=ar, end_column=2)
    K.merge_cells(start_row=tr, start_column=3, end_row=ar, end_column=3)
    K.merge_cells(start_row=tr, start_column=4, end_row=ar, end_column=4)
    for cc in range(1, 5): K.cell(row=ar, column=cc).border = BOX
    put(K, tr, 5, "목표", CALC, fill=CALC_FILL)
    put(K, ar, 5, "실적", F(bold=True, color=BLUE))
    b, t, s, e = MREF("base", i), MREF("target", i), MREF("start", i), MREF("end", i)
    for n in range(1, Dt.NWEEK + 1):
        c = KC0 + n - 1; L = CL(c)
        wk = f"{L}$4"
        f = (f'=IF(OR($A${tr}="",{b}="",{t}="",{s}="",{e}=""),"",IF({wk}+6<{s},"",IF(OR({wk}>={e},{e}<={s}),{t},'
             f'ROUND({b}+({t}-{b})*({wk}-{s})/({e}-{s}),3))))')
        put(K, tr, c, f, CALC, "General", CALC_FILL)
        v = it["actuals"].get(n) if it else None
        if it and not EX and n > 3: v = None
        put(K, ar, c, v, INP, "General")
K.freeze_panes = K.cell(row=6, column=KC0)
KL = krow_a(NSLOT - 1)
# 기준 주차 강조
wrng = f"{CL(KC0)}3:{KLAST}{KL}"
K.conditional_formatting.add(wrng, FormulaRule(formula=[f"AND({CL(KC0)}$4<={BASE},{CL(KC0)}$4+6>={BASE})"],
                             border=Border(left=Side(style="medium", color="E46C0A"), right=Side(style="medium", color="E46C0A"))))
K[f"A{KL+2}"] = "※ 목표 행 수식 : 시작 주차 이전 공란 → 시작~완료목표일 직선 감소/증가 → 완료 후 목표값 유지. 단계별 목표(예: 분기 계단식)가 있으면 목표 행에 직접 값 입력."
K[f"A{KL+2}"].font = F(size=9, color="5F5E5A")
K[f"A{KL+3}"] = "※ 주황 테두리 열 = 보고 기준일 주차. 실적 행 비어있는 주는 그래프에서 끊김 없이 건너뜀."
K[f"A{KL+3}"].font = F(size=9, color="5F5E5A")

# =====================================================================
# Gantt
# =====================================================================
title(G, "연간 추진 일정 (Gantt)", "자동 생성 : Action_Master 시작/완료일·진척률 + Milestone 계획일(◆). 연한 파랑 = 계획 기간, 진한 파랑 = 진척 구간, 빨강 = 완료일 경과 미완료, 주황 테두리 = 기준 주차")
gh = [("No", 7), ("과제명", 40), ("담당(정/부)", 13), ("시작", 9), ("완료", 9), ("진척", 6), ("신호", 6)]
GC0 = len(gh) + 1
for j, (h, w) in enumerate(gh):
    hdr(G, 5, j + 1, h, w); hdr(G, 3, j + 1, None); G.merge_cells(start_row=3, start_column=j + 1, end_row=4, end_column=j + 1)
for n in range(1, Dt.NWEEK + 1):
    c = GC0 + n - 1; L = CL(c)
    put(G, 3, c, f'=IF(MONTH({L}4)<>MONTH({L}4-7),MONTH({L}4)&"월","")' if n > 1 else f'=MONTH({L}4)&"월"', F(bold=True, color=NAVY, size=9), fill=SUB_FILL)
    put(G, 4, c, f"={W01C}+7*{n-1}", F(size=7), "d", CALC_FILL)
    hdr(G, 5, c, f"{n}", 3.2).font = F(bold=True, color="FFFFFF", size=7)
GR0 = 6
for i in range(NSLOT):
    r = GR0 + i
    put(G, r, 1, f'=IF({MREF("id",i)}="","",{MREF("id",i)})', LINK)
    put(G, r, 2, f'=IF({MREF("title",i)}="","",{MREF("title",i)})', LINK, align=LEFT)
    put(G, r, 3, f'=IF({MREF("owner",i)}="","",{MREF("owner",i)}&" / "&{MREF("sub",i)})', LINK)
    put(G, r, 4, f'=IF({MREF("start",i)}="","",{MREF("start",i)})', LINK, "m/d")
    put(G, r, 5, f'=IF({MREF("end",i)}="","",{MREF("end",i)})', LINK, "m/d")
    put(G, r, 6, f'=IF({MREF("prog",i)}="","",{MREF("prog",i)})', LINK, "0%")
    put(G, r, 7, f'=IF({MREF("signal",i)}="","",{MREF("signal",i)})', LINK)
    for n in range(1, Dt.NWEEK + 1):
        c = GC0 + n - 1; L = CL(c)
        f = f'=IF($A{r}="","",IF(COUNTIFS(Milestone!$A$5:$A$300,$A{r},Milestone!$C$5:$C$300,">="&{L}$4,Milestone!$C$5:$C$300,"<"&({L}$4+7))>0,"◆",""))'
        cc = put(G, r, c, f, F(size=8, bold=True, color="C00000"))
        cc.border = Border(left=Side(style="hair", color="D9D9D9"), right=Side(style="hair", color="D9D9D9"),
                           top=Side(style="thin", color="BFBFBF"), bottom=Side(style="thin", color="BFBFBF"))
    G.row_dimensions[r].height = 22
GL = GR0 + NSLOT - 1
F0 = CL(GC0); rng = f"{F0}{GR0}:{CL(GC0+Dt.NWEEK-1)}{GL}"
inplan = f"AND($D{GR0}<>\"\",{F0}$4+6>=$D{GR0},{F0}$4<=$E{GR0})"
done_until = f"$D{GR0}+($E{GR0}-$D{GR0})*N($F{GR0})"
G.conditional_formatting.add(rng, FormulaRule(formula=[f"AND({inplan},{F0}$4<={done_until})"], fill=PatternFill("solid", fgColor=BLUE), font=Font(color="FFFFFF"), stopIfTrue=True))
G.conditional_formatting.add(rng, FormulaRule(formula=[f"AND({inplan},$G{GR0}=\"지연\")"], fill=PatternFill("solid", fgColor="F4A6A6"), stopIfTrue=True))
G.conditional_formatting.add(rng, FormulaRule(formula=[f"AND($G{GR0}=\"지연\",{F0}$4>$E{GR0},{F0}$4<={BASE})"], fill=PatternFill("solid", fgColor="E06666"), stopIfTrue=True))
G.conditional_formatting.add(rng, FormulaRule(formula=[inplan], fill=PatternFill("solid", fgColor="BDD7EE"), stopIfTrue=True))
G.conditional_formatting.add(f"{F0}3:{CL(GC0+Dt.NWEEK-1)}{GL}", FormulaRule(formula=[f"AND({F0}$4<={BASE},{F0}$4+6>={BASE})"],
                             border=Border(left=Side(style="medium", color="E46C0A"), right=Side(style="medium", color="E46C0A"))))
gsig = f"G{GR0}:G{GL}"
for txt, col in [("지연", "F8D7DA"), ("주의", "FFF3CD"), ("정상", "D4EDDA"), ("완료", "D6E4F0")]:
    G.conditional_formatting.add(gsig, FormulaRule(formula=[f'G{GR0}="{txt}"'], fill=PatternFill("solid", fgColor=col)))
G.freeze_panes = G.cell(row=GR0, column=GC0)
G.sheet_view.zoomScale = 85
G[f"B{GL+2}"] = "※ 이 시트는 전부 자동입니다. 일정 변경은 Action_Master(시작/완료일, 진척) · Milestone(계획일)에서 하세요."
G[f"B{GL+2}"].font = F(size=9, color="5F5E5A")
G.page_setup.orientation = "landscape"; G.page_setup.fitToWidth = 1; G.sheet_properties.pageSetUpPr.fitToPage = True

# =====================================================================
# Milestone
# =====================================================================
title(MS, "Milestone 관리", "과제별 주요 일정(계획일/실적일) · 계획일은 Gantt 에 ◆ 로 표시 · 상태 자동 판정")
mh = [("No", 8), ("마일스톤", 26), ("계획일", 12), ("실적일", 12), ("상태(자동)", 10), ("차이(일)", 9), ("과제명(자동)", 32), ("비고", 28)]
for j, (h, w) in enumerate(mh):
    hdr(MS, 4, j + 1, h, w, fill=HDR_FILL if j in (0, 1, 2, 3, 7) else PatternFill("solid", fgColor="5F5E5A"))
mlist = Dt.MILESTONES if EX else Dt.MILESTONES[:4]
for i in range(120):
    r = 5 + i
    m = mlist[i] if i < len(mlist) else None
    put(MS, r, 1, m["id"] if m else None, INP)
    put(MS, r, 2, m["name"] if m else None, INP, align=LEFT)
    put(MS, r, 3, m["plan"] if m else None, INP, "yyyy-mm-dd")
    put(MS, r, 4, (m["actual"] if m else None), INP, "yyyy-mm-dd")
    put(MS, r, 5, f'=IF(A{r}="","",IF(D{r}<>"","완료",IF(C{r}="","",IF(C{r}<{BASE},"지연","예정"))))', CALC, fill=CALC_FILL)
    put(MS, r, 6, f'=IF(OR(C{r}="",D{r}=""),"",D{r}-C{r})', CALC, "0;-0;0", CALC_FILL)
    put(MS, r, 7, f'=IF(A{r}="","",IFERROR(INDEX(Action_Master!${MCL("title")}${R0}:${MCL("title")}${RL},MATCH(A{r},Action_Master!$A${R0}:$A${RL},0)),"No 확인"))', LINK, align=LEFT)
    put(MS, r, 8, None, INP, align=LEFT)
dv(MS, f"Action_Master!$A${R0}:$A${RL}", "A5:A124")
for txt, col in [("지연", "F8D7DA"), ("완료", "D6E4F0"), ("예정", "FFFFFF")]:
    MS.conditional_formatting.add("E5:E124", FormulaRule(formula=[f'E5="{txt}"'], fill=PatternFill("solid", fgColor=col)))
MS.freeze_panes = "C5"; MS.auto_filter.ref = "A4:H124"

# =====================================================================
# Weekly_Report
# =====================================================================
title(WR, "주간 / 격주 보고 Log", "보고 때마다 과제별 1행 누적 · 필터로 과제별 이력 조회 · 팀장 보고 장표 '주간 진척 현황' 원본")
wh = [("보고일", 11), ("주차", 7), ("No", 8), ("과제명(자동)", 28), ("담당(자동)", 9), ("KPI 실적(자동)", 11), ("금주 실적", 40), ("차주 계획", 34), ("이슈 / 지원 요청", 30), ("신호(자동)", 9)]
for j, (h, w) in enumerate(wh):
    hdr(WR, 4, j + 1, h, w, fill=HDR_FILL if j in (0, 2, 6, 7, 8) else PatternFill("solid", fgColor="5F5E5A"))
rep = Dt.REPORTS if EX else Dt.REPORTS[:1]
for i in range(200):
    r = 5 + i
    x = rep[i] if i < len(rep) else None
    put(WR, r, 1, (Dt.wk_start(x[1]) + dt.timedelta(days=4)) if x else None, INP, "yyyy-mm-dd")
    put(WR, r, 2, f'=IF(A{r}="","","W"&TEXT(INT((A{r}-{W01C})/7)+1,"00"))', CALC, fill=CALC_FILL)
    put(WR, r, 3, x[0] if x else None, INP)
    lk = lambda k: f'=IF(C{r}="","",IFERROR(INDEX(Action_Master!${MCL(k)}${R0}:${MCL(k)}${RL},MATCH(C{r},Action_Master!$A${R0}:$A${RL},0)),""))'
    put(WR, r, 4, lk("title"), LINK, align=LEFT)
    put(WR, r, 5, lk("owner"), LINK)
    # 해당 주차 실적 값
    kref = f"Weekly_KPI!${CL(KC0)}$6:${KLAST}$45"
    put(WR, r, 6, f'=IF(OR(C{r}="",A{r}=""),"",IFERROR(INDEX({kref},MATCH(C{r},Weekly_KPI!$A$6:$A$45,0)+1,INT((A{r}-{W01C})/7)+1)&"",""))', LINK)
    put(WR, r, 7, x[2] if x else None, INP, align=LEFT)
    put(WR, r, 8, x[3] if x else None, INP, align=LEFT)
    put(WR, r, 9, x[4] if x else None, INP, align=LEFT)
    put(WR, r, 10, lk("signal"), LINK)
    WR.row_dimensions[r].height = 30
dv(WR, f"Action_Master!$A${R0}:$A${RL}", "C5:C204")
for txt, col in [("지연", "F8D7DA"), ("주의", "FFF3CD"), ("정상", "D4EDDA"), ("완료", "D6E4F0")]:
    WR.conditional_formatting.add("J5:J204", FormulaRule(formula=[f'J5="{txt}"'], fill=PatternFill("solid", fgColor=col)))
WR.freeze_panes = "D5"; WR.auto_filter.ref = "A4:J204"

# =====================================================================
# Torque_FU
# =====================================================================
title(TQ, "Deep-dive F/U : edge_cr ↔ stack torque 관리 실효성 검증" if EX else "Deep-dive F/U : [defect] ↔ [관리 인자] 관리 실효성 검증",
      "불량 발생 자재(lot)의 관리 인자(torque) 실측 이력을 연계 → '관리 기준 내에서도 불량이 나는가?' 를 수치로 확인. 다른 과제(온도, 압력 등)도 복사해서 사용")
TS = Dt.TQ_SPEC
hdr(TQ, 4, 1, "관리 기준 (입력)", 18); TQ.merge_cells("A4:B4"); hdr(TQ, 4, 2, None)
spec_rows = [("관리 인자", "Torque" if EX else "[인자]"), ("단위", TS["unit"]), ("LSL", TS["lsl"]), ("Target", TS["tgt"]), ("USL", TS["usl"]),
             ("측정 주기 기준 (hr)", TS["cycle_hr"])]
for j, (a, v) in enumerate(spec_rows):
    put(TQ, 5 + j, 1, a, CALC, align=LEFT); put(TQ, 5 + j, 2, v, INP)
TQ.column_dimensions["B"].width = 11
LSL, TGT, USL, CYC = "$B$7", "$B$8", "$B$9", "$B$10"
# Summary
hdr(TQ, 4, 4, "검증 요약 (자동)", 30); TQ.merge_cells("D4:F4"); hdr(TQ, 4, 5, None); hdr(TQ, 4, 6, None)
TR0, TN = 20, 60
TRL = TR0 + TN - 1
lotc, avgc, judc, gapc, cyc_c, eqc = f"C{TR0}:C{TRL}", f"J{TR0}:J{TRL}", f"L{TR0}:L{TRL}", f"M{TR0}:M{TRL}", f"N{TR0}:N{TRL}", f"E{TR0}:E{TRL}"
summ = [
 ("불량 발생 lot 수", f"=COUNTA({lotc})", "0"),
 ("관리 기준 내 lot 수", f'=COUNTIF({judc},"규격 내")', "0"),
 ("관리 기준 내 비율", f'=IF(E5=0,"",E6/E5)', "0.0%"),
 ("불량 lot 평균 (실측)", f'=IF(COUNT({avgc})=0,"",AVERAGE({avgc}))', "0.00"),
 ("양품 monitoring 평균", '=IF(COUNT(W6:W200)=0,"",AVERAGE(W6:W200))', "0.00"),
 ("양품 monitoring Cpk", '=IF(COUNT(W6:W200)<2,"",MIN($B$9-E9,E9-$B$7)/(3*STDEV(W6:W200)))', "0.00"),
 ("측정 주기 미준수 lot", f'=COUNTIF({cyc_c},"미준수")', "0"),
 ("최다 발생 설비 / 건수", '=IF(MAX(I3:I14)=0,"",INDEX(H3:H14,MATCH(MAX(I3:I14),I3:I14,0))&" / "&MAX(I3:I14)&"건")', None),
 ("판단", '=IF(E5=0,"",IF(E7>=0.7,"관리 기준 내 불량 다수 → torque 외 인자 추가 검증 필요",IF(E7>=0.4,"혼재 → torque 기준 재설정 + 타 인자 병행 검증","기준 이탈 불량 다수 → 관리 기준 준수·interlock 강화")))', None),
]
for j, (a, f, fmt) in enumerate(summ):
    r = 5 + j
    put(TQ, r, 4, a, CALC, align=LEFT)
    c = put(TQ, r, 5, f, F(bold=True), fmt, CALC_FILL)
    TQ.merge_cells(start_row=r, start_column=5, end_row=r, end_column=6)
TQ["E13"].alignment = LEFT; TQ.row_dimensions[13].height = 32
TQ.column_dimensions["E"].width = 22; TQ.column_dimensions["F"].width = 22
# 설비별 집계
hdr(TQ, 2, 8, "설비", 8); hdr(TQ, 2, 9, "불량 lot", 8); hdr(TQ, 2, 10, "기준 이탈", 9)
for j in range(12):
    r = 3 + j
    put(TQ, r, 8, Dt.EQUIP[j] if j < len(Dt.EQUIP) else None, INP)
    put(TQ, r, 9, f'=IF(H{r}="","",COUNTIF({eqc},H{r}))', CALC, "0", CALC_FILL)
    put(TQ, r, 10, f'=IF(H{r}="","",COUNTIFS({eqc},H{r},{judc},"기준 이탈"))', CALC, "0", CALC_FILL)
# 불량 lot table
th = [("No", 5), ("발생일", 11), ("Lot ID", 12), ("Die/Slot", 8), ("설비", 8), ("Head", 9), ("실측 #1", 8), ("실측 #2", 8), ("실측 #3", 9),
      ("평균(자동)", 10), ("Range(자동)", 10), ("판정(자동)", 10), ("측정→작업 gap(hr)", 11), ("주기 준수(자동)", 11), ("불량 위치", 10), ("추가 의심 인자", 14), ("조치 / F-U", 24)]
TQ[f"A{TR0-2}"] = "▶ 불량 발생 lot 별 관리 인자 실측 이력 (MES/설비 log 에서 작업 시점 직전 측정값 연계)"
TQ[f"A{TR0-2}"].font = F(bold=True, color=NAVY, size=11)
for j, (h, w) in enumerate(th):
    hdr(TQ, TR0 - 1, j + 1, h, max(w, TQ.column_dimensions[CL(j + 1)].width or 0), fill=HDR_FILL if j not in (9, 10, 11, 13) else PatternFill("solid", fgColor="5F5E5A"))
lots = Dt.TQ_LOTS if EX else Dt.TQ_LOTS[:2]
for i in range(TN):
    r = TR0 + i
    x = lots[i] if i < len(lots) else None
    put(TQ, r, 1, f'=IF(C{r}="","",ROW()-{TR0-1})', CALC, fill=CALC_FILL)
    vals = [x["date"], x["lot"], x["die"], x["eq"], x["head"], *x["t"]] if x else [None] * 8
    fmts = ["yyyy-mm-dd", None, None, None, None, "0.00", "0.00", "0.00"]
    for j, (v, fm) in enumerate(zip(vals, fmts)):
        put(TQ, r, 2 + j, v, INP, fm)
    put(TQ, r, 10, f'=IF(COUNT(G{r}:I{r})=0,"",AVERAGE(G{r}:I{r}))', CALC, "0.00", CALC_FILL)
    put(TQ, r, 11, f'=IF(COUNT(G{r}:I{r})<2,"",MAX(G{r}:I{r})-MIN(G{r}:I{r}))', CALC, "0.00", CALC_FILL)
    put(TQ, r, 12, f'=IF(J{r}="","",IF(OR(MIN(G{r}:I{r})<{LSL},MAX(G{r}:I{r})>{USL}),"기준 이탈","규격 내"))', CALC, fill=CALC_FILL)
    put(TQ, r, 13, x["gap"] if x else None, INP, "0.0")
    put(TQ, r, 14, f'=IF(M{r}="","",IF(M{r}<={CYC},"준수","미준수"))', CALC, fill=CALC_FILL)
    put(TQ, r, 15, x["pos"] if x else None, INP)
    put(TQ, r, 16, x["sus"] if x else None, INP)
    put(TQ, r, 17, ("#3 head 평탄도 측정 중" if x and x["eq"] == "#3" else None), INP, align=LEFT)
dv(TQ, "$H$3:$H$14", f"E{TR0}:E{TRL}")
TQ.conditional_formatting.add(f"L{TR0}:L{TRL}", FormulaRule(formula=[f'L{TR0}="기준 이탈"'], fill=PatternFill("solid", fgColor="F8D7DA"), font=Font(bold=True, color="C00000")))
TQ.conditional_formatting.add(f"N{TR0}:N{TRL}", FormulaRule(formula=[f'N{TR0}="미준수"'], fill=PatternFill("solid", fgColor="FFF3CD")))
# 양품 monitoring
hdr(TQ, 5, 22, "양품 측정일", 13); hdr(TQ, 5, 23, "실측값", 9); hdr(TQ, 5, 24, "설비", 8)
TQ["V4"] = "▶ 정상 lot 정기 측정 (비교군 · Cpk 산출)"; TQ["V4"].font = F(bold=True, color=NAVY)
mon = Dt.TQ_MON if EX else Dt.TQ_MON[:3]
for i in range(195):
    r = 6 + i
    x = mon[i] if i < len(mon) else None
    put(TQ, r, 22, x["date"] if x else None, INP, "yyyy-mm-dd")
    put(TQ, r, 23, x["v"] if x else None, INP, "0.00")
    put(TQ, r, 24, x["eq"] if x else None, INP)
# chart : 설비별
ch = BarChart(); ch.type = "col"; ch.grouping = "clustered"
ch.add_data(Reference(TQ, min_col=9, max_col=10, min_row=2, max_row=8), titles_from_data=True)
ch.set_categories(Reference(TQ, min_col=8, min_row=3, max_row=8))
ch.title = "설비별 불량 lot / 기준 이탈"; ch.height = 6.5; ch.width = 11
ch.y_axis.title = "lot"; ch.legend.position = "b"
TQ.add_chart(ch, "L3")
TQ.freeze_panes = f"A{TR0}"

# =====================================================================
# KPI_Chart (과제별 목표 vs 실적 추이)
# =====================================================================
title(KC, "KPI 추이 Chart (과제별 목표 vs 실적)", "Weekly_KPI 연동 자동 그래프 · 제목은 Action_Master 과제명 자동 반영 · 그래프 복사 → PPT 붙여넣기 가능")
nchart = len(ITEMS) if EX else 6
for i in range(nchart):
    KC.cell(row=3 + i, column=30, value=f'=IF({MREF("id",i)}="","(빈 슬롯)",{MREF("id",i)}&"  "&{MREF("kpi",i)}&" ("&{MREF("unit",i)}&", "&{MREF("dir",i)}&")")').font = F(color="FFFFFF")
    lc = LineChart()
    lc.height = 7; lc.width = 15.5
    tr, ar = krow_t(i), krow_a(i)
    lc.add_data(Reference(K, min_col=KC0, max_col=KC0 + Dt.NWEEK - 1, min_row=tr), from_rows=True, titles_from_data=False)
    lc.add_data(Reference(K, min_col=KC0, max_col=KC0 + Dt.NWEEK - 1, min_row=ar), from_rows=True, titles_from_data=False)
    lc.set_categories(Reference(K, min_col=KC0, max_col=KC0 + Dt.NWEEK - 1, min_row=5))
    from openpyxl.chart.series import SeriesLabel
    lc.series[0].tx = SeriesLabel(v="목표"); lc.series[1].tx = SeriesLabel(v="실적")
    s0, s1 = lc.series
    s0.graphicalProperties.line.solidFill = "9E9E9E"; s0.graphicalProperties.line.dashStyle = "dash"; s0.graphicalProperties.line.width = 19050
    s1.graphicalProperties.line.solidFill = BLUE; s1.graphicalProperties.line.width = 28575
    s1.marker.symbol = "circle"; s1.marker.size = 5
    s1.marker.graphicalProperties.solidFill = BLUE; s1.marker.graphicalProperties.line.solidFill = BLUE
    s0.smooth = False; s1.smooth = False
    it_ = ITEMS[i] if i < len(ITEMS) else None
    cache = f'{it_["id"]}  {it_["kpi"]} ({it_["unit"]}, {it_["dir"]})' if it_ else "(빈 슬롯)"
    lc.title = Title(tx=Text(strRef=StrRef(f"'KPI_Chart'!$AD${3+i}", strCache=StrData(ptCount=1, pt=[StrVal(idx=0, v=cache)]))), overlay=False)
    lc.legend.position = "b"
    lc.x_axis.tickLblSkip = 4
    lc.display_blanks = "span"
    lc.x_axis.delete = False; lc.y_axis.delete = False
    lc.y_axis.majorGridlines.spPr = None
    row = 4 + (i // 2) * 15; col = "A" if i % 2 == 0 else "J"
    KC.add_chart(lc, f"{col}{row}")
KC.column_dimensions["AD"].hidden = True

# =====================================================================
# Dashboard
# =====================================================================
title(DASH, "Stack Layer Action Item Dashboard", None)
DASH["A2"] = '="기준일 : "&TEXT(\'설정\'!B5,"yyyy-mm-dd")&"  ("&\'설정\'!B7&")   |   "&\'설정\'!B9&"   |   작성 : "&\'설정\'!B10'
DASH["A2"].font = F(size=10, color="5F5E5A")
cards = [("전체 과제", f'=COUNTA(Action_Master!$A${R0}:$A${RL})', "0"),
         ("완료", f'=COUNTIF(Action_Master!${MCL("signal")}${R0}:${MCL("signal")}${RL},"완료")', "0"),
         ("정상", f'=COUNTIF(Action_Master!${MCL("signal")}${R0}:${MCL("signal")}${RL},"정상")', "0"),
         ("주의", f'=COUNTIF(Action_Master!${MCL("signal")}${R0}:${MCL("signal")}${RL},"주의")', "0"),
         ("지연", f'=COUNTIF(Action_Master!${MCL("signal")}${R0}:${MCL("signal")}${RL},"지연")', "0"),
         ("평균 진척", f'=IFERROR(AVERAGE(Action_Master!${MCL("prog")}${R0}:${MCL("prog")}${RL}),0)', "0%"),
         ("평균 목표 달성률", f'=IFERROR(AVERAGE(Action_Master!${MCL("ach")}${R0}:${MCL("ach")}${RL}),0)', "0%")]
card_col = {"완료": "D6E4F0", "정상": "D4EDDA", "주의": "FFF3CD", "지연": "F8D7DA"}
for j, (lab, f, fmt) in enumerate(cards):
    c0 = 1 + j * 2
    DASH.merge_cells(start_row=4, start_column=c0, end_row=4, end_column=c0 + 1)
    DASH.merge_cells(start_row=5, start_column=c0, end_row=5, end_column=c0 + 1)
    a = DASH.cell(row=4, column=c0, value=lab); a.font = F(bold=True, color="FFFFFF"); a.fill = HDR_FILL; a.alignment = CEN
    b = DASH.cell(row=5, column=c0, value=f); b.font = F(bold=True, size=20, color=NAVY); b.alignment = CEN
    b.fill = PatternFill("solid", fgColor=card_col.get(lab, LIGHT)); b.number_format = fmt
    for cc in (c0, c0 + 1):
        DASH.cell(row=4, column=cc).border = BOX; DASH.cell(row=5, column=cc).border = BOX
DASH.row_dimensions[5].height = 40
dh = [("No", 7), ("Step", 15), ("과제명", 36), ("KPI", 15), ("단위", 6), ("Baseline", 9), ("목표", 9), ("현재", 9), ("달성률", 8), ("진척", 7), ("담당(정/부)", 11), ("완료목표", 10), ("신호", 7), ("최근주차", 8)]
for j, (h, w) in enumerate(dh):
    hdr(DASH, 7, j + 1, h, w)
for i in range(NSLOT):
    r = 8 + i
    refs = ["id", "step", "title", "kpi", "unit", "base", "target", "current", "ach", "prog", None, "end", "signal", "lastwk"]
    for j, k in enumerate(refs):
        if k is None:
            f = f'=IF({MREF("owner",i)}="","",{MREF("owner",i)}&" / "&{MREF("sub",i)})'
        else:
            f = f'=IF({MREF(k,i)}="","",{MREF(k,i)})'
        fmt = {"ach": "0%", "prog": "0%", "end": "m/d"}.get(k, "General")
        put(DASH, r, j + 1, f, LINK, fmt, align=LEFT if k == "title" else CEN)
dsig = f"M8:M{7+NSLOT}"
for txt, col in [("지연", "F8D7DA"), ("주의", "FFF3CD"), ("정상", "D4EDDA"), ("완료", "D6E4F0")]:
    DASH.conditional_formatting.add(dsig, FormulaRule(formula=[f'M8="{txt}"'], fill=PatternFill("solid", fgColor=col), font=Font(bold=True)))
from openpyxl.formatting.rule import DataBarRule
DASH.conditional_formatting.add(f"I8:I{7+NSLOT}", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color="5B9BD5"))
# step별 집계
hdr(DASH, 7, 16, "Step", 18); hdr(DASH, 7, 17, "과제 수", 8); hdr(DASH, 7, 18, "평균 진척", 9)
for j in range(len(Dt.STEPS)):
    r = 8 + j
    put(DASH, r, 16, f"='설정'!D{5+j}", LINK)
    put(DASH, r, 17, f'=IF(P{r}="","",COUNTIF(Action_Master!$B${R0}:$B${RL},P{r}))', CALC, "0", CALC_FILL)
    put(DASH, r, 18, f'=IF(OR(P{r}="",Q{r}=0),"",AVERAGEIF(Action_Master!$B${R0}:$B${RL},P{r},Action_Master!${MCL("prog")}${R0}:${MCL("prog")}${RL}))', CALC, "0%", CALC_FILL)
bc = BarChart(); bc.type = "bar"; bc.title = "과제별 목표 달성률"; bc.height = 8; bc.width = 13
bc.add_data(Reference(DASH, min_col=9, min_row=7, max_row=7 + max(len(ITEMS), 1)), titles_from_data=True)
bc.set_categories(Reference(DASH, min_col=1, min_row=8, max_row=7 + max(len(ITEMS), 1)))
bc.legend = None; bc.y_axis.number_format = "0%"; bc.y_axis.scaling.min = 0; bc.y_axis.scaling.max = 1.2
bc.x_axis.scaling.orientation = "maxMin"
bc.series[0].graphicalProperties.solidFill = BLUE
bc.x_axis.delete = False; bc.y_axis.delete = False
from openpyxl.chart.label import DataLabelList
bc.dataLabels = DataLabelList(); bc.dataLabels.showVal = True
for a in ('showSerName','showCatName','showLegendKey','showPercent'): setattr(bc.dataLabels, a, False)
DASH.add_chart(bc, "P18")
for r in range(8, 8 + NSLOT): DASH.row_dimensions[r].height = 28
DASH.freeze_panes = "A8"

# =====================================================================
# README
# =====================================================================
README.column_dimensions["A"].width = 3; README.column_dimensions["B"].width = 22; README.column_dimensions["C"].width = 95
README["B1"] = "Stack Layer Action Item Tracker (1년 운영용)"; README["B1"].font = F(size=18, bold=True, color=NAVY)
README["B2"] = ("[예시 파일] 2027년 가상 데이터 · 기준일 2027-06-04(W22) 로 채워둔 상태" if EX else
                "[빈 템플릿] 각 시트 첫 행은 '예시 행' 입니다. 형식 확인 후 지우거나 덮어쓰세요. 설정!B5 기준일 = TODAY()")
README["B2"].font = F(size=10, bold=True, color="C00000")
rows = [
 ("시트", "용도 / 입력 방법"),
 ("Dashboard", "팀장 보고용 1장 요약. 과제 수·신호등·평균 진척/달성률 + 과제별 현황 + Step별 집계. 전부 자동(입력 없음)."),
 ("Action_Master", "연간 과제 총괄(최대 20개). 과제 1행 = KPI 1개. Step·Defect·담당(정/부)·상태 등 드롭다운. 회색 칸은 자동 계산."),
 ("Gantt", "주차(W01~W52) 간트. Master 시작/완료일·진척률로 바 자동 생성, Milestone 계획일 ◆ 표시, 기준 주차 주황 테두리."),
 ("Weekly_KPI", "주차별 KPI 수치 입력. 과제마다 2행(목표 자동 glide path / 실적 입력). 'mean 값 감소' 같은 수치를 매주 입력해 추적."),
 ("KPI_Chart", "과제별 목표 vs 실적 추이 그래프(자동). 그래프 복사 → PPT 붙여넣기."),
 ("Milestone", "과제별 주요 일정. 계획일/실적일 입력 → 완료·지연·예정 자동 판정, Gantt ◆ 연동."),
 ("Weekly_Report", "Weekly / Bi-weekly 보고 log. 보고일·No·금주 실적·차주 계획·이슈 입력 → 과제명·담당·해당 주차 KPI 값 자동."),
 ("Torque_FU", "Deep-dive 검증 시트. 불량 lot 별 관리 인자(torque) 실측 이력 연계 → 기준 내 불량 비율·설비 편중·Cpk 자동 → 판단 문구."),
 ("설정", "기준일·W01 시작일·주의 판정 기준·드롭다운 목록(Step 7개, Defect, 담당자 등). 목록 수정 시 전체 반영."),
 ("", ""),
 ("색 규칙", "파란 글씨 = 직접 입력 · 검정 글씨+회색 칸 = 자동 계산(수정 금지) · 초록 글씨 = 다른 시트 연동."),
 ("신호등", "완료(파랑) / 정상(초록) / 주의(노랑: 실제 진척 < 계획 진척 - 15%p) / 지연(빨강: 완료목표일 경과 미완료)."),
 ("달성률 수식", "(현재 - Baseline) ÷ (목표 - Baseline). ↓(감소) / ↑(증가) 과제 모두 같은 수식으로 0%→100% 표현. 100% 초과 = 목표 초과 달성."),
 ("", ""),
 ("운영 순서", "① 킥오프: 설정에 Step·담당자 입력 → Master 에 과제·KPI·Baseline·목표·정/부·일정 확정 → Milestone 4개 내외 입력"),
 ("", "② 매주(격주): 담당자가 Weekly_KPI 실적 행 + Master 실제 진척/상태 + Weekly_Report 1행 입력"),
 ("", "③ 보고: Dashboard·Gantt·KPI_Chart 확인 → PPT 총괄표/간트/KPI 추이 장표 수치 갱신"),
 ("", "④ 분기: 주의·지연 과제 대책 재수립, 목표 재설정 필요시 Master 목표값 수정(변경 이력은 비고에 기록)"),
 ("", "⑤ 연말: Baseline vs 최종 실적 · 달성률 · 개선율로 성과 정리 (PPT '연간 성과 요약' 장표)"),
 ("", ""),
 ("과제 유형 예시", "AI-01 불량률 ppm↓ + 관리 인자 F/U · AI-02 mean 값↓ · AI-03 불량률 %↓ · AI-04 산포 σ↓ · AI-05 Cpk↑ · AI-06 설비 MTBF↑ · AI-07 검출률↑ · AI-08 비수치(SOP 건수) · AI-09 완료 과제"),
 ("과제 추가", "Master 빈 행(20개 슬롯)에 입력하면 Weekly_KPI·Gantt·Dashboard 자동 연동. KPI_Chart 그래프는 기존 그래프 복사 후 데이터 범위만 다음 행으로 변경."),
 ("Deep-dive 추가", "Torque_FU 시트를 복사(시트 탭 우클릭 → 이동/복사)해서 다른 인자(온도, 압력, 속도 등) 검증에 재사용."),
 ("주의", "Master 의 행 순서 = Weekly_KPI/Gantt 의 행 순서입니다. Master 행은 정렬(Sort)·삭제 대신 내용만 수정하세요. 필터 조회는 괜찮습니다."),
]
for j, (a, b) in enumerate(rows):
    r = 4 + j
    ca = README.cell(row=r, column=2, value=a); cb = README.cell(row=r, column=3, value=b)
    if j == 0:
        for c in (ca, cb): c.font = F(bold=True, color="FFFFFF"); c.fill = HDR_FILL; c.alignment = CEN
    else:
        ca.font = F(bold=True, color=NAVY); cb.font = F(); cb.alignment = LEFT
        if a or b:
            ca.border = BOX; cb.border = BOX
    README.row_dimensions[r].height = 20
for ws in wb.worksheets:
    ws.sheet_properties.tabColor = {"README": "5F5E5A", "Dashboard": NAVY, "설정": "5F5E5A", "Torque_FU": "C00000"}.get(ws.title, BLUE)
wb.active = 1
wb.save(OUT)
print("saved", OUT)
