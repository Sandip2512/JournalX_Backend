import os
import uuid
from io import BytesIO
from datetime import datetime
from typing import Dict, Any
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend for speed and stability
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.units import inch

class PDFReportService:
    def __init__(self):
        self.reports_dir = os.path.join(os.getcwd(), "generated_reports")
        os.makedirs(self.reports_dir, exist_ok=True)
        self.styles = getSampleStyleSheet()
        
        # Professional Color Palette
        self.primary_color = colors.HexColor("#10b981") # Emerald 500
        self.secondary_color = colors.HexColor("#0f172a") # Slate 900
        self.muted_color = colors.HexColor("#64748b") # Slate 500
        self.success_color = colors.HexColor("#059669") # Emerald 600
        self.danger_color = colors.HexColor("#e11d48") # Rose 600
        self.bg_muted = colors.HexColor("#f8fafc") # Slate 50
        
        self.create_custom_styles()

    def create_custom_styles(self):
        # Header / Title
        self.styles.add(ParagraphStyle(
            'MainHeader',
            parent=self.styles['Heading1'],
            fontSize=26,
            textColor=self.secondary_color,
            alignment=0, # Left
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            'SubHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.muted_color,
            alignment=0,
            spaceAfter=20
        ))
        
        # Section Styles
        self.styles.add(ParagraphStyle(
            'H2',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=self.secondary_color,
            spaceBefore=15,
            spaceAfter=15,
            borderPadding=(0, 0, 5, 0),
            borderColor=self.primary_color,
            borderWidth=0 # Side border only? Not easy in reportlab Para, use Spacer/Table
        ))
        
        # Card Styles
        self.styles.add(ParagraphStyle(
            'CardLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=self.muted_color,
            textTransform='uppercase',
            alignment=1 # Center
        ))
        self.styles.add(ParagraphStyle(
            'CardValue',
            parent=self.styles['Normal'],
            fontSize=18,
            textColor=self.secondary_color,
            fontWeight='bold',
            alignment=1 # Center
        ))
        
        # Insight Styles
        self.styles.add(ParagraphStyle(
            'InsightTitle',
            parent=self.styles['Normal'],
            fontSize=11,
            fontWeight='bold',
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            'InsightText',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.secondary_color,
            leftIndent=15,
            bulletIndent=5,
            spaceAfter=8
        ))

    def generate_equity_chart(self, equity_curve: list) -> str:
        """Generate enhanced equity curve chart."""
        if not equity_curve: return None
        
        times = [datetime.strptime(e['time'], "%Y-%m-%d %H:%M") for e in equity_curve]
        equities = [e['equity'] for e in equity_curve]
        
        plt.figure(figsize=(10, 5), facecolor='white')
        plt.plot(times, equities, color='#10b981', linewidth=2.5, marker='o', markersize=3, markerfacecolor='white')
        plt.fill_between(times, equities, [min(equities)-10 for _ in equities], color='#10b981', alpha=0.1)
        
        plt.title('Performance Trajectory', color='#0f172a', fontsize=14, fontweight='bold', pad=20)
        plt.xticks(rotation=30, fontsize=8)
        plt.yticks(fontsize=9)
        plt.grid(True, linestyle='--', alpha=0.2, color='#64748b')
        
        # Remove spines
        for spine in plt.gca().spines.values():
            spine.set_visible(False)
            
        plt.tight_layout()
        
        char_id = str(uuid.uuid4())
        chart_path = os.path.join(self.reports_dir, f"equity_{char_id}.png")
        plt.savefig(chart_path, dpi=150)
        plt.close()
        return chart_path

    def generate_win_loss_chart(self, stats: Dict) -> str:
        """Generate Win/Loss distribution chart."""
        wins = stats.get('winning_trades', 0)
        losses = stats.get('losing_trades', 0)
        if wins + losses == 0: return None
        
        plt.figure(figsize=(4, 4), facecolor='white')
        labels = ['Wins', 'Losses']
        sizes = [wins, losses]
        colors_list = ['#10b981', '#f43f5e']
        
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, 
                colors=colors_list, textprops={'color':"#0f172a", 'weight':'bold'},
                pctdistance=0.85, explode=(0.05, 0))
        
        # Draw circle for donut effect
        centre_circle = plt.Circle((0,0), 0.70, fc='white')
        fig = plt.gcf()
        fig.gca().add_artist(centre_circle)
        
        plt.title('Trade Distribution', color='#0f172a', fontsize=12, fontweight='bold')
        plt.axis('equal')
        plt.tight_layout()
        
        char_id = str(uuid.uuid4())
        chart_path = os.path.join(self.reports_dir, f"winloss_{char_id}.png")
        plt.savefig(chart_path, dpi=150)
        plt.close()
        return chart_path

    def generate_report_pdf(self, user_name: str, report_type: str, stats: Dict, insights: Dict) -> str:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            rightMargin=40, 
            leftMargin=40, 
            topMargin=40, 
            bottomMargin=40
        )
        elements = []

        # 1. Branding / Header
        header_table = Table([
            [
                Paragraph("JournalX", ParagraphStyle('logo', fontSize=24, textColor=self.primary_color, fontWeight='bold')),
                Paragraph(f"{report_type.upper()} PERFORMANCE REVIEW", self.styles['MainHeader'])
            ]
        ], colWidths=[2*inch, 4*inch])
        elements.append(header_table)
        elements.append(Paragraph(f"Trader Profile: {user_name}  |  Period: {datetime.now().strftime('%B %Y')}", self.styles['SubHeader']))
        
        # Horizontal Rule
        elements.append(Table([['']], colWidths=[doc.width], style=[('LINEBELOW', (0,0), (-1,-1), 1, self.bg_muted)]))
        elements.append(Spacer(1, 25))

        # 2. Key Performance Metrics (Cards Layout)
        metrics_data = [
            [
                [Paragraph("TOTAL P&L", self.styles['CardLabel']), Paragraph(f"${stats['total_pl']:,.2f}", self.styles['CardValue'])],
                [Paragraph("WIN RATE", self.styles['CardLabel']), Paragraph(f"{stats['win_rate']:.1f}%", self.styles['CardValue'])],
                [Paragraph("TOTAL TRADES", self.styles['CardLabel']), Paragraph(str(stats['total_trades']), self.styles['CardValue'])]
            ],
            [
                [Paragraph("AVG WIN", self.styles['CardLabel']), Paragraph(f"${stats['avg_profit_winner']:,.2f}", self.styles['CardValue'])],
                [Paragraph("AVG LOSS", self.styles['CardLabel']), Paragraph(f"${stats['avg_loss_loser']:,.2f}", self.styles['CardValue'])],
                [Paragraph("PROFIT FACTOR", self.styles['CardLabel']), Paragraph(f"{abs(stats['avg_profit_winner'] / stats['avg_loss_loser']):.2f}" if stats['avg_loss_loser'] != 0 else "∞", self.styles['CardValue'])]
            ]
        ]
        
        # Create metric cards using nested tables
        cards = []
        for row in metrics_data:
            row_cards = []
            for item in row:
                t = Table([[item[0]], [item[1]]], colWidths=[2*inch])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), self.bg_muted),
                    ('BOX', (0,0), (-1,-1), 0.5, colors.white),
                    ('TOPPADDING', (0,0), (-1,-1), 12),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 12),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ]))
                row_cards.append(t)
            cards.append(row_cards)
            
        metrics_table = Table(cards, colWidths=[2.1*inch, 2.1*inch, 2.1*inch])
        elements.append(metrics_table)
        elements.append(Spacer(1, 30))

        # 3. Main Analysis (Double Column: Text + WinLoss Chart)
        elements.append(Paragraph("Trade Analysis & Distribution", self.styles['Heading2']))
        
        win_loss_chart = self.generate_win_loss_chart(stats)
        analysis_summary = [
            Paragraph("Execution Summary", self.styles['InsightTitle']),
            Paragraph(insights['summary'], self.styles['Normal']),
            Spacer(1, 10),
            Paragraph(f"<b>Symbol Performance:</b> Best performing pair was <b>{stats['most_profitable_pair']}</b>, while <b>{stats['least_profitable_pair']}</b> showed room for improvement.", self.styles['Normal'])
        ]
        
        analysis_data = [[analysis_summary, RLImage(win_loss_chart, 2.5*inch, 2.5*inch)]] if win_loss_chart else [[analysis_summary, ""]]
        at = Table(analysis_data, colWidths=[4*inch, 2.5*inch])
        at.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
        elements.append(at)
        elements.append(Spacer(1, 20))

        # 4. Long Performance Chart
        equity_chart = self.generate_equity_chart(stats['equity_curve'])
        if equity_chart:
            elements.append(Paragraph("Performance Trajectory", self.styles['Heading2']))
            elements.append(RLImage(equity_chart, 6.5*inch, 3.25*inch))
            elements.append(Spacer(1, 20))

        # 5. Behavioral Insights (The AI Part)
        elements.append(Paragraph("AI Behavioral Insights & Recommendations", self.styles['Heading2']))
        
        # Strengths Card
        if insights['strengths']:
            elements.append(Paragraph("Proven Strengths", ParagraphStyle('SuccessTitle', parent=self.styles['InsightTitle'], textColor=self.success_color)))
            for s in insights['strengths']:
                elements.append(Paragraph(f"• {s}", self.styles['InsightText']))
            elements.append(Spacer(1, 8))

        # Challenges Card
        if insights['weaknesses']:
            elements.append(Paragraph("Critical Challenges", ParagraphStyle('DangerTitle', parent=self.styles['InsightTitle'], textColor=self.danger_color)))
            for w in insights['weaknesses']:
                elements.append(Paragraph(f"• {w}", self.styles['InsightText']))
            elements.append(Spacer(1, 8))

        # Action Plan
        elements.append(Paragraph("Recommended Action Plan", self.styles['InsightTitle']))
        for s in insights['suggestions']:
            elements.append(Paragraph(f"→ {s}", self.styles['InsightText']))

        # 6. Build PDF & Cleanup
        filename = f"report_{report_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        file_path = os.path.join(self.reports_dir, filename)
        
        doc.build(elements)
        
        # Save from buffer to file
        with open(file_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        # Comprehensive Cleanup
        for path in [equity_chart, win_loss_chart]:
            if path and os.path.exists(path): os.remove(path)
            
        return filename

def uuid_str():
    return str(uuid.uuid4())
