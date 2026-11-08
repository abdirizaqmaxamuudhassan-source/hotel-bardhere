"""PDF generation with ReportLab (invoices, receipts, analytics reports)."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#0B1F3A")
GOLD = colors.HexColor("#C9A24B")
LIGHT = colors.HexColor("#F3F4F6")

_base = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_base["Title"], textColor=NAVY, fontSize=20, alignment=0, spaceAfter=2)
H2 = ParagraphStyle("H2", parent=_base["Heading2"], textColor=NAVY, fontSize=13, spaceBefore=12, spaceAfter=4)
BODY = ParagraphStyle("Body", parent=_base["BodyText"], fontSize=10, leading=14)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8.5, textColor=colors.HexColor("#555555"))


def P(text, style=BODY):
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def money(site, value):
    return f"{site.currency_symbol}{float(value or 0):,.2f}"


def _table(rows, col_widths=None, header=True, align_right_from=None):
    table = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    if align_right_from is not None:
        style.append(("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"))
    table.setStyle(TableStyle(style))
    return table


def _build(story, title):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title=title)

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.2)
        canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, f"Page {_doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def _header(site, doc_title, number):
    left = [P(site.hotel_name, H1), P(site.address_en, SMALL), P(f"{site.phone}  |  {site.email}", SMALL)]
    right = [P(doc_title, ParagraphStyle("R", parent=H1, alignment=2, textColor=GOLD)),
             P(number, ParagraphStyle("R2", parent=BODY, alignment=2))]
    t = Table([[left, right]], colWidths=[100 * mm, 74 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 1.5, NAVY),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


def invoice_pdf(booking, site):
    c = booking.customer
    story = [_header(site, "INVOICE", f"INV-{booking.reference}"), Spacer(1, 8)]
    story.append(_table([
        [P("Billed to"), P("Stay details")],
        [P(f"{c.full_name}\n{c.phone}\n{c.email}"),
         P(f"Booking: {booking.reference}\nRoom: {booking.room.number} ({booking.room.room_type.name_en})\n"
           f"Check-in: {booking.check_in:%d %b %Y}\nCheck-out: {booking.check_out:%d %b %Y}\nGuests: {booking.guests}")],
    ], col_widths=[87 * mm, 87 * mm]))
    story += [Spacer(1, 10), _table([
        ["Description", "Nights", "Rate", "Amount"],
        [f"{booking.room.room_type.name_en} – Room {booking.room.number}", booking.nights,
         money(site, booking.price_per_night), money(site, booking.total_price)],
    ], col_widths=[84 * mm, 20 * mm, 32 * mm, 38 * mm], align_right_from=1)]
    rows = [["Payments received", "Method", "Reference", "Amount"]]
    for p in booking.payments.filter(status="completed").order_by("paid_at"):
        rows.append([f"{p.receipt_number} – {p.paid_at:%d %b %Y}", p.get_method_display(),
                     p.transaction_reference or "-", money(site, p.amount)])
    if len(rows) > 1:
        story += [Spacer(1, 10), _table(rows, col_widths=[70 * mm, 32 * mm, 34 * mm, 38 * mm], align_right_from=3)]
    story += [Spacer(1, 10), _table([
        ["Total", money(site, booking.total_price)],
        ["Paid", money(site, booking.amount_paid)],
        ["Balance due", money(site, booking.balance_due)],
    ], col_widths=[136 * mm, 38 * mm], header=False, align_right_from=1)]
    if site.invoice_note:
        story += [Spacer(1, 14), P(site.invoice_note, SMALL)]
    return _build(story, f"Invoice {booking.reference}")


def receipt_pdf(payment, site):
    b = payment.booking
    story = [_header(site, "RECEIPT", payment.receipt_number), Spacer(1, 8)]
    story.append(_table([
        ["Received from", b.customer.full_name],
        ["Booking", f"{b.reference} – Room {b.room.number}"],
        ["Date", f"{payment.paid_at:%d %b %Y}"],
        ["Method", payment.get_method_display()],
        ["Transaction reference", payment.transaction_reference or "-"],
        ["Payer phone", payment.payer_phone or "-"],
        ["Status", payment.get_status_display()],
        ["Amount", money(site, payment.amount)],
        ["Booking balance after this payment", money(site, b.balance_due)],
    ], col_widths=[70 * mm, 104 * mm], header=False))
    story += [Spacer(1, 10), P("Mobile money references are recorded by staff from the customer's payment message "
                               "and are not verified automatically by this system.", SMALL)]
    if payment.received_by:
        story.append(P(f"Received by: {payment.received_by.get_full_name() or payment.received_by.username}", SMALL))
    return _build(story, f"Receipt {payment.receipt_number}")


def report_pdf(report, period, site):
    story = [_header(site, "REPORT", f"Generated {report['today']:%d %b %Y}"), Spacer(1, 6)]
    story.append(P("Summary", H2))
    c = report["customers"]
    story.append(_table([
        ["Measure", "Value"],
        ["Total revenue (completed payments)", money(site, report["revenue_total"])],
        ["Revenue, last 30 days", money(site, report["revenue_30d"])],
        ["Total bookings", report["total_bookings"]],
        ["Occupancy, last 30 days", f"{report['occupancy_overall']}%"],
        ["Customers (total / new in 30 days / repeat)", f"{c['total']} / {c['new_30d']} / {c['repeat']}"],
    ], col_widths=[110 * mm, 64 * mm], align_right_from=1))
    series = report["revenue"].get(period, report["revenue"]["monthly"])
    story.append(P(f"Revenue – {period}", H2))
    story.append(_table([["Period", "Revenue"]] + [[l, money(site, v)] for l, v in zip(series["labels"], series["values"])],
                        col_widths=[110 * mm, 64 * mm], align_right_from=1))
    story.append(P("Bookings by status", H2))
    story.append(_table([["Status", "Bookings"]] + [[l, v] for l, v in zip(report["statuses"]["labels"], report["statuses"]["values"])],
                        col_widths=[110 * mm, 64 * mm], align_right_from=1))
    story.append(P("Most popular room types", H2))
    story.append(_table([["Room type", "Bookings"]] + [[l, v] for l, v in zip(report["popular"]["labels"], report["popular"]["values"])]
                        or [["-", "-"]], col_widths=[110 * mm, 64 * mm], align_right_from=1))
    story.append(P("Occupancy by room type (last 30 days)", H2))
    story.append(_table([["Room type", "Occupancy"]] + [[l, f"{v}%"] for l, v in zip(report["occupancy"]["labels"], report["occupancy"]["values"])],
                        col_widths=[110 * mm, 64 * mm], align_right_from=1))
    story.append(P("Payments by method", H2))
    story.append(_table([["Method", "Amount"]] + [[k, money(site, v)] for k, v in report["by_method"].items()] or [["-", "-"]],
                        col_widths=[110 * mm, 64 * mm], align_right_from=1))
    if c["top"]:
        story.append(P("Top customers", H2))
        story.append(_table([["Customer", "Phone", "Bookings"]] + [[x["name"], x["phone"], x["bookings"]] for x in c["top"]],
                            col_widths=[80 * mm, 60 * mm, 34 * mm], align_right_from=2))
    return _build(story, "HOTEL BARDHERE HB report")
