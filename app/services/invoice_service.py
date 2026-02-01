from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from io import BytesIO
from datetime import datetime

class InvoiceService:
    def generate_invoice_pdf(self, transaction: dict) -> BytesIO:
        buffer = BytesIO()
        # Increased bottom margin for footer
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=60)
        styles = getSampleStyleSheet()
        
        # Define Brand Colors
        brand_blue = colors.HexColor("#3b82f6")
        brand_slate = colors.HexColor("#0f172a") # Slate 900 for 'Journal'
        brand_light_bg = colors.HexColor("#f8fafc")
        
        # Custom styles
        journal_style = ParagraphStyle(
            'JournalStyle',
            parent=styles['Heading1'],
            fontSize=32,
            textColor=brand_slate,
            fontName='Helvetica-Bold'
        )
        
        x_style = ParagraphStyle(
            'XStyle',
            parent=styles['Heading1'],
            fontSize=32,
            textColor=brand_blue,
            fontName='Helvetica-Bold'
        )
        
        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            textTransform='uppercase',
            fontName='Helvetica-Bold',
            spaceAfter=2
        )
        
        value_style = ParagraphStyle(
            'ValueStyle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=brand_slate,
            fontName='Helvetica',
            spaceAfter=12
        )
        
        # Helper for the logo
        def get_logo():
            return Table([[
                Paragraph("Journal", journal_style),
                Paragraph("X", x_style)
            ]], colWidths=[105, 30], style=TableStyle([
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('VALIGN', (0,0), (-1,-1), 'BASELINE'),
            ]))

        small_style = ParagraphStyle(
            'SmallStyle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=1 # Center
        )
        
        elements = []
        
        # --- Top Header Section ---
        invoice_num = transaction.get('invoice_number', 'N/A')
        payment_date = transaction.get('payment_date')
        if isinstance(payment_date, str):
            date_str = payment_date.split('T')[0] if 'T' in payment_date else payment_date
        elif hasattr(payment_date, 'strftime'):
            date_str = payment_date.strftime('%Y-%m-%d')
        else:
            date_str = str(payment_date) if payment_date else datetime.now().strftime('%Y-%m-%d')

        header_data = [
            [
                get_logo(),
                [
                    Paragraph("Invoice Number", label_style),
                    Paragraph(invoice_num, value_style),
                    Paragraph("Date of Issue", label_style),
                    Paragraph(date_str, value_style)
                ]
            ]
        ]
        
        header_table = Table(header_data, colWidths=[350, 150])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))
        elements.append(header_table)
        
        # Decorative line
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=brand_light_bg, spaceAfter=30))
        
        # --- Billing Info Section ---
        billing = transaction.get('billing_details', {})
        billing_data = [
            [
                [
                    Paragraph("Seller", label_style),
                    Paragraph("JournalX Trading Inc.", value_style),
                    Paragraph("123 Trading Street", value_style),
                    Paragraph("Finance City, FC 12345", value_style),
                ],
                [
                    Paragraph("Bill To", label_style),
                    Paragraph(billing.get('full_name', 'Customer'), value_style),
                    Paragraph(billing.get('email', 'N/A'), value_style),
                    Paragraph(billing.get('address', 'N/A'), value_style),
                ]
            ]
        ]
        
        billing_table = Table(billing_data, colWidths=[250, 250])
        billing_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        elements.append(billing_table)
        elements.append(Spacer(1, 40))
        
        # --- Transaction Items Table ---
        plan_name = billing.get('plan_name', 'Monthly')
        payment_method = billing.get('payment_method', 'card')
        coupon_code = billing.get('coupon_code', '')
        
        total_amount = transaction.get('total_amount', 0.0)
        discount_amount = transaction.get('discount_amount', 0.0)
        amount_paid = transaction.get('amount_paid', total_amount)
        
        sub_data = [
            [Paragraph("Description", label_style), Paragraph("Amount", label_style)],
        ]
        
        # Principal Item
        sub_data.append([
            Paragraph(f"Subscription Plan: {str(plan_name).title()}", value_style),
            Paragraph(f"${total_amount:.2f}", value_style)
        ])
        
        # Discount Row
        if discount_amount > 0:
            discount_label = f"Discount ({coupon_code})" if coupon_code else "Discount"
            sub_data.append([
                Paragraph(discount_label, value_style),
                Paragraph(f"-${discount_amount:.2f}", value_style)
            ])
        
        sub_table = Table(sub_data, colWidths=[400, 100])
        sub_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), brand_light_bg),
            ('LINEBELOW', (0,0), (-1,0), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('TOPPADDING', (1,1), (-1,-1), 10),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ]))
        elements.append(sub_table)
        elements.append(Spacer(1, 30))
        
        # --- Totals Section (Fixed Overlap) ---
        totals_data = []
        
        # Promotion note if applicable
        if payment_method == 'coupon' and coupon_code:
             totals_data.append(["", Paragraph(f"Payment Method: Promotional Code ({coupon_code})", label_style)])
        
        totals_data.append(["", Paragraph("Total Paid", label_style)])
        
        # Large Total Value
        total_paid_style = ParagraphStyle(
            'TotalPaidStyle',
            parent=styles['Heading1'],
            fontSize=36,
            textColor=brand_blue,
            fontName='Helvetica-Bold',
            alignment=2 # Right align
        )
        totals_data.append(["", Paragraph(f"${amount_paid:.2f}", total_paid_style)])
            
        totals_table = Table(totals_data, colWidths=[300, 200])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (1,0), (1,-1), 10),
        ]))
        elements.append(totals_table)
        
        # --- Footer ---
        elements.append(Spacer(1, 100)) # Large spacer to push to bottom
        elements.append(Paragraph("Thank you for your business!", styles['Italic']))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph("For support, contact support@journalx.com", small_style))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer

invoice_service = InvoiceService()
