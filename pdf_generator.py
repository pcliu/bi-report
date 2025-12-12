#!/usr/bin/env python3
"""
PDF报告生成器
使用DataService统一数据接口
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import plotly.io as pio
import platform
from data_service import DataService


def setup_chinese_font():
    """设置中文字体"""
    try:
        # 尝试注册中文字体
        system = platform.system()
        if system == "Darwin":  # macOS
            font_paths = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/Library/Fonts/Arial Unicode MS.ttf"
            ]
        elif system == "Windows":
            font_paths = [
                "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
                "C:/Windows/Fonts/simsun.ttc",  # 宋体
                "C:/Windows/Fonts/simhei.ttf"   # 黑体
            ]
        else:  # Linux
            font_paths = [
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ]
        
        # 尝试注册第一个可用的字体
        for font_path in font_paths:
            try:
                import os
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('chinese-font', font_path))
                    return 'chinese-font'
            except:
                continue
        
        # 如果都失败了，使用默认字体
        return 'Helvetica'
    except:
        return 'Helvetica'


def create_plotly_image(fig, width=600, height=400):
    """将Plotly图表转换为图片"""
    try:
        # 确保图表有良好的配色方案
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='black', size=12),
            showlegend=True,
            legend=dict(
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='black',
                borderwidth=1
            )
        )
        
        # 为饼图设置明亮的颜色
        if 'Pie' in str(fig.data):
            colors_list = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', '#54A0FF', '#5F27CD']
            for i, trace in enumerate(fig.data):
                if hasattr(trace, 'marker'):
                    trace.marker.colors = colors_list[:len(trace.labels)] if hasattr(trace, 'labels') else colors_list
        
        # 为柱状图设置颜色
        if 'Bar' in str(fig.data):
            colors_list = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#34495e', '#e67e22']
            for i, trace in enumerate(fig.data):
                if hasattr(trace, 'marker'):
                    trace.marker.color = colors_list[i % len(colors_list)]
        
        # 为散点图设置颜色 - 保留原有的颜色映射
        if 'Scatter' in str(fig.data):
            for i, trace in enumerate(fig.data):
                if hasattr(trace, 'marker'):
                    # 只有当marker没有颜色映射时才设置固定颜色
                    if not hasattr(trace.marker, 'color') or trace.marker.color is None:
                        colors_list = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
                        trace.marker.color = colors_list[i % len(colors_list)]
                    
                    # 确保散点图大小设置正确
                    if hasattr(trace.marker, 'size'):
                        trace.marker.sizemode = 'diameter'
                        trace.marker.sizeref = 2.0  # 调整大小参考值
                        # 确保最小大小可见
                        if hasattr(trace.marker, 'sizemin'):
                            trace.marker.sizemin = 4
        
        img_bytes = pio.to_image(fig, format="png", width=width, height=height, scale=2, engine="kaleido")
        img_buffer = io.BytesIO(img_bytes)
        return Image(img_buffer, width=width*0.6, height=height*0.6)
    except Exception as e:
        # 如果图片生成失败，返回错误文本
        chinese_font = setup_chinese_font()
        error_style = ParagraphStyle(
            'ErrorStyle',
            fontName=chinese_font,
            fontSize=10,
            textColor=colors.red
        )
        return Paragraph(f"图表生成失败: {str(e)}", error_style)


def generate_complete_pdf_report(filters=None):
    """生成完整的PDF报告，包含所有图表和数据"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # 设置中文字体
    chinese_font = setup_chinese_font()
    
    # 自定义样式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # 居中
        fontName=chinese_font,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.darkblue,
        fontName=chinese_font,
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        spaceAfter=10,
        textColor=colors.blue,
        fontName=chinese_font,
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=chinese_font,
        fontSize=10,
    )
    
    # 标题页
    story.append(Paragraph("用户流量分析完整报告", title_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 20))
    
    # 显示筛选条件
    if filters:
        filter_desc = filters.get_description()
        story.append(Paragraph(f"筛选条件: {filter_desc}", normal_style))
        story.append(Spacer(1, 20))
    
    story.append(Paragraph("本报告包含所有Dashboard页面的图表和数据分析", normal_style))
    story.append(PageBreak())
    
    # 获取数据服务实例
    data_service = DataService()
    
    try:
        # === 1. 基础统计信息 ===
        story.append(Paragraph("1. 基础统计信息", heading_style))
        
        basic_stats = data_service.get_basic_stats(filters)
        stats_data = [
            ['指标', '数值'],
            ['总记录数', f"{basic_stats['total_records']:,}"],
            ['用户总数', f"{basic_stats['total_users']:,}"],
            ['总流量', f"{basic_stats['total_traffic_gb']:.2f} GB"],
            ['应用大类数', f"{basic_stats['app_categories']:,}"],
        ]
        
        stats_table = Table(stats_data, colWidths=[2*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), chinese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(stats_table)
        story.append(PageBreak())
        
        # === 2. 流量分析 ===
        story.append(Paragraph("2. 流量分析", heading_style))
        
        # 2.1 上行vs下行流量分布
        story.append(Paragraph("2.1 上行vs下行流量分布", subheading_style))
        fig = data_service.create_traffic_pie_chart(filters)
        if fig:
            story.append(create_plotly_image(fig, width=500, height=400))
        
        story.append(Spacer(1, 12))
        
        # 2.2 IPv4 vs IPv6流量分布
        story.append(Paragraph("2.2 IPv4 vs IPv6流量分布", subheading_style))
        fig = data_service.create_ip_type_pie_chart(filters, by_traffic=True)
        if fig:
            story.append(create_plotly_image(fig, width=500, height=400))
        
        story.append(Spacer(1, 12))
        
        # 2.3 流量时长分布
        story.append(Paragraph("2.3 流量时长分布", subheading_style))
        fig = data_service.create_duration_bar_chart(filters)
        if fig:
            story.append(create_plotly_image(fig, width=500, height=400))
        
        # 2.4 流量TOP用户
        story.append(Paragraph("2.4 流量TOP用户", subheading_style))
        fig = data_service.create_top_users_bar_chart(10, filters)
        if fig:
            story.append(create_plotly_image(fig, width=600, height=400))
        
        story.append(PageBreak())
        
        # === 3. 用户分析 ===
        story.append(Paragraph("3. 用户分析", heading_style))
        
        # 3.1 用户活跃度分析
        story.append(Paragraph("3.1 用户活跃度分析", subheading_style))
        fig = data_service.create_user_activity_pie_chart(filters)
        if fig:
            story.append(create_plotly_image(fig, width=500, height=400))
        
        story.append(Spacer(1, 12))
        
        # 3.2 用户流量消耗分布
        story.append(Paragraph("3.2 用户流量消耗分布", subheading_style))
        fig = data_service.create_user_traffic_bar_chart(filters)
        if fig:
            story.append(create_plotly_image(fig, width=500, height=400))
        
        # 3.3 高活跃上传用户分析
        story.append(Paragraph("3.3 高活跃上传用户分析", subheading_style))
        fig = data_service.create_upload_users_bar_chart(10, filters)
        if fig:
            story.append(create_plotly_image(fig, width=600, height=400))
        
        story.append(Spacer(1, 12))
        
        fig = data_service.create_upload_ratio_scatter_chart(10, filters)
        if fig:
            story.append(create_plotly_image(fig, width=600, height=400))
        
        story.append(PageBreak())
        
        # === 4. 应用分析 ===
        story.append(Paragraph("4. 应用分析", heading_style))
        
        # 4.1 应用大类流量分析
        story.append(Paragraph("4.1 应用大类流量分析", subheading_style))
        fig = data_service.create_app_traffic_bar_chart(10, filters)
        if fig:
            story.append(create_plotly_image(fig, width=600, height=400))
        
        story.append(Spacer(1, 12))
        
        # 4.2 应用大类用户数分析
        story.append(Paragraph("4.2 应用大类用户数分析", subheading_style))
        fig = data_service.create_app_users_bar_chart(10, filters)
        if fig:
            story.append(create_plotly_image(fig, width=600, height=400))
        
        story.append(PageBreak())
        
        # === 5. 时间分析 ===
        story.append(Paragraph("5. 时间分析", heading_style))
        
        # 5.1 总体流量时间趋势
        story.append(Paragraph("5.1 总体流量时间趋势", subheading_style))
        fig = data_service.create_flexible_time_chart(
            group_by_field='none',
            metric_type='traffic',
            traffic_type='total',
            filters=filters
        )
        if fig:
            story.append(create_plotly_image(fig, width=600, height=400))
        
        # 5.2 IP类型流量时间分布
        story.append(Paragraph("5.2 IPv4 vs IPv6流量时间分布", subheading_style))
        fig = data_service.create_flexible_time_chart(
            group_by_field='ip_type',
            metric_type='traffic', 
            traffic_type='total',
            filters=filters
        )
        if fig:
            story.append(create_plotly_image(fig, width=600, height=400))
        
        # 5.3 会话数时间趋势
        story.append(Paragraph("5.3 会话数时间趋势", subheading_style))
        fig = data_service.create_flexible_time_chart(
            group_by_field='none',
            metric_type='session_count',
            filters=filters
        )
        if fig:
            story.append(create_plotly_image(fig, width=600, height=400))
        
        # 5.4 TOP用户流量时间趋势
        story.append(Paragraph("5.4 TOP用户流量时间趋势", subheading_style))
        fig = data_service.create_flexible_time_chart(
            group_by_field='user_account',
            metric_type='traffic',
            traffic_type='total',
            filters=filters
        )
        if fig:
            story.append(create_plotly_image(fig, width=600, height=400))
        
        
        story.append(PageBreak())
        
    except Exception as e:
        error_style = ParagraphStyle(
            'ErrorStyle',
            fontName=chinese_font,
            fontSize=12,
            textColor=colors.red
        )
        story.append(Paragraph(f"数据获取失败: {str(e)}", error_style))
    
    # === 6. 报告总结 ===
    story.append(Paragraph("6. 报告总结", heading_style))
    
    summary_text = """
    本完整报告基于用户流量数据生成，包含以下分析维度：
    
    1. 基础统计信息：提供数据总览，包括用户数、流量总量等关键指标
    
    2. 流量分析：包含上下行流量分布、流量时长分布、TOP用户分析
    
    3. 用户分析：用户活跃度分析、流量消耗分布、高活跃上传用户分析
    
    4. 应用分析：应用大类流量和用户数统计分析
    
    5. 时间分析：多维度时间趋势分析，包括：
       - 总体流量时间趋势
       - IPv4 vs IPv6流量时间分布对比
       - 会话数时间变化趋势
       - TOP用户流量时间趋势分析
    
    本报告包含所有Dashboard页面的图表和数据，提供全面的流量分析视角。
    新增的灵活时间分析功能支持多维度分组和指标选择，便于深入了解数据的时间变化规律。
    建议定期生成此报告，监控网络使用趋势和异常行为。
    """
    
    story.append(Paragraph(summary_text, normal_style))
    
    # 构建PDF
    doc.build(story)
    buffer.seek(0)
    return buffer