import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import database as db

async def generate_pdf_report(user_id: int) -> io.BytesIO:
    """
    Query database for social accounts and their analytics snapshots
    and build a styled PDF report inside an in-memory buffer.
    """
    user = await db.get_user(user_id)
    accounts = await db.get_social_accounts(user_id=user_id)
    stats = await db.get_post_stats(user_id=user_id)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        rightMargin=36, 
        leftMargin=36, 
        topMargin=36, 
        bottomMargin=36
    )
    story = []
    
    # Styles config
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        textColor=colors.HexColor('#7c3aed'), # Violet brand color
        fontSize=24,
        leading=28,
        spaceAfter=8
    )
    
    subtitle_style = ParagraphStyle(
        'SubTitleStyle',
        parent=styles['Normal'],
        textColor=colors.HexColor('#64748b'),
        fontSize=10,
        leading=12,
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        textColor=colors.HexColor('#0f172a'),
        fontSize=14,
        leading=18,
        spaceBefore=14,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        textColor=colors.HexColor('#334155'),
        fontSize=9,
        leading=13
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    # 1. Document Title & Subtitle
    story.append(Paragraph("SMM & LeadGen Omnichannel Platform", title_style))
    story.append(Paragraph(f"Analytics Executive Report — Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", subtitle_style))
    story.append(Spacer(1, 10))
    
    # 2. Executive Summary Card
    story.append(Paragraph("Executive Summary", heading_style))
    summary_data = [
        [Paragraph("Metric", body_bold), Paragraph("Value", body_bold)],
        [Paragraph("Total Connected Pages / Accounts", body_style), Paragraph(str(len(accounts)), body_style)],
        [Paragraph("Total Outbound Messages (All Platforms)", body_style), Paragraph(str(stats.get("total_posts", 0)), body_style)],
        [Paragraph("Delivery Success Rate", body_style), Paragraph(f"{stats.get('success_rate', 100)}%", body_style)],
    ]
    t_summary = Table(summary_data, colWidths=[240, 100])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 20))
    
    # 3. Connected Accounts stats
    story.append(Paragraph("Social Account Performance Logs", heading_style))
    
    for acc in accounts:
        plat_name = acc['platform'].capitalize()
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>Account:</b> @{acc['username']} ({plat_name})", body_bold))
        story.append(Spacer(1, 4))
        
        # Get snapshots
        snapshots = await db.get_analytics_snapshots(acc["id"], limit=10)
        
        if not snapshots:
            story.append(Paragraph("No historical weekly snapshots found yet. Statistics gather loop runs every Sunday.", body_style))
            story.append(Spacer(1, 10))
            continue
            
        # Draw analytics table
        table_data = [[
            Paragraph("Date", body_bold),
            Paragraph("Followers", body_bold),
            Paragraph("Impressions", body_bold),
            Paragraph("Engagement", body_bold),
            Paragraph("Clicks", body_bold)
        ]]
        
        # We display them oldest first to show progression
        for snap in reversed(snapshots):
            table_data.append([
                Paragraph(snap["snapshot_date"], body_style),
                Paragraph(str(snap["followers"]), body_style),
                Paragraph(str(snap["impressions"]), body_style),
                Paragraph(str(snap["engagement"]), body_style),
                Paragraph(str(snap["clicks"]), body_style)
            ])
            
        t_acc = Table(table_data, colWidths=[110, 105, 105, 105, 105])
        t_acc.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(t_acc)
        story.append(Spacer(1, 12))
        
    doc.build(story)
    buffer.seek(0)
    return buffer
