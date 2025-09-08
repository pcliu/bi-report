#!/usr/bin/env python3
"""
CSV数据服务层
统一管理所有数据查询和分析逻辑，从CSV文件读取数据替代ClickHouse数据库
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import os
import glob
from pathlib import Path


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
    
    def apply_to_dataframe(self, df: pd.DataFrame, app_major_mapping: Dict[str, int] = None) -> pd.DataFrame:
        """将筛选条件应用到DataFrame"""
        filtered_df = df.copy()
        
        if self.user_account:
            filtered_df = filtered_df[filtered_df['user_account'] == self.user_account]
        
        if self.ip_type is not None:
            filtered_df = filtered_df[filtered_df['ip_type'] == self.ip_type]
        
        # 日期筛选
        if self.start_date or self.end_date:
            # 确保stat_time列是日期类型
            if 'stat_time' in filtered_df.columns:
                filtered_df['stat_date'] = pd.to_datetime(filtered_df['stat_time']).dt.date
                
                if self.start_date and self.end_date:
                    filtered_df = filtered_df[
                        (filtered_df['stat_date'] >= self.start_date) & 
                        (filtered_df['stat_date'] <= self.end_date)
                    ]
                elif self.start_date:
                    filtered_df = filtered_df[filtered_df['stat_date'] >= self.start_date]
                elif self.end_date:
                    filtered_df = filtered_df[filtered_df['stat_date'] <= self.end_date]
        
        if self.app_category_major and app_major_mapping:
            # 如果是数字，直接按ID筛选；如果是文本，按名称筛选
            if self.app_category_major.isdigit():
                filtered_df = filtered_df[filtered_df['app_category_major'] == int(self.app_category_major)]
            else:
                # 按名称筛选，查找对应的ID
                category_id = app_major_mapping.get(self.app_category_major)
                if category_id:
                    filtered_df = filtered_df[filtered_df['app_category_major'] == category_id]
        
        return filtered_df
    
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


class CSVDataService:
    """基于CSV文件的数据服务层，提供所有分析所需的数据查询方法"""
    
    def __init__(self, data_folder: str = "./data"):
        """初始化CSV数据服务
        
        Args:
            data_folder: 包含CSV文件的文件夹路径
        """
        self.data_folder = Path(data_folder)
        self._main_data = None
        self._app_major_categories = None
        self._app_minor_categories = None
        self._app_major_mapping = None
        self._app_minor_mapping = None
        
        # 确保数据文件夹存在
        if not self.data_folder.exists():
            self.data_folder.mkdir(parents=True, exist_ok=True)
    
    def _load_main_data(self) -> pd.DataFrame:
        """加载主数据文件"""
        if self._main_data is not None:
            return self._main_data
        
        # 查找主数据文件（支持通配符匹配）
        main_data_patterns = [
            "tbl_statistic_userapp_day*.csv",
            "main_data.csv",
            "traffic_data.csv"
        ]
        
        main_data_file = None
        for pattern in main_data_patterns:
            files = list(self.data_folder.glob(pattern))
            if files:
                # 选择最新的文件
                main_data_file = max(files, key=lambda x: x.stat().st_mtime)
                break
        
        if not main_data_file:
            # 如果当前目录没有找到，尝试当前工作目录
            for pattern in main_data_patterns:
                files = list(Path(".").glob(pattern))
                if files:
                    main_data_file = max(files, key=lambda x: x.stat().st_mtime)
                    break
        
        if not main_data_file:
            raise FileNotFoundError(f"在 {self.data_folder} 中未找到主数据文件")
        
        print(f"加载主数据文件: {main_data_file}")
        
        # 读取CSV文件，根据是否有标题行决定处理方式
        try:
            # 先尝试读取第一行判断格式
            sample = pd.read_csv(main_data_file, nrows=1)
            
            # 如果第一行看起来像数据而不是标题，则没有标题行
            if sample.iloc[0, 0].startswith('"') or str(sample.iloc[0, 0]).replace('@', '').replace('.', '').isalnum():
                # 没有标题行，手动指定列名
                column_names = [
                    'user_account', 'ip_type', 'app_category_major', 'app_category_minor',
                    'upstream_traffic', 'downstream_traffic', 'total_traffic', 'duration', 'stat_time'
                ]
                self._main_data = pd.read_csv(main_data_file, names=column_names, header=None)
            else:
                # 有标题行，使用现有的列名映射逻辑
                df = pd.read_csv(main_data_file)
                column_mapping = {
                    '用户账号': 'user_account',
                    'IP类型': 'ip_type',
                    '应用大类编号': 'app_category_major',
                    '应用小类编号': 'app_category_minor',
                    '上行流量': 'upstream_traffic',
                    '下行流量': 'downstream_traffic',
                    '上下行总流量': 'total_traffic',
                    '流量时长': 'duration',
                    '统计时间': 'stat_time'
                }
                self._main_data = df.rename(columns=column_mapping)
        except Exception as e:
            print(f"读取文件时出错，尝试无标题行模式: {e}")
            column_names = [
                'user_account', 'ip_type', 'app_category_major', 'app_category_minor',
                'upstream_traffic', 'downstream_traffic', 'total_traffic', 'duration', 'stat_time'
            ]
            self._main_data = pd.read_csv(main_data_file, names=column_names, header=None)
        
        # 数据类型转换
        self._main_data['ip_type'] = pd.to_numeric(self._main_data['ip_type'], errors='coerce').fillna(0).astype(int)
        self._main_data['app_category_major'] = pd.to_numeric(self._main_data['app_category_major'], errors='coerce').fillna(0).astype(int)
        self._main_data['app_category_minor'] = pd.to_numeric(self._main_data['app_category_minor'], errors='coerce').fillna(0).astype(int)
        
        # 流量和时长转换为数值
        traffic_columns = ['upstream_traffic', 'downstream_traffic', 'total_traffic', 'duration']
        for col in traffic_columns:
            self._main_data[col] = pd.to_numeric(self._main_data[col], errors='coerce').fillna(0.0)
        
        # 清理用户账号中的引号
        if 'user_account' in self._main_data.columns:
            self._main_data['user_account'] = self._main_data['user_account'].astype(str).str.strip('"')
        
        # 时间格式转换
        if 'stat_time' in self._main_data.columns:
            self._main_data['stat_time'] = self._main_data['stat_time'].astype(str).str.strip('"')
            # 尝试转换为日期时间
            try:
                self._main_data['stat_datetime'] = pd.to_datetime(self._main_data['stat_time'])
            except:
                print("警告：无法解析统计时间格式")
        
        print(f"成功加载 {len(self._main_data)} 行主数据")
        return self._main_data
    
    def _load_app_categories(self):
        """加载应用分类数据"""
        if self._app_major_categories is not None:
            return
        
        # 加载应用大类
        major_file_patterns = ["app_catagory_major.csv", "app_category_major.csv", "major_categories.csv"]
        major_file = None
        for pattern in major_file_patterns:
            file_path = self.data_folder / pattern
            if file_path.exists():
                major_file = file_path
                break
            # 也尝试当前目录
            file_path = Path(pattern)
            if file_path.exists():
                major_file = file_path
                break
        
        if major_file:
            print(f"加载应用大类文件: {major_file}")
            self._app_major_categories = pd.read_csv(major_file, names=['id', 'name'], header=None)
            self._app_major_mapping = dict(zip(self._app_major_categories['name'], self._app_major_categories['id']))
        else:
            print("警告：未找到应用大类文件，将使用ID作为名称")
            self._app_major_categories = pd.DataFrame(columns=['id', 'name'])
            self._app_major_mapping = {}
        
        # 加载应用小类
        minor_file_patterns = ["app_catagory_minor.csv", "app_category_minor.csv", "minor_categories.csv"]
        minor_file = None
        for pattern in minor_file_patterns:
            file_path = self.data_folder / pattern
            if file_path.exists():
                minor_file = file_path
                break
            # 也尝试当前目录
            file_path = Path(pattern)
            if file_path.exists():
                minor_file = file_path
                break
        
        if minor_file:
            print(f"加载应用小类文件: {minor_file}")
            self._app_minor_categories = pd.read_csv(minor_file, names=['id', 'name'], header=None)
            self._app_minor_mapping = dict(zip(self._app_minor_categories['name'], self._app_minor_categories['id']))
        else:
            print("警告：未找到应用小类文件，将使用ID作为名称")
            self._app_minor_categories = pd.DataFrame(columns=['id', 'name'])
            self._app_minor_mapping = {}
    
    def get_data(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取筛选后的数据"""
        main_data = self._load_main_data()
        self._load_app_categories()
        
        if filters:
            return filters.apply_to_dataframe(main_data, self._app_major_mapping)
        return main_data
    
    # === 基础统计查询 ===
    
    def get_basic_stats(self, filters: Optional[FilterConditions] = None) -> Dict[str, Any]:
        """获取基础统计信息"""
        df = self.get_data(filters)
        
        stats = {
            'total_records': len(df),
            'total_users': df['user_account'].nunique() if 'user_account' in df.columns else 0,
            'total_traffic': df['total_traffic'].sum() if 'total_traffic' in df.columns else 0,
            'app_categories': df['app_category_major'].nunique() if 'app_category_major' in df.columns else 0
        }
        
        stats['total_traffic_gb'] = stats['total_traffic'] / (1024*1024*1024)
        return stats
    
    # === 流量分析查询 ===
    
    def get_traffic_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取上行vs下行流量分布"""
        df = self.get_data(filters)
        
        result = pd.DataFrame({
            'upstream': [df['upstream_traffic'].sum()],
            'downstream': [df['downstream_traffic'].sum()]
        })
        return result
    
    def get_duration_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取流量时长分布"""
        df = self.get_data(filters)
        
        def duration_category(duration):
            if duration < 1000000:
                return '<1秒'
            elif duration < 60000000:
                return '1-60秒'
            elif duration < 3600000000:
                return '1-60分钟'
            elif duration < 86400000000:
                return '1-24小时'
            else:
                return '>24小时'
        
        df['duration_range'] = df['duration'].apply(duration_category)
        result = df['duration_range'].value_counts().reset_index()
        result.columns = ['duration_range', 'count']
        return result.sort_values('count', ascending=False)
    
    def get_top_traffic_users(self, limit: int = 20, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取流量TOP用户"""
        df = self.get_data(filters)
        
        user_stats = df.groupby('user_account').agg({
            'total_traffic': 'sum',
            'upstream_traffic': 'sum',
            'downstream_traffic': 'sum',
            'user_account': 'count'  # 用于统计会话数
        }).rename(columns={'user_account': 'sessions'})
        
        user_stats = user_stats.sort_values('total_traffic', ascending=False).head(limit)
        user_stats = user_stats.reset_index()
        
        # 添加GB单位的列
        user_stats['total_traffic_gb'] = user_stats['total_traffic'] / (1024*1024*1024)
        user_stats['upstream_gb'] = user_stats['upstream_traffic'] / (1024*1024*1024)
        user_stats['downstream_gb'] = user_stats['downstream_traffic'] / (1024*1024*1024)
        
        return user_stats
    
    # === 用户分析查询 ===
    
    def get_user_activity_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取用户活跃度分布"""
        df = self.get_data(filters)
        
        user_sessions = df.groupby('user_account').size().reset_index(name='session_count')
        
        def activity_category(count):
            if count == 1:
                return '单次会话'
            elif count <= 5:
                return '2-5次会话'
            elif count <= 10:
                return '6-10次会话'
            elif count <= 20:
                return '11-20次会话'
            else:
                return '>20次会话'
        
        user_sessions['activity_level'] = user_sessions['session_count'].apply(activity_category)
        result = user_sessions['activity_level'].value_counts().reset_index()
        result.columns = ['activity_level', 'user_count']
        return result.sort_values('user_count', ascending=False)
    
    def get_user_traffic_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取用户流量消耗分布"""
        df = self.get_data(filters)
        
        user_traffic = df.groupby('user_account')['total_traffic'].sum().reset_index()
        
        def traffic_category(traffic):
            if traffic < 1048576:  # <1MB
                return '<1MB'
            elif traffic < 10485760:  # 1-10MB
                return '1-10MB'
            elif traffic < 104857600:  # 10-100MB
                return '10-100MB'
            elif traffic < 1073741824:  # 100MB-1GB
                return '100MB-1GB'
            else:
                return '>1GB'
        
        user_traffic['traffic_range'] = user_traffic['total_traffic'].apply(traffic_category)
        result = user_traffic['traffic_range'].value_counts().reset_index()
        result.columns = ['traffic_range', 'user_count']
        return result.sort_values('user_count', ascending=False)
    
    def get_upload_heavy_users(self, limit: int = 20, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取高活跃上传用户"""
        df = self.get_data(filters)
        
        user_stats = df.groupby('user_account').agg({
            'upstream_traffic': 'sum',
            'downstream_traffic': 'sum',
            'total_traffic': 'sum',
            'user_account': 'count'
        }).rename(columns={'user_account': 'session_count'})
        
        # 筛选高活跃上传用户
        high_upload = user_stats[
            (user_stats['session_count'] >= 5) &
            (user_stats['upstream_traffic'] > user_stats['downstream_traffic']) &
            (user_stats['upstream_traffic'] >= 104857600)  # 100MB
        ]
        
        # 计算上传比例
        high_upload['upload_ratio'] = high_upload['upstream_traffic'] / high_upload['downstream_traffic'].replace(0, 1)
        high_upload['upload_ratio'] = high_upload['upload_ratio'].replace([float('inf')], 999.99).round(2)
        
        result = high_upload.sort_values('upstream_traffic', ascending=False).head(limit).reset_index()
        result.rename(columns={'upstream_traffic': 'total_upstream', 'downstream_traffic': 'total_downstream'}, inplace=True)
        
        # 添加GB单位
        result['upstream_gb'] = result['total_upstream'] / (1024*1024*1024)
        result['downstream_gb'] = result['total_downstream'] / (1024*1024*1024)
        result['total_gb'] = result['total_traffic'] / (1024*1024*1024)
        
        return result
    
    # === 应用分析查询 ===
    
    def get_app_major_analysis(self, limit: int = 10, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取应用大类分析数据（仅上行流量）"""
        df = self.get_data(filters)
        self._load_app_categories()
        
        # 计算总上行流量用于百分比计算
        total_upstream = df['upstream_traffic'].sum()
        
        # 按应用大类分组统计
        app_stats = df.groupby('app_category_major').agg({
            'upstream_traffic': 'sum',
            'user_account': ['count', 'nunique']
        }).reset_index()
        
        app_stats.columns = ['app_category_major', 'upstream_traffic', 'session_count', 'user_count']
        app_stats = app_stats.sort_values('upstream_traffic', ascending=False).head(limit)
        
        # 添加应用名称
        if not self._app_major_categories.empty:
            major_name_map = dict(zip(self._app_major_categories['id'], self._app_major_categories['name']))
            app_stats['major_name'] = app_stats['app_category_major'].map(major_name_map)
        else:
            app_stats['major_name'] = None
        
        app_stats['app_name'] = app_stats['major_name'].fillna(app_stats['app_category_major'].astype(str) + "类应用")
        
        # 计算GB和百分比
        app_stats['upstream_traffic_gb'] = app_stats['upstream_traffic'] / (1024*1024*1024)
        app_stats['upstream_percentage'] = (app_stats['upstream_traffic'] / total_upstream * 100) if total_upstream > 0 else 0
        
        return app_stats
    
    def get_app_minor_analysis(self, limit: int = 20, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取应用小类分析数据（仅上行流量）"""
        df = self.get_data(filters)
        self._load_app_categories()
        
        # 计算总上行流量用于百分比计算
        total_upstream = df['upstream_traffic'].sum()
        
        # 按应用小类分组统计
        app_stats = df.groupby(['app_category_major', 'app_category_minor']).agg({
            'upstream_traffic': 'sum',
            'user_account': 'nunique'
        }).reset_index()
        
        app_stats.columns = ['app_category_major', 'app_category_minor', 'upstream_traffic', 'user_count']
        app_stats = app_stats.sort_values('upstream_traffic', ascending=False).head(limit)
        
        # 添加应用名称
        if not self._app_major_categories.empty:
            major_name_map = dict(zip(self._app_major_categories['id'], self._app_major_categories['name']))
            app_stats['major_name'] = app_stats['app_category_major'].map(major_name_map)
        else:
            app_stats['major_name'] = None
            
        if not self._app_minor_categories.empty:
            minor_name_map = dict(zip(self._app_minor_categories['id'], self._app_minor_categories['name']))
            app_stats['minor_name'] = app_stats['app_category_minor'].map(minor_name_map)
        else:
            app_stats['minor_name'] = None
        
        # 生成显示名称
        app_stats['major_display'] = app_stats['major_name'].fillna(app_stats['app_category_major'].astype(str))
        app_stats['minor_display'] = app_stats['minor_name'].fillna(app_stats['app_category_minor'].astype(str))
        app_stats['应用名称'] = app_stats['major_display'] + " - " + app_stats['minor_display']
        app_stats['应用标识'] = app_stats['app_category_major'].astype(str) + "-" + app_stats['app_category_minor'].astype(str)
        
        # 计算GB和百分比
        app_stats['upstream_traffic_gb'] = app_stats['upstream_traffic'] / (1024*1024*1024)
        app_stats['upstream_percentage'] = (app_stats['upstream_traffic'] / total_upstream * 100) if total_upstream > 0 else 0
        
        return app_stats
    
    def get_app_category_top_users(self, limit_categories: int = 10, limit_users: int = 10, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取应用大类TOP10及每个大类中TOP10用户的详细分析"""
        df = self.get_data(filters)
        self._load_app_categories()
        
        # 首先获取上行流量TOP10的应用大类
        top_categories = df.groupby('app_category_major')['upstream_traffic'].sum().reset_index()
        top_categories = top_categories.sort_values('upstream_traffic', ascending=False).head(limit_categories)
        
        if top_categories.empty:
            return pd.DataFrame()
        
        all_results = []
        
        for _, category_row in top_categories.iterrows():
            category_id = category_row['app_category_major']
            category_total_traffic = category_row['upstream_traffic']
            
            # 获取分类名称
            if not self._app_major_categories.empty:
                category_name = self._app_major_categories[self._app_major_categories['id'] == category_id]['name']
                category_name = category_name.iloc[0] if not category_name.empty else f"应用{category_id}"
            else:
                category_name = f"应用{category_id}"
            
            # 获取该大类中的TOP用户
            category_users = df[df['app_category_major'] == category_id].groupby('user_account').agg({
                'upstream_traffic': 'sum',
                'downstream_traffic': 'sum',
                'total_traffic': 'sum',
                'user_account': 'count'
            }).rename(columns={'user_account': 'session_count'}).reset_index()
            
            category_users = category_users.sort_values('upstream_traffic', ascending=False).head(limit_users)
            
            if not category_users.empty:
                # 添加类别信息
                category_users['app_category_major'] = category_id
                category_users['category_name'] = category_name
                category_users['category_total_traffic'] = category_total_traffic
                category_users['user_traffic_percentage'] = (category_users['upstream_traffic'] / category_total_traffic * 100) if category_total_traffic > 0 else 0
                
                # 转换单位为GB
                category_users['user_upstream_gb'] = category_users['upstream_traffic'] / (1024*1024*1024)
                category_users['user_downstream_gb'] = category_users['downstream_traffic'] / (1024*1024*1024)  
                category_users['user_total_gb'] = category_users['total_traffic'] / (1024*1024*1024)
                
                # 重命名列以匹配原有接口
                category_users = category_users.rename(columns={
                    'upstream_traffic': 'user_upstream_traffic',
                    'downstream_traffic': 'user_downstream_traffic', 
                    'total_traffic': 'user_total_traffic'
                })
                
                all_results.append(category_users)
        
        if all_results:
            return pd.concat(all_results, ignore_index=True)
        else:
            return pd.DataFrame()
    
    # === 时间分析查询 ===
    
    def get_time_analysis(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取时间分析数据"""
        df = self.get_data(filters)
        
        # 确保有时间列
        if 'stat_time' not in df.columns:
            return pd.DataFrame()
        
        time_stats = df.groupby('stat_time').agg({
            'user_account': ['count', 'nunique'],
            'total_traffic': 'sum'
        }).reset_index()
        
        time_stats.columns = ['stat_time', 'record_count', 'user_count', 'total_traffic']
        time_stats['total_traffic_gb'] = time_stats['total_traffic'] / (1024*1024*1024)
        
        return time_stats.sort_values('stat_time')
    
    def get_flexible_time_analysis(self, 
                                 group_by_field: str = 'none',
                                 metric_type: str = 'session_count',
                                 traffic_type: str = 'total',
                                 filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取灵活的时间分析数据"""
        df = self.get_data(filters)
        self._load_app_categories()
        
        if df.empty or 'stat_time' not in df.columns:
            return pd.DataFrame()
        
        # 确保有日期字段
        if 'stat_datetime' not in df.columns:
            df['stat_datetime'] = pd.to_datetime(df['stat_time'], errors='coerce')
        
        df['date_key'] = df['stat_datetime'].dt.date
        
        # 根据分组字段准备数据
        if group_by_field == 'none':
            df['category'] = '总体'
        elif group_by_field == 'ip_type':
            df['category'] = df['ip_type'].apply(lambda x: 'IPv4' if x == 0 else 'IPv6')
        elif group_by_field == 'app_category_major':
            # 添加应用大类名称
            if not self._app_major_categories.empty:
                major_name_map = dict(zip(self._app_major_categories['id'], self._app_major_categories['name']))
                df['category'] = df['app_category_major'].map(major_name_map).fillna(df['app_category_major'].astype(str) + '类应用')
            else:
                df['category'] = df['app_category_major'].astype(str) + '类应用'
        elif group_by_field == 'user_account':
            # 只显示TOP用户避免过多线条
            top_users = df.groupby('user_account')['total_traffic'].sum().nlargest(10).index
            df = df[df['user_account'].isin(top_users)]
            df['category'] = df['user_account']
        else:
            df['category'] = '总体'
        
        # 构建聚合指标
        if metric_type == 'session_count':
            agg_func = {'user_account': 'count'}
            metric_col = 'user_account'
        elif metric_type == 'traffic':
            if traffic_type == 'upstream':
                agg_func = {'upstream_traffic': 'sum'}
                metric_col = 'upstream_traffic'
            elif traffic_type == 'downstream':  
                agg_func = {'downstream_traffic': 'sum'}
                metric_col = 'downstream_traffic'
            else:  # total
                agg_func = {'total_traffic': 'sum'}
                metric_col = 'total_traffic'
        elif metric_type == 'session_duration':
            agg_func = {'duration': 'mean'}
            metric_col = 'duration'
        else:
            agg_func = {'user_account': 'count'}
            metric_col = 'user_account'
        
        # 按日期和类别分组聚合
        if group_by_field == 'none':
            result = df.groupby('date_key').agg(agg_func).reset_index()
            result['value'] = result[metric_col]
        else:
            result = df.groupby(['date_key', 'category']).agg(agg_func).reset_index()
            result['value'] = result[metric_col]
        
        # 流量单位转换为GB
        if metric_type == 'traffic':
            result['value'] = result['value'] / (1024*1024*1024)
        elif metric_type == 'session_duration':
            result['value'] = result['value'] / 1000000  # 转换为秒
        
        return result.sort_values('date_key')
    
    def create_flexible_time_chart(self, 
                                 group_by_field: str = 'none',
                                 metric_type: str = 'session_count',
                                 traffic_type: str = 'total',
                                 filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建灵活的时间分析图表"""
        time_data = self.get_flexible_time_analysis(group_by_field, metric_type, traffic_type, filters)
        if time_data.empty:
            return None
        
        # 构建图表标题和轴标签
        group_labels = {
            'none': '总体',
            'ip_type': 'IP类型',
            'app_category_major': '应用大类',
            'user_account': '用户'
        }
        
        metric_labels = {
            'session_count': '会话数',
            'traffic': '流量(GB)',
            'session_duration': '平均会话时长(秒)'
        }
        
        traffic_labels = {
            'total': '总流量',
            'upstream': '上行流量', 
            'downstream': '下行流量'
        }
        
        # 构建标题
        group_label = group_labels.get(group_by_field, '总体')
        if metric_type == 'traffic':
            metric_label = traffic_labels.get(traffic_type, '总流量')
        else:
            metric_label = metric_labels.get(metric_type, '会话数')
        
        if group_by_field == 'none':
            title = f'时间趋势 - {metric_label}'
        else:
            title = f'时间趋势 - {metric_label} (按{group_label}分组)'
        
        # 创建图表
        fig = go.Figure()
        
        # 如果有分组，创建多条线
        if 'category' in time_data.columns and group_by_field != 'none':
            categories = time_data['category'].unique()
            colors = px.colors.qualitative.Set1
            
            for i, category in enumerate(categories):
                category_data = time_data[time_data['category'] == category]
                color = colors[i % len(colors)]
                
                fig.add_trace(go.Scatter(
                    x=category_data['date_key'],
                    y=category_data['value'],
                    mode='lines+markers',
                    name=str(category),
                    line=dict(color=color, width=2),
                    marker=dict(color=color, size=6)
                ))
        else:
            # 单条线
            fig.add_trace(go.Scatter(
                x=time_data['date_key'],
                y=time_data['value'],
                mode='lines+markers',
                name=metric_label,
                line=dict(color='#3498db', width=3),
                marker=dict(color='#e74c3c', size=8)
            ))
        
        # 更新布局
        fig.update_layout(
            title=title,
            xaxis_title='日期',
            yaxis_title=metric_labels.get(metric_type, '值'),
            font=dict(size=12),
            showlegend=True if 'category' in time_data.columns and len(time_data['category'].unique()) > 1 and group_by_field != 'none' else False,
            hovermode='x unified'
        )
        
        return fig
    
    def get_ip_type_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取IPv4和IPv6分布"""
        df = self.get_data(filters)
        
        def ip_type_name(ip_type):
            if ip_type == 0:
                return 'IPv4'
            elif ip_type == 1:
                return 'IPv6'
            else:
                return 'Unknown'
        
        ip_stats = df.groupby('ip_type').agg({
            'user_account': ['count', 'nunique'],
            'total_traffic': 'sum'
        }).reset_index()
        
        ip_stats.columns = ['ip_type', 'session_count', 'user_count', 'total_traffic']
        ip_stats['ip_type_name'] = ip_stats['ip_type'].apply(ip_type_name)
        
        return ip_stats.sort_values('session_count', ascending=False)
    
    # === 图表生成方法（重用原有逻辑） ===
    
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
        
        # 对大小进行归一化处理，避免气泡过大
        import numpy as np
        min_size = upload_heavy_users['upstream_gb'].min()
        max_size = upload_heavy_users['upstream_gb'].max()
        
        # 使用对数缩放来减少大小差异
        if max_size > min_size:
            # 对数变换 + 归一化到合理范围 (5-30)
            upload_heavy_users['normalized_size'] = np.log1p(upload_heavy_users['upstream_gb'])
            min_norm = upload_heavy_users['normalized_size'].min()
            max_norm = upload_heavy_users['normalized_size'].max()
            upload_heavy_users['bubble_size'] = 5 + (upload_heavy_users['normalized_size'] - min_norm) / (max_norm - min_norm) * 25
        else:
            upload_heavy_users['bubble_size'] = 15  # 默认大小
        
        fig = px.scatter(upload_heavy_users, 
                       x='session_count', y='upload_ratio',
                       size='bubble_size', hover_name='user_account',
                       title='用户活跃度 vs 上传比例',
                       labels={'session_count': '会话数', 'upload_ratio': '上传/下载比例'},
                       color='upstream_gb',
                       color_continuous_scale='Reds',
                       hover_data={'upstream_gb': ':.2f', 'bubble_size': False})
        
        # 更新布局和大小设置
        fig.update_layout(
            font=dict(size=12),
            showlegend=False
        )
        
        # 设置更合理的大小参考
        fig.update_traces(
            marker=dict(
                sizemode='diameter',
                sizeref=2,
                sizemin=4,
                opacity=0.7
            )
        )
        
        return fig
    
    def create_app_traffic_bar_chart(self, limit: int = 10, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建应用大类上行流量柱状图（含占比）"""
        app_major = self.get_app_major_analysis(limit, filters)
        if app_major.empty:
            return None
        
        # 创建自定义文本，包含流量和占比
        app_major['text_label'] = app_major.apply(
            lambda row: f"{row['upstream_traffic_gb']:.1f}GB<br>({row['upstream_percentage']:.1f}%)", 
            axis=1
        )
        
        fig = px.bar(app_major, x='app_name', y='upstream_traffic_gb',
                    title='应用大类上行流量消耗TOP 10（含占比）',
                    labels={'app_name': '应用大类', 'upstream_traffic_gb': '上行流量(GB)'},
                    color='upstream_traffic_gb',
                    color_continuous_scale='Viridis',
                    text='text_label')
        
        # 设置文本显示在柱状图上方
        fig.update_traces(textposition='outside')
        fig.update_layout(
            xaxis_tickangle=45, 
            font=dict(size=12), 
            showlegend=False,
            margin=dict(t=100)
        )
        return fig
    
    def create_app_traffic_pie_chart(self, limit: int = 10, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建应用大类上行流量饼图（占比）"""
        app_major = self.get_app_major_analysis(limit, filters)
        if app_major.empty:
            return None
        
        # 计算其他应用的占比
        top_apps_percentage = app_major['upstream_percentage'].sum()
        others_percentage = 100 - top_apps_percentage
        
        # 准备饼图数据
        labels = app_major['app_name'].tolist()
        values = app_major['upstream_percentage'].tolist()
        
        # 如果其他应用占比大于1%，则添加"其他"项
        if others_percentage > 1:
            labels.append('其他应用')
            values.append(others_percentage)
        
        fig = px.pie(values=values, names=labels,
                    title=f'应用大类上行流量占比TOP {limit}')
        
        # 设置显示格式
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>占比: %{percent}<br>数值: %{value:.1f}%<extra></extra>'
        )
        
        fig.update_layout(
            font=dict(size=12),
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
        )
        
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
    
    def create_ip_type_pie_chart(self, filters: Optional[FilterConditions] = None, by_traffic: bool = True) -> Optional[go.Figure]:
        """创建IPv4 vs IPv6分布饼图"""
        ip_data = self.get_ip_type_distribution(filters)
        if ip_data.empty:
            return None
        
        # 根据参数选择显示流量分布还是会话分布
        if by_traffic:
            values = ip_data['total_traffic']
            title = 'IPv4 vs IPv6 流量分布'
            # 转换为GB并格式化显示
            ip_data['traffic_gb'] = ip_data['total_traffic'] / (1024*1024*1024)
            hover_template = '<b>%{label}</b><br>' + \
                           '流量: %{customdata:.2f} GB<br>' + \
                           '占比: %{percent}<br>' + \
                           '<extra></extra>'
            customdata = ip_data['traffic_gb']
        else:
            values = ip_data['session_count']
            title = 'IPv4 vs IPv6 会话分布'
            hover_template = '<b>%{label}</b><br>' + \
                           '会话数: %{value:,}<br>' + \
                           '占比: %{percent}<br>' + \
                           '<extra></extra>'
            customdata = None
        
        fig = go.Figure(data=[go.Pie(
            labels=ip_data['ip_type_name'],
            values=values,
            textinfo='label+percent',
            textposition='auto',
            hovertemplate=hover_template,
            customdata=customdata,
            marker=dict(
                colors=['#3498db', '#e74c3c', '#95a5a6'],  # 蓝色IPv4, 红色IPv6, 灰色Unknown
                line=dict(color='#FFFFFF', width=2)
            )
        )])
        
        fig.update_layout(
            title=title,
            font=dict(size=12),
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
        )
        
        return fig
    
    # === 辅助方法 ===
    
    def get_available_users(self, limit: int = 100) -> List[str]:
        """获取可用的用户账号列表"""
        df = self._load_main_data()
        users = df['user_account'].unique()
        return sorted(users)[:limit]
    
    def get_available_app_categories(self) -> List[str]:
        """获取可用的应用大类列表（返回名称）"""
        self._load_app_categories()
        if not self._app_major_categories.empty:
            return sorted(self._app_major_categories['name'].tolist())
        return []
    
    def get_date_range(self) -> Dict[str, date]:
        """获取数据的日期范围"""
        df = self._load_main_data()
        if 'stat_datetime' in df.columns:
            min_date = df['stat_datetime'].min().date()
            max_date = df['stat_datetime'].max().date()
            return {'min_date': min_date, 'max_date': max_date}
        return {'min_date': None, 'max_date': None}
    
    def close(self):
        """关闭服务（CSV版本无需特殊处理）"""
        pass