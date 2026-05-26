"""Minimal PDF report for mock sessions (no external deps)."""

from __future__ import annotations

import json
from io import BytesIO


def _pdf_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_mock_report_pdf(session: dict) -> bytes:
    """Build a single-page PDF with session summary."""
    report = session.get("report") or {}
    scores = report.get("scores") or session.get("scores") or {}
    lines = [
        "Agent Knowledge Hub - Mock Interview Report",
        f"Session: {session.get('id', '')[:8]}",
        f"Vendor: {session.get('vendor', '')}  Mode: {session.get('mode', '')}",
        "",
        "Scores:",
    ]
    for k, v in scores.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("Highlights:")
    for h in report.get("highlights", [])[:5]:
        lines.append(f"  - {h}")
    lines.append("")
    lines.append("Gaps:")
    for g in report.get("gaps", [])[:5]:
        lines.append(f"  - {g}")
    if report.get("answer_rewrite"):
        lines.append("")
        lines.append("Rewrite suggestion:")
        lines.append(str(report["answer_rewrite"])[:500])

    text = "\n".join(lines)[:3500]
    content_stream = "BT\n/F1 11 Tf\n50 750 Td\n"
    y = 0
    for line in text.split("\n"):
        safe = _pdf_escape(line[:90])
        content_stream += f"0 -14 Td\n({safe}) Tj\n"
        y += 14
        if y > 700:
            break
    content_stream += "ET"
    stream_bytes = content_stream.encode("latin-1", errors="replace")

    objects = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream_bytes)} >>stream\n".encode()
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    buf = BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(buf.tell())
        buf.write(obj)
    xref_start = buf.tell()
    buf.write(f"xref\n0 {len(offsets)}\n".encode())
    buf.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.write(f"{off:010d} 00000 n \n".encode())
    buf.write(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode()
    )
    return buf.getvalue()
