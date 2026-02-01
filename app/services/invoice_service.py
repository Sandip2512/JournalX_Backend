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
        invoice_num = transaction.get('invoice_number', 'N/A')
        elements.append(Paragraph(f"Invoice Number: {invoice_num}", styles['Normal']))
        
        # Handle payment_date - could be datetime or string
        payment_date = transaction.get('payment_date')
        if isinstance(payment_date, str):
            date_str = payment_date.split('T')[0] if 'T' in payment_date else payment_date
        elif hasattr(payment_date, 'strftime'):
            date_str = payment_date.strftime('%Y-%m-%d')
        else:
            date_str = str(payment_date) if payment_date else datetime.now().strftime('%Y-%m-%d')
            
        elements.append(Paragraph(f"Date: {date_str}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Seller & Customer Details
        billing = transaction.get('billing_details', {})
        data = [
            ["Seller:", "Bill To:"],
            ["JournalX Trading Inc.", billing.get('full_name', 'Customer')],
            ["123 Trading St.", billing.get('email', '')],
            ["Finance City, FC 12345", billing.get('address', '')]
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
        plan_name = billing.get('plan_name', 'Monthly')
        payment_method = billing.get('payment_method', 'card')
        coupon_code = billing.get('coupon_code', '')
        
        total_amount = transaction.get('total_amount', 0.0)
        discount_amount = transaction.get('discount_amount', 0.0)
        amount_paid = transaction.get('amount_paid', total_amount)
        
        sub_data = [
            ["Description", "Amount"],
            [f"Subscription Plan: {str(plan_name).title()}", f"${total_amount:.2f}"],
        ]
        
        # Add discount row if applicable
        if discount_amount > 0:
            discount_label = f"Discount ({coupon_code})" if coupon_code else "Discount"
            sub_data.append([discount_label, f"-${discount_amount:.2f}"])
        
        # Add total
        sub_data.append(["Total Paid", f"${amount_paid:.2f}"])
        
        if payment_method == 'coupon':
            sub_data.append(["Payment Method", f"Promotional Code: {coupon_code}"])
        
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
