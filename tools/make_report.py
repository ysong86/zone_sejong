# -*- coding: utf-8 -*-
"""보고자료: 세종 생활권 진단 상황판의 진단 과정과 활용방안 (A4 5쪽 내외, .docx).

수치는 data/latest.json(실측)에서 읽는다. 그림은 tools/make_figures.py 가 먼저 만들어 둔다.
  python tools/make_figures.py && python tools/make_report.py
"""
from __future__ import annotations

import json
import os
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import livingzone as LZ  # noqa: E402

OUT = os.path.join(HERE, "docs", "생활권진단_상황판_보고서.docx")
FIG = os.path.join(HERE, "docs", "figures")
FONT = "맑은 고딕"
INK = RGBColor(0x15, 0x23, 0x2A)
ACCENT = RGBColor(0x1D, 0x5C, 0x7C)
MUTED = RGBColor(0x4B, 0x5B, 0x62)
HEAD_FILL = "E1ECF1"
BOX_FILL = "F2F6F7"

with open(os.path.join(HERE, "data", "latest.json"), encoding="utf-8") as f:
    L = json.load(f)
U = L["units"]
ZONE_OF = {a["name"]: a["zone"] for a in LZ.ADMIN}


# ── 서식 도우미 ────────────────────────────────────────────────────────
def set_font(run, size=10, bold=False, color=INK):
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def para(doc_or_cell, text="", size=10, bold=False, color=INK, align=None, before=0, after=3,
         indent=0.0, hanging=0.0, line=1.12):
    p = doc_or_cell.add_paragraph()
    pf = p.paragraph_format
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = line
    if indent or hanging:
        pf.left_indent = Cm(indent + hanging)
        pf.first_line_indent = Cm(-hanging)
    if align:
        p.alignment = align
    if text:
        add_runs(p, text, size, bold, color)
    return p


def add_runs(p, text, size=10, bold=False, color=INK):
    """**굵게** 표기를 run 으로 나눈다."""
    parts = text.split("**")
    for i, part in enumerate(parts):
        if part:
            set_font(p.add_run(part), size, bold or i % 2 == 1, color)


def shade(cell, fill):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def cell_margins(table, top=50, bottom=50, left=90, right=90):
    tblPr = table._element.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(v))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)


def borders(table, color="B8C4C8", size=4):
    tblPr = table._element.tblPr
    b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:color"), color)
        b.append(el)
    tblPr.append(b)


def table(doc, header, rows, widths, size=8.5, head_size=8.5, align_center=()):
    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    borders(t)
    cell_margins(t, 30, 30, 80, 80)
    for r_i, row in enumerate([header] + rows):
        for c_i, text in enumerate(row):
            c = t.cell(r_i, c_i)
            c.width = Cm(widths[c_i])
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            if r_i == 0 or c_i in align_center:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_runs(p, str(text), head_size if r_i == 0 else size, r_i == 0)
            if r_i == 0:
                shade(c, HEAD_FILL)
    for c_i, w in enumerate(widths):
        for cell in t.columns[c_i].cells:
            cell.width = Cm(w)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trPr.append(cs)
    return t


def caption(doc, text):
    para(doc, text, size=8.5, bold=True, color=MUTED, before=6, after=3)


def note(doc, text):
    para(doc, text, size=8, color=MUTED, before=2, after=6)


def h1(doc, text):
    p = para(doc, text, size=12.5, bold=True, color=ACCENT, before=9, after=4)
    pPr = p._element.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    bot = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", "6"), ("space", "2"), ("color", "1D5C7C")):
        bot.set(qn(f"w:{k}"), v)
    bdr.append(bot)
    pPr.append(bdr)
    p.paragraph_format.keep_with_next = True
    return p


def sq(doc, text):      # □ 수준
    p = para(doc, "□ " + text, size=10, bold=True, before=4, after=1.5, hanging=0.5)
    p.paragraph_format.keep_with_next = True
    return p


def ci(doc, text):      # ○ 수준
    return para(doc, "○ " + text, size=9.5, before=0, after=1.5, indent=0.4, hanging=0.45)


def da(doc, text):      # - 수준
    return para(doc, "- " + text, size=9.5, color=INK, before=0, after=1.5, indent=0.95, hanging=0.35)


def box(doc, lines, title=None):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    borders(t, color="1D5C7C", size=8)
    cell_margins(t, 110, 110, 160, 160)
    c = t.cell(0, 0)
    c.width = Cm(17)
    shade(c, BOX_FILL)
    c.paragraphs[0].paragraph_format.space_after = Pt(0)
    if title:
        add_runs(c.paragraphs[0], title, 10.5, True, ACCENT)
    else:
        c._element.remove(c.paragraphs[0]._element)
    for ln in lines:
        para(c, "○ " + ln, size=9.5, after=2, hanging=0.45)
    return t


# ── 수치 ──────────────────────────────────────────────────────────────
def zone_stat(z, key):
    s = w = 0.0
    for n, u in U.items():
        v, p = u.get(key), u.get("pop") or 0
        if ZONE_OF.get(n) == z and v is not None and p:
            s += v * p
            w += p
    return s / w if w else None


def zone_pop(z):
    return sum(u.get("pop") or 0 for n, u in U.items() if ZONE_OF.get(n) == z)


def fmt(v, d=1, suffix=""):
    return "—" if v is None else f"{v:.{d}f}{suffix}"


LQ = L["lq"]
FLOOR = L["floor"]
C = L["counts"]
A = L["asof"]
nas = U["나성동"]
total_pop = sum(u.get("pop") or 0 for u in U.values())
total_stores = sum(u.get("stores") or 0 for u in U.values())
gov_extra = FLOOR.get("_gov_extra", 0)


def ym(s):
    return f"{s[:4]}. {int(s[4:])}." if s and len(s) == 6 else s


# ── 문서 ──────────────────────────────────────────────────────────────
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.top_margin = sec.bottom_margin = Cm(2.0)
sec.left_margin = sec.right_margin = Cm(2.0)
st = doc.styles["Normal"]
st.font.name = FONT
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.font.size = Pt(10)

# 쪽 번호(가운데 아래)
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = fp.add_run()
for tag, txt in (("begin", None), (None, "PAGE"), ("end", None)):
    if tag:
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), tag)
    else:
        el = OxmlElement("w:instrText")
        el.set(qn("xml:space"), "preserve")
        el.text = txt
    r._element.append(el)
set_font(r, 8.5, color=MUTED)

# 제목부
para(doc, "보고자료", size=9, bold=True, color=ACCENT, after=2)
para(doc, "세종 생활권 진단 상황판 구축과 활용방안", size=18, bold=True, after=2, line=1.1)
para(doc, "행복도시 생활권 재구조화 검토를 위한 지표·지도 기반 진단 체계", size=11, color=MUTED, after=6)
para(doc, "2026. 9. │ 세종연구원 연구모임(김성표, 안용준, 김흥주, 남영식, 이재민, 송양호, 이자은)",
     size=9, color=MUTED, after=1)
para(doc, "상황판 https://ysong86.github.io/zone_sejong/", size=9, color=MUTED, after=8)

lq = {z: (LQ.get(z) or [0] * 6)[i] for z, i in LZ.PLANNED.items()}
box(doc, [
    "행복도시 6개 생활권 체계를 경계조정이 아니라 **① 개발·건설 진척도 → ② 계획기능 실현도 → ③ 생활권 간 연계 → "
    "④ 국가중추·광역 관계** 네 단계로 진단하는 지표·지도 상황판을 구축함. 조성 중인 생활권은 진척도 대비 형성도로 봄",
    f"공공 API 15종, KTDB 통행 OD, 도서관 표준데이터로 지표 {len(LZ.INDICATORS)}개 중 **{len(L['live'])}개를 실측화**하고, 행정동 25곳 단위 지도와 "
    f"건축물대장(39,178동) 연면적 기반 **생활권별 기능 특화도(LQ)**를 산정함",
    f"시범 진단 결과 1·3·4생활권은 계획기능이 뚜렷하게 형성(LQ {lq['1']:.1f}·{lq['3']:.1f}·{lq['4']:.1f})된 반면, "
    f"조성 중인 **6생활권은 주거 입주 대비 첨단지식기반 기능(LQ {lq['6']:.2f})이 뒤따르지 못하고, 5생활권은 초기 조성 단계**라 "
    "'조성단계 점검' 대상으로 분류. 의료 기능은 1·2생활권에 집중",
    "상황판은 재구조화 논의의 공통 근거, 생활SOC 우선순위 판단, 생활권 계획의 정기 모니터링 도구로 활용 가능",
], title="요 약")

# 1. 배경
h1(doc, "1. 검토 배경과 목적")
sq(doc, "배경")
ci(doc, "행복도시는 중앙녹지를 비워 두고 그 둘레에 6개 기능 생활권(중앙행정, 문화·국제교류, 도시행정, 대학·연구, "
        "의료·복지, 첨단지식기반)을 배치한 환상형 다핵 구조로 계획됨(21개 기초생활권, 2~3만 명 단위)")
ci(doc, "조성 20년이 지나며 ① 국회세종의사당·대통령 세종집무실 등 국가중추기능의 입지 확정, ② 생활권별 조성 속도와 "
        "기능 형성의 편차, ③ 대전·청주 등 광역권과의 관계 변화가 겹쳐 기존 생활권 체계의 적합성을 다시 볼 필요가 커짐")
ci(doc, "연구원 내부 논의에서 단순한 경계조정보다 **생활권별 기능 재정립, 생활권 간 연계 강화, 국가중추기능 및 "
        "광역권과의 관계 재설정** 관점의 접근이 필요하다는 데 의견이 모임")
sq(doc, "목적")
ci(doc, "생활권 체계의 현재 상태를 공공데이터로 반복 측정할 수 있는 진단 틀과 상황판(웹)을 마련")
ci(doc, "재구조화 논의에서 공통으로 쓸 근거(지표·지도)와 이론에 기반한 개선방향 초안을 제시")

# 2. 진단 틀
h1(doc, "2. 진단 틀: 네 단계와 이론 근거")
ci(doc, "① 개발·건설 진척도 → ② 계획기능 실현도 → ③ 생활권 간 연계 → ④ 국가중추·광역 관계 순으로 진단함. "
        "진척도를 먼저 보는 것은 아직 조성 중인 생활권(4·5·6)을 성숙 생활권(1·2·3)과 같은 잣대로 판정하지 않기 위함")
ci(doc, "국내외 도시계획 이론을 단계별로 대응시키고, 이론이 요구하는 측정 대상을 공공데이터 지표로 옮겼음")
caption(doc, "<표 1> 진단 단계별 핵심 질문·이론 근거·지표")
table(doc, ["검토축", "핵심 질문", "이론 근거", "주요 지표"], [
    ["① 개발·건설\n진척도", "생활권이 어느 조성 단계에 있는가(판정 잣대를 정하는 선행 단계)",
     "행복도시 단계별 조성 계획(행정중심복합도시건설청)",
     "최근 5년 준공 비중, 준공 주택 대비 입주, 시가지화율, 주거 대비 계획기능 연면적"],
    ["② 계획기능\n실현도", "생활권마다 계획된 기능이 실제로 형성되었는가",
     "중심지이론(Christaller, 1933)\n다핵도시권 기능 분업(Parr, 2004)",
     "기능 특화도(LQ), 직주비(종사자 ÷ 인구), 비주거 연면적 비중, 기능혼합도, 인구 1천 명당 점포, 인구 1만 명당 의사, 인구·연령 구조"],
    ["③ 생활권 간\n연계 강화", "생활권이 스스로 채워지고 서로 이어지는가",
     "근린주구(Perry, 1929)\n15분 도시(Moreno et al., 2021)\n형태적·기능적 다핵성(Burger & Meijers, 2012)\n노드–장소 모형(Bertolini, 1999)",
     "15분 생활서비스, 초등학교 도보 10분, 정류장 400m 커버리지, BRT 도보시간, 도서관 15분 커버리지, 공공체육시설, 생활권 간 통행"],
    ["④ 국가중추·\n광역 관계", "국가중추기능과 광역 관계가 생활권 위계에 담겨 있는가",
     "차용 규모(Meijers & Burger, 2017)\n세종 공간구조 변화(변은주 외, 2023)",
     "공공·연구 연면적 비중, ㎡당 아파트 매매가, 시외 통근, 광역 통행"],
], [2.3, 3.9, 5.0, 5.8], size=8.3)
ci(doc, "지표는 통행과 건조환경의 메타분석(Ewing & Cervero, 2010)이 제시한 5D(밀도·다양성·설계·목적지 접근성·"
        "대중교통 거리)에 맞춰 골랐고, 접근성은 Hansen(1959)의 정의와 2단계 유동집수역법(Luo & Wang, 2003)을 참고함")
ci(doc, "환상형 다핵 구조의 원형인 사회도시(Howard, 1902)는 '녹지로 나뉜 여러 중심이 교통으로 이어져 하나로 작동'하는지를 "
        "보라는 점에서 B축의 판단 기준으로 삼음")

# 3. 자료
h1(doc, "3. 자료와 지표 구성")
caption(doc, "<표 2> 연동 자료와 산출 지표 (2026. 9. 24. 수집)")
table(doc, ["자료", "제공기관", "규모·기준시점", "산출 지표"], [
    ["행정동별 주민등록 인구·세대, 성·연령별 인구", "행정안전부", f"행정동 25곳, {ym(A['mois_pop'])} 말",
     "인구, 1년 증감률, 세대당 인구, 60세 이상·0~19세 비중"],
    ["상가(상권)정보", "소상공인시장진흥공단", f"점포 {C['stores']:,}곳, {ym(A['sbiz'])}", "기능혼합도, 1천 명당 점포, 15분 생활서비스"],
    ["버스정류소정보", "국토교통부(TAGO)", f"정류장 {C['stops']:,}곳(BRT {C['brt_stops']}곳)", "정류장 400m 커버리지, BRT 도보시간"],
    ["아파트 매매 실거래가", "국토교통부", f"{C['trades']:,}건(최근 12개월)", "㎡당 매매가 중앙값"],
    ["병원정보서비스", "건강보험심사평가원", f"의료기관 {C['hospitals']}곳", "1만 명당 의사, 15분 서비스(의원)"],
    ["전국체육시설 정보", "국민체육진흥공단", f"정상운영 {C['sports']}곳", "1만 명당 공공체육시설, 15분 서비스(운동)"],
    ["전국도서관표준데이터", "공공데이터포털", f"도서관 {C['libraries']}곳({A['lib'][:7].replace('-', '. ')}.)", "도서관 15분 커버리지"],
    ["건축물대장정보(표제부)", "국토교통부(건축HUB)", f"{C['buildings']:,}동", "기능 특화도(LQ), 비주거·공공연구 연면적 비중"],
    ["상업용부동산 임대동향(R-ONE)", "한국부동산원", f"표본 상권 3곳, {A['reb']}", "상가 공실률(나성·한솔, 도담·어진, 조치원)"],
    ["여객 기종점 통행량(목적·주수단 OD)", "국가교통DB(KTDB)", "대전세종충청권 2024, 세종 행정동 24존",
     "생활권 간 통행, 다른 생활권 통행, 시외 통근, 대중교통 분담률"],
    ["주택인허가정보(사업계획승인)", "국토교통부(건축HUB)", "30세대 이상 단지, 승인 후 입주 전", "주택 파이프라인, 입주 예정 연도"],
    ["건축인허가정보", "국토교통부(건축HUB)", "2018년 이후 허가·미준공", "건설 파이프라인(착공 중·허가), 건설 진척률"],
    ["사업체 통계(SGIS)", "통계청", f"{A['sgis']}년, 행정동별 종사자", "직주비(종사자 ÷ 인구)"],
    ["인구총조사 통근·통학(KOSIS)", "통계청", f"2020년, 세종 유출 {L['commute']['out']:,}명", "광역 통근·통학 흐름(대전·청주·공주·천안 등)"],
    ["학교기본정보(NEIS)", "교육부(좌표: 브이월드)", f"학교 {C['schools']}곳(초등 55곳)", "초등학교 도보 10분(800m) 커버리지"],
    ["도시공원정보", "세종특별자치시", f"공원 {C['parks']}곳", "지도 표출(시 관리분만 수록돼 지표 미사용)"],
], [4.3, 3.0, 3.8, 5.9], size=8.2)
sq(doc, "산정 원칙")
ci(doc, "**공간단위**: 인구 통계가 행정동 단위로 공표되므로 행정동 25곳(도담·어진동 합산)을 기본 단위로 하고, "
        "생활권 경계는 구성 법정동을 합쳐 구성")
ci(doc, "**거주지 대용**: 행정동 안 120m 격자점 가운데 점포·정류장 300m 이내 점을 '시가지 격자점'으로 두고 접근성 지표를 "
        "평균. 도보 15분은 직선 1km(우회계수 1.25, 시속 4.8km)로 환산")
ci(doc, "**기능 특화도**: 건축물 주용도를 6개 기능으로 분류해 생활권별 연면적 입지계수(LQ = 생활권 내 기능 비중 ÷ "
        "세종 전체 기능 비중)를 산정. 초·중·고·학원은 어느 생활권에나 있는 생활시설로 보아 제외")
ci(doc, f"**보정**: 정부세종청사 본관은 건축물대장에 등재돼 있지 않아, 공표 연면적(836,999㎡, 정부청사관리본부)과 "
        f"등재분의 차이(약 {gov_extra / 10000:.0f}만㎡)를 1생활권 중앙행정 연면적에 더함")
sq(doc, "한계")
ci(doc, "연령 통계가 10세 단위라 고령은 60세 이상, 유소년은 0~19세로 산정. 집현동 행정동이 4·5생활권을 함께 관할해 "
        "5생활권 인구를 따로 뗄 수 없음. 5생활권은 등재 건물 연면적이 "
        f"{FLOOR.get('5', {}).get('tot', 0) / 10000:.1f}만㎡에 그쳐 LQ가 몇 동에 좌우됨")
ci(doc, "지표는 모두 실측이나, 상가 공실률은 부동산원 표본 상권이 있는 행정동(나성·한솔, 도담·어진, 조치원)만 값이 있고, "
        "KTDB OD 는 모형으로 추정한 통행량(2024 기준)이며 집현동이 분동 전이라 반곡동 존에 포함됨")

# 4. 진단 과정
h1(doc, "4. 진단 과정")
ci(doc, "상황판은 아래 다섯 단계를 한 번에 수행하며, 명령 한 줄(run.py --collect --live)로 전체를 다시 계산함")
caption(doc, "<표 3> 진단 절차")
table(doc, ["단계", "내용", "결과물"], [
    ["① 자료 수집", "공공 API 호출(월 1회 권장), 원자료 보관. 일시 오류는 자동 재시도", "원자료(인구·점포·정류장·건축물 등)"],
    ["② 공간 결합", "좌표 자료는 행정동 면에 점 포함 판정, 코드 자료는 행정동코드·법정동명으로 결합", "행정동별 자료표"],
    ["③ 지표 산정", f"행정동별 실측 지표 {len(L['live'])}개, 생활권별 기능 특화도(LQ) 계산", "지표 지도, 순위표"],
    ["④ 교차 진단", "조성 단계를 먼저 매기고, 성숙 생활권은 계획기능 LQ로, 조성 중 생활권은 주거 대비 계획기능 연면적으로 판정",
     "유지·고도화 / 보강 / 전환·재정의 / 조성단계 점검"],
    ["⑤ 방향 연결", "판정 결과를 이론 근거가 붙은 개선방향 9개와 점검 지표로 연결", "축별 개선방향, 해외 사례"],
], [2.3, 9.2, 5.5], size=8.5, align_center=(0,))
ci(doc, "화면은 세 축 요약 → 지표 지도(지표 선택·5분위 채색·동별 상세) → 생활권 진단 카드(방사형 그래프) → 연계 구조 → "
        "이론 틀 → 개선방향 → 자료원 연동 상태 순으로 구성해, 요약에서 근거까지 내려가며 읽을 수 있게 함")

# 5. 결과
h1(doc, "5. 시범 진단 결과")
caption(doc, "<표 4> 생활권별 진단 요약 (실측)")
rows = []
for z in ["1", "2", "3", "4", "5", "6", "S", "R"]:
    zn = next(q for q in LZ.ZONES if q["id"] == z)
    plan = LZ.PLANNED.get(z)
    lqv = (LQ.get(z) or [None] * 6)
    lqtxt = "—" if plan is None or lqv[plan] is None else f"{lqv[plan]:.2f}" + ("*" if FLOOR.get(z, {}).get("thin") else "")
    pop = zone_pop(z)
    stg = {"mature": "성숙", "late": "조성 후기", "building": "조성 중", "early": "초기 조성"}.get(
        (L.get("progress", {}).get(z) or {}).get("stage"), "—")
    rows.append([zn["name"] + "\n(" + stg + ")", zn["role"], lqtxt, f"{pop / 10000:.1f}" if pop else "—",
                 fmt(zone_stat(z, "svc")), fmt(zone_stat(z, "lib"), 0, "%"), fmt(zone_stat(z, "med")),
                 LZ_TYPE[z] if (LZ_TYPE := {k: {"keep": "유지·고도화", "boost": "보강", "shift": "전환·재정의", "watch": "조성단계 점검"}[v["type"]]
                                           for k, v in LZ.DIAGNOSIS.items()}) else ""])
table(doc, ["생활권", "계획기능", "계획기능\nLQ", "인구\n(만 명)", "15분 서비스\n(종/8)", "도서관\n15분", "의사\n(1만 명당)", "판정"],
      rows, [1.9, 3.5, 1.6, 1.5, 1.9, 1.6, 1.8, 2.2], size=8.2, align_center=(2, 3, 4, 5, 6, 7))
note(doc, "주: 인구·15분 서비스 등은 행정동 인구가중 평균. 4생활권 인구에는 집현동 행정동이 관할하는 5생활권(합강·다솜·용호) "
          "인구가 포함됨. * 등재 연면적 0.6만㎡로 몇 동에 좌우되는 값. S생활권은 거주인구가 거의 없음.")

sq(doc, "주요 진단")
PR = L.get("progress", {})
ci(doc, f"**조성 단계의 차이**: 최근 5년 준공 연면적 비중이 1~3생활권 {PR['1']['recent']}·{PR['2']['recent']}·{PR['3']['recent']}%인 반면 "
        f"4생활권 {PR['4']['recent']}%, 6생활권 {PR['6']['recent']}%로 한창 조성 중이고, 5생활권은 준공 건물이 거의 없는 초기 조성 단계. "
        f"6생활권은 주택 입주율이 {PR['6']['occ']}%에 이르렀지만 주거 대비 첨단기능 연면적은 {PR['6']['fn_per_res'] * 100:.1f}%로 "
        f"성숙 생활권 평균({sum(PR[z]['fn_per_res'] for z in '123') / 3 * 100:.0f}%)에 크게 못 미치고, 허가·착공 중인 물량"
        f"({PR['6']['pipe_started_man'] + PR['6']['pipe_permitted_man']:.1f}만㎡)에도 첨단기능 용도가 없음 — '주거 조성 대비 첨단지식기반 "
        f"기능 형성도' 점검 대상. 5생활권은 건설 진척률 {PR['5']['build_rate']}%로 조성 초입이며, 사업계획승인 후 입주 전인 "
        f"공동주택이 {PR['5']['hs_started'] + PR['5']['hs_approved']:,}세대(입주 예정 "
        f"{', '.join(f'{y}년 {n:,}' for y, n in PR['5']['hs_due'].items())})로 주거가 먼저 들어올 예정 — "
        "의료·복지 기능이 이 입주 속도를 따라오는지가 점검 포인트")
ci(doc, f"**계획기능 형성의 이분화**: 1·3·4생활권은 계획기능 LQ가 {lq['1']:.1f}·{lq['3']:.1f}·{lq['4']:.1f}로 뚜렷하나, "
        f"6생활권 첨단지식기반은 {lq['6']:.2f}, 5생활권 의료·복지는 등재 건물조차 거의 없음. 6생활권(해밀동)은 1년 새 인구가 "
        f"{U['해밀동']['chg']:.1f}% 늘고 0~19세 비중이 {U['해밀동']['kid']:.1f}%로 가장 젊은 주거지로 먼저 채워지는 중")
ci(doc, f"**일터와 잠자리의 분리**: 인구 대비 종사자(직주비)는 나성동 {nas['emp']:.2f}, 도담·어진동 "
        f"{U['도담·어진동']['emp']:.2f}인 반면 해밀동 {U['해밀동']['emp']:.2f}, 종촌·다정동 {U['종촌동']['emp']:.2f}로 "
        f"신규·주거 생활권은 일자리가 거의 없음({A['sgis']}년 사업체조사)")
ci(doc, f"**의료 기능의 계획 외 입지**: 인구 1만 명당 의사는 나성동 {nas['med']:.0f}명, 도담·어진동 "
        f"{U['도담·어진동']['med']:.0f}명(세종충남대병원)인 반면 집현동 {U['집현동']['med']:.1f}명, 해밀동 "
        f"{U['해밀동']['med']:.1f}명 — '의료·복지 생활권' 전제를 다시 볼 근거")
vc = L.get("vacancy") or {}
ci(doc, f"**상업 기능의 쏠림**: 세종 점포의 {nas['stores'] / total_stores * 100:.0f}%({nas['stores']:,}곳)가 나성동 한 곳에 있고 "
        f"인구 1천 명당 {nas['dens']:.0f}곳. 세종 중대형 상가 공실률은 {vc.get('중대형', {}).get('세종', ['', 0])[1]:.1f}%"
        f"({A.get('reb', '')}, 부동산원) — 생활권마다 같은 급으로 계획된 중심상가와 실제 위계가 어긋남(중심지이론)")
ci(doc, f"**공공 생활SOC 격차가 상업 서비스보다 큼**: 15분 생활서비스는 1~3생활권 7.8~8.0종, 4·6생활권 "
        f"{zone_stat('4', 'svc'):.1f}·{zone_stat('6', 'svc'):.1f}종으로 차이가 작지만, 도서관 15분 커버리지는 3생활권 "
        f"{zone_stat('3', 'lib'):.0f}%에 비해 4생활권 {zone_stat('4', 'lib'):.0f}%, 6생활권 {zone_stat('6', 'lib'):.0f}%에 그침")
ci(doc, f"**근린주구 원칙의 약화**: 초등학교 도보 10분(800m) 안의 시가지 비율이 1~3생활권은 "
        f"{zone_stat('1', 'school'):.0f}~{zone_stat('3', 'school'):.0f}%이나 4생활권 {zone_stat('4', 'school'):.0f}%, "
        f"6생활권 {zone_stat('6', 'school'):.0f}%로 떨어짐 — 신규 생활권에서 기초생활권 설계 원칙(Perry)이 느슨해짐")
cm = L["commute"]; pt = cm["partners"]
ci(doc, f"**광역 관계는 대전 쏠림**: 세종 통근·통학 인구의 {cm['out'] / cm['total'] * 100:.0f}%({cm['out']:,}명)가 시 밖으로 "
        f"나가며, 그 {pt['dj']['out'] / cm['out'] * 100:.0f}%가 대전(유성구 중심)으로 감. 청주 {pt['cj']['out']:,}명, "
        f"공주 {pt['gj']['out']:,}명, 천안·아산 {pt['ca']['out']:,}명으로 북동 방향 연계는 약함(2020 인구총조사) — "
        "변은주 외(2023)의 결과와 같은 방향")
FL = L["od"]["flows"]
_tot = sum(f[2] for f in FL)
_hub = sum(f[2] for f in FL if "1" in f[:2])
_nm = lambda f: f"{f[0]}↔{f[1]}".replace("R", "읍면")
ci(doc, f"**1생활권 중심의 허브형 연계**: 생활권 사이 하루 통행 {_tot:,.0f}천 가운데 {_hub / _tot * 100:.0f}%가 1생활권을 한쪽 끝으로 함"
        f"(가장 강한 {', '.join(_nm(f) + ' ' + str(f[2]) + '천' for f in FL[:3])}). 반면 {', '.join(_nm(f) + ' ' + str(f[2]) + '천' for f in FL[-2:])}처럼 "
        "이웃 생활권끼리의 직접 연결은 약해, 환상형 순환 구조보다 1생활권 집중 구조로 작동함(KTDB 2024). "
        f"해밀동(6생활권)은 활동 통행의 {U['해밀동']['inter']}%를 다른 생활권에 기대면서 대중교통 분담률은 {U['해밀동']['transit']}%로 가장 낮음")
ci(doc, f"**읍면은 다른 도시**: 60세 이상 {zone_stat('R', 'old'):.0f}%, 세대당 {zone_stat('R', 'hh'):.1f}명으로 행복도시"
        f"(각 13% 안팎, 2.6명)와 인구구조가 전혀 다르고, 공장 중심의 첨단·민간업무 LQ {(LQ.get('R') or [0]*6)[5]:.2f}로 "
        "산업 기능을 담당 — 두 생활권 체계를 함께 보는 틀이 필요")

ft = doc.add_table(rows=2, cols=2)
ft.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, (img, w, cap) in enumerate((
        ("fig1_svc_map.png", 8.4, "<그림 1> 행정동별 15분 생활서비스(종/8)"),
        ("fig2_lq_bar.png", 8.4, "<그림 2> 생활권별 계획기능 특화도(LQ)  * 참고값"))):
    c = ft.cell(0, i)
    c.width = Cm(8.6)
    pp = c.paragraphs[0]
    pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pp.add_run().add_picture(os.path.join(FIG, img), width=Cm(w))
    cp = ft.cell(1, i).paragraphs[0]
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_runs(cp, cap, 8.3, True, MUTED)
para(doc, "", after=2)

# 6. 활용방안
h1(doc, "6. 활용방안")
sq(doc, "생활권 재구조화 논의의 공통 근거")
ci(doc, "**기능 재정립**: 성숙 생활권(1~3)은 LQ 판정표로 역할을 점검하고, 조성 중 생활권(5·6)은 진척도 대비 "
        "계획기능 형성도를 정기 점검함. 5생활권은 조성 진척에 맞춰 의료·복지 용지·시설이 착공되는지, 6생활권은 주거 대비 "
        "첨단지식기반 연면적이 따라오는지를 보고, 준공 뒤에도 미형성이면 역할 재설정을 검토")
ci(doc, "**연계 강화**: BRT 도보시간·15분 서비스 결핍 행정동을 우선 대상으로, 생활권 경계부 BRT 정류장 주변에 "
        "두 생활권이 함께 쓰는 복합 거점 입지를 검토(노드–장소 모형)")
ci(doc, "**국가중추·광역**: 국가상징구역 입지에 따른 중심 위계 변화, 대전·청주·오송과의 기능 분담을 공공·연구 연면적과 "
        "광역 흐름 지표로 함께 검토(차용 규모 관점)")
sq(doc, "정책·계획 연계")
ci(doc, "**생활SOC 우선순위**: 도서관·공공체육시설 커버리지가 낮은 행정동(집현·해밀, 읍면)부터 배치하되, 신축보다 "
        "학교·공공청사의 시간 공유를 우선(파리 15분 도시 사례)")
ci(doc, "**상가 대응**: 인구 1천 명당 점포와 공실 지표를 겹쳐 중심상가 총량 조정·용도 유연화 대상지를 고름")
ci(doc, "**행복도시–읍면 연계**: 두 생활권 체계를 한 화면에서 비교해 조치원 부도심 기능 강화 논의의 근거로 씀")
sq(doc, "상시 모니터링")
ci(doc, "월 1회 자동 갱신(인구·상가·실거래·건축물), 분기별 진단 요약으로 생활권 계획 재검토 시점의 기준선을 관리")
ci(doc, "지표마다 '실측/샘플'과 자료 기준시점을 화면에 밝혀, 근거의 신뢰 수준을 함께 전달")

# 7. 향후 과제
h1(doc, "7. 향후 과제")
ci(doc, "**샘플 지표 실측화**: 생활권 간 통행(KTDB 여객 O/D, 세종 BIS·교통카드), 시외 통근(KOSIS 인구주택총조사), "
        "상가 공실(한국부동산원 R-ONE) 자료 확보")
ci(doc, "**공간단위 정교화**: 행정안전부 법정동별 인구 API로 5생활권 인구를 분리하고, 어진동·가람동 경계를 확보")
ci(doc, "**지표 고도화**: 2단계 유동집수역법으로 시설 정원·병상 대비 접근성 산정, 통신 생활인구 확보 시 주간인구 반영")
ci(doc, "**운영**: 연구원 NAS 기반 자동 갱신 체계 구축, 연구모임 정례 검토회의에서 진단 결과 점검")

# 참고문헌
h1(doc, "참고문헌")
refs = [t["cite"] for t in LZ.THEORY]
refs = [r.replace(" / Luo, W., & Wang, F. (2003). Environment and Planning B, 30(6), 865–884.", "") for r in refs]
refs.append("Luo, W., & Wang, F. (2003). Measures of spatial accessibility to health care in a GIS environment: "
            "Synthesis and a case study in the Chicago region. Environment and Planning B, 30(6), 865–884.")
refs.append("정부청사관리본부. 정부세종청사 소개(대지면적·연면적). https://gbmo.go.kr")
dom = sorted([r for r in refs if not r[0].isascii()])
intl = sorted([r for r in refs if r[0].isascii()])
for r in dom + intl:
    para(doc, r, size=8, after=1, hanging=0.6, line=1.0)
para(doc, "※ 사례: 파리 '15분 도시', 멜버른 '20분 동네'(Plan Melbourne 2017–2050), 네덜란드 란트스타트, 캔버라 계획수도",
     size=8, color=MUTED, before=2)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
doc.save(OUT)
print("저장:", OUT)
