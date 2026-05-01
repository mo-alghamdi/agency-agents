#!/usr/bin/env python3
"""
توليد docs/agency-agents-roster.pdf — جدول الوكلاء بالعربية، مع إيموجي ووصف مترجم.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PDF = REPO_ROOT / "docs" / "agency-agents-roster.pdf"
CACHE_PATH = REPO_ROOT / "docs" / ".roster_ar_cache.json"

# خطوط ويندوز (عربي + لاتيني)
FONT_PATHS = [
    Path(r"C:\Windows\Fonts\tahoma.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
]
FONT_NAME = "AgencyRoster"

AGENT_DIRS = [
    "academic",
    "design",
    "engineering",
    "finance",
    "game-development",
    "marketing",
    "paid-media",
    "product",
    "project-management",
    "sales",
    "spatial-computing",
    "specialized",
    "strategy",
    "support",
    "testing",
]

DIVISION_AR: dict[str, str] = {
    "academic": "القسم الأكاديمي",
    "design": "قسم التصميم",
    "engineering": "قسم الهندسة البرمجية",
    "finance": "قسم المالية",
    "game-development": "قسم تطوير الألعاب",
    "marketing": "قسم التسويق",
    "paid-media": "قسم الإعلانات المدفوعة",
    "product": "قسم المنتج",
    "project-management": "قسم إدارة المشاريع",
    "sales": "قسم المبيعات",
    "spatial-computing": "قسم الحوسبة المكانية",
    "specialized": "القسم المتخصص",
    "strategy": "قسم الاستراتيجية",
    "support": "قسم الدعم والتشغيل",
    "testing": "قسم الاختبار والجودة",
}

FRONTMATTER_BLOCK = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)
CORE_MISSION = re.compile(
    r"^##[^\n]*Core Mission[^\n]*\n(?P<block>.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)


def register_font() -> None:
    for p in FONT_PATHS:
        if p.is_file():
            pdfmetrics.registerFont(TTFont(FONT_NAME, str(p)))
            return
    raise FileNotFoundError("لم يُعثر على خط Tahoma أو Arial في النظام.")


def parse_frontmatter(path: Path) -> dict[str, str] | None:
    raw = path.read_text(encoding="utf-8")
    m = FRONTMATTER_BLOCK.match(raw)
    if not m:
        return None
    block = m.group(1)
    data: dict[str, str] = {}
    key: str | None = None
    buf: list[str] = []
    for line in block.splitlines():
        if re.match(r"^[a-zA-Z0-9_-]+:\s*", line):
            if key is not None:
                data[key] = " ".join(buf).strip()
            key, _, rest = line.partition(":")
            key = key.strip()
            buf = [rest.strip()] if rest.strip() else []
        elif key is not None and line.startswith((" ", "\t")):
            buf.append(line.strip())
        elif key is not None:
            data[key] = " ".join(buf).strip()
            key = None
            buf = []
    if key is not None:
        data[key] = " ".join(buf).strip()
    return data


def body_after_fm(raw: str) -> str:
    m = FRONTMATTER_BLOCK.match(raw)
    if not m:
        return ""
    return raw[m.end() :].lstrip()


def mission_bullets(body: str, max_bullets: int = 2) -> list[str]:
    m = CORE_MISSION.search(body)
    if not m:
        return []
    block = m.group("block")
    out: list[str] = []
    for line in block.splitlines():
        t = line.strip()
        if not t or t.startswith("###"):
            continue
        if t.startswith("#"):
            break
        if t[:1] in "-*•" or re.match(r"^\d+\.", t):
            t = re.sub(r"^[-*•]\s*", "", t)
            t = re.sub(r"^\d+\.\s*", "", t).strip()
            if t:
                out.append(t)
        if len(out) >= max_bullets:
            break
    return out


def collect_agents() -> dict[str, list[dict[str, str]]]:
    by_div: dict[str, list[dict[str, str]]] = defaultdict(list)
    for cat in AGENT_DIRS:
        root = REPO_ROOT / cat
        if not root.is_dir():
            continue
        for md in root.rglob("*.md"):
            raw = md.read_text(encoding="utf-8")
            fm = parse_frontmatter(md)
            if not fm:
                continue
            name = (fm.get("name") or "").strip()
            desc = (fm.get("description") or "").strip()
            emoji = (fm.get("emoji") or "").strip()
            if not name:
                continue
            body = body_after_fm(raw)
            extra = mission_bullets(body)
            combined = desc
            if len(desc.split()) < 22 and extra:
                combined = desc + " — " + " ".join(extra[:2])
            by_div[cat].append(
                {
                    "name": name,
                    "desc_en": desc or "—",
                    "combined_en": combined or desc,
                    "emoji": emoji,
                }
            )
    for cat in by_div:
        by_div[cat].sort(key=lambda x: x["name"].lower())
    return dict(by_div)


def load_cache() -> dict[str, str]:
    if CACHE_PATH.is_file():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(c: dict[str, str]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(c, ensure_ascii=False, indent=0), encoding="utf-8")


def cache_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def translate_batch(strings: list[str], cache: dict[str, str]) -> dict[str, str]:
    """ترجمة إلى العربية مع التخزين المؤقت (المفتاح SHA للنص الإنجليزي)."""
    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        return {s: s for s in strings}

    tr = GoogleTranslator(source="auto", target="ar")
    resolved: dict[str, str] = {}
    pending: list[str] = []
    for s in strings:
        ck = cache_key(s)
        if ck in cache:
            resolved[s] = cache[ck]
        else:
            pending.append(s)

    for i, s in enumerate(pending):
        ck = cache_key(s)
        try:
            ar = tr.translate(s)
            cache[ck] = ar
            resolved[s] = ar
            if (i + 1) % 25 == 0:
                save_cache(cache)
            time.sleep(0.15)
        except Exception:
            cache[ck] = s
            resolved[s] = s
    save_cache(cache)
    return resolved


def shape_ar(text: str) -> str:
    if not text.strip():
        return text
    cfg = arabic_reshaper.config_for_arabic()
    r = arabic_reshaper.reshape(text, configuration=cfg)
    return get_display(r)


def esc_xml(s: str) -> str:
    return escape(s)


def para_ar(raw: str) -> str:
    """تهريب XML ثم إعادة تشكيل عربي للعرض."""
    return shape_ar(escape(raw))


def build_pdf(by_div: dict[str, list[dict[str, str]]], ar_map: dict[str, str]) -> None:
    register_font()
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ArTitle",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=20,
        leading=26,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=8,
    )
    sub_style = ParagraphStyle(
        "ArSub",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )
    div_style = ParagraphStyle(
        "ArDiv",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=13,
        leading=18,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#e2e8f0"),
        borderPadding=(8, 10, 8, 10),
        spaceBefore=12,
        spaceAfter=10,
    )
    name_style = ParagraphStyle(
        "ArName",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=11,
        leading=16,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=2,
    )
    body_style = ParagraphStyle(
        "ArBody",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=9,
        leading=13,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6,
    )

    story: list = []
    story.append(Paragraph(para_ar("🎭 الوكالة — دليل الوكلاء"), title_style))
    story.append(
        Paragraph(
            para_ar(
                f"agency-agents · التاريخ: {date.today().isoformat()} · الحقول name و description و emoji من YAML"
            ),
            sub_style,
        )
    )
    story.append(
        Paragraph(
            para_ar(
                "التخطيط: أقسام حسب مجلدات المستودع (متوافق مع README). "
                "كل إدخال: الإيموجي والاسم الرسمي، ثم ملخص المهام بالعربية من الحقل description "
                "ومقتطف اختياري من «Core Mission» عندما يكون الوصف قصيراً."
            ),
            sub_style,
        )
    )
    story.append(Spacer(1, 0.25 * cm))

    order = [d for d in AGENT_DIRS if d in by_div]
    first = True
    for div_key in order:
        agents = by_div[div_key]
        if not agents:
            continue
        div_ar = DIVISION_AR.get(div_key, div_key)
        if not first:
            story.append(PageBreak())
        first = False
        story.append(Paragraph(para_ar(div_ar), div_style))
        story.append(Spacer(1, 0.12 * cm))
        for ag in agents:
            comb = ag["combined_en"]
            ar_text = ar_map.get(comb) or ar_map.get(ag["desc_en"]) or ag["desc_en"]
            em = ag["emoji"] or "🤖"
            name_line = f"{em}  <b>{esc_xml(ag['name'])}</b>"
            story.append(Paragraph(name_line, name_style))
            story.append(Paragraph(para_ar(ar_text), body_style))

    def on_page(canv, doc):
        canv.saveState()
        canv.setStrokeColor(colors.HexColor("#cbd5e1"))
        canv.setLineWidth(0.5)
        canv.line(2 * cm, 1.4 * cm, A4[0] - 2 * cm, 1.4 * cm)
        canv.setFont(FONT_NAME, 8)
        canv.setFillColor(colors.HexColor("#64748b"))
        canv.drawRightString(A4[0] - 2 * cm, 1 * cm, para_ar("الوكالة · agency-agents"))
        canv.drawString(2 * cm, 1 * cm, str(canv.getPageNumber()))
        canv.restoreState()

    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.2 * cm,
        title="agency-agents roster",
        author="agency-agents",
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


def main() -> None:
    by_div = collect_agents()
    total = sum(len(v) for v in by_div.values())
    cache = load_cache()
    # جمع كل النصوص المراد ترجمتها (فريدة)
    need: set[str] = set()
    for agents in by_div.values():
        for ag in agents:
            need.add(ag["combined_en"])
    ar_map = translate_batch(sorted(need), cache)
    build_pdf(by_div, ar_map)
    print(f"تم إنشاء {OUT_PDF} — {total} وكيلاً، {len(by_div)} قسماً")


if __name__ == "__main__":
    main()
