import sys, os, zipfile, shutil
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import FormulaRule
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter as CL
import data as Dt

OUT = sys.argv[1]
FONT = "맑은 고딕"; NAVY = "0C447C"; LIGHT = "E6F1FB"
def F(**k): b = dict(name=FONT, size=10); b.update(k); return Font(**b)
thin = Side(style="thin", color="BFBFBF"); BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
HDR = PatternFill("solid", fgColor=NAVY); CALC = PatternFill("solid", fgColor="F2F2F2"); GRAYH = PatternFill("solid", fgColor="5F5E5A")
CEN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
TREEAL = Alignment(horizontal="left", vertical="center", wrap_text=False)

ROOT = "2027_StackLayer_ActionItem"
SUB = [("01_현황분석", "불량 현황, trend, map, baseline 산출 자료", "AI-01_01현황_edge_cr_trend_20270115.pptx"),
       ("02_원인분석", "원인 분석, 가설 검증, 관리 인자 연계 (Torque_FU 등)", "AI-01_02원인_torque이력연계_20270528.xlsx"),
       ("03_대책_평가", "대책 수립, DOE·평가 계획 / 결과", "AI-01_03대책_평탄도측정계획_20270604.pptx"),
       ("04_효과검증", "적용 전후 비교, KPI 효과 확인", "AI-01_04효과_적용전후비교_20270820.xlsx"),
       ("05_표준화", "SOP·관리 기준 개정본, 시스템 등록 증빙", "SOP_S5_DieStacking_edge_cr_v1.0.docx"),
       ("99_회의록_협업", "유관부서 협의, 회의록, 메일 캡처", "AI-01_회의록_Stack팀협업_20270528.docx")]
short = {"AI-01": "S5_edge_cr_torque", "AI-02": "S2_chipping_mean", "AI-03": "S4_die_crack", "AI-04": "S1_void_산포",
         "AI-05": "S6_warpage_Cpk", "AI-06": "S3_debond_MTBF", "AI-07": "S7_particle_검출률", "AI-08": "공통_defect_SOP",
         "AI-09": "S5_head_온도편차"}

# (lv1, lv2, lv3, 용도, 보관 파일 예시, 담당, 갱신 주기, 권한)
R = []
def add(l1, l2="", l3="", use="", ex="", own="", cyc="", auth=""): R.append((l1, l2, l3, use, ex, own, cyc, auth))
add("00_운영관리", use="연간 운영 원본 · 기준 자료 (모듈장 관리)", own="모듈장", auth="모듈장 편집 / 전원 보기")
add("00_운영관리", "01_Tracker_원본", use="★ Excel tracker 원본 1개만 보관 (전원 이 파일에 직접 입력)", ex="StackLayer_ActionItem_Tracker_2027.xlsx", own="모듈장", cyc="매주", auth="담당자 전원 편집")
add("00_운영관리", "02_Tracker_백업", use="보고 직후 주차별 스냅샷 (수정 금지, 이력 확인용)", ex="StackLayer_Tracker_2027_W22.xlsx", own="모듈장", cyc="매주 보고 후", auth="모듈장 편집")
add("00_운영관리", "03_킥오프_과제선정", use="킥오프 자료, 과제 선정 회의록, R&R 합의본", ex="2027_StackLayer_킥오프_과제선정_v1.0.pptx", own="모듈장", cyc="연초 1회")
add("00_운영관리", "04_운영Rule", use="운영 rule, 신호 기준, 폴더·파일명 규칙 (이 파일)", ex="StackLayer_폴더구조_운영가이드.xlsx", own="모듈장", cyc="변경 시")
add("10_주간보고", use="weekly / bi-weekly 보고 장표 (월별 폴더)", own="모듈장", auth="전원 보기")
for m in range(1, 13):
    add("10_주간보고", f"2027_{m:02d}월", use=f"{m}월 주간 보고 장표 · 회의 결과" if m == 1 else "", ex="2027_W22_StackLayer_주간보고_v1.pptx" if m == 6 else ("2027_W01_StackLayer_주간보고_v1.pptx" if m == 1 else ""), own="모듈장", cyc="매주")
add("20_과제별", use="과제 1개 = 폴더 1개 · 폴더명 = Tracker No (AI-xx) + Step + 약칭", own="담당(정)", auth="담당 정/부 편집 / 전원 보기")
for it in Dt.ITEMS:
    fn = f'{it["id"]}_{short[it["id"]]}'
    add("20_과제별", fn, use=f'{it["title"]} (정 {it["owner"]} / 부 {it["sub"]})', own=it["owner"], cyc=it["cycle"])
    for s, u, e in SUB:
        add("20_과제별", fn, s, use=u if it["id"] == "AI-01" else "", ex=e.replace("AI-01", it["id"]) if it["id"] in ("AI-01",) else "", own=it["owner"])
add("20_과제별", "AI-xx_[Step]_[약칭]", use="(신규 과제용 빈 폴더 : 통째로 복사 후 이름 변경)", own="담당(정)")
for s, u, e in SUB: add("20_과제별", "AI-xx_[Step]_[약칭]", s)
add("30_Step별_기준정보", use="step별 공정 spec · 관리 기준 · defect 정의 (과제 공통 참조)", own="step 담당", auth="전원 보기")
for st in Dt.STEPS[:-1]:
    add("30_Step별_기준정보", st.replace(" ", "_").replace("(", "_").replace(")", ""), use="공정 flow, 관리 항목·spec, defect code 정의" if st.startswith("S1") else "",
        ex="S5_관리기준_torque_spec_v2.pdf" if st.startswith("S5") else "", own="step 담당", cyc="변경 시")
add("40_분기_연말보고", use="분기 review · 연말 성과 보고", own="모듈장", auth="전원 보기")
for q in ["2027_Q1", "2027_Q2", "2027_Q3", "2027_Q4_연간성과"]:
    add("40_분기_연말보고", q, use="분기 review 장표, 목표 재설정 내역" if q == "2027_Q1" else ("연간 성과 보고 (baseline 대비 개선율·효과 환산)" if "Q4" in q else ""),
        ex="2027_Q2_StackLayer_분기보고.pptx" if q == "2027_Q2" else ("2027_StackLayer_연간성과보고.pptx" if "Q4" in q else ""), own="모듈장", cyc="분기")
add("50_공용Data", use="여러 과제가 같이 쓰는 원천 data (MES 추출, inline 측정, 설비 log)", own="담당자 전원", auth="전원 편집")
for d, u in [("01_MES_추출", "lot 이력, 불량 집계 추출 원본"), ("02_설비log_torque등", "torque·온도 등 관리 인자 log (Torque_FU 연계 원본)"), ("03_분석script_query", "추출 query, 분석 script")]:
    add("50_공용Data", d, use=u, ex="MES_edge_cr_lot_2027W01-W22.csv" if d.startswith("01") else ("Stack_torque_log_2027-05.csv" if d.startswith("02") else ""), cyc="수시")
add("90_Template", use="빈 템플릿 (복사해서 사용, 원본 수정 금지)", own="모듈장", auth="모듈장 편집 / 전원 보기")
add("90_Template", "01_Tracker_빈템플릿", ex="StackLayer_ActionItem_Tracker_빈템플릿.xlsx")
add("90_Template", "02_보고장표_빈템플릿", ex="StackLayer_ActionItem_보고장표_빈템플릿.pptx")
add("90_Template", "03_작성예시", use="작성 예시 (예시 tracker · 예시 장표)", ex="StackLayer_ActionItem_Tracker_예시.xlsx")
add("99_Archive", use="Drop·보류 과제, 이전 버전, 연도 종료 자료", own="모듈장", auth="모듈장 편집")
add("99_Archive", "Drop_보류과제", use="drop/보류 과제 폴더 통째로 이동 (Tracker 상태도 변경)")
add("99_Archive", "구버전", use="대체된 장표·기준서 구버전")

wb = Workbook()
# ---------------- 설정 / 개요 ----------------
G = wb.active; G.title = "개요"; G.sheet_view.showGridLines = False
G.column_dimensions["A"].width = 3; G.column_dimensions["B"].width = 24; G.column_dimensions["C"].width = 100
G["B1"] = "Stack Layer Action Item 폴더 구조 · 운영 가이드"; G["B1"].font = F(size=18, bold=True, color=NAVY)
G["B3"] = "최상위 폴더명 (입력)"; G["B3"].font = F(bold=True)
G["C3"] = ROOT; G["C3"].font = F(color="0000FF", bold=True); G["C3"].border = BOX
G["B4"] = "상위 경로 (입력)"; G["B4"].font = F(bold=True)
G["C4"] = r"\\공유드라이브\Stack Layer"; G["C4"].font = F(color="0000FF"); G["C4"].border = BOX
G["C5"] = "※ 위 두 칸을 실제 경로로 바꾸면 '폴더구조' 시트의 전체 경로·생성 명령이 자동으로 바뀝니다."; G["C5"].font = F(size=9, color="5F5E5A")
rows = [("구성 원칙", ""),
        ("① 원본은 1개", "Excel tracker 원본은 00_운영관리/01_Tracker_원본 에만 둡니다. 메일·개인 PC 복사본 편집 금지 → 담당자 전원 원본에 직접 입력."),
        ("② 과제 ID = 폴더명", "Tracker No(AI-01) = 20_과제별 폴더명 앞자리 = 파일명 앞자리. 검색·정렬·연결이 한 번에 됩니다."),
        ("③ 과제 폴더는 동일 구조", "모든 과제 폴더 하위는 01현황 → 02원인 → 03대책 → 04효과 → 05표준화 + 99회의록 (8D 흐름 그대로)."),
        ("④ 숫자 prefix", "00·10·20… 로 정렬 순서 고정, 사이 번호는 추가용 여유. 깊이는 최대 3단계."),
        ("⑤ 보고는 시간축, 과제는 주제축", "10_주간보고 / 40_분기보고 = 언제 보고했나 · 20_과제별 = 무엇을 했나. 보고 장표에 쓴 근거 자료는 과제 폴더에 둡니다."),
        ("⑥ 끝난 것은 Archive", "Drop·보류 과제는 99_Archive 로 이동. 20_과제별 에는 진행 과제만 남깁니다."),
        ("", ""),
        ("시트 안내", ""),
        ("폴더구조", "전체 폴더 트리 · 용도 · 보관 파일 예시 · 담당 · 갱신 주기 · 권한. Lv1~Lv3 칸을 고치면 트리/경로 자동 반영."),
        ("과제폴더_생성", "신규 과제 추가 시 No·Step·약칭 입력 → 폴더명 + 하위 6개 폴더 경로 자동 생성."),
        ("파일명_규칙", "자료 유형별 파일명 규칙과 예시."),
        ("운영_Rule", "백업 · 권한 · archive · 버전 관리 rule."),
        ("", ""),
        ("폴더 한 번에 만들기", "방법 1) 함께 드린 zip 압축 해제 (빈 템플릿·예시 파일 포함)  /  방법 2) 폴더구조 시트 L열(mkdir 명령) 전체 복사 → 메모장 붙여넣기 → '폴더생성.bat' 로 저장(인코딩 UTF-8) → 실행"),
        ]
for j, (a, b) in enumerate(rows):
    r = 7 + j
    ca, cb = G.cell(row=r, column=2, value=a), G.cell(row=r, column=3, value=b)
    if b == "" and a:
        ca.font = F(bold=True, color="FFFFFF"); ca.fill = HDR; cb.fill = HDR
    elif a:
        ca.font = F(bold=True, color=NAVY); cb.font = F(); cb.alignment = LEFT; ca.border = BOX; cb.border = BOX
    G.row_dimensions[r].height = 22 if b else 18
G.row_dimensions[21].height = 34
ROOTREF, BASEREF = "'개요'!$C$3", "'개요'!$C$4"

# ---------------- 폴더구조 ----------------
S = wb.create_sheet("폴더구조"); S.sheet_view.showGridLines = False
S["A1"] = "폴더 구조 (트리)"; S["A1"].font = F(size=16, bold=True, color=NAVY)
S["A2"] = "파란 글씨 = 입력 (Lv1~Lv3 폴더명, 용도 등) · 회색 칸 = 자동 (트리 보기 / 전체 경로 / mkdir 명령). 행 추가 시 윗 행 복사 후 폴더명만 수정."
S["A2"].font = F(size=9, color="5F5E5A")
H = [("No", 5, 0), ("트리 보기 (자동)", 44, 1), ("용도", 46, 0), ("보관 파일 예시", 40, 0), ("담당", 9, 0), ("갱신 주기", 11, 0), ("권한", 20, 0),
     ("Lv1", 18, 0), ("Lv2", 22, 0), ("Lv3", 16, 0), ("전체 경로 (자동)", 60, 1), ("폴더 생성 명령 (자동)", 60, 1)]
for j, (h, w, c) in enumerate(H):
    cell = S.cell(row=4, column=j + 1, value=h); cell.font = F(bold=True, color="FFFFFF"); cell.fill = GRAYH if c else HDR
    cell.alignment = CEN; cell.border = BOX; S.column_dimensions[CL(j + 1)].width = w
S.row_dimensions[4].height = 26
N = len(R) + 20
for i in range(N):
    r = 5 + i
    x = R[i] if i < len(R) else ("", "", "", "", "", "", "", "")
    l1, l2, l3, use, ex, own, cyc, auth = x
    S.cell(row=r, column=1, value=f'=IF(H{r}="","",ROW()-4)')
    lvl = f'IF(J{r}<>"",3,IF(I{r}<>"",2,1))'
    S.cell(row=r, column=2, value=f'=IF(H{r}="","",IF({lvl}=1,"■ "&H{r},REPT("      ",{lvl}-1)&"└ "&INDEX(H{r}:J{r},{lvl})))')
    for c, v in zip(range(3, 11), [use, ex, own, cyc, auth, l1, l2, l3]):
        S.cell(row=r, column=c, value=v or None)
    S.cell(row=r, column=11, value=f'=IF(H{r}="","",{BASEREF}&"\\"&{ROOTREF}&"\\"&H{r}&IF(I{r}="","","\\"&I{r})&IF(J{r}="","","\\"&J{r}))')
    S.cell(row=r, column=12, value=f'=IF(K{r}="","","mkdir """&K{r}&"""")')
    for c in range(1, 13):
        cell = S.cell(row=r, column=c); cell.border = BOX
        calc = c in (1, 2, 11, 12)
        cell.font = F(color="000000" if calc else "0000FF", size=9 if c in (11, 12) else 10)
        if calc and c != 2: cell.fill = CALC
        cell.alignment = TREEAL if c == 2 else (CEN if c in (1, 5, 6) else LEFT)
    S.row_dimensions[r].height = 30 if (len(use or '') > 24 or len(auth or '') > 11 or len(ex or '') > 40) else 18
L = 4 + N
rng = f"A5:L{L}"
S.conditional_formatting.add(f"B5:B{L}", FormulaRule(formula=['AND($H5<>"",$I5="")'], fill=PatternFill("solid", fgColor=LIGHT), font=Font(bold=True, color=NAVY)))
S.conditional_formatting.add(f"B5:B{L}", FormulaRule(formula=['AND($I5<>"",$J5="")'], font=Font(bold=True)))
S.conditional_formatting.add(f"H5:H{L}", FormulaRule(formula=['AND(ROW()>5,H5=H4)'], font=Font(color="BFBFBF")))
S.conditional_formatting.add(f"I5:I{L}", FormulaRule(formula=['AND(ROW()>5,I5=I4,I5<>"")'], font=Font(color="BFBFBF")))
S.conditional_formatting.add(f"C5:G{L}", FormulaRule(formula=['AND($H5<>"",$I5="")'], fill=PatternFill("solid", fgColor=LIGHT)))
S.freeze_panes = "C5"; S.auto_filter.ref = f"A4:L{L}"
S[f"B{L+2}"] = "※ 연한 회색 Lv1/Lv2 = 윗 행과 같은 상위 폴더 (상위 폴더명을 반복 입력해야 경로가 만들어집니다)."
S[f"B{L+2}"].font = F(size=9, color="5F5E5A")

# ---------------- 과제폴더_생성 ----------------
P = wb.create_sheet("과제폴더_생성"); P.sheet_view.showGridLines = False
P["A1"] = "신규 과제 폴더 생성"; P["A1"].font = F(size=16, bold=True, color=NAVY)
P["A2"] = "No · Step 코드 · 약칭 입력 → 폴더명과 하위 폴더 생성 명령 자동. 생성 명령을 복사해 .bat 로 실행하거나, 20_과제별/AI-xx 빈 폴더를 복사 후 이름만 변경."
P["A2"].font = F(size=9, color="5F5E5A")
ph = [("No (Tracker)", 12), ("Step 코드", 10), ("약칭 (영문/한글, 공백 대신 _)", 26), ("폴더명 (자동)", 32)] + [(s, 13) for s, _, _ in SUB] + [("생성 명령 (자동 · 7개 폴더 한 줄)", 90)]
for j, (h, w) in enumerate(ph):
    c = P.cell(row=4, column=j + 1, value=h); c.font = F(bold=True, color="FFFFFF"); c.fill = HDR if j < 3 else GRAYH
    c.alignment = CEN; c.border = BOX; P.column_dimensions[CL(j + 1)].width = w
for i in range(30):
    r = 5 + i
    it = Dt.ITEMS[i] if i < len(Dt.ITEMS) else None
    if it:
        sc, nm = short[it["id"]].split("_", 1)
        vals = [it["id"], sc, nm]
    else:
        vals = [None, None, None]
    for j, v in enumerate(vals):
        c = P.cell(row=r, column=j + 1, value=v); c.font = F(color="0000FF"); c.border = BOX; c.alignment = CEN
    P.cell(row=r, column=4, value=f'=IF(A{r}="","",A{r}&"_"&B{r}&"_"&C{r})')
    base = f'{BASEREF}&"\\"&{ROOTREF}&"\\20_과제별\\"&D{r}'
    for k, (s, _, _) in enumerate(SUB):
        P.cell(row=r, column=5 + k, value=f'=IF(D{r}="","","{s}")')
    cmd = "&".join([f'" && mkdir """&{base}&"\\{s}"""' for s, _, _ in SUB])
    P.cell(row=r, column=11, value=f'=IF(D{r}="","","mkdir """&{base}&""""{("&" + cmd)})')
    for c in range(4, 12):
        cell = P.cell(row=r, column=c); cell.fill = CALC; cell.border = BOX; cell.font = F(size=9)
        cell.alignment = LEFT if c in (4, 11) else CEN
dv = DataValidation(type="list", formula1='"S1,S2,S3,S4,S5,S6,S7,공통"', allow_blank=True); P.add_data_validation(dv); dv.add("B5:B34")
P.freeze_panes = "E5"

# ---------------- 파일명 규칙 ----------------
Fn = wb.create_sheet("파일명_규칙"); Fn.sheet_view.showGridLines = False
Fn["A1"] = "파일명 규칙"; Fn["A1"].font = F(size=16, bold=True, color=NAVY)
Fn["A2"] = "기본형 : [과제ID 또는 연도_주차]_[단계/구분]_[내용]_[YYYYMMDD 또는 vX.X].확장자  ·  공백 대신 _ 사용  ·  '최종', '최최종', '수정본' 금지 → 버전 번호로 관리"
Fn["A2"].font = F(size=9, color="5F5E5A")
fh = [("자료 유형", 18), ("저장 폴더", 30), ("파일명 규칙", 46), ("예시", 52), ("비고", 34)]
for j, (h, w) in enumerate(fh):
    c = Fn.cell(row=4, column=j + 1, value=h); c.font = F(bold=True, color="FFFFFF"); c.fill = HDR; c.alignment = CEN; c.border = BOX
    Fn.column_dimensions[CL(j + 1)].width = w
fr = [("Tracker 원본", "00_운영관리/01_Tracker_원본", "StackLayer_ActionItem_Tracker_[연도]", "StackLayer_ActionItem_Tracker_2027.xlsx", "날짜·버전 붙이지 않음 (1개 고정 → 링크 안 깨짐)"),
      ("Tracker 백업", "00_운영관리/02_Tracker_백업", "StackLayer_Tracker_[연도]_W[주차]", "StackLayer_Tracker_2027_W22.xlsx", "보고 직후 원본 복사 · 수정 금지"),
      ("주간 보고 장표", "10_주간보고/[연도]_[월]", "[연도]_W[주차]_StackLayer_주간보고_v[n]", "2027_W22_StackLayer_주간보고_v1.pptx", "팀장 보고 후 수정본은 v2"),
      ("과제 분석 자료", "20_과제별/AI-xx/0x_단계", "[과제ID]_[단계번호+단계]_[내용]_[YYYYMMDD]", "AI-01_02원인_torque이력연계_20270528.xlsx", "단계번호 = 하위 폴더 번호와 동일"),
      ("과제 회의록", "20_과제별/AI-xx/99_회의록_협업", "[과제ID]_회의록_[상대부서/주제]_[YYYYMMDD]", "AI-01_회의록_Stack팀협업_20270528.docx", "협의 결과 · 담당 · 기한 3줄 요약 필수"),
      ("평가·DOE 결과", "20_과제별/AI-xx/03_대책_평가", "[과제ID]_03대책_[평가명]_[차수]_[YYYYMMDD]", "AI-03_03대책_DOE_feedspeed_1차_20270520.xlsx", "차수 표기 (1차, 2차)"),
      ("SOP / 관리 기준", "20_과제별/AI-xx/05_표준화 → 30_Step별 반영", "SOP_[Step코드]_[Step명]_[내용]_v[X.X]", "SOP_S4_Dicing_defectFU_v1.0.docx", "v0.x 초안 / v1.0 확정 / v1.1 개정"),
      ("분기 보고", "40_분기_연말보고/[연도]_Q[n]", "[연도]_Q[n]_StackLayer_분기보고", "2027_Q2_StackLayer_분기보고.pptx", ""),
      ("연간 성과 보고", "40_분기_연말보고/[연도]_Q4_연간성과", "[연도]_StackLayer_연간성과보고_v[n]", "2027_StackLayer_연간성과보고_v1.pptx", ""),
      ("원천 data", "50_공용Data/0x_구분", "[출처]_[내용]_[기간]", "MES_edge_cr_lot_2027W01-W22.csv", "대용량은 링크·query 만 보관 가능"),
      ("분석 script / query", "50_공용Data/03_분석script_query", "[내용]_[언어/도구]_v[n]", "edge_cr_torque_join_sql_v1.sql", "")]
for i, row in enumerate(fr):
    r = 5 + i
    for j, v in enumerate(row):
        c = Fn.cell(row=r, column=j + 1, value=v); c.border = BOX; c.alignment = LEFT; c.font = F(bold=(j == 0), color=NAVY if j == 0 else ("185FA5" if j == 3 else "000000"))
    Fn.row_dimensions[r].height = 30
r = 5 + len(fr) + 1
Fn.cell(row=r, column=1, value="버전 규칙").font = F(bold=True, color=NAVY)
for k, t in enumerate(["v0.1, v0.2 … = 작성 중 초안", "v1.0 = 팀장 보고 / 합의 확정본", "v1.1, v1.2 = 확정 후 부분 수정 · v2.0 = 구조 변경", "구버전은 99_Archive/구버전 으로 이동 (같은 폴더에 버전 여러 개 두지 않기)"]):
    Fn.cell(row=r + 1 + k, column=1, value="•"); Fn.cell(row=r + 1 + k, column=2, value=t).font = F()

# ---------------- 운영 Rule ----------------
O = wb.create_sheet("운영_Rule"); O.sheet_view.showGridLines = False
O["A1"] = "폴더 운영 Rule"; O["A1"].font = F(size=16, bold=True, color=NAVY)
oh = [("구분", 14), ("Rule", 70), ("담당", 12), ("시점", 16)]
for j, (h, w) in enumerate(oh):
    c = O.cell(row=3, column=j + 1, value=h); c.font = F(bold=True, color="FFFFFF"); c.fill = HDR; c.alignment = CEN; c.border = BOX
    O.column_dimensions[CL(j + 1)].width = w
orow = [("원본 관리", "Tracker 원본은 01_Tracker_원본 1개. 담당자는 이 파일에 직접 입력 (공유 편집 / 체크아웃 사용)", "전원", "상시"),
        ("입력", "담당(정)이 Weekly_KPI 실적 · Master 진척/상태 · Weekly_Report 입력, 부 담당은 부재 시 대체", "담당 정/부", "매주 목요일"),
        ("백업", "보고 직후 원본을 02_Tracker_백업 에 _Wxx 로 복사 (덮어쓰기 금지)", "모듈장", "매주 보고 후"),
        ("근거 자료", "보고 장표에 들어간 그래프·수치의 원본 파일은 해당 과제 폴더 단계 폴더에 저장", "담당(정)", "보고 전"),
        ("과제 추가", "Tracker Master 에 No 부여 → 과제폴더_생성 시트로 폴더명 확정 → AI-xx 빈 폴더 복사·이름 변경", "모듈장", "분기 review"),
        ("과제 종료", "완료 과제 : 05_표준화 증빙 확인 후 폴더 유지 / Drop·보류 : 99_Archive/Drop_보류과제 로 이동", "모듈장", "상태 변경 시"),
        ("SOP 반영", "05_표준화 확정본(v1.0)을 30_Step별_기준정보/해당 step 에도 복사 (step 기준 최신화)", "담당(정)", "표준화 완료 시"),
        ("권한", "00 = 모듈장 편집 (01_Tracker 만 전원 편집) · 20 = 과제 담당 정/부 편집, 전원 보기 · 90 = 모듈장만 편집", "모듈장", "연초 설정"),
        ("정리", "개인 임시 파일 (~$, 복사본 (1), 사본) 월 1회 삭제 · 폴더 깊이 3단계 초과 금지", "모듈장", "월 1회"),
        ("연말", "연간 성과 보고 후 전체 폴더를 [연도]_StackLayer_ActionItem 그대로 보존, 차년도는 새 최상위 폴더로 시작 (90_Template 복사)", "모듈장", "연말")]
for i, row in enumerate(orow):
    r = 4 + i
    for j, v in enumerate(row):
        c = O.cell(row=r, column=j + 1, value=v); c.border = BOX; c.alignment = CEN if j in (0, 2, 3) else LEFT
        c.font = F(bold=(j == 0), color=NAVY if j == 0 else "000000")
    O.row_dimensions[r].height = 32
for ws in wb.worksheets:
    ws.sheet_properties.tabColor = NAVY if ws.title == "폴더구조" else "185FA5"
wb.active = 1
wb.save(OUT)

# ---------------- zip : 실제 폴더 세트 ----------------
if len(sys.argv) > 2:
    zout = sys.argv[2]
    tmp = "/tmp/claude-0/-home-user-my-brief/a7e05e14-6de7-5566-8a82-f35982df1d6c/scratchpad/fz"
    shutil.rmtree(tmp, ignore_errors=True)
    root = os.path.join(tmp, ROOT)
    for x in R:
        p = os.path.join(root, *[v for v in x[:3] if v]); os.makedirs(p, exist_ok=True)
    src = os.path.abspath("..")
    shutil.copy(os.path.join(src, "StackLayer_ActionItem_Tracker_빈템플릿.xlsx"), os.path.join(root, "00_운영관리", "01_Tracker_원본", "StackLayer_ActionItem_Tracker_2027.xlsx"))
    shutil.copy(os.path.join(src, "StackLayer_ActionItem_Tracker_빈템플릿.xlsx"), os.path.join(root, "90_Template", "01_Tracker_빈템플릿"))
    shutil.copy(os.path.join(src, "StackLayer_ActionItem_보고장표_빈템플릿.pptx"), os.path.join(root, "90_Template", "02_보고장표_빈템플릿"))
    shutil.copy(os.path.join(src, "StackLayer_ActionItem_Tracker_예시.xlsx"), os.path.join(root, "90_Template", "03_작성예시"))
    shutil.copy(os.path.join(src, "StackLayer_ActionItem_보고장표_예시.pptx"), os.path.join(root, "90_Template", "03_작성예시"))
    shutil.copy(OUT, os.path.join(root, "00_운영관리", "04_운영Rule"))
    with zipfile.ZipFile(zout, "w", zipfile.ZIP_DEFLATED) as z:
        for d, dirs, files in os.walk(tmp):
            rel = os.path.relpath(d, tmp)
            if rel != ".":
                z.writestr(zipfile.ZipInfo(rel.replace(os.sep, "/") + "/"), "")
            for f in files:
                z.write(os.path.join(d, f), os.path.relpath(os.path.join(d, f), tmp))
    print("zip", zout, sum(1 for _ in os.walk(root)), "folders")
print("rows", len(R))
