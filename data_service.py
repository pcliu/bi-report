#!/usr/bin/env python3
"""
数据服务层
统一管理所有数据查询和分析逻辑，供Web Dashboard和PDF生成使用
"""

import pandas as pd
import clickhouse_connect
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any, List
from datetime import datetime, date


class FilterConditions:
    """筛选条件类"""
    def __init__(self, 
                 user_account: Optional[str] = None,
                 ip_type: Optional[int] = None,  # 0为IPv4, 1为IPv6
                 start_date: Optional[date] = None,
                 end_date: Optional[date] = None,
                 app_category_major: Optional[str] = None):
        self.user_account = user_account
        self.ip_type = ip_type
        self.start_date = start_date
        self.end_date = end_date
        self.app_category_major = app_category_major
    
    def build_where_clause(self) -> str:
        """构建WHERE子句"""
        conditions = []
        
        if self.user_account:
            conditions.append(f"user_account = '{self.user_account}'")
        
        if self.ip_type is not None:
            conditions.append(f"ip_type = {self.ip_type}")
        
        if self.start_date:
            # 转换为数据库期望的格式 'YYYY/M/D H:M'
            start_str = f"{self.start_date.year}/{self.start_date.month}/{self.start_date.day} 0:00"
            conditions.append(f"stat_time >= '{start_str}'")
        
        if self.end_date:
            # 转换为数据库期望的格式 'YYYY/M/D H:M'
            end_str = f"{self.end_date.year}/{self.end_date.month}/{self.end_date.day} 23:59"
            conditions.append(f"stat_time <= '{end_str}'")
        
        if self.app_category_major:
            conditions.append(f"app_category_major = '{self.app_category_major}'")
        
        if conditions:
            return " WHERE " + " AND ".join(conditions)
        return ""
    
    def get_description(self) -> str:
        """获取筛选条件描述"""
        desc_parts = []
        
        if self.user_account:
            desc_parts.append(f"用户: {self.user_account}")
        
        if self.ip_type is not None:
            ip_type_desc = "IPv4" if self.ip_type == 0 else "IPv6"
            desc_parts.append(f"IP类型: {ip_type_desc}")
        
        if self.start_date and self.end_date:
            desc_parts.append(f"日期: {self.start_date} 至 {self.end_date}")
        elif self.start_date:
            desc_parts.append(f"开始日期: {self.start_date}")
        elif self.end_date:
            desc_parts.append(f"结束日期: {self.end_date}")
        
        if self.app_category_major:
            desc_parts.append(f"应用大类: {self.app_category_major}")
        
        if desc_parts:
            return "筛选条件: " + " | ".join(desc_parts)
        return "无筛选条件"


class DataService:
    """统一数据服务层，提供所有分析所需的数据查询方法"""
    
    def __init__(self, host='127.0.0.1', port=8123, username='default', password='12345678'):
        """初始化数据库连接"""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._client = None
    
    @property
    def client(self):
        """获取ClickHouse客户端（懒加载）"""
        if self._client is None:
            try:
                self._client = clickhouse_connect.get_client(
                    host=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password
                )
            except Exception as e:
                raise ConnectionError(f"无法连接到ClickHouse数据库: {str(e)}")
        return self._client
    
    def execute_query(self, query: str) -> pd.DataFrame:
        """执行查询并返回DataFrame"""
        try:
            result = self.client.query_df(query)
            return result
        except Exception as e:
            raise RuntimeError(f"查询执行失败: {str(e)}")
    
    def close(self):
        """关闭数据库连接"""
        if self._client:
            self._client.close()
            self._client = None
    
    # === 基础统计查询 ===
    
    def get_basic_stats(self, filters: Optional[FilterConditions] = None) -> Dict[str, Any]:
        """获取基础统计信息"""
        stats = {}
        where_clause = filters.build_where_clause() if filters else ""
        
        # 总记录数
        total_records = self.execute_query(f"SELECT COUNT(*) as count FROM default.tbl_statistic_userapp_day{where_clause}")
        stats['total_records'] = total_records.iloc[0]['count'] if not total_records.empty else 0
        
        # 用户总数
        total_users = self.execute_query(f"SELECT COUNT(DISTINCT user_account) as count FROM default.tbl_statistic_userapp_day{where_clause}")
        stats['total_users'] = total_users.iloc[0]['count'] if not total_users.empty else 0
        
        # 总流量
        total_traffic = self.execute_query(f"SELECT SUM(total_traffic) as total FROM default.tbl_statistic_userapp_day{where_clause}")
        stats['total_traffic'] = total_traffic.iloc[0]['total'] if not total_traffic.empty else 0
        stats['total_traffic_gb'] = stats['total_traffic'] / (1024*1024*1024)
        
        # 应用大类数
        app_categories = self.execute_query(f"SELECT COUNT(DISTINCT app_category_major) as count FROM default.tbl_statistic_userapp_day{where_clause}")
        stats['app_categories'] = app_categories.iloc[0]['count'] if not app_categories.empty else 0
        
        return stats
    
    # === 流量分析查询 ===
    
    def get_traffic_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取上行vs下行流量分布"""
        where_clause = filters.build_where_clause() if filters else ""
        return self.execute_query(f"""
            SELECT 
                SUM(upstream_traffic) as upstream,
                SUM(downstream_traffic) as downstream
            FROM default.tbl_statistic_userapp_day{where_clause}
        """)
    
    def get_duration_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取流量时长分布"""
        where_clause = filters.build_where_clause() if filters else ""
        return self.execute_query(f"""
            SELECT 
                CASE 
                    WHEN duration < 1000000 THEN '<1秒'
                    WHEN duration < 60000000 THEN '1-60秒'
                    WHEN duration < 3600000000 THEN '1-60分钟'
                    WHEN duration < 86400000000 THEN '1-24小时'
                    ELSE '>24小时'
                END as duration_range,
                COUNT(*) as count
            FROM default.tbl_statistic_userapp_day{where_clause}
            GROUP BY duration_range
            ORDER BY count DESC
        """)
    
    def get_top_traffic_users(self, limit: int = 20, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取流量TOP用户"""
        where_clause = filters.build_where_clause() if filters else ""
        df = self.execute_query(f"""
            SELECT 
                user_account,
                SUM(total_traffic) as total_traffic,
                SUM(upstream_traffic) as upstream,
                SUM(downstream_traffic) as downstream,
                COUNT(*) as sessions
            FROM default.tbl_statistic_userapp_day{where_clause}
            GROUP BY user_account
            ORDER BY total_traffic DESC
            LIMIT {limit}
        """)
        
        if not df.empty:
            df['total_traffic_gb'] = df['total_traffic'] / (1024*1024*1024)
            df['upstream_gb'] = df['upstream'] / (1024*1024*1024)
            df['downstream_gb'] = df['downstream'] / (1024*1024*1024)
        
        return df
    
    # === 用户分析查询 ===
    
    def get_user_activity_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取用户活跃度分布"""
        where_clause = filters.build_where_clause() if filters else ""
        return self.execute_query(f"""
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
                FROM default.tbl_statistic_userapp_day{where_clause}
                GROUP BY user_account
            ) 
            GROUP BY activity_level
            ORDER BY user_count DESC
        """)
    
    def get_user_traffic_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取用户流量消耗分布"""
        where_clause = filters.build_where_clause() if filters else ""
        return self.execute_query(f"""
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
                FROM default.tbl_statistic_userapp_day{where_clause}
                GROUP BY user_account
            )
            GROUP BY traffic_range
            ORDER BY user_count DESC
        """)
    
    def get_upload_heavy_users(self, limit: int = 20, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取高活跃上传用户"""
        where_clause = filters.build_where_clause() if filters else ""
        df = self.execute_query(f"""
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
            FROM default.tbl_statistic_userapp_day{where_clause}
            GROUP BY user_account
            HAVING session_count >= 5 
                AND total_upstream > total_downstream 
                AND total_upstream >= 104857600
            ORDER BY total_upstream DESC
            LIMIT {limit}
        """)
        
        if not df.empty:
            df['upstream_gb'] = df['total_upstream'] / (1024*1024*1024)
            df['downstream_gb'] = df['total_downstream'] / (1024*1024*1024)
            df['total_gb'] = df['total_traffic'] / (1024*1024*1024)
        
        return df
    
    # === 应用分析查询 ===
    
    def get_app_major_analysis(self, limit: int = 10, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取应用大类分析数据"""
        where_clause = filters.build_where_clause() if filters else ""
        df = self.execute_query(f"""
            SELECT 
                app_category_major,
                SUM(total_traffic) as total_traffic,
                COUNT(*) as session_count,
                COUNT(DISTINCT user_account) as user_count
            FROM default.tbl_statistic_userapp_day{where_clause}
            GROUP BY app_category_major
            ORDER BY total_traffic DESC
            LIMIT {limit}
        """)
        
        if not df.empty:
            df['total_traffic_gb'] = df['total_traffic'] / (1024*1024*1024)
            df['app_name'] = df['app_category_major'].astype(str) + "类应用"
        
        return df
    
    def get_app_minor_analysis(self, limit: int = 20, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取应用小类分析数据"""
        where_clause = filters.build_where_clause() if filters else ""
        df = self.execute_query(f"""
            SELECT 
                app_category_major,
                app_category_minor,
                SUM(total_traffic) as total_traffic,
                COUNT(DISTINCT user_account) as user_count
            FROM default.tbl_statistic_userapp_day{where_clause}
            GROUP BY app_category_major, app_category_minor
            ORDER BY total_traffic DESC
            LIMIT {limit}
        """)
        
        if not df.empty:
            df['total_traffic_gb'] = df['total_traffic'] / (1024*1024*1024)
            df['应用标识'] = df['app_category_major'].astype(str) + "-" + df['app_category_minor'].astype(str)
        
        return df
    
    # === 时间分析查询 ===
    
    def get_time_analysis(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取时间分析数据"""
        where_clause = filters.build_where_clause() if filters else ""
        df = self.execute_query(f"""
            SELECT 
                stat_time,
                COUNT(*) as record_count,
                SUM(total_traffic) as total_traffic,
                COUNT(DISTINCT user_account) as user_count
            FROM default.tbl_statistic_userapp_day{where_clause}
            GROUP BY stat_time
            ORDER BY stat_time
        """)
        
        if not df.empty:
            df['total_traffic_gb'] = df['total_traffic'] / (1024*1024*1024)
        
        return df
    
    # === 图表生成方法 ===
    
    def create_traffic_pie_chart(self, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建上行vs下行流量饼图"""
        traffic_data = self.get_traffic_distribution(filters)
        if traffic_data.empty:
            return None
        
        fig = go.Figure(data=[
            go.Pie(
                labels=['上行流量', '下行流量'],
                values=[traffic_data.iloc[0]['upstream'], traffic_data.iloc[0]['downstream']],
                hole=0.3,
                marker=dict(colors=['#FF6B6B', '#4ECDC4'])
            )
        ])
        fig.update_layout(
            title="上行vs下行流量占比", 
            font=dict(size=14),
            showlegend=True
        )
        return fig
    
    def create_duration_bar_chart(self, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建流量时长分布柱状图"""
        duration_data = self.get_duration_distribution(filters)
        if duration_data.empty:
            return None
        
        fig = px.bar(duration_data, x='duration_range', y='count', 
                    title='流量时长分布', 
                    labels={'duration_range': '时长范围', 'count': '记录数'},
                    color='count',
                    color_continuous_scale='Blues')
        fig.update_layout(font=dict(size=12), showlegend=False)
        return fig
    
    def create_top_users_bar_chart(self, limit: int = 10, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建TOP用户流量柱状图"""
        top_users = self.get_top_traffic_users(limit, filters)
        if top_users.empty:
            return None
        
        fig = px.bar(top_users.head(limit), x='user_account', y='total_traffic_gb',
                    title=f'TOP {limit}用户流量消耗 (GB)',
                    labels={'user_account': '用户账号', 'total_traffic_gb': '总流量(GB)'},
                    color='total_traffic_gb',
                    color_continuous_scale='Reds')
        fig.update_layout(xaxis_tickangle=45, font=dict(size=10), showlegend=False)
        return fig
    
    def create_user_activity_pie_chart(self, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建用户活跃度分布饼图"""
        user_activity = self.get_user_activity_distribution(filters)
        if user_activity.empty:
            return None
        
        fig = px.pie(user_activity, values='user_count', names='activity_level',
                    title='用户活跃度分布',
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57'])
        fig.update_layout(font=dict(size=12), showlegend=True)
        return fig
    
    def create_user_traffic_bar_chart(self, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建用户流量消耗分布柱状图"""
        user_traffic_dist = self.get_user_traffic_distribution(filters)
        if user_traffic_dist.empty:
            return None
        
        fig = px.bar(user_traffic_dist, x='traffic_range', y='user_count',
                    title='用户流量消耗分布',
                    labels={'traffic_range': '流量范围', 'user_count': '用户数'},
                    color='user_count',
                    color_continuous_scale='Greens')
        fig.update_layout(font=dict(size=12), showlegend=False)
        return fig
    
    def create_upload_users_bar_chart(self, limit: int = 10, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建高活跃上传用户柱状图"""
        upload_heavy_users = self.get_upload_heavy_users(limit, filters)
        if upload_heavy_users.empty:
            return None
        
        fig = px.bar(upload_heavy_users.head(limit), 
                    x='user_account', y='upstream_gb',
                    title='高活跃上传用户 - 上行流量',
                    labels={'user_account': '用户账号', 'upstream_gb': '上行流量(GB)'},
                    color='upstream_gb',
                    color_continuous_scale='Oranges')
        fig.update_layout(xaxis_tickangle=45, font=dict(size=10), showlegend=False)
        return fig
    
    def create_upload_ratio_scatter_chart(self, limit: int = 20, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建上传比例散点图"""
        upload_heavy_users = self.get_upload_heavy_users(limit, filters)
        if upload_heavy_users.empty:
            return None
        
        fig = px.scatter(upload_heavy_users, 
                       x='session_count', y='upload_ratio',
                       size='upstream_gb', hover_name='user_account',
                       title='用户活跃度 vs 上传比例',
                       labels={'session_count': '会话数', 'upload_ratio': '上传/下载比例'},
                       color='upstream_gb',
                       color_continuous_scale='Reds')
        fig.update_layout(font=dict(size=12))
        return fig
    
    def create_app_traffic_bar_chart(self, limit: int = 10, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建应用大类流量柱状图"""
        app_major = self.get_app_major_analysis(limit, filters)
        if app_major.empty:
            return None
        
        fig = px.bar(app_major, x='app_name', y='total_traffic_gb',
                    title='应用大类流量消耗TOP 10',
                    labels={'app_name': '应用大类', 'total_traffic_gb': '总流量(GB)'},
                    color='total_traffic_gb',
                    color_continuous_scale='Viridis')
        fig.update_layout(xaxis_tickangle=45, font=dict(size=12), showlegend=False)
        return fig
    
    def create_app_users_bar_chart(self, limit: int = 10, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建应用大类用户数柱状图"""
        app_major = self.get_app_major_analysis(limit, filters)
        if app_major.empty:
            return None
        
        app_major_sorted = app_major.sort_values('user_count', ascending=False)
        fig = px.bar(app_major_sorted, x='app_name', y='user_count',
                    title='应用大类用户数TOP 10',
                    labels={'app_name': '应用大类', 'user_count': '用户数'},
                    color='user_count',
                    color_continuous_scale='Plasma')
        fig.update_layout(xaxis_tickangle=45, font=dict(size=12), showlegend=False)
        return fig
    
    def create_time_series_chart(self, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建时间序列图"""
        time_data = self.get_time_analysis(filters)
        if time_data.empty:
            return None
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=time_data['stat_time'], y=time_data['record_count'],
                                mode='lines+markers', name='记录数',
                                line=dict(color='#3498db', width=3),
                                marker=dict(color='#e74c3c', size=8)))
        fig.update_layout(title='时间序列记录数变化', 
                         xaxis_title='统计时间', yaxis_title='记录数',
                         font=dict(size=12),
                         showlegend=True)
        return fig
    
    # === 辅助方法 ===
    
    def get_available_users(self, limit: int = 100) -> List[str]:
        """获取可用的用户账号列表"""
        df = self.execute_query(f"""
            SELECT DISTINCT user_account 
            FROM default.tbl_statistic_userapp_day 
            ORDER BY user_account 
            LIMIT {limit}
        """)
        return df['user_account'].tolist() if not df.empty else []
    
    def get_available_app_categories(self) -> List[str]:
        """获取可用的应用大类列表"""
        df = self.execute_query("""
            SELECT DISTINCT app_category_major 
            FROM default.tbl_statistic_userapp_day 
            ORDER BY app_category_major
        """)
        return df['app_category_major'].astype(str).tolist() if not df.empty else []
    
    def get_date_range(self) -> Dict[str, date]:
        """获取数据的日期范围"""
        df = self.execute_query("""
            SELECT 
                MIN(stat_time) as min_date,
                MAX(stat_time) as max_date
            FROM default.tbl_statistic_userapp_day
        """)
        if df.empty:
            return {'min_date': None, 'max_date': None}
        
        return {
            'min_date': df.iloc[0]['min_date'],
            'max_date': df.iloc[0]['max_date']
        }