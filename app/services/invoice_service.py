from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from io import BytesIO
from datetime import datetime

class InvoiceService:
    def generate_invoice_pdf(self, transaction: dict) -> BytesIO:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor("#3b82f6"), # Primary blue
            spaceAfter=20
        )
        
        elements = []
        
        # Header
        elements.append(Paragraph("JournalX Invoice", title_style))
        elements.append(Paragraph(f"Invoice Number: {transaction['invoice_number']}", styles['Normal']))
        elements.append(Paragraph(f"Date: {transaction['payment_date'].strftime('%Y-%m-%d')}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Seller & Customer Details
        data = [
            ["Seller:", "Bill To:"],
            ["JournalX Trading Inc.", transaction['billing_details'].get('full_name', 'Customer')],
            ["123 Trading St.", transaction['billing_details'].get('email', '')],
            ["Finance City, FC 12345", transaction['billing_details'].get('address', '')]
        ]
        
        details_table = Table(data, colWidths=[250, 250])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        elements.append(details_table)
        elements.append(Spacer(1, 40))
        
        # Subscription Details Table
        sub_data = [
            ["Description", "Amount"],
            [f"Subscription Plan: {transaction['billing_details'].get('plan_name', 'Monthly')}", f"${transaction['amount']:.2f}"],
            ["Tax (GST/VAT)", f"${transaction['tax_amount']:.2f}"],
            ["Total", f"${transaction['total_amount']:.2f}"]
        ]
        
        sub_table = Table(sub_data, colWidths=[350, 100])
        sub_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
            ('LINEABOVE', (0,-1), (-1,-1), 1, colors.black),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        elements.append(sub_table)
        
        # Footer
        elements.append(Spacer(1, 60))
        elements.append(Paragraph("Thank you for your business!", styles['Italic']))
        elements.append(Paragraph("For support, contact support@journalx.com", styles['Small']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer

invoice_service = InvoiceService()
