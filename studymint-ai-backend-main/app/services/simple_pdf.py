from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.services.template_ids import is_blue_certification_template, is_main_template

A4_WIDTH = 595.28
A4_HEIGHT = 841.89


@dataclass(frozen=True)
class PdfStyle:
    font: str
    size: float
    line_height: float
    color: tuple[float, float, float]
    bold: bool = False
    underline: bool = False


BLACK = (0.0588, 0.0667, 0.0824)
RED = (0.7529, 0.0941, 0.0941)
BLUE = (0.0431, 0.4, 0.5098)
GRAY = (0.4, 0.4, 0.4)
RULE_GRAY = (0.64, 0.64, 0.64)
BORDER_RED = (0.9333, 0.0, 0.0)

BODY_STYLE = PdfStyle("F1", 11.2, 16.2, BLACK)
BODY_BOLD_STYLE = PdfStyle("F2", 11.2, 16.2, BLACK, bold=True)
SMALL_STYLE = PdfStyle("F1", 9.4, 13.4, GRAY)
HEADING_STYLE = PdfStyle("F2", 14.0, 19.0, BLACK, bold=True)
TITLE_STYLE = PdfStyle("F2", 17.0, 24.0, BLACK, bold=True)
QUESTION_STYLE = PdfStyle("F2", 12.2, 17.0, BLACK, bold=True)
ANSWER_LABEL_STYLE = PdfStyle("F2", 11.2, 16.2, RED, bold=True)
RATIONALE_LABEL_STYLE = PdfStyle("F2", 11.2, 16.2, BLUE, bold=True)
BLUE_TITLE_STYLE = PdfStyle("F2", 14.0, 19.0, BLUE, bold=True, underline=True)
BLUE_HEADING_STYLE = PdfStyle("F2", 10.6, 15.0, BLUE, bold=True, underline=True)
BLUE_QUESTION_STYLE = PdfStyle("F2", 12.2, 17.0, BLUE, bold=True, underline=False)
BLUE_OVERVIEW_STYLE = PdfStyle("F2", 12.4, 18.0, BLUE, bold=True, underline=True)
OVERVIEW_STYLE = PdfStyle("F2", 12.4, 18.0, BLACK, bold=True, underline=True)


PUNCTUATION_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }
)


class SimplePdf:
    def __init__(self, border_style: str | None = None) -> None:
        self.pages: list[list[str]] = []
        self.current: list[str] = []
        self.border_style = border_style or ""
        self.draw_page_border = bool(border_style)
        self.top = 60.0
        self.left = 62.0
        self.right = 62.0
        self.bottom = 64.0

        if self.border_style == "blue_double":
            self.top = 62.0
            self.left = 68.0
            self.right = 68.0

        self.y = A4_HEIGHT - self.top
        self.content_width = A4_WIDTH - self.left - self.right
        self.add_page()

    def add_page(self) -> None:
        if self.current:
            self.pages.append(self.current)
        self.current = []
        if self.draw_page_border:
            self.current.extend(self.page_border_commands())
        self.y = A4_HEIGHT - self.top

    @property
    def page_count(self) -> int:
        return len(self.pages) + (1 if self.current else 0)

    def page_border_commands(self) -> list[str]:
        if self.border_style == "blue_double":
            outer_inset = 28.0
            inner_inset = 31.8
            return [
                "0 0 0 RG",
                f"2.3 w {outer_inset:.2f} {outer_inset:.2f} {A4_WIDTH - outer_inset * 2:.2f} {A4_HEIGHT - outer_inset * 2:.2f} re S",
                f"0.9 w {inner_inset:.2f} {inner_inset:.2f} {A4_WIDTH - inner_inset * 2:.2f} {A4_HEIGHT - inner_inset * 2:.2f} re S",
            ]

        inset = 3.0
        r, g, b = BORDER_RED
        return [
            f"{r:.4f} {g:.4f} {b:.4f} RG",
            f"3.3 w {inset:.2f} {inset:.2f} {A4_WIDTH - inset * 2:.2f} {A4_HEIGHT - inset * 2:.2f} re S",
        ]

    def normalize(self, text: str) -> str:
        return str(text or "").translate(PUNCTUATION_TRANSLATION).replace("\r", " ").replace("\t", " ")

    def ensure_space(self, required: float) -> None:
        if self.y - required < self.bottom:
            self.add_page()

    def text_width(self, text: str, style: PdfStyle) -> float:
        width = 0.0
        for char in self.normalize(text):
            if char == " ":
                width += 0.26
            elif char in ".,;:!|'":
                width += 0.22
            elif char in "MW@#%&":
                width += 0.82
            elif char.isupper():
                width += 0.63
            elif char.isdigit():
                width += 0.5
            else:
                width += 0.48
        if style.bold:
            width *= 1.03
        return width * style.size

    def wrap(self, text: str, style: PdfStyle, width: float | None = None) -> list[str]:
        available = width or self.content_width
        words = self.normalize(text).split()

        if not words:
            return [""]

        lines: list[str] = []
        current = words[0]

        for word in words[1:]:
            candidate = f"{current} {word}"
            if self.text_width(candidate, style) <= available:
                current = candidate
            else:
                lines.append(current)
                current = word

        lines.append(current)
        return lines

    def draw_text(self, x: float, y: float, text: str, style: PdfStyle) -> None:
        r, g, b = style.color
        escaped = (
            self.normalize(text)
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .replace("\n", " ")
        )
        self.current.append(f"{r:.4f} {g:.4f} {b:.4f} rg")
        self.current.append(f"BT /{style.font} {style.size:g} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ({escaped}) Tj ET")
        if style.underline:
            underline_y = y - 3.0
            width = self.text_width(text, style)
            self.current.append(f"{r:.4f} {g:.4f} {b:.4f} RG")
            self.current.append(f"0.8 w {x:.2f} {underline_y:.2f} m {x + width:.2f} {underline_y:.2f} l S")

    def paragraph(self, text: str, style: PdfStyle = BODY_STYLE, after: float = 7, before: float = 0) -> None:
        normalized = self.normalize(text)

        if not normalized.strip():
            self.y -= style.line_height * 0.5
            return

        if before:
            self.y -= before

        for raw_line in normalized.splitlines():
            for line in self.wrap(raw_line, style):
                self.ensure_space(style.line_height)
                self.draw_text(self.left, self.y, line, style)
                self.y -= style.line_height

        self.y -= after

    def centered_paragraph(self, text: str, style: PdfStyle, after: float = 18) -> None:
        for raw_line in self.normalize(text).splitlines():
            for line in self.wrap(raw_line, style):
                self.ensure_space(style.line_height)
                width = self.text_width(line, style)
                x = self.left + max((self.content_width - width) / 2, 0)
                self.draw_text(x, self.y, line, style)
                self.y -= style.line_height
        self.y -= after

    def horizontal_rule(self, before: float = 8, after: float = 10) -> None:
        if before:
            self.y -= before
        self.ensure_space(5)
        r, g, b = RULE_GRAY
        self.current.append(f"{r:.4f} {g:.4f} {b:.4f} RG")
        self.current.append(f"0.45 w {self.left:.2f} {self.y:.2f} m {self.left + self.content_width:.2f} {self.y:.2f} l S")
        self.y -= after

    def labeled_paragraph(self, label: str, body: str, label_style: PdfStyle, body_style: PdfStyle, after: float = 6) -> None:
        first_line = f"{label} {self.normalize(body).strip()}".strip()
        lines = self.wrap(first_line, body_style)

        for index, line in enumerate(lines):
            self.ensure_space(body_style.line_height)
            if index == 0 and line.startswith(label):
                self.draw_text(self.left, self.y, label, label_style)
                label_width = self.text_width(label + " ", label_style)
                remainder = line[len(label) :].strip()
                if remainder:
                    self.draw_text(self.left + label_width, self.y, remainder, body_style)
            else:
                self.draw_text(self.left, self.y, line, body_style)
            self.y -= body_style.line_height

        self.y -= after

    def add_page_numbers(self) -> None:
        total = len(self.pages)

        for index, page in enumerate(self.pages, start=1):
            text = f"Page {index} of {total}"
            width = self.text_width(text, SMALL_STYLE)
            x = self.left + max((self.content_width - width) / 2, 0)
            r, g, b = SMALL_STYLE.color
            page.append(f"{r:.4f} {g:.4f} {b:.4f} rg")
            page.append(f"BT /{SMALL_STYLE.font} {SMALL_STYLE.size:g} Tf 1 0 0 1 {x:.2f} 34.00 Tm ({text}) Tj ET")

    def render(self) -> bytes:
        if self.current:
            self.pages.append(self.current)
            self.current = []

        self.add_page_numbers()

        objects: list[bytes] = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objects.append(b"")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold >>")

        page_object_ids: list[int] = []
        for page_commands in self.pages:
            content = "\n".join(page_commands).encode("latin-1", "replace")
            stream = b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream"
            content_id = len(objects) + 1
            objects.append(stream)
            page_id = len(objects) + 1
            page_object_ids.append(page_id)
            page = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {A4_WIDTH:.2f} {A4_HEIGHT:.2f}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>"
            )
            objects.append(page.encode())

        kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
        objects[1] = f"<< /Type /Pages /Count {len(page_object_ids)} /Kids [{kids}] >>".encode()

        pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]

        for index, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{index} 0 obj\n".encode())
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")

        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode())
        pdf.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
        )
        return bytes(pdf)


def _iter_section_lines(section: dict[str, str]) -> Iterable[str]:
    body = section.get("body", "")
    for line in str(body).splitlines():
        cleaned = line.strip()
        if cleaned:
            yield cleaned


def _question_number_from_line(line: str) -> int | None:
    match = re.match(r"(?i)^Question\s+(\d+)\s*:", line.strip())
    if not match:
        return None
    return int(match.group(1))


def _draw_line_by_role(pdf: SimplePdf, line: str, *, compact: bool = False) -> None:
    if re.match(r"(?i)^Question\s+\d+\s*:", line):
        pdf.paragraph(line, QUESTION_STYLE if not compact else BLUE_QUESTION_STYLE, after=6, before=6)
    elif line.startswith("Answer:"):
        pdf.labeled_paragraph("Answer:", line[len("Answer:") :].strip(), ANSWER_LABEL_STYLE, BODY_STYLE, after=5)
    elif line.startswith("Rationale:"):
        pdf.labeled_paragraph("Rationale:", line[len("Rationale:") :].strip(), RATIONALE_LABEL_STYLE, BODY_STYLE, after=8)
    elif re.match(r"^[A-D][\.)]\s+", line):
        pdf.paragraph(line, BODY_STYLE, after=2)
    else:
        pdf.paragraph(line, BODY_STYLE, after=4)


def _draw_question_item(pdf: SimplePdf, question: dict, *, compact: bool = False) -> None:
    number = int(question.get("number") or 0)
    heading = f"Question {number}: {question.get('stem', '')}".strip()
    option_count = len(question.get("options") or [])
    estimated_height = 44 + (option_count * BODY_STYLE.line_height) + 70
    pdf.ensure_space(min(estimated_height, 260))
    _draw_line_by_role(pdf, heading, compact=compact)

    for option in question.get("options") or []:
        label = str(option.get("label") or "").strip()
        text = str(option.get("text") or "").strip()
        if label and text:
            pdf.paragraph(f"{label}. {text}", BODY_STYLE, after=2)

    correct_option = str(question.get("correct_option") or "").strip()
    selected_text = ""
    for option in question.get("options") or []:
        if option.get("label") == correct_option:
            selected_text = str(option.get("text") or "").strip()
            break

    answer_text = f"{correct_option}. {selected_text}".strip(". ")
    pdf.labeled_paragraph("Answer:", answer_text, ANSWER_LABEL_STYLE, BODY_STYLE, after=5)
    pdf.labeled_paragraph("Rationale:", str(question.get("rationale") or ""), RATIONALE_LABEL_STYLE, BODY_STYLE, after=10)


def _draw_question_bank(pdf: SimplePdf, content: dict, *, compact: bool = False) -> None:
    questions = [question for question in content.get("question_bank", []) if isinstance(question, dict)]

    for question in questions:
        _draw_question_item(pdf, question, compact=compact)


def _draw_sections(pdf: SimplePdf, content: dict, *, hesi_style: bool = False, compact: bool = False) -> None:
    for section_index, section in enumerate(content.get("sections", []), start=1):
        title = str(section.get("title") or "").strip()
        lines = list(_iter_section_lines(section))

        if title and not hesi_style:
            pdf.paragraph(title, HEADING_STYLE, after=4, before=10)
        elif title and compact and not any(_question_number_from_line(line) for line in lines):
            pdf.paragraph(f"SECTION {section_index}: {title.upper()}", BLUE_HEADING_STYLE, after=6, before=10)

        for line in lines:
            _draw_line_by_role(pdf, line, compact=compact)


def _draw_content(pdf: SimplePdf, content: dict, template_id: str | None) -> None:
    title_page = str(content.get("title_page") or "StudyMint AI Document").strip()
    compact = is_blue_certification_template(template_id)
    hesi_style = is_main_template(template_id)

    if compact:
        pdf.centered_paragraph(title_page.upper(), BLUE_TITLE_STYLE, after=34)
    elif hesi_style:
        pdf.centered_paragraph(title_page.upper(), PdfStyle("F2", 20, 27, RED, bold=True, underline=True), after=34)
    else:
        pdf.centered_paragraph(title_page, TITLE_STYLE, after=22)

    if content.get("question_bank"):
        introduction = str(content.get("introduction") or "").strip()
        if not introduction:
            introduction = (
                "A concise exam question bank for fast review with focused practice, "
                "clear answers, and rationale sections."
            )
        pdf.paragraph(
            "EXAM OVERVIEW",
            BLUE_OVERVIEW_STYLE if compact else OVERVIEW_STYLE,
            after=6,
        )
        pdf.paragraph(introduction, BODY_STYLE, after=12)
        _draw_question_bank(pdf, content, compact=compact)
        return

    introduction = str(content.get("introduction") or "").strip()

    if introduction and not hesi_style:
        pdf.paragraph("About This Resource", HEADING_STYLE, after=6)
        pdf.paragraph(introduction, BODY_STYLE, after=12)

    _draw_sections(pdf, content, hesi_style=hesi_style, compact=compact)

    if content.get("key_points") and not hesi_style:
        pdf.paragraph("Key Points", HEADING_STYLE, after=6, before=10)
        for item in content["key_points"]:
            pdf.paragraph(str(item), BODY_STYLE, after=3)

    if content.get("examples") and not hesi_style:
        pdf.paragraph("Examples", HEADING_STYLE, after=6, before=10)
        for item in content["examples"]:
            pdf.paragraph(str(item), BODY_STYLE, after=3)

    if content.get("study_questions") and not hesi_style:
        pdf.paragraph("Study Questions", HEADING_STYLE, after=6, before=10)
        for question in content["study_questions"]:
            pdf.paragraph(str(question), BODY_STYLE, after=3)

    if content.get("conclusion") and not hesi_style:
        pdf.paragraph("Conclusion", HEADING_STYLE, after=6, before=10)
        pdf.paragraph(str(content["conclusion"]), BODY_STYLE, after=0)


def render_study_document_pdf(content: dict, template_id: str | None, output_path: Path) -> None:
    border_style = "blue_double" if is_blue_certification_template(template_id) else ("red" if is_main_template(template_id) else "")
    pdf = SimplePdf(border_style=border_style)
    _draw_content(pdf, content, template_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf.render())
