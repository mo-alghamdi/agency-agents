#!/usr/bin/env python3
"""مختصر دور وكيل Frontend Developer — docs/frontend-developer-role.pdf"""
from __future__ import annotations

from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PDF = REPO_ROOT / "docs" / "frontend-developer-role.pdf"

FONT_PATHS = [
    Path(r"C:\Windows\Fonts\tahoma.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
]
FONT_NAME = "FDRoleFont"


def register_font() -> None:
    for p in FONT_PATHS:
        if p.is_file():
            pdfmetrics.registerFont(TTFont(FONT_NAME, str(p)))
            return
    raise FileNotFoundError("Tahoma or Arial not found.")


def shape_ar(text: str) -> str:
    if not text.strip():
        return text
    try:
        cfg = arabic_reshaper.config_for_arabic()
        r = arabic_reshaper.reshape(text, configuration=cfg)
    except AttributeError:
        r = arabic_reshaper.reshape(text)
    return get_display(r)


def p_ar(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(shape_ar(text).replace("\n", "<br/>"), style)


def main() -> None:
    register_font()
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "t",
        parent=styles["Heading1"],
        fontName=FONT_NAME,
        fontSize=18,
        leading=26,
        alignment=TA_CENTER,
    )
    h2 = ParagraphStyle(
        "h2",
        parent=styles["Heading2"],
        fontName=FONT_NAME,
        fontSize=13,
        leading=20,
        alignment=TA_RIGHT,
    )
    body = ParagraphStyle(
        "b",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=11,
        leading=18,
        alignment=TA_JUSTIFY,
    )

    story: list = []
    story.append(p_ar("وكيل مطوّر الواجهات الأمامية (Frontend Developer)", title))
    story.append(Spacer(1, 0.6 * cm))

    sections: list[tuple[str, str]] = [
        (
            "الهوية والدور",
            "خبير في بناء واجهات الويب الحديثة (React وVue وAngular وغيرها)، "
            "يركّز على التنفيذ الدقيق للتصميم، الأداء، وتجربة المستخدم. شخصيته: دقيق، "
            "موجّه للأداء، يضع المستخدم في المركز.",
        ),
        (
            "المهام الأساسية (مختصر)",
            "• بناء تطبيقات ويب متجاوبة وسريعة مع مكوّنات قابلة لإعادة الاستخدام وتكامل مع واجهات البرمجة الخلفية.\n"
            "• تحسين الأداء (مؤشرات الويب الأساسية، تقسيم الحزم، التحميل الكسول) وتجربة استخدام سلسة.\n"
            "• ضمان إمكانية الوصول (WCAG 2.1 AA) وهيكلة HTML دلالية وARIA حيث يلزم.\n"
            "• في سياق أدوات المحرر: دمج التوسعات، جسور WebSocket/RPC، وتجربة تنقّل سريعة بين التطبيق والمحرر.",
        ),
        (
            "قواعد يتبعها دائماً",
            "الأداء أولاً؛ إمكانية الوصول جزء افتراضي من العمل وليس إضافة لاحقة؛ "
            "اختبارات ووضوح في معالجة الأخطاء والتغذية الراجعة للمستخدم.",
        ),
        (
            "متى تستدعيه في Cursor؟",
            "عند تصميم أو تنفيذ واجهات، مراجعة أداء الواجهة، تحسين CSS/التخطيط، "
            "أو عندما تحتاج منطقاً واضحاً لمكوّنات الواجهة الأمامية مع معايير جودة حديثة.",
        ),
    ]

    for head, para in sections:
        story.append(p_ar(head, h2))
        story.append(Spacer(1, 0.15 * cm))
        story.append(p_ar(para, body))
        story.append(Spacer(1, 0.45 * cm))

    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    doc.build(story)
    print(f"Wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
