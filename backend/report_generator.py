"""
Report Generator - CSV and PDF export for P&L reports
"""
import csv
import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_csv_report(positions, summary):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Moon Hunters - Trading Report"])
    writer.writerow([f"Period: {summary.get('period', 'all')}"])
    writer.writerow([f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"])
    writer.writerow([])

    writer.writerow(["Summary"])
    writer.writerow(["Total Trades", summary.get("total_trades", 0)])
    writer.writerow(["Winning Trades", summary.get("winning_trades", 0)])
    writer.writerow(["Losing Trades", summary.get("losing_trades", 0)])
    writer.writerow(["Win Rate", f"{summary.get('win_rate', 0)}%"])
    writer.writerow(["Total Realized P&L", f"${summary.get('total_realized_pnl', 0):.2f}"])
    writer.writerow(["Avg Hold Time (hours)", summary.get("avg_hold_hours", 0)])
    writer.writerow([])

    writer.writerow([
        "Date", "Symbol", "Status", "Entry Price", "Exit Price",
        "Quantity", "Invested (USDT)", "P&L (USDT)", "Fee (USDT)",
        "Chain ID", "TX Hash"
    ])

    for pos in positions:
        entry_date = pos.get("entry_date", "")
        if isinstance(entry_date, str) and len(entry_date) > 10:
            entry_date = entry_date[:10]

        writer.writerow([
            entry_date,
            pos.get("symbol", ""),
            pos.get("status", ""),
            f"{pos.get('entry_price', 0):.6f}",
            f"{pos.get('exit_price', 0):.6f}" if pos.get("exit_price") else "",
            f"{pos.get('quantity', 0):.6f}",
            f"{pos.get('invested_usdt', 0):.2f}",
            f"{pos.get('realized_pnl', 0):.2f}" if pos.get("realized_pnl") is not None else "",
            f"{pos.get('fee_amount', 0):.2f}",
            pos.get("chain_id", ""),
            pos.get("tx_hash", "")
        ])

    output.seek(0)
    return io.BytesIO(output.getvalue().encode("utf-8"))


def generate_pdf_report(positions, summary):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "MHTitle", parent=styles["Title"],
            fontSize=20, textColor=colors.HexColor("#FFD700"),
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            "MHSubtitle", parent=styles["Normal"],
            fontSize=10, textColor=colors.grey,
            spaceAfter=12
        )
        header_style = ParagraphStyle(
            "MHHeader", parent=styles["Heading2"],
            fontSize=14, textColor=colors.HexColor("#FFD700"),
            spaceBefore=12, spaceAfter=6
        )

        elements = []

        elements.append(Paragraph("Moon Hunters Trading Report", title_style))
        elements.append(Paragraph(
            f"Period: {summary.get('period', 'all').title()} | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            subtitle_style
        ))

        elements.append(Paragraph("Performance Summary", header_style))
        summary_data = [
            ["Total Trades", str(summary.get("total_trades", 0)),
             "Win Rate", f"{summary.get('win_rate', 0)}%"],
            ["Winning", str(summary.get("winning_trades", 0)),
             "Losing", str(summary.get("losing_trades", 0))],
            ["Total P&L", f"${summary.get('total_realized_pnl', 0):.2f}",
             "Avg Hold", f"{summary.get('avg_hold_hours', 0):.1f}h"],
        ]

        summary_table = Table(summary_data, colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#333")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 12))

        elements.append(Paragraph("Trade Details", header_style))

        trade_data = [["Date", "Symbol", "Status", "Entry", "Exit", "Qty", "P&L"]]
        for pos in positions[:100]:
            entry_date = pos.get("entry_date", "")
            if isinstance(entry_date, str) and len(entry_date) > 10:
                entry_date = entry_date[:10]

            pnl = pos.get("realized_pnl")
            pnl_str = f"${pnl:.2f}" if pnl is not None else "-"

            trade_data.append([
                entry_date[:10] if entry_date else "",
                pos.get("symbol", ""),
                pos.get("status", ""),
                f"${pos.get('entry_price', 0):.4f}",
                f"${pos.get('exit_price', 0):.4f}" if pos.get("exit_price") else "-",
                f"{pos.get('quantity', 0):.4f}",
                pnl_str
            ])

        trade_table = Table(trade_data, colWidths=[0.9 * inch, 0.7 * inch, 0.7 * inch, 0.9 * inch, 0.9 * inch, 0.8 * inch, 0.8 * inch])
        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFD700")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#0d0d1a")),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#333")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ]

        for i, pos in enumerate(positions[:100], 1):
            pnl = pos.get("realized_pnl", 0)
            if pnl and pnl > 0:
                style_commands.append(("TEXTCOLOR", (6, i), (6, i), colors.HexColor("#00FF88")))
            elif pnl and pnl < 0:
                style_commands.append(("TEXTCOLOR", (6, i), (6, i), colors.HexColor("#FF4444")))

        trade_table.setStyle(TableStyle(style_commands))
        elements.append(trade_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer

    except ImportError:
        logger.warning("reportlab not installed, falling back to CSV")
        return generate_csv_report(positions, summary)
