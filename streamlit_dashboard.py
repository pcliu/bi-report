#!/usr/bin/env python3
"""
ClickHouse数据可视化Dashboard
基于Streamlit构建的互动式数据分析报表
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import clickhouse_connect
from datetime import datetime
import numpy as np

# 页面配置
st.set_page_config(
    page_title="用户流量分析Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 连接ClickHouse的函数
@st.cache_resource
def get_clickhouse_client():
    """获取ClickHouse客户端连接"""
    try:
        client = clickhouse_connect.get_client(
            host='127.0.0.1',
            port=8123,
            username='default',
            password='12345678'
        )
        return client
    except Exception as e:
        st.error(f"无法连接到ClickHouse数据库: {str(e)}")
        return None

# 执行查询的函数
@st.cache_data(ttl=300)  # 缓存5分钟
def execute_query(query):
    """执行ClickHouse查询并返回DataFrame"""
    client = get_clickhouse_client()
    if client is None:
        return pd.DataFrame()
    
    try:
        result = client.query_df(query)
        return result
    except Exception as e:
        st.error(f"查询执行失败: {str(e)}")
        return pd.DataFrame()

# 主页面
def main():
    st.title("📊 用户流量分析Dashboard")
    st.markdown("---")
    
    # 侧边栏
    st.sidebar.title("🎛️ 控制面板")
    
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