#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pnu-hwpx-report — 빌더
부산대학교 「산지니 AI 활용 사례 공모전 추진계획」 예시 HWPX 와 동일한 서식으로
한글(HWPX) 보고서를 생성한다.

동작 방식
  - 원본 예시의 자원 풀(assets/header.xml : 폰트·글자·문단·테두리·그라데이션)과
    로고 이미지·스크립트를 **그대로 재사용**하여 서식 충실도 100% 를 보장한다.
  - 본문(Contents/section0.xml)만 콘텐츠 JSON 으로부터 코드로 생성한다.
    (섹션·글머리·표 행 수 자유. linesegarray 는 생략 → 한글이 열 때 재계산)
  - 그라데이션 제목 배너와 로고 발신부는 원본 조각(tpl_title/tpl_issuer)을 재사용하고
    텍스트만 치환한다.

사용법
  python build.py -c content.json -o 결과물.hwpx
"""
import argparse, datetime, json, os, re, sys, zipfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")

# ----------------------------------------------------------------------------
# 네임스페이스 (본문 section)
# ----------------------------------------------------------------------------
NS_SEC = (
    'xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" '
    'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
    'xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph" '
    'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
    'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" '
    'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
    'xmlns:hhs="http://www.hancom.co.kr/hwpml/2011/history" '
    'xmlns:hm="http://www.hancom.co.kr/hwpml/2011/master-page" '
    'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:opf="http://www.idpf.org/2007/opf/" '
    'xmlns:ooxmlchart="http://www.hancom.co.kr/hwpml/2016/ooxmlchart" '
    'xmlns:hwpunitchar="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar" '
    'xmlns:epub="http://www.idpf.org/2007/ops" '
    'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0"'
)

# ----------------------------------------------------------------------------
# 자원 ID 맵 (assets/header.xml 에 정의된 실제 ID — 예시 문서에서 추출)
#   charPr(글자모양) / paraPr(문단모양) / borderFill(테두리채움)
# ----------------------------------------------------------------------------
# 글자모양
C_NUM_WHITE   = 16   # 절 번호(네모 남색박스 안 흰색) 16pt HY헤드라인M
C_SEC_TITLE   = 17   # 절 표제 17pt HY헤드라인M
C_BULLET      = 18   # ◦ 글머리표 15pt 휴먼명조
C_LABEL       = 19   # (라벨) 14pt 휴먼명조 볼드
C_BODY        = 20   # 본문 14pt 휴먼명조
C_NOTE        = 27   # ※ 주석 12pt 한양중고딕
C_TH2         = 22   # 표 머리행(2열) 12pt 휴먼명조 볼드
C_TH_MULTI    = 29   # 표 머리행(3열+) 12pt 휴먼명조 볼드
C_TD_LABEL    = 23   # 표 본문 라벨열 12pt 휴먼명조
C_TD          = 24   # 표 본문 내용 12pt 휴먼명조
C_ATT_NUM     = 49   # 붙임 번호(청록박스 안 흰색) 17pt HY헤드라인M
C_ATT_TITLE   = 51   # 붙임 제목 16pt HY헤드라인M
C_SPACER      = 8    # 여백 문단용

# 문단모양
P_GENERAL     = 0    # 일반(제목 문단 래퍼)
P_PLAIN       = 13   # 무테 일반(주석·표 셀)
P_SPACER1     = 16   # 여백(prev 6000)
P_DATE        = 17   # 날짜(가운데, 큰 글씨)
P_SPACER2     = 18   # 여백(prev 4000)
P_ISSUER      = 20   # 발신부 래퍼(가운데)
P_SEC_NUM     = 21   # 절 번호 셀(가운데)
P_SEC_TITLE   = 22   # 절 표제 셀(왼쪽, 밑줄)
P_SEC_WRAP    = 23   # 절 표제 표 래퍼(prev 1000)
P_BULLET      = 24   # ◦ 글머리(내어쓰기 -3014, prev 500)
P_TH          = 25   # 표 머리행 셀(가운데)
P_TD_CENTER   = 26   # 표 본문 라벨 셀(가운데)
P_TD_JUST     = 27   # 표 본문 내용 셀(양쪽) + 표 래퍼
P_ATT_TITLE   = 51   # 붙임 제목 셀

# 테두리채움 — 표 셀 매트릭스 (행 역할 × 열 위치)
#  2열 표 (내부 세로선 0.2mm)
BF2 = {
    "head":  {"L": 15, "R": 16},
    "first": {"L": 17, "R": 18},   # 머리행 아래 첫 본문행(위 이중선)
    "mid":   {"L": 19, "R": 20},
    "last":  {"L": 21, "R": 22},   # 마지막행(아래 굵은선)
}
#  3열+ 표 (내부 세로선 0.1mm)
BFN = {
    "head":  {"L": 23, "M": 24, "R": 25},
    "first": {"L": 26, "M": 27, "R": 28},
    "mid":   {"L": 29, "M": 30, "R": 31},
    "last":  {"L": 32, "M": 33, "R": 34},
    "sum":   {"L": 35, "M": 36, "R": 37},   # 합계행(연노랑 채움)
}
BF_TBL_OUTER  = 4    # 표 외곽(가는 실선 0.12)
BF_SEC_NUM    = 13   # 절 번호 셀(남색 #3E57A5 박스)
BF_SEC_TITLE  = 14   # 절 표제 셀(아래 밑줄만)
BF_ATT_NUM    = 38   # 붙임 번호 셀(청록 #079FCE 박스)
BF_ATT_GAP    = 39   # 붙임 사이 얇은 칸
BF_ATT_TITLE  = 40   # 붙임 제목 셀(전체 테두리)

TEXT_W = 45352       # 본문 가로폭(HWPUNIT) = A4(59528) - 좌우여백(7088*2)

# ----------------------------------------------------------------------------
# 유틸
# ----------------------------------------------------------------------------
def _t(s):
    """텍스트 이스케이프 + 줄바꿈 처리."""
    return escape(str(s)).replace("\n", "</hp:t><hp:lineBreak/><hp:t>")

_idc = [2200000000]
def _nid():
    _idc[0] += 1
    return _idc[0]

def _asset(name):
    with open(os.path.join(ASSETS, name), encoding="utf-8") as f:
        return f.read()

# ----------------------------------------------------------------------------
# 문단 / 셀 / 표 헬퍼
# ----------------------------------------------------------------------------
def para(paraPr, runs, pid=None, page_break=0):
    """runs = [(charPrIDRef, text), ...]. text=None 이면 빈 run."""
    pid = pid if pid is not None else _nid()
    inner = ""
    for cpr, text in runs:
        if text is None:
            inner += f'<hp:run charPrIDRef="{cpr}"/>'
        else:
            inner += f'<hp:run charPrIDRef="{cpr}"><hp:t>{_t(text)}</hp:t></hp:run>'
    if not runs:
        inner = f'<hp:run charPrIDRef="{C_SPACER}"/>'
    return (f'<hp:p id="{pid}" paraPrIDRef="{paraPr}" styleIDRef="0" '
            f'pageBreak="{page_break}" columnBreak="0" merged="0">{inner}</hp:p>')

def cell(runs, paraPr, bf, w, col, row, colspan=1, rowspan=1,
         header=False, margin=(510, 510, 141, 141), height=None):
    """표 셀. runs 는 [(charPr, text), ...] 또는 이미 만들어진 문단 XML 리스트(str)."""
    if runs and isinstance(runs[0], str):
        paras = "".join(runs)
        nlines = len(runs)
    else:
        rr = "".join(
            (f'<hp:run charPrIDRef="{c}"/>' if t is None
             else f'<hp:run charPrIDRef="{c}"><hp:t>{_t(t)}</hp:t></hp:run>')
            for c, t in runs) or f'<hp:run charPrIDRef="{C_TD}"/>'
        paras = (f'<hp:p id="{_nid()}" paraPrIDRef="{paraPr}" styleIDRef="0" '
                 f'pageBreak="0" columnBreak="0" merged="0">{rr}</hp:p>')
        nlines = max(1, sum(1 + str(t).count("\n") for _, t in runs if t is not None))
    # 셀 최소 높이 : 원본 단일 줄 행 ≈ 2048 에 맞춰 줄 수에 비례하여 넉넉히
    if height is None:
        height = 900 + nlines * 1250
    ml, mr, mt, mb = margin
    return (f'<hp:tc name="" header="{1 if header else 0}" hasMargin="0" protect="0" '
            f'editable="0" dirty="0" borderFillIDRef="{bf}">'
            f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" '
            f'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" '
            f'hasTextRef="0" hasNumRef="0">{paras}</hp:subList>'
            f'<hp:cellAddr colAddr="{col}" rowAddr="{row}"/>'
            f'<hp:cellSpan colSpan="{colspan}" rowSpan="{rowspan}"/>'
            f'<hp:cellSz width="{w}" height="{height}"/>'
            f'<hp:cellMargin left="{ml}" right="{mr}" top="{mt}" bottom="{mb}"/></hp:tc>')

def tbl_open(rowcnt, colcnt, width, outer_bf=BF_TBL_OUTER,
             out_m=(141, 141, 300, 200), in_m=(510, 510, 141, 141), treat_char=1):
    ol, orr, ot, ob = out_m
    il, ir, it, ib = in_m
    return (f'<hp:tbl id="{_nid()}" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" '
            f'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" '
            f'rowCnt="{rowcnt}" colCnt="{colcnt}" cellSpacing="0" borderFillIDRef="{outer_bf}" noAdjust="0">'
            f'<hp:sz width="{width}" widthRelTo="ABSOLUTE" height="1000" heightRelTo="ABSOLUTE" protect="0"/>'
            f'<hp:pos treatAsChar="{treat_char}" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
            f'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" '
            f'vertOffset="0" horzOffset="0"/>'
            f'<hp:outMargin left="{ol}" right="{orr}" top="{ot}" bottom="{ob}"/>'
            f'<hp:inMargin left="{il}" right="{ir}" top="{it}" bottom="{ib}"/>')

# ----------------------------------------------------------------------------
# 커버(표지) 블록
# ----------------------------------------------------------------------------
def cover(data):
    secpr = _asset("secpr.xml").strip()
    title_tbl = _asset("tpl_title.xml").strip()
    issuer_tbl = _asset("tpl_issuer.xml").strip()

    회차 = data.get("회차", "")
    title_tbl = title_tbl.replace("{{회차}}", _t(회차)).replace("{{제목}}", _t(data.get("제목", "")))
    issuer_tbl = (issuer_tbl.replace("{{발신1}}", _t(data.get("발신1", "")))
                            .replace("{{발신2}}", _t(data.get("발신2", ""))))

    out = []
    # 1) 제목 문단(id=0) : secPr(페이지설정) + 쪽번호 + 제목 배너 표
    colpr = ('<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" '
             'sameSz="1" sameGap="0"/></hp:ctrl>')
    pagenum = ('<hp:ctrl><hp:pageNum pos="BOTTOM_CENTER" formatType="DIGIT" sideChar="-"/></hp:ctrl>')
    out.append(
        f'<hp:p id="0" paraPrIDRef="{P_GENERAL}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="6">{secpr}{colpr}</hp:run>'
        f'<hp:run charPrIDRef="6">{pagenum}</hp:run>'
        f'<hp:run charPrIDRef="8">{title_tbl}<hp:t/></hp:run>'
        f'</hp:p>')
    # 2) 여백 3줄
    for _ in range(3):
        out.append(para(P_SPACER1, [], page_break=0))
    # 3) 날짜(가운데 큰 글씨) + 표지 쪽번호 숨김
    date_hide = ('<hp:ctrl><hp:pageHiding hideHeader="0" hideFooter="0" hideMasterPage="0" '
                 'hideBorder="0" hideFill="0" hidePageNum="1"/></hp:ctrl>')
    out.append(
        f'<hp:p id="{_nid()}" paraPrIDRef="{P_DATE}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="12"><hp:t>{_t(data.get("날짜",""))}</hp:t>{date_hide}<hp:t/></hp:run>'
        f'</hp:p>')
    # 4) 여백
    out.append(f'<hp:p id="{_nid()}" paraPrIDRef="{P_SPACER2}" styleIDRef="0" pageBreak="0" '
               f'columnBreak="0" merged="0"><hp:run charPrIDRef="12"/></hp:p>')
    # 5) 발신부(로고 + 부서) 표
    out.append(
        f'<hp:p id="{_nid()}" paraPrIDRef="{P_ISSUER}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="7">{issuer_tbl}<hp:t/></hp:run>'
        f'</hp:p>')
    return "".join(out)

# ----------------------------------------------------------------------------
# 본문 블록
# ----------------------------------------------------------------------------
def section_header(num, title, page_break=0, reset_page=False):
    """네모 숫자 절 표제 : [남색박스 번호][밑줄 제목]."""
    num_w = 3267
    title_w = max(18623, min(41000, len(str(title)) * 1900 + 3000))
    total = num_w + title_w
    num_cell = cell([(C_NUM_WHITE, str(num))], P_SEC_NUM, BF_SEC_NUM, num_w, 0, 0,
                    margin=(141, 141, 141, 141), height=2731)
    ttl_cell = cell([(C_SEC_TITLE, f" {title}")], P_SEC_TITLE, BF_SEC_TITLE, title_w, 1, 0,
                    margin=(141, 141, 141, 141), height=2731)
    t = (tbl_open(1, 2, total, out_m=(140, 140, 140, 140), in_m=(141, 141, 141, 141))
         + f'<hp:tr>{num_cell}{ttl_cell}</hp:tr></hp:tbl>')
    # 표지 다음 첫 절에서 쪽번호를 1 로 재설정(표지는 쪽번호 숨김 → 본문이 1페이지)
    newnum = '<hp:ctrl><hp:newNum num="1" numType="PAGE"/></hp:ctrl>' if reset_page else ''
    return (f'<hp:p id="{_nid()}" paraPrIDRef="{P_SEC_WRAP}" styleIDRef="0" '
            f'pageBreak="{page_break}" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="15">{t}{newnum}<hp:t/></hp:run></hp:p>')

def bullet(item):
    """◦ (라벨) 내용  — 라벨 없으면 ◦ 내용."""
    if isinstance(item, dict):
        runs = [(C_BULLET, " ◦ ")]
        if item.get("라벨"):
            runs.append((C_LABEL, f"({item['라벨']}) "))
        runs.append((C_BODY, item.get("내용", "")))
    else:
        runs = [(C_BULLET, " ◦ "), (C_BODY, str(item))]
    return para(P_BULLET, runs)

def subbullet(text):
    """하위 글머리 : - 내용 (◦ 아래 들여쓰기)."""
    return para(P_BULLET, [(C_BODY, f"   - {text}")])

def note(text):
    """※ 주석(작은 고딕)."""
    return para(P_PLAIN, [(C_NOTE, f"   ※ {text}")])

def spacer(char=C_BODY):
    return para(P_BULLET, [(char, None)])

def _col_role(i, ncol):
    if ncol <= 2:
        return "L" if i == 0 else "R"
    if i == 0:
        return "L"
    if i == ncol - 1:
        return "R"
    return "M"

def _row_role(r, nbody):
    """r: 본문행 인덱스(0부터). nbody: 본문행 수."""
    if nbody == 1:
        return "last"          # 단일 본문행 → 아래 굵은선(머리행 이중선은 머리행이 그림)
    if r == 0:
        return "first"
    if r == nbody - 1:
        return "last"
    return "mid"

def table(spec):
    """표 : {머리:[...], 행:[[...]], 폭:[...](선택), 정렬:['C'|'J', ...](선택), 합계행:bool(선택)}"""
    headers = spec["머리"]
    rows = spec["행"]
    ncol = len(headers)
    widths = spec.get("폭")
    if not widths:
        base = TEXT_W // ncol
        widths = [base] * ncol
        widths[-1] = TEXT_W - base * (ncol - 1)
    total = sum(widths)
    align = spec.get("정렬") or (["C"] + ["J"] * (ncol - 1))
    has_sum = spec.get("합계행", False)
    scheme = BF2 if ncol == 2 else BFN

    # 머리행
    th_char = C_TH2 if ncol == 2 else C_TH_MULTI
    trs = "<hp:tr>" + "".join(
        cell([(th_char, h)], P_TH, scheme["head"][_col_role(i, ncol)], widths[i], i, 0, header=True)
        for i, h in enumerate(headers)) + "</hp:tr>"

    nbody = len(rows)
    for r, rowv in enumerate(rows):
        role = "sum" if (has_sum and r == nbody - 1) else _row_role(r, nbody)
        role_scheme = scheme.get(role, scheme["mid"])
        tcs = ""
        for i, val in enumerate(rowv):
            a = align[i] if i < len(align) else "J"
            if a == "C":
                pp, ch = P_TD_CENTER, C_TD_LABEL
            else:
                pp, ch = P_TD_JUST, (C_TD_LABEL if i == 0 else C_TD)
            # 셀 내용이 여러 줄이면 문자열 리스트로 각 줄을 별도 문단화
            if isinstance(val, list):
                paras = [f'<hp:p id="{_nid()}" paraPrIDRef="{pp}" styleIDRef="0" pageBreak="0" '
                         f'columnBreak="0" merged="0"><hp:run charPrIDRef="{ch}">'
                         f'<hp:t>{_t(line)}</hp:t></hp:run></hp:p>' for line in val]
                tcs += cell(paras, pp, role_scheme[_col_role(i, ncol)], widths[i], i, r + 1)
            else:
                tcs += cell([(ch, val)], pp, role_scheme[_col_role(i, ncol)], widths[i], i, r + 1)
        trs += f"<hp:tr>{tcs}</hp:tr>"

    t = tbl_open(1 + nbody, ncol, total) + trs + "</hp:tbl>"
    return (f'<hp:p id="{_nid()}" paraPrIDRef="{P_TD_JUST}" styleIDRef="0" '
            f'pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{C_BODY}">{t}<hp:t/></hp:run></hp:p>')

def attach_header(num, title, page_break=1):
    """붙임 N + 제목."""
    w_num, w_gap = 6670, 1303
    w_title = TEXT_W - w_num - w_gap
    c0 = cell([(C_ATT_NUM, f"붙임 {num}")], P_TH, BF_ATT_NUM, w_num, 0, 0,
              margin=(141, 141, 200, 200))
    c1 = cell([(C_BODY, None)], P_PLAIN, BF_ATT_GAP, w_gap, 1, 0)
    c2 = cell([(C_ATT_TITLE, title)], P_PLAIN, BF_ATT_TITLE, w_title, 2, 0,
              margin=(400, 141, 200, 200))
    t = (tbl_open(1, 3, TEXT_W, out_m=(141, 141, 300, 300), in_m=(141, 141, 141, 141))
         + f'<hp:tr>{c0}{c1}{c2}</hp:tr></hp:tbl>')
    return (f'<hp:p id="{_nid()}" paraPrIDRef="{P_BULLET}" styleIDRef="0" '
            f'pageBreak="{page_break}" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{C_BODY}">{t}<hp:t/></hp:run></hp:p>')

def render_items(items):
    out = []
    for it in items:
        if not isinstance(it, dict):
            out.append(bullet(it)); continue
        if "글머리" in it:
            out.append(bullet(it["글머리"]))
        elif "하위" in it:
            out.append(subbullet(it["하위"]))
        elif "주석" in it:
            out.append(note(it["주석"]))
        elif "표" in it:
            out.append(table(it["표"]))
        elif "여백" in it:
            out.append(spacer())
        else:
            out.append(bullet(it))   # {라벨,내용} 형태
    return "".join(out)

# ----------------------------------------------------------------------------
# section0.xml 조립
# ----------------------------------------------------------------------------
def build_section(data):
    body = [cover(data)]
    first = True
    for i, sec in enumerate(data.get("섹션", []), start=1):
        body.append(section_header(sec.get("번호", i), sec["표제"],
                                   page_break=1 if first else 0, reset_page=first))
        first = False
        body.append(render_items(sec.get("항목", [])))
    for j, att in enumerate(data.get("붙임", []), start=1):
        body.append(attach_header(att.get("번호", j), att["제목"], page_break=1))
        body.append(render_items(att.get("항목", [])))
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<hs:sec {NS_SEC}>' + "".join(body) + '</hs:sec>')

# ----------------------------------------------------------------------------
# 패키지 보일러플레이트
# ----------------------------------------------------------------------------
def content_hpf(title, modified):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            '<opf:package xmlns:opf="http://www.idpf.org/2007/opf/" '
            'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" version="" unique-identifier="" id="">'
            '<opf:metadata><opf:title>' + escape(title) + '</opf:title>'
            '<opf:language>ko</opf:language>'
            '<opf:meta name="CreatedDate" content="' + modified + '"/>'
            '<opf:meta name="ModifiedDate" content="' + modified + '"/></opf:metadata>'
            '<opf:manifest>'
            '<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>'
            '<opf:item id="image1" href="BinData/image1.jpg" media-type="image/jpg" isEmbeded="1"/>'
            '<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>'
            '<opf:item id="headersc" href="Scripts/headerScripts.js" media-type="application/x-javascript ;charset=utf-16"/>'
            '<opf:item id="sourcesc" href="Scripts/sourceScripts.js" media-type="application/x-javascript ;charset=utf-16"/>'
            '<opf:item id="settings" href="settings.xml" media-type="application/xml"/>'
            '</opf:manifest>'
            '<opf:spine><opf:itemref idref="header" linear="yes"/>'
            '<opf:itemref idref="section0" linear="yes"/></opf:spine></opf:package>')

CONTAINER_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    '<ocf:container xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container" '
    'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf"><ocf:rootfiles>'
    '<ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>'
    '<ocf:rootfile full-path="Preview/PrvText.txt" media-type="text/plain"/>'
    '</ocf:rootfiles></ocf:container>')

CONTAINER_RDF = ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    '<rdf:Description rdf:about=""><ns0:hasPart xmlns:ns0="http://www.hancom.co.kr/hwpml/2016/meta/pkg#" '
    'rdf:resource="Contents/header.xml"/></rdf:Description>'
    '<rdf:Description rdf:about="Contents/header.xml"><rdf:type '
    'rdf:resource="http://www.hancom.co.kr/hwpml/2016/meta/pkg#HeaderFile"/></rdf:Description>'
    '<rdf:Description rdf:about=""><ns0:hasPart xmlns:ns0="http://www.hancom.co.kr/hwpml/2016/meta/pkg#" '
    'rdf:resource="Contents/section0.xml"/></rdf:Description>'
    '<rdf:Description rdf:about="Contents/section0.xml"><rdf:type '
    'rdf:resource="http://www.hancom.co.kr/hwpml/2016/meta/pkg#SectionFile"/></rdf:Description>'
    '<rdf:Description rdf:about=""><rdf:type '
    'rdf:resource="http://www.hancom.co.kr/hwpml/2016/meta/pkg#Document"/></rdf:Description></rdf:RDF>')

MANIFEST = ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    '<odf:manifest xmlns:odf="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"/>')

SETTINGS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    '<ha:HWPApplicationSetting xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" '
    'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0">'
    '<ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/></ha:HWPApplicationSetting>')

VERSION = ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    '<hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version" '
    'tagetApplication="WORDPROCESSOR" major="5" minor="1" micro="1" buildNumber="0" os="1" '
    'xmlVersion="1.5" application="Hancom Office Hangul" appVersion="12, 0, 0, 535 WIN32LEWindows_10"/>')

def preview_text(data):
    lines = [data.get("제목", "")]
    if data.get("날짜"):
        lines.append(data["날짜"])
    for sec in data.get("섹션", []):
        lines.append(f"{sec.get('번호','')} {sec.get('표제','')}")
    return "\n".join(lines)

# ----------------------------------------------------------------------------
# 빌드
# ----------------------------------------------------------------------------
def build(config_path, out_path=None):
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    meta = data.get("메타", {})
    if out_path is None:
        out_path = os.path.join(os.getcwd(), meta.get("출력_파일명", "report.hwpx"))
    modified = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    section = build_section(data)
    header = _asset("header.xml")

    files_text = {
        "version.xml": VERSION,
        "settings.xml": SETTINGS,
        "Contents/header.xml": header,
        "Contents/section0.xml": section,
        "Contents/content.hpf": content_hpf(data.get("제목", "보고서"), modified),
        "META-INF/container.xml": CONTAINER_XML,
        "META-INF/container.rdf": CONTAINER_RDF,
        "META-INF/manifest.xml": MANIFEST,
        "Scripts/headerScripts.js": _asset("headerScripts.js"),
        "Scripts/sourceScripts.js": _asset("sourceScripts.js"),
        "Preview/PrvText.txt": preview_text(data),
    }
    with open(os.path.join(ASSETS, "image1.jpg"), "rb") as f:
        image_bytes = f.read()

    with zipfile.ZipFile(out_path, "w") as z:
        zi = zipfile.ZipInfo("mimetype")
        zi.compress_type = zipfile.ZIP_STORED
        z.writestr(zi, "application/hwp+zip")
        z.writestr("BinData/image1.jpg", image_bytes, zipfile.ZIP_DEFLATED)
        for name, content in files_text.items():
            z.writestr(name, content.encode("utf-8"), zipfile.ZIP_DEFLATED)

    report = verify(out_path, header, section)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return out_path

def verify(out_path, header, section):
    """구조·참조 무결성 검증."""
    import xml.dom.minidom as minidom
    result = {"output": out_path, "section_bytes": len(section), "PASS": True, "문제": []}
    # 1) zip 무결성
    with zipfile.ZipFile(out_path) as z:
        bad = z.testzip()
        if bad:
            result["문제"].append(f"zip 손상: {bad}"); result["PASS"] = False
        names = z.namelist()
        if names[0] != "mimetype":
            result["문제"].append("mimetype 이 첫 엔트리가 아님"); result["PASS"] = False
    # 2) well-formed XML
    for label, xml in (("header", header), ("section", section)):
        try:
            minidom.parseString(xml.encode("utf-8"))
        except Exception as e:
            result["문제"].append(f"{label} XML 오류: {e}"); result["PASS"] = False
    # 3) 참조 무결성 : section 이 쓰는 ID 가 header 에 모두 정의되어 있는지
    def defined(prefix):
        return set(re.findall(prefix + r' id="(\d+)"', header))
    def used(attr):
        return set(re.findall(attr + r'="(\d+)"', section))
    checks = [
        ("charPr", r'<hh:charPr', "charPrIDRef"),
        ("paraPr", r'<hh:paraPr', "paraPrIDRef"),
        ("borderFill", r'<hh:borderFill', "borderFillIDRef"),
    ]
    for label, defpat, usepat in checks:
        d = defined(defpat)
        u = used(usepat)
        missing = sorted(int(x) for x in (u - d))
        if missing:
            result["문제"].append(f"{label} 미정의 참조: {missing}"); result["PASS"] = False
        result[f"{label}_정의수"] = len(d)
    # 4) 잔존 placeholder
    left = re.findall(r"\{\{[^}]+\}\}", section)
    if left:
        result["문제"].append(f"미치환 placeholder: {left}"); result["PASS"] = False
    return result

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", required=True)
    ap.add_argument("-o", "--output", default=None)
    a = ap.parse_args()
    build(a.config, a.output)
