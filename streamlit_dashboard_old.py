#!/usr/bin/env python3
"""
ClickHouse数据可视化Dashboard
基于Streamlit构建的互动式数据分析报表
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
from data_service import DataService
from pdf_generator import generate_complete_pdf_report
import io
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import plotly.io as pio
import platform

# 页面配置
st.set_page_config(
    page_title="用户流量分析Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 获取数据服务实例
@st.cache_resource
def get_data_service():
    """获取数据服务实例"""
    try:
        return DataService()
    except Exception as e:
        st.error(f"无法连接到数据服务: {str(e)}")
        return None

# 主页面
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
        
        # 为散点图设置颜色
        if 'Scatter' in str(fig.data):
            colors_list = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
            for i, trace in enumerate(fig.data):
                if hasattr(trace, 'marker'):
                    trace.marker.color = colors_list[i % len(colors_list)]
                    if hasattr(trace.marker, 'size'):
                        trace.marker.sizemode = 'diameter'
                        trace.marker.sizeref = 0.1
        
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

def generate_pdf_report():
    """生成简化PDF报告（保持向后兼容）"""
    return generate_complete_pdf_report()
    
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
    story.append(Paragraph("本报告包含所有Dashboard页面的图表和数据分析", normal_style))
    story.append(PageBreak())
    
    # 基础统计信息
    story.append(Paragraph("1. 基础统计信息", heading_style))
    
    # 获取数据服务实例
    data_service = DataService()
    
    try:
        # 获取基础统计数据
        basic_stats = data_service.get_basic_stats()
        
        # 创建统计表格
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
        fig = data_service.create_traffic_pie_chart()
        if fig:
            story.append(create_plotly_image(fig, width=500, height=400))
    
    story.append(Spacer(1, 12))
    
        # 2.2 流量时长分布
        story.append(Paragraph("2.2 流量时长分布", subheading_style))
        fig = data_service.create_duration_bar_chart()
        if fig:
            story.append(create_plotly_image(fig, width=500, height=400))
    
        # 2.3 流量TOP用户
        story.append(Paragraph("2.3 流量TOP用户", subheading_style))
        top_users = data_service.get_top_traffic_users(10)
        
        if not top_users.empty:
            # 生成TOP用户柱状图
            fig = data_service.create_top_users_bar_chart(10)
            if fig:
                story.append(create_plotly_image(fig, width=600, height=400))
        
        story.append(Spacer(1, 12))
        
        # 详细数据表格
        user_data = [['排名', '用户账号', '总流量(GB)', '会话数']]
        for idx, row in top_users.head(10).iterrows():
            user_data.append([
                str(len(user_data)),
                row['user_account'][:25] + "..." if len(row['user_account']) > 25 else row['user_account'],
                f"{row['total_traffic_gb']:.2f}",
                str(row['sessions'])
            ])
        
        user_table = Table(user_data, colWidths=[0.8*inch, 2.5*inch, 1.2*inch, 1*inch])
        user_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), chinese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        story.append(user_table)
    
    story.append(PageBreak())
    
    # === 3. 用户分析 ===
    story.append(Paragraph("3. 用户分析", heading_style))
    
    # 3.1 用户活跃度分析
    story.append(Paragraph("3.1 用户活跃度分析", subheading_style))
    user_activity = execute_query("""
        SELECT 
            CASE 
                WHEN session_count = 1 THEN '单次会话'
                WHEN session_count <= 5 THEN '2-5次会话'
                WHEN session_count <= 10 THEN '6-10次会话'
                WHEN session_count <= 20 THEN '11-20次会话'
                ELSE '>20次会话'
            END as activity_level,
            COUNT(*) as user_count
        FROM (
            SELECT user_account, COUNT(*) as session_count
            FROM default.tbl_statistic_userapp_day
            GROUP BY user_account
        ) 
        GROUP BY activity_level
        ORDER BY user_count DESC
    """)
    
    if not user_activity.empty:
        fig = px.pie(user_activity, values='user_count', names='activity_level',
                    title='用户活跃度分布',
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57'])
        fig.update_layout(font=dict(size=12), showlegend=True)
        story.append(create_plotly_image(fig, width=500, height=400))
    
    story.append(Spacer(1, 12))
    
    # 3.2 用户流量消耗分布
    story.append(Paragraph("3.2 用户流量消耗分布", subheading_style))
    user_traffic_dist = execute_query("""
        SELECT 
            CASE 
                WHEN total_traffic < 1048576 THEN '<1MB'
                WHEN total_traffic < 10485760 THEN '1-10MB'
                WHEN total_traffic < 104857600 THEN '10-100MB'
                WHEN total_traffic < 1073741824 THEN '100MB-1GB'
                ELSE '>1GB'
            END as traffic_range,
            COUNT(*) as user_count
        FROM (
            SELECT user_account, SUM(total_traffic) as total_traffic
            FROM default.tbl_statistic_userapp_day
            GROUP BY user_account
        )
        GROUP BY traffic_range
        ORDER BY user_count DESC
    """)
    
    if not user_traffic_dist.empty:
        fig = px.bar(user_traffic_dist, x='traffic_range', y='user_count',
                    title='用户流量消耗分布',
                    labels={'traffic_range': '流量范围', 'user_count': '用户数'},
                    color='user_count',
                    color_continuous_scale='Greens')
        fig.update_layout(font=dict(size=12), showlegend=False)
        story.append(create_plotly_image(fig, width=500, height=400))
    
    # 3.3 高活跃上传用户分析
    story.append(Paragraph("3.3 高活跃上传用户分析", subheading_style))
    upload_heavy_users = execute_query("""
        SELECT 
            user_account,
            COUNT(*) as session_count,
            SUM(upstream_traffic) as total_upstream,
            SUM(downstream_traffic) as total_downstream,
            SUM(total_traffic) as total_traffic,
            CASE 
                WHEN SUM(downstream_traffic) = 0 THEN 999.99
                ELSE ROUND(SUM(upstream_traffic) / SUM(downstream_traffic), 2)
            END as upload_ratio
        FROM default.tbl_statistic_userapp_day
        GROUP BY user_account
        HAVING session_count >= 5 
            AND total_upstream > total_downstream 
            AND total_upstream >= 104857600
        ORDER BY total_upstream DESC
        LIMIT 10
    """)
    
    if not upload_heavy_users.empty:
        upload_heavy_users['upstream_gb'] = upload_heavy_users['total_upstream'] / (1024*1024*1024)
        upload_heavy_users['downstream_gb'] = upload_heavy_users['total_downstream'] / (1024*1024*1024)
        
        # 上传用户柱状图
        fig = px.bar(upload_heavy_users, 
                    x='user_account', y='upstream_gb',
                    title='高活跃上传用户 - 上行流量',
                    labels={'user_account': '用户账号', 'upstream_gb': '上行流量(GB)'},
                    color='upstream_gb',
                    color_continuous_scale='Oranges')
        fig.update_layout(xaxis_tickangle=45, font=dict(size=10), showlegend=False)
        story.append(create_plotly_image(fig, width=600, height=400))
        
        story.append(Spacer(1, 12))
        
        # 散点图：活跃度vs上传比例
        fig = px.scatter(upload_heavy_users, 
                       x='session_count', y='upload_ratio',
                       size='upstream_gb', hover_name='user_account',
                       title='用户活跃度 vs 上传比例',
                       labels={'session_count': '会话数', 'upload_ratio': '上传/下载比例'},
                       color='upstream_gb',
                       color_continuous_scale='Reds')
        fig.update_layout(font=dict(size=12))
        story.append(create_plotly_image(fig, width=600, height=400))
        
        story.append(Spacer(1, 12))
        
        # 详细数据表格
        upload_data = [['排名', '用户账号', '会话数', '上行(GB)', '下行(GB)', '上传比例', '风险等级']]
        for idx, row in upload_heavy_users.iterrows():
            ratio_display = "仅上传" if row['upload_ratio'] >= 999 else f"{row['upload_ratio']:.1f}:1"
            
            # 风险等级判断
            if (row['upload_ratio'] >= 999 or row['upload_ratio'] >= 10) and row['upstream_gb'] >= 5:
                risk_level = "高风险"
            elif (row['upload_ratio'] >= 999 or row['upload_ratio'] >= 5) and row['upstream_gb'] >= 1:
                risk_level = "中风险"
            else:
                risk_level = "低风险"
            
            upload_data.append([
                str(len(upload_data)),
                row['user_account'][:18] + "..." if len(row['user_account']) > 18 else row['user_account'],
                str(row['session_count']),
                f"{row['upstream_gb']:.2f}",
                f"{row['downstream_gb']:.2f}",
                ratio_display,
                risk_level
            ])
        
        upload_table = Table(upload_data, colWidths=[0.5*inch, 1.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch, 0.8*inch])
        upload_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), chinese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        
        story.append(upload_table)
    else:
        story.append(Paragraph("未找到符合条件的高活跃上传用户", normal_style))
    
    story.append(PageBreak())
    
    # === 4. 应用分析 ===
    story.append(Paragraph("4. 应用分析", heading_style))
    
    # 4.1 应用大类流量分析
    story.append(Paragraph("4.1 应用大类流量分析", subheading_style))
    app_major = execute_query("""
        SELECT 
            app_category_major,
            SUM(total_traffic) as total_traffic,
            COUNT(*) as session_count,
            COUNT(DISTINCT user_account) as user_count
        FROM default.tbl_statistic_userapp_day
        GROUP BY app_category_major
        ORDER BY total_traffic DESC
        LIMIT 10
    """)
    
    if not app_major.empty:
        app_major['total_traffic_gb'] = app_major['total_traffic'] / (1024*1024*1024)
        app_major['app_name'] = app_major['app_category_major'].astype(str) + "类应用"
        
        # 应用大类流量柱状图
        fig = px.bar(app_major, x='app_name', y='total_traffic_gb',
                    title='应用大类流量消耗TOP 10',
                    labels={'app_name': '应用大类', 'total_traffic_gb': '总流量(GB)'},
                    color='total_traffic_gb',
                    color_continuous_scale='Viridis')
        fig.update_layout(xaxis_tickangle=45, font=dict(size=12), showlegend=False)
        story.append(create_plotly_image(fig, width=600, height=400))
        
        story.append(Spacer(1, 12))
        
        # 4.2 应用大类用户数分析
        story.append(Paragraph("4.2 应用大类用户数分析", subheading_style))
        app_major_sorted = app_major.sort_values('user_count', ascending=False)
        
        fig = px.bar(app_major_sorted, x='app_name', y='user_count',
                    title='应用大类用户数TOP 10',
                    labels={'app_name': '应用大类', 'user_count': '用户数'},
                    color='user_count',
                    color_continuous_scale='Plasma')
        fig.update_layout(xaxis_tickangle=45, font=dict(size=12), showlegend=False)
        story.append(create_plotly_image(fig, width=600, height=400))
        
        story.append(Spacer(1, 12))
        
        # 详细数据表格
        app_data = [['排名', '应用大类', '流量(GB)', '用户数', '会话数']]
        for idx, row in app_major.iterrows():
            app_data.append([
                str(len(app_data)),
                f"{row['app_category_major']}类应用",
                f"{row['total_traffic_gb']:.2f}",
                str(row['user_count']),
                str(row['session_count'])
            ])
        
        app_table = Table(app_data, colWidths=[0.8*inch, 1.5*inch, 1.2*inch, 1*inch, 1*inch])
        app_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), chinese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        
        story.append(app_table)
    
    story.append(PageBreak())
    
    # === 5. 时间分析 ===
    story.append(Paragraph("5. 时间分析", heading_style))
    
    # 5.1 数据统计时间分布
    story.append(Paragraph("5.1 数据统计时间分布", subheading_style))
    time_data = execute_query("""
        SELECT 
            stat_time,
            COUNT(*) as record_count,
            SUM(total_traffic) as total_traffic,
            COUNT(DISTINCT user_account) as user_count
        FROM default.tbl_statistic_userapp_day
        GROUP BY stat_time
        ORDER BY stat_time
    """)
    
    if not time_data.empty:
        time_data['total_traffic_gb'] = time_data['total_traffic'] / (1024*1024*1024)
        
        # 时间序列记录数变化
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=time_data['stat_time'], y=time_data['record_count'],
                                mode='lines+markers', name='记录数',
                                line=dict(color='#3498db', width=3),
                                marker=dict(color='#e74c3c', size=8)))
        fig.update_layout(title='时间序列记录数变化', 
                         xaxis_title='统计时间', yaxis_title='记录数',
                         font=dict(size=12),
                         showlegend=True)
        story.append(create_plotly_image(fig, width=600, height=400))
        
        story.append(Spacer(1, 12))
        
        # 时间数据表格
        time_table_data = [['统计时间', '记录数', '流量(GB)', '用户数']]
        for idx, row in time_data.iterrows():
            time_table_data.append([
                row['stat_time'],
                f"{row['record_count']:,}",
                f"{row['total_traffic_gb']:.2f}",
                str(row['user_count'])
            ])
        
        time_table = Table(time_table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        time_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), chinese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        
        story.append(time_table)
    
    story.append(PageBreak())
    
    # === 6. 报告总结 ===
    story.append(Paragraph("6. 报告总结", heading_style))
    
    summary_text = """
    本完整报告基于用户流量数据生成，包含以下分析维度：
    
    1. 基础统计信息：提供数据总览，包括用户数、流量总量等关键指标
    
    2. 流量分析：包含上下行流量分布、流量时长分布、TOP用户分析
    
    3. 用户分析：用户活跃度分析、流量消耗分布、高活跃上传用户分析
    
    4. 应用分析：应用大类流量和用户数统计分析
    
    5. 时间分析：数据统计时间分布和趋势分析
    
    本报告包含所有Dashboard页面的图表和数据，提供全面的流量分析视角。
    建议定期生成此报告，监控网络使用趋势和异常行为。
    """
    
    story.append(Paragraph(summary_text, normal_style))
    
    # 构建PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_pdf_report():
    """生成简化PDF报告（保持向后兼容）"""
    return generate_complete_pdf_report()

def main():
    st.title("📊 用户流量分析Dashboard")
    st.markdown("---")
    
    # 侧边栏
    st.sidebar.title("🎛️ 控制面板")
    
    # 添加PDF导出按钮
    if st.sidebar.button("📄 导出完整PDF报告", type="primary"):
        with st.spinner("正在生成完整PDF报告（包含所有图表）..."):
            try:
                pdf_buffer = generate_pdf_report()
                
                st.sidebar.success("完整PDF报告生成成功！")
                st.sidebar.download_button(
                    label="⬇️ 下载PDF报告",
                    data=pdf_buffer.getvalue(),
                    file_name=f"用户流量分析完整报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.sidebar.error(f"PDF生成失败: {str(e)}")
    
    st.sidebar.info("📊 此PDF包含所有Dashboard页面的图表和数据分析")
    
    st.sidebar.markdown("---")
    
    # 基础统计信息
    st.header("📈 基础统计信息")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # 总数据量
    total_records = execute_query("SELECT COUNT(*) as count FROM default.tbl_statistic_userapp_day")
    if not total_records.empty:
        with col1:
            st.metric("总记录数", f"{total_records.iloc[0]['count']:,}")
    
    # 用户总数
    total_users = execute_query("SELECT COUNT(DISTINCT user_account) as count FROM default.tbl_statistic_userapp_day")
    if not total_users.empty:
        with col2:
            st.metric("用户总数", f"{total_users.iloc[0]['count']:,}")
    
    # 总流量
    total_traffic = execute_query("SELECT SUM(total_traffic) as total FROM default.tbl_statistic_userapp_day")
    if not total_traffic.empty:
        traffic_gb = total_traffic.iloc[0]['total'] / (1024*1024*1024)  # byte转换为GB
        with col3:
            st.metric("总流量", f"{traffic_gb:.2f} GB")
    
    # 应用类别数
    app_categories = execute_query("SELECT COUNT(DISTINCT app_category_major) as count FROM default.tbl_statistic_userapp_day")
    if not app_categories.empty:
        with col4:
            st.metric("应用大类数", f"{app_categories.iloc[0]['count']:,}")
    
    st.markdown("---")
    
    # 选择分析类型
    analysis_type = st.sidebar.selectbox(
        "选择分析类型",
        ["流量分析", "用户分析", "应用分析", "时间分析"]
    )
    
    if analysis_type == "流量分析":
        show_traffic_analysis()
    elif analysis_type == "用户分析":
        show_user_analysis()
    elif analysis_type == "应用分析":
        show_app_analysis()
    elif analysis_type == "时间分析":
        show_time_analysis()

def show_traffic_analysis():
    """流量分析页面"""
    st.header("🌊 流量分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("上行vs下行流量分布")
        traffic_data = execute_query("""
            SELECT 
                SUM(upstream_traffic) as upstream,
                SUM(downstream_traffic) as downstream
            FROM default.tbl_statistic_userapp_day
        """)
        
        if not traffic_data.empty:
            fig = go.Figure(data=[
                go.Pie(
                    labels=['上行流量', '下行流量'],
                    values=[traffic_data.iloc[0]['upstream'], traffic_data.iloc[0]['downstream']],
                    hole=0.3
                )
            ])
            fig.update_layout(title="上行vs下行流量占比")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("流量时长分布")
        duration_data = execute_query("""
            SELECT 
                CASE 
                    WHEN duration < 1000000 THEN '<1秒'
                    WHEN duration < 60000000 THEN '1-60秒'
                    WHEN duration < 3600000000 THEN '1-60分钟'
                    WHEN duration < 86400000000 THEN '1-24小时'
                    ELSE '>24小时'
                END as duration_range,
                COUNT(*) as count
            FROM default.tbl_statistic_userapp_day
            GROUP BY duration_range
            ORDER BY count DESC
        """)
        
        if not duration_data.empty:
            fig = px.bar(duration_data, x='duration_range', y='count', 
                        title='流量时长分布', 
                        labels={'duration_range': '时长范围', 'count': '记录数'})
            st.plotly_chart(fig, use_container_width=True)
    
    # 流量TOP排行
    st.subheader("🏆 流量TOP 20用户")
    top_users = execute_query("""
        SELECT 
            user_account,
            SUM(total_traffic) as total_traffic,
            SUM(upstream_traffic) as upstream,
            SUM(downstream_traffic) as downstream,
            COUNT(*) as sessions
        FROM default.tbl_statistic_userapp_day
        GROUP BY user_account
        ORDER BY total_traffic DESC
        LIMIT 20
    """)
    
    if not top_users.empty:
        # 转换为GB (从byte)
        top_users['total_traffic_gb'] = top_users['total_traffic'] / (1024*1024*1024)
        top_users['upstream_gb'] = top_users['upstream'] / (1024*1024*1024)
        top_users['downstream_gb'] = top_users['downstream'] / (1024*1024*1024)
        
        fig = px.bar(top_users.head(10), x='user_account', y='total_traffic_gb',
                    title='TOP 10用户流量消耗 (GB)',
                    labels={'user_account': '用户账号', 'total_traffic_gb': '总流量(GB)'})
        fig.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(top_users[['user_account', 'total_traffic_gb', 'upstream_gb', 'downstream_gb', 'sessions']])

def show_user_analysis():
    """用户分析页面"""
    st.header("👥 用户分析")
    
    # 用户活跃度分析
    st.subheader("用户活跃度分析")
    user_activity = execute_query("""
        SELECT 
            CASE 
                WHEN session_count = 1 THEN '单次会话'
                WHEN session_count <= 5 THEN '2-5次会话'
                WHEN session_count <= 10 THEN '6-10次会话'
                WHEN session_count <= 20 THEN '11-20次会话'
                ELSE '>20次会话'
            END as activity_level,
            COUNT(*) as user_count
        FROM (
            SELECT user_account, COUNT(*) as session_count
            FROM default.tbl_statistic_userapp_day
            GROUP BY user_account
        ) 
        GROUP BY activity_level
        ORDER BY user_count DESC
    """)
    
    if not user_activity.empty:
        fig = px.pie(user_activity, values='user_count', names='activity_level',
                    title='用户活跃度分布')
        st.plotly_chart(fig, use_container_width=True)
    
    # 用户流量消耗分布
    st.subheader("用户流量消耗分布")
    user_traffic_dist = execute_query("""
        SELECT 
            CASE 
                WHEN total_traffic < 1048576 THEN '<1MB'
                WHEN total_traffic < 10485760 THEN '1-10MB'
                WHEN total_traffic < 104857600 THEN '10-100MB'
                WHEN total_traffic < 1073741824 THEN '100MB-1GB'
                ELSE '>1GB'
            END as traffic_range,
            COUNT(*) as user_count
        FROM (
            SELECT user_account, SUM(total_traffic) as total_traffic
            FROM default.tbl_statistic_userapp_day
            GROUP BY user_account
        )
        GROUP BY traffic_range
        ORDER BY user_count DESC
    """)
    
    if not user_traffic_dist.empty:
        fig = px.bar(user_traffic_dist, x='traffic_range', y='user_count',
                    title='用户流量消耗分布',
                    labels={'traffic_range': '流量范围', 'user_count': '用户数'})
        st.plotly_chart(fig, use_container_width=True)
    
    # 高活跃且上行流量为主的用户分析
    st.subheader("🔍 高活跃上传用户分析")
    st.markdown("**分析条件**: 活跃用户(会话数≥5) + 上行流量>下行流量 + 上行流量≥100MB")
    
    upload_heavy_users = execute_query("""
        SELECT 
            user_account,
            COUNT(*) as session_count,
            SUM(upstream_traffic) as total_upstream,
            SUM(downstream_traffic) as total_downstream,
            SUM(total_traffic) as total_traffic,
            CASE 
                WHEN SUM(downstream_traffic) = 0 THEN 999.99
                ELSE ROUND(SUM(upstream_traffic) / SUM(downstream_traffic), 2)
            END as upload_ratio
        FROM default.tbl_statistic_userapp_day
        GROUP BY user_account
        HAVING session_count >= 5 
            AND total_upstream > total_downstream 
            AND total_upstream >= 104857600
        ORDER BY total_upstream DESC
        LIMIT 20
    """)
    
    if not upload_heavy_users.empty:
        # 数据转换
        upload_heavy_users['upstream_gb'] = upload_heavy_users['total_upstream'] / (1024*1024*1024)
        upload_heavy_users['downstream_gb'] = upload_heavy_users['total_downstream'] / (1024*1024*1024)
        upload_heavy_users['total_gb'] = upload_heavy_users['total_traffic'] / (1024*1024*1024)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 上行流量TOP用户柱状图
            fig = px.bar(upload_heavy_users.head(10), 
                        x='user_account', y='upstream_gb',
                        title='TOP 10高活跃上传用户 - 上行流量',
                        labels={'user_account': '用户账号', 'upstream_gb': '上行流量(GB)'},
                        text='upstream_gb')
            fig.update_traces(texttemplate='%{text:.1f}GB', textposition='outside')
            fig.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 上传比例散点图
            fig = px.scatter(upload_heavy_users, 
                           x='session_count', y='upload_ratio',
                           size='upstream_gb', hover_name='user_account',
                           title='用户活跃度 vs 上传比例',
                           labels={'session_count': '会话数', 'upload_ratio': '上传/下载比例'},
                           color='upstream_gb',
                           color_continuous_scale='Reds')
            fig.update_layout(showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        
        # 详细数据表格
        st.subheader("📋 高活跃上传用户详细数据")
        display_df = upload_heavy_users[['user_account', 'session_count', 'upstream_gb', 
                                       'downstream_gb', 'total_gb', 'upload_ratio']].copy()
        display_df.columns = ['用户账号', '会话数', '上行流量(GB)', '下行流量(GB)', '总流量(GB)', '上传比例']
        
        # 格式化上传比例显示
        display_df['上传比例'] = display_df['上传比例'].apply(
            lambda x: "仅上传" if x >= 999 else f"{x:.1f}:1"
        )
        
        # 添加风险等级（使用原始数值进行判断）
        def get_risk_level(row):
            ratio = upload_heavy_users.loc[row.name, 'upload_ratio'] 
            upstream_gb = row['上行流量(GB)']
            
            if (ratio >= 999 or ratio >= 10) and upstream_gb >= 5:
                return "🔴 高风险"
            elif (ratio >= 999 or ratio >= 5) and upstream_gb >= 1:
                return "🟡 中风险" 
            else:
                return "🟢 低风险"
        
        display_df['风险等级'] = display_df.apply(get_risk_level, axis=1)
        st.dataframe(display_df, use_container_width=True)
        
        # 统计摘要
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("符合条件用户数", len(upload_heavy_users))
        with col2:
            avg_ratio = upload_heavy_users['upload_ratio'].mean()
            st.metric("平均上传比例", f"{avg_ratio:.1f}:1")
        with col3:
            total_upstream = upload_heavy_users['upstream_gb'].sum()
            st.metric("总上行流量", f"{total_upstream:.1f} GB")
        with col4:
            high_risk_count = len(display_df[display_df['风险等级'] == '🔴 高风险'])
            st.metric("高风险用户数", high_risk_count)
        
        st.info("""
        📊 **分析说明**: 
        - **高活跃**: 会话数≥5次，表示用户使用频繁
        - **上传为主**: 上行流量>下行流量，可能涉及内容上传、数据同步等行为
        - **上传比例**: "仅上传"表示下行流量为0，其他显示为上传:下载的比例
        - **风险等级**: 基于上传比例和流量大小综合评估，"仅上传"用户自动视为高风险
        - **业务建议**: 关注高风险用户的使用行为，确保合规使用
        """)
    else:
        st.warning("未找到符合条件的高活跃上传用户")

def show_app_analysis():
    """应用分析页面"""
    st.header("📱 应用分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("应用大类流量TOP 10")
        app_major = execute_query("""
            SELECT 
                app_category_major,
                SUM(total_traffic) as total_traffic,
                COUNT(*) as session_count,
                COUNT(DISTINCT user_account) as user_count
            FROM default.tbl_statistic_userapp_day
            GROUP BY app_category_major
            ORDER BY total_traffic DESC
            LIMIT 10
        """)
        
        if not app_major.empty:
            app_major['total_traffic_gb'] = app_major['total_traffic'] / (1024*1024*1024)  # byte转GB
            # 创建应用类别名称映射
            app_major['app_name'] = app_major['app_category_major'].astype(str) + "类应用"
            
            fig = px.bar(app_major, x='app_name', y='total_traffic_gb',
                        title='应用大类流量消耗TOP 10',
                        labels={'app_name': '应用大类', 'total_traffic_gb': '总流量(GB)'},
                        text='total_traffic_gb')
            fig.update_traces(texttemplate='%{text:.1f}GB', textposition='outside') 
            fig.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
            
    
    with col2:
        st.subheader("应用大类用户数TOP 10")
        if not app_major.empty:
            # 按用户数排序（降序）
            app_major_sorted = app_major.sort_values('user_count', ascending=False)
            # 创建应用类别名称映射
            app_major_sorted['app_name'] = app_major_sorted['app_category_major'].astype(str) + "类应用"
            
            fig = px.bar(app_major_sorted, x='app_name', y='user_count',
                        title='应用大类用户数TOP 10',
                        labels={'app_name': '应用大类', 'user_count': '用户数'},
                        text='user_count')
            fig.update_traces(textposition='outside') 
            fig.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

            
    
    # 应用小类分析
    st.subheader("热门应用小类TOP 20")
    app_minor = execute_query("""
        SELECT 
            app_category_major,
            app_category_minor,
            SUM(total_traffic) as total_traffic,
            COUNT(DISTINCT user_account) as user_count
        FROM default.tbl_statistic_userapp_day
        GROUP BY app_category_major, app_category_minor
        ORDER BY total_traffic DESC
        LIMIT 20
    """)
    
    if not app_minor.empty:
        app_minor['total_traffic_gb'] = app_minor['total_traffic'] / (1024*1024*1024)  # byte转GB
        app_minor['应用标识'] = app_minor['app_category_major'].astype(str) + "-" + app_minor['app_category_minor'].astype(str)
        
        # 重命名列以便更好理解
        display_df = app_minor[['应用标识', 'app_category_major', 'app_category_minor', 'total_traffic_gb', 'user_count']].copy()
        display_df.columns = ['应用标识', '大类编号', '小类编号', '流量(GB)', '用户数']
        st.dataframe(display_df)
        
        st.info("📋 **表格说明**: 应用标识格式为'大类-小类'，如'4-17649'表示大类4下的小类17649应用。")

def show_time_analysis():
    """时间分析页面"""
    st.header("⏰ 时间分析")
    
    st.subheader("数据统计时间分布")
    time_data = execute_query("""
        SELECT 
            stat_time,
            COUNT(*) as record_count,
            SUM(total_traffic) as total_traffic,
            COUNT(DISTINCT user_account) as user_count
        FROM default.tbl_statistic_userapp_day
        GROUP BY stat_time
        ORDER BY stat_time
    """)
    
    if not time_data.empty:
        time_data['total_traffic_gb'] = time_data['total_traffic'] / (1024*1024*1024)  # byte转GB
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=time_data['stat_time'], y=time_data['record_count'],
                                mode='lines+markers', name='记录数'))
        fig.update_layout(title='时间序列记录数变化', 
                         xaxis_title='统计时间', yaxis_title='记录数')
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(time_data)

if __name__ == "__main__":
    main()