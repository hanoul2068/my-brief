"""공용 예시 데이터 (Excel / PPT 공통). 이름·수치는 모두 예시."""
import datetime as dt, random

YEAR = 2027
W01 = dt.date(2027, 1, 4)          # 1주차 시작(월)
BASE_DATE = dt.date(2027, 6, 4)    # 예시 보고 기준일 (W22 금)
NWEEK = 52
def wk_start(n): return W01 + dt.timedelta(days=7 * (n - 1))
def week_of(d): return (d - W01).days // 7 + 1
CUR_WEEK = week_of(BASE_DATE)      # 22

STEPS = ["S1 Carrier Bonding", "S2 Back Grinding", "S3 Carrier Debonding", "S4 Dicing",
         "S5 Die Stacking", "S6 Molding(MUF)", "S7 Stack Insp", "공통"]
DEFECTS = ["edge_cr", "chipping", "die_cr", "void", "warpage", "particle", "설비 loss", "표준화", "기타"]
OWNERS = ["김OO", "이OO", "박OO", "최OO", "정OO", "강OO", "조OO", "윤OO", "장OO", "임OO"]
STATUS = ["미착수", "진행중", "완료", "보류", "Drop"]
PRIORITY = ["상", "중", "하"]
DIRECTION = ["↓", "↑"]
CYCLE = ["Weekly", "Bi-weekly", "Monthly"]
DEPTS = ["Stack팀", "공정기술", "설비기술", "품질", "분석팀"]

D = dt.date
# id, step, defect, title, problem, cause, action, kpi, unit, dir, base, target, f(달성률@W22), owner, sub, dept,
# start, end, progress, status, prio, cycle
ITEMS = [
 dict(id="AI-01", step="S5 Die Stacking", defect="edge_cr", title="edge_cr 불량률 저감 (torque 관리 실효성 검증)",
      problem="die edge_cr 불량률 상승 (850ppm, 전년 대비 2.1배)", cause="stack 체결 torque 산포 추정 : 불량 lot torque 연계 검증 필요",
      action="torque 관리 기준 운영 + 불량 lot torque 이력 연계 검증 + 추가 인자 발굴", kpi="edge_cr 불량률", unit="ppm", dir="↓",
      base=850, target=300, f=0.42, owner="김OO", sub="이OO", dept="Stack팀", start=D(2027,1,4), end=D(2027,9,24),
      prog=0.45, status="진행중", prio="상", cycle="Weekly"),
 dict(id="AI-02", step="S2 Back Grinding", defect="chipping", title="BG 후 edge chipping size mean 감소",
      problem="chipping size mean 12.5µm : 후속 dicing crack 연계 risk", cause="wheel 마모 주기 대비 dressing 주기 미연계",
      action="dressing 주기 최적화 + wheel 교체 기준 수치화", kpi="chipping size mean", unit="µm", dir="↓",
      base=12.5, target=8.0, f=0.60, owner="박OO", sub="최OO", dept="공정기술", start=D(2027,1,11), end=D(2027,7,30),
      prog=0.55, status="진행중", prio="상", cycle="Weekly"),
 dict(id="AI-03", step="S4 Dicing", defect="die_cr", title="dicing die crack 불량률 저감",
      problem="die crack 0.42% : edge 영역 집중 발생", cause="blade feed speed / 냉각수 유량 조건 영향 추정",
      action="DOE 기반 조건 최적화 + blade 수명 관리 기준 수립", kpi="die crack 불량률", unit="%", dir="↓",
      base=0.42, target=0.15, f=0.30, owner="정OO", sub="강OO", dept="공정기술", start=D(2027,2,1), end=D(2027,10,29),
      prog=0.30, status="진행중", prio="중", cycle="Weekly"),
 dict(id="AI-04", step="S1 Carrier Bonding", defect="void", title="bonding void 면적 산포(σ) 개선",
      problem="void area σ 3.2% : 설비 간 산포 상이", cause="adhesive 도포량 / 가압 profile 설비 간 차이",
      action="설비 간 profile matching + 도포량 SPC 편입", kpi="void area σ", unit="%", dir="↓",
      base=3.2, target=2.0, f=0.45, owner="조OO", sub="윤OO", dept="설비기술", start=D(2027,1,18), end=D(2027,6,25),
      prog=0.60, status="진행중", prio="중", cycle="Bi-weekly"),
 dict(id="AI-05", step="S6 Molding(MUF)", defect="warpage", title="MUF 후 warpage Cpk 향상",
      problem="warpage Cpk 0.90 : 규격 대비 공정 능력 부족", cause="cure profile / EMC lot 간 차이 영향",
      action="cure profile 재설정 + EMC 수입검사 항목 추가", kpi="warpage Cpk", unit="Cpk", dir="↑",
      base=0.90, target=1.33, f=0.35, owner="장OO", sub="임OO", dept="품질", start=D(2027,3,1), end=D(2027,11,26),
      prog=0.25, status="진행중", prio="중", cycle="Weekly"),
 dict(id="AI-06", step="S3 Carrier Debonding", defect="설비 loss", title="debond 설비 MTBF 향상",
      problem="MTBF 120hr : laser 출력 저하 알람 반복", cause="laser module PM 주기 미최적화",
      action="PM 주기 재설정 + 출력 monitoring interlock", kpi="설비 MTBF", unit="hr", dir="↑",
      base=120, target=200, f=0.70, owner="강OO", sub="박OO", dept="설비기술", start=D(2027,1,4), end=D(2027,5,28),
      prog=0.85, status="진행중", prio="하", cycle="Bi-weekly"),
 dict(id="AI-07", step="S7 Stack Insp", defect="particle", title="stack insp particle 검출률 향상",
      problem="particle 검출률 78% : 후공정 유출 발생", cause="insp recipe threshold / 조명 조건 최적화 미흡",
      action="recipe threshold 재설정 + 유출 sample 기준 검증", kpi="particle 검출률", unit="%", dir="↑",
      base=78, target=95, f=0.55, owner="이OO", sub="정OO", dept="분석팀", start=D(2027,2,15), end=D(2027,8,27),
      prog=0.50, status="진행중", prio="상", cycle="Weekly"),
 dict(id="AI-08", step="공통", defect="표준화", title="step별 defect F/U 표준(SOP) 수립",
      problem="step별 defect F/U 기준 상이 : 이력 추적 체계 미연계", cause="step별 관리 항목·주기 표준 미수립",
      action="7개 step defect F/U SOP 수립 및 시스템 등록", kpi="SOP 수립 건수", unit="건", dir="↑",
      base=0, target=7, f=0.43, owner="최OO", sub="조OO", dept="품질", start=D(2027,1,4), end=D(2027,12,24),
      prog=0.40, status="진행중", prio="중", cycle="Bi-weekly"),
 dict(id="AI-09", step="S5 Die Stacking", defect="기타", title="TC bonding head 온도 편차 개선",
      problem="head 간 온도 편차 4.0℃ : bonding 품질 산포 요인", cause="heater 열전대 위치 편차",
      action="열전대 위치 표준화 + 일 1회 온도 mapping", kpi="head 온도 편차", unit="℃", dir="↓",
      base=4.0, target=1.5, f=1.04, owner="윤OO", sub="장OO", dept="설비기술", start=D(2027,1,4), end=D(2027,4,30),
      prog=1.0, status="완료", prio="중", cycle="Weekly"),
]

def gen_actuals(it, seed):
    """주차별 실적(예시). 기준일 주차까지만 입력."""
    rnd = random.Random(seed)
    sw, ew = week_of(it["start"]), week_of(it["end"])
    out = {}
    step = 2 if it["cycle"] == "Bi-weekly" else 1
    span = it["target"] - it["base"]
    for w in range(max(1, sw), CUR_WEEK + 1, step):
        frac = min(1.0, (w - sw) / max(1, (CUR_WEEK - sw)))
        if it["id"] == "AI-09":
            frac = min(1.0, (w - sw) / max(1, (ew - sw)))
            v = it["base"] + span * it["f"] * frac
        else:
            v = it["base"] + span * it["f"] * (frac ** 0.9)
        noise = abs(span) * 0.06 * rnd.uniform(-1, 1)
        if w == max(1, sw):
            noise = 0
        v = v + noise
        if it["unit"] == "건":
            v = round(it["base"] + span * it["f"] * frac)
        elif it["unit"] in ("ppm", "hr"):
            v = round(v)
        elif it["unit"] in ("%",) and abs(span) < 1:
            v = round(v, 3)
        else:
            v = round(v, 2)
        out[w] = v
    return out

for i, it in enumerate(ITEMS):
    it["actuals"] = gen_actuals(it, 100 + i)
    last_w = max(it["actuals"])
    it["current"] = it["actuals"][last_w]
    it["ach"] = (it["current"] - it["base"]) / (it["target"] - it["base"])

def milestones(it):
    names = ["현황 분석·원인 규명", "대책 수립", "대책 적용·평가", "효과 검증·표준화"]
    fr = [0.2, 0.45, 0.75, 1.0]
    dur = (it["end"] - it["start"]).days
    out = []
    for n, f in zip(names, fr):
        plan = it["start"] + dt.timedelta(days=round(dur * f))
        actual = None
        if plan <= BASE_DATE:
            actual = plan + dt.timedelta(days=random.Random(it["id"] + n).choice([-3, 0, 2, 5]))
            if it["id"] == "AI-04" and n == "대책 적용·평가": actual = None      # 지연 예시
            if it["id"] == "AI-06" and n == "효과 검증·표준화": actual = None   # 지연 예시
            if actual and actual > BASE_DATE: actual = BASE_DATE
        out.append(dict(id=it["id"], name=n, plan=plan, actual=actual))
    return out
MILESTONES = [m for it in ITEMS for m in milestones(it)]

# ---------- Torque F/U (AI-01) 예시 ----------
TQ_SPEC = dict(lsl=2.0, tgt=2.5, usl=3.0, unit="N·m", cycle_hr=8)
_r = random.Random(7)
EQUIP = ["#1", "#2", "#3", "#4", "#5", "#6"]
TQ_LOTS = []
eq_seq = ["#3"] * 14 + ["#1"] * 3 + ["#5"] * 3 + ["#2"] * 2 + ["#4"] * 1 + ["#6"] * 1
_r.shuffle(eq_seq)
oos_idx = {4, 11, 19}
for k in range(24):
    d0 = D(2027, 3, 2) + dt.timedelta(days=int(k * 3.6))
    if k in oos_idx:
        vals = [round(_r.uniform(1.82, 1.97), 2) for _ in range(3)]
    else:
        c = _r.uniform(2.35, 2.65)
        vals = [round(c + _r.uniform(-0.08, 0.08), 2) for _ in range(3)]
    gap = round(_r.choice([2, 3, 4, 5, 6, 7, 9, 11, 14]) + _r.random(), 1)
    TQ_LOTS.append(dict(date=d0, lot=f"P7{_r.randint(1000,9999)}.{_r.randint(1,9)}", die=f"S{_r.randint(1,25):02d}",
                        eq=eq_seq[k], head=_r.choice(["H1", "H2"]), t=vals, gap=gap,
                        pos=_r.choice(["edge 좌", "edge 우", "corner", "edge 상", "edge 하"]),
                        sus=("head 평탄도" if eq_seq[k] == "#3" else "-")))
TQ_MON = []
for k in range(40):
    TQ_MON.append(dict(date=D(2027, 3, 1) + dt.timedelta(days=int(k * 2.2)), eq=EQUIP[k % 6],
                       v=round(_r.gauss(2.52, 0.11), 2)))

# ---------- 주간 보고 log 예시 ----------
REPORTS = [
 ("AI-01", 21, "불량 lot 24건 torque 이력 연계 완료 : 21건(87.5%) 규격 내", "#3 호기 head 평탄도 측정 (Stack팀 협업)", "head 평탄도 측정 jig 지원 요청"),
 ("AI-01", 22, "#3 호기 14건 편중 확인 : head 평탄도 측정 진행", "평탄도 vs edge_cr 상관 분석", "-"),
 ("AI-02", 22, "dressing 주기 300→200 wafer 적용 : mean 9.8µm", "wheel 교체 기준 수치화 (잔량 기준)", "-"),
 ("AI-03", 22, "DOE 1차 (feed speed 3수준) 완료", "냉각수 유량 2차 DOE", "DOE wafer 50매 지원 요청"),
 ("AI-04", 22, "#2 설비 profile matching 진행 : 계획 대비 2주 지연", "#2 matching 완료 후 σ 재측정", "설비 PM 일정 조정 필요"),
 ("AI-05", 22, "cure profile 2안 평가 진행", "EMC lot별 warpage 비교", "-"),
 ("AI-06", 22, "PM 주기 변경 적용 : MTBF 176hr", "효과 검증 완료 후 표준화 (2주)", "완료 목표일 경과 : 6월 2주 완료 예정"),
 ("AI-07", 22, "threshold 재설정 recipe 평가 : 검출률 87%", "유출 sample 30ea 재검증", "-"),
 ("AI-08", 22, "S1~S3 SOP 3건 등록 완료", "S4 dicing SOP 초안 review", "-"),
]
