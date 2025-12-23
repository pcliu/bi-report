#!/usr/bin/env python3
"""
数据服务层
统一管理所有数据查询和分析逻辑，使用SQLite作为底层存储
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date
import os
from pathlib import Path
from db_manager import DBManager

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
    
    def to_sql(self, app_major_mapping: Dict[str, int] = None) -> Tuple[str, List[Any]]:
        """生成SQL WHERE子句"""
        conditions = []
        params = []
        
        if self.user_account:
            conditions.append("user_account = ?")
            params.append(self.user_account)
        
        if self.ip_type is not None:
            conditions.append("ip_type = ?")
            params.append(self.ip_type)
        
        # 日期筛选 - 假设数据库中stat_time格式为 'YYYY-MM-DD HH:MM:SS' 或类似
        # 我们可以使用字符串比较，因为ISO格式日期字符串是可比较的
        if self.start_date:
            conditions.append("stat_time >= ?")
            params.append(self.start_date.strftime('%Y-%m-%d 00:00:00'))
            
        if self.end_date:
            conditions.append("stat_time <= ?")
            params.append(self.end_date.strftime('%Y-%m-%d 23:59:59'))
        
        if self.app_category_major:
            # 如果是数字，直接按ID筛选；如果是文本，尝试查找ID
            if self.app_category_major.isdigit():
                conditions.append("app_category_major = ?")
                params.append(int(self.app_category_major))
            elif app_major_mapping:
                category_id = app_major_mapping.get(self.app_category_major)
                if category_id:
                    conditions.append("app_category_major = ?")
                    params.append(category_id)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        return where_clause, params
    
    def apply_to_dataframe(self, df: pd.DataFrame, app_major_mapping: Dict[str, int] = None) -> pd.DataFrame:
        """(兼容性保留) 将筛选条件应用到DataFrame"""
        filtered_df = df.copy()
        
        if self.user_account:
            filtered_df = filtered_df[filtered_df['user_account'] == self.user_account]
        
        if self.ip_type is not None:
            filtered_df = filtered_df[filtered_df['ip_type'] == self.ip_type]
        
        if self.start_date or self.end_date:
            if 'stat_time' in filtered_df.columns:
                filtered_df['stat_date'] = pd.to_datetime(filtered_df['stat_time']).dt.date
                if self.start_date:
                    filtered_df = filtered_df[filtered_df['stat_date'] >= self.start_date]
                if self.end_date:
                    filtered_df = filtered_df[filtered_df['stat_date'] <= self.end_date]
        
        if self.app_category_major and app_major_mapping:
            if self.app_category_major.isdigit():
                filtered_df = filtered_df[filtered_df['app_category_major'] == int(self.app_category_major)]
            else:
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


class DataService:
    """基于SQLite的数据服务层"""
    
    def __init__(self, db_path: str = None):
        """初始化数据服务"""
        self.db_manager = DBManager(db_path)
        # self.conn removed - use on-demand connections
        self._app_major_categories = None
        self._app_minor_categories = None
        self._app_major_mapping = None
        
        print(f"📁 数据服务初始化，数据库: {self.db_manager.db_path}")

    def reload_all_data(self, data_folder: str = "./data") -> Dict[str, Any]:
        """重载所有数据（清空DB并从磁盘加载）"""
        stats = {'files_loaded': 0, 'rows_inserted': 0, 'categories_loaded': False}
        data_path = Path(data_folder)
        
        if not data_path.exists():
            print(f"⚠️ 数据目录不存在: {data_folder}")
            return stats

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                # 1. 清空所有表
                cursor.execute("DELETE FROM traffic_data")
                cursor.execute("DELETE FROM app_major_categories")
                cursor.execute("DELETE FROM app_minor_categories")
                # 可选：重置自增ID
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='traffic_data'")
                print("🗑️ 已清空数据库")
                
                # 2. 加载分类
                try:
                    major_csv = data_path / "app_catagory_major.csv"
                    if major_csv.exists():
                        df_major = pd.read_csv(major_csv, names=['id', 'name'], header=None)
                        df_major.to_sql('app_major_categories', conn, if_exists='replace', index=False)
                    
                    minor_csv = data_path / "app_catagory_minor.csv"
                    if minor_csv.exists():
                        df_minor = pd.read_csv(minor_csv, names=['id', 'name'], header=None)
                        df_minor.to_sql('app_minor_categories', conn, if_exists='replace', index=False)
                        
                    stats['categories_loaded'] = True
                    print("✅ 分类数据加载完成")
                except Exception as e:
                    print(f"⚠️ 分类加载失败: {e}")

                # 3. 加载流量数据
                traffic_files = list(data_path.glob("tbl_statistic_userapp_day*.csv")) + \
                              list(data_path.glob("traffic_data*.csv"))
                
                rows_count = 0
                for file_path in traffic_files:
                    try:
                        df = self._read_csv_to_df(file_path)
                        if df is not None and not df.empty:
                            df['import_batch_id'] = datetime.now().strftime('%Y%m%d%H%M%S')
                            df.to_sql('traffic_data', conn, if_exists='append', index=False)
                            rows_count += len(df)
                            stats['files_loaded'] += 1
                            print(f"  - 加载 {file_path.name}: {len(df)} 行")
                    except Exception as e:
                        print(f"  ⚠️ 加载失败 {file_path.name}: {e}")
                
                stats['rows_inserted'] = rows_count
                
                # 提交事务
                conn.commit()
                
            # 清除缓存
            self._app_major_categories = None
            self._app_minor_categories = None 
            self._app_major_mapping = None
            
            return stats
            
        except Exception as e:
            print(f"重载数据失败: {e}")
            raise e

    def import_csv_file(self, file_path_or_buffer) -> int:
        """导入CSV文件到数据库"""
        try:
            # 读取CSV
            df = self._read_csv_to_df(file_path_or_buffer)
            if df is None:
                return 0

            # 写入数据库
            import_batch = datetime.now().strftime('%Y%m%d%H%M%S')
            df['import_batch_id'] = import_batch
            
            with self.db_manager.get_connection() as conn:
                df.to_sql('traffic_data', conn, if_exists='append', index=False)
                # Context manager commits automatically on success
            
            return len(df)
        except Exception as e:
            print(f"导入失败: {e}")
            raise e

    def import_category_file(self, file_path_or_buffer, category_type: str = 'major') -> int:
        """导入应用分类文件
        category_type: 'major' or 'minor'
        """
        try:
            if isinstance(file_path_or_buffer, (str, Path)):
                df = pd.read_csv(file_path_or_buffer, names=['id', 'name'], header=None)
            else:
                df = pd.read_csv(file_path_or_buffer, names=['id', 'name'], header=None)
            
            table_name = 'app_major_categories' if category_type == 'major' else 'app_minor_categories'
            
            with self.db_manager.get_connection() as conn:
                df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            # 清除缓存
            self._app_major_categories = None
            self._app_minor_categories = None
            self._app_major_mapping = None
            
            return len(df)
        except Exception as e:
            print(f"分类导入失败: {e}")
            raise e

    def _read_csv_to_df(self, file_path) -> pd.DataFrame:
        """读取并处理CSV文件，统一列名和类型"""
        column_names = [
            'user_account', 'ip_type', 'app_category_major', 'app_category_minor',
            'upstream_traffic', 'downstream_traffic', 'total_traffic', 'duration', 'stat_time',
            'new_connections', 'removed_connections'
        ]
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

        try:
            # 判断是否有表头
            # 如果是buffer (UploadFile), 需要小心处理指针
            if hasattr(file_path, 'seek'):
                file_path.seek(0)
                sample = pd.read_csv(file_path, nrows=1)
                file_path.seek(0)
            else:
                sample = pd.read_csv(file_path, nrows=1)
            
            sample_columns = {str(col).strip() for col in sample.columns}
            has_header = bool(sample_columns & set(column_names) or sample_columns & set(column_mapping.keys()))
            
            if has_header:
                df = pd.read_csv(file_path)
                df.columns = [str(col).strip() for col in df.columns]
                df = df.rename(columns=column_mapping)
                for col in column_names:
                    if col not in df.columns:
                        df[col] = None
            else:
                df = pd.read_csv(file_path, names=column_names, header=None)
                
            # 数据转换
            df['ip_type'] = pd.to_numeric(df['ip_type'], errors='coerce').fillna(0).astype(int)
            df['app_category_major'] = pd.to_numeric(df['app_category_major'], errors='coerce').fillna(0).astype(int)
            df['app_category_minor'] = pd.to_numeric(df['app_category_minor'], errors='coerce').fillna(0).astype(int)
            
            traffic_columns = ['upstream_traffic', 'downstream_traffic', 'total_traffic', 'duration']
            for col in traffic_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
            if 'user_account' in df.columns:
                df['user_account'] = df['user_account'].astype(str).str.strip('"')
            
            if 'stat_time' in df.columns:
                df['stat_time'] = df['stat_time'].astype(str).str.strip('"')
            
            # 连接数列转换
            df['new_connections'] = pd.to_numeric(df['new_connections'], errors='coerce').fillna(0).astype(int)
            df['removed_connections'] = pd.to_numeric(df['removed_connections'], errors='coerce').fillna(0).astype(int)

            return df
        except Exception as e:
            print(f"CSV解析错误: {e}")
            return None

    def _load_app_categories(self):
        """从数据库加载应用分类"""
        if self._app_major_categories is not None:
            return

        try:
            with self.db_manager.get_connection() as conn:
                self._app_major_categories = pd.read_sql("SELECT * FROM app_major_categories", conn)
                if not self._app_major_categories.empty:
                    self._app_major_mapping = dict(zip(self._app_major_categories['name'], self._app_major_categories['id']))
                else:
                    self._app_major_mapping = {}
                    
                self._app_minor_categories = pd.read_sql("SELECT * FROM app_minor_categories", conn)
            
        except Exception as e:
            print(f"加载应用分类失败(可能是表为空): {e}")
            self._app_major_categories = pd.DataFrame(columns=['id', 'name'])
            self._app_minor_categories = pd.DataFrame(columns=['id', 'name'])
            self._app_major_mapping = {}

    def get_available_users(self) -> List[str]:
        """获取所有可用用户账号"""
        try:
            with self.db_manager.get_connection() as conn:
                df = pd.read_sql("SELECT DISTINCT user_account FROM traffic_data", conn)
            return sorted(df['user_account'].astype(str).tolist())
        except:
            return []

    def get_date_range(self) -> Dict[str, Any]:
        """获取数据日期范围"""
        try:
            query = "SELECT MIN(stat_time) as min_date, MAX(stat_time) as max_date FROM traffic_data"
            with self.db_manager.get_connection() as conn:
                df = pd.read_sql(query, conn)
            if not df.empty and df.iloc[0]['min_date']:
                return {
                    'min_date': pd.to_datetime(df.iloc[0]['min_date']).date(),
                    'max_date': pd.to_datetime(df.iloc[0]['max_date']).date()
                }
        except Exception as e:
            print(f"获取日期范围失败: {e}")
        return {'min_date': None, 'max_date': None}

    def get_available_app_categories(self) -> List[str]:
        """获取可用应用大类名称"""
        self._load_app_categories()
        if self._app_major_categories is not None and not self._app_major_categories.empty:
            return sorted(self._app_major_categories['name'].tolist())
        
        # 如果没有名称映射，返回ID列表
        try:
            with self.db_manager.get_connection() as conn:
                df = pd.read_sql("SELECT DISTINCT app_category_major FROM traffic_data", conn)
            return sorted(df['app_category_major'].astype(str).tolist())
        except:
            return []

    def get_data(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """从数据库获取筛选后的数据"""
        self._load_app_categories()
        
        query = "SELECT * FROM traffic_data"
        params = []
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            query += f" WHERE {where_clause}"
        
        try:
            with self.db_manager.get_connection() as conn:
                df = pd.read_sql(query, conn, params=params)
            
             # 确保类型转换（这是为了兼容原有分析逻辑，虽然read_sql会做部分转换）
            if not df.empty:
                 if 'stat_time' in df.columns:
                     df['stat_datetime'] = pd.to_datetime(df['stat_time'], errors='coerce')
            return df
        except Exception as e:
            print(f"查询数据失败: {e}")
            return pd.DataFrame()

    # === 下面的分析方法可以直接复用，因为 get_data 返回兼容的 DataFrame ===

    def get_basic_stats(self, filters: Optional[FilterConditions] = None) -> Dict[str, Any]:
        """获取基础统计信息 (SQL优化版)"""
        self._load_app_categories()
        
        query = """
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT user_account) as total_users,
                SUM(total_traffic) as total_traffic,
                COUNT(DISTINCT app_category_major) as app_categories
            FROM traffic_data
        """
        params = []
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            query += f" WHERE {where_clause}"
        
        try:
            with self.db_manager.get_connection() as conn:
                df = pd.read_sql(query, conn, params=params)
            
            if df.empty:
                return {'total_records': 0, 'total_users': 0, 'total_traffic': 0, 'app_categories': 0, 'total_traffic_gb': 0}
            
            row = df.iloc[0]
            total_traffic = row['total_traffic'] or 0
            return {
                'total_records': int(row['total_records']),
                'total_users': int(row['total_users']),
                'total_traffic': total_traffic,
                'app_categories': int(row['app_categories']),
                'total_traffic_gb': total_traffic / (1024*1024*1024)
            }
        except Exception as e:
            print(f"获取基础统计失败: {e}")
            return {'total_records': 0, 'total_users': 0, 'total_traffic': 0, 'app_categories': 0, 'total_traffic_gb': 0}
    
    def get_traffic_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取上行vs下行流量分布 (SQL优化版)"""
        self._load_app_categories()
        
        query = "SELECT SUM(upstream_traffic) as upstream, SUM(downstream_traffic) as downstream FROM traffic_data"
        params = []
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            query += f" WHERE {where_clause}"
        
        try:
            with self.db_manager.get_connection() as conn:
                df = pd.read_sql(query, conn, params=params)
            if df.empty or df.iloc[0]['upstream'] is None:
                return pd.DataFrame({'upstream': [0], 'downstream': [0]})
            return df
        except Exception as e:
            print(f"获取流量分布失败: {e}")
            return pd.DataFrame({'upstream': [0], 'downstream': [0]})

    def get_ip_type_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取IPv4 vs IPv6分布 (SQL优化版)"""
        self._load_app_categories()
        
        query = """
            SELECT 
                ip_type,
                SUM(total_traffic) as total_traffic,
                SUM(new_connections) as connection_count
            FROM traffic_data
        """
        params = []
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            query += f" WHERE {where_clause}"
        
        query += " GROUP BY ip_type"
        
        try:
            with self.db_manager.get_connection() as conn:
                ip_stats = pd.read_sql(query, conn, params=params)
            if ip_stats.empty:
                return pd.DataFrame()
            ip_stats['ip_type_name'] = ip_stats['ip_type'].apply(lambda x: 'IPv4' if x == 0 else 'IPv6')
            return ip_stats
        except Exception as e:
            print(f"获取IP类型分布失败: {e}")
            return pd.DataFrame()
    
    def get_duration_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取流量时长分布 (SQL优化版)"""
        self._load_app_categories()
        
        # 使用SQL CASE语句进行分组
        query = """
            SELECT 
                CASE 
                    WHEN duration < 1000000 THEN '<1秒'
                    WHEN duration < 60000000 THEN '1-60秒'
                    WHEN duration < 3600000000 THEN '1-60分钟'
                    WHEN duration < 86400000000 THEN '1-24小时'
                    ELSE '>24小时'
                END as duration_range,
                COUNT(*) as count
            FROM traffic_data
        """
        params = []
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            query += f" WHERE {where_clause}"
        
        query += " GROUP BY duration_range ORDER BY count DESC"
        
        try:
            with self.db_manager.get_connection() as conn:
                result = pd.read_sql(query, conn, params=params)
            return result
        except Exception as e:
            print(f"获取时长分布失败: {e}")
            return pd.DataFrame()
    
    def get_top_traffic_users(self, limit: int = 20, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取流量TOP用户 (SQL优化版)"""
        self._load_app_categories()
        
        query = """
            SELECT 
                user_account,
                SUM(total_traffic) as total_traffic,
                SUM(upstream_traffic) as upstream_traffic,
                SUM(downstream_traffic) as downstream_traffic,
                SUM(new_connections) as connections
            FROM traffic_data
        """
        params = []
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            query += f" WHERE {where_clause}"
        
        query += f" GROUP BY user_account ORDER BY total_traffic DESC LIMIT {limit}"
        
        try:
            with self.db_manager.get_connection() as conn:
                user_stats = pd.read_sql(query, conn, params=params)
            
            if user_stats.empty:
                return pd.DataFrame()
            
            user_stats['total_traffic_gb'] = user_stats['total_traffic'] / (1024*1024*1024)
            user_stats['upstream_gb'] = user_stats['upstream_traffic'] / (1024*1024*1024)
            user_stats['downstream_gb'] = user_stats['downstream_traffic'] / (1024*1024*1024)
            return user_stats
        except Exception as e:
            print(f"获取TOP用户失败: {e}")
            return pd.DataFrame()
    
    def get_user_activity_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取用户活跃度分布 (SQL优化版)"""
        self._load_app_categories()
        
        # 使用子查询：先按用户统计连接数，再分组
        query = """
            SELECT 
                CASE 
                    WHEN connection_count = 1 THEN '单次连接'
                    WHEN connection_count <= 5 THEN '2-5次连接'
                    WHEN connection_count <= 10 THEN '6-10次连接'
                    WHEN connection_count <= 20 THEN '11-20次连接'
                    ELSE '>20次连接'
                END as activity_level,
                COUNT(*) as user_count
            FROM (
                SELECT user_account, SUM(new_connections) as connection_count
                FROM traffic_data
        """
        params = []
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            query += f" WHERE {where_clause}"
        
        query += " GROUP BY user_account) GROUP BY activity_level ORDER BY user_count DESC"
        
        try:
            with self.db_manager.get_connection() as conn:
                result = pd.read_sql(query, conn, params=params)
            return result
        except Exception as e:
            print(f"获取用户活跃度分布失败: {e}")
            return pd.DataFrame()
    
    def get_user_traffic_distribution(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取用户流量消耗分布 (SQL优化版)"""
        self._load_app_categories()
        
        query = """
            SELECT 
                CASE 
                    WHEN user_traffic < 1048576 THEN '<1MB'
                    WHEN user_traffic < 10485760 THEN '1-10MB'
                    WHEN user_traffic < 104857600 THEN '10-100MB'
                    WHEN user_traffic < 1073741824 THEN '100MB-1GB'
                    ELSE '>1GB'
                END as traffic_range,
                COUNT(*) as user_count
            FROM (
                SELECT user_account, SUM(total_traffic) as user_traffic
                FROM traffic_data
        """
        params = []
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            query += f" WHERE {where_clause}"
        
        query += " GROUP BY user_account) GROUP BY traffic_range ORDER BY user_count DESC"
        
        try:
            with self.db_manager.get_connection() as conn:
                result = pd.read_sql(query, conn, params=params)
            return result
        except Exception as e:
            print(f"获取用户流量分布失败: {e}")
            return pd.DataFrame()
    
    def get_upload_heavy_users(self, limit: int = 20, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取高活跃上传用户 (SQL优化版)"""
        self._load_app_categories()
        
        # 使用 HAVING 进行条件筛选
        query = """
            SELECT 
                user_account,
                SUM(upstream_traffic) as total_upstream,
                SUM(downstream_traffic) as total_downstream,
                SUM(total_traffic) as total_traffic,
                SUM(new_connections) as connection_count
            FROM traffic_data
        """
        params = []
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            query += f" WHERE {where_clause}"
        
        query += """
            GROUP BY user_account
            HAVING connection_count >= 5 
               AND total_upstream > total_downstream 
               AND total_upstream >= 104857600
            ORDER BY total_upstream DESC
            LIMIT ?
        """
        params.append(limit)
        
        try:
            with self.db_manager.get_connection() as conn:
                result = pd.read_sql(query, conn, params=params)
            
            if result.empty:
                return pd.DataFrame()
            
            # 计算上传比例
            result['upload_ratio'] = result['total_upstream'] / result['total_downstream'].replace(0, 1)
            result['upload_ratio'] = result['upload_ratio'].replace([float('inf')], 999.99).round(2)
            
            result['upstream_gb'] = result['total_upstream'] / (1024*1024*1024)
            result['downstream_gb'] = result['total_downstream'] / (1024*1024*1024)
            result['total_gb'] = result['total_traffic'] / (1024*1024*1024)
            
            return result
        except Exception as e:
            print(f"获取高活跃上传用户失败: {e}")
            return pd.DataFrame()
    
    def get_app_major_analysis(self, limit: int = 10, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取应用大类分析数据（仅上行流量）(SQL优化版)"""
        self._load_app_categories()
        
        # 先获取总上行流量
        total_query = "SELECT SUM(upstream_traffic) as total FROM traffic_data"
        params = []
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            total_query += f" WHERE {where_clause}"
        
        try:
            with self.db_manager.get_connection() as conn:
                total_df = pd.read_sql(total_query, conn, params=params)
                total_upstream = total_df.iloc[0]['total'] or 0
                
                # 再获取分组统计
                query = """
                    SELECT 
                        app_category_major,
                        SUM(upstream_traffic) as upstream_traffic,
                        SUM(new_connections) as connection_count,
                        COUNT(DISTINCT user_account) as user_count
                    FROM traffic_data
                """
                
                if filters:
                    query += f" WHERE {where_clause}"
                
                query += f" GROUP BY app_category_major ORDER BY upstream_traffic DESC LIMIT {limit}"
                
                app_stats = pd.read_sql(query, conn, params=params)
            
            if app_stats.empty:
                return pd.DataFrame()
            
            if not self._app_major_categories.empty:
                major_name_map = dict(zip(self._app_major_categories['id'], self._app_major_categories['name']))
                app_stats['major_name'] = app_stats['app_category_major'].map(major_name_map)
            else:
                app_stats['major_name'] = None
            
            app_stats['app_name'] = app_stats['major_name'].fillna(app_stats['app_category_major'].astype(str) + "类应用")
            app_stats['upstream_traffic_gb'] = app_stats['upstream_traffic'] / (1024*1024*1024)
            app_stats['upstream_percentage'] = (app_stats['upstream_traffic'] / total_upstream * 100) if total_upstream > 0 else 0
            
            return app_stats
        except Exception as e:
            print(f"获取应用大类分析失败: {e}")
            return pd.DataFrame()
    
    def get_app_minor_analysis(self, limit: int = 20, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取应用小类分析数据（仅上行流量）(SQL优化版)"""
        self._load_app_categories()
        
        # 先获取总上行流量
        total_query = "SELECT SUM(upstream_traffic) as total FROM traffic_data"
        params = []
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            total_query += f" WHERE {where_clause}"
        
        try:
            with self.db_manager.get_connection() as conn:
                total_df = pd.read_sql(total_query, conn, params=params)
                total_upstream = total_df.iloc[0]['total'] or 0
                
                query = """
                    SELECT 
                        app_category_major,
                        app_category_minor,
                        SUM(upstream_traffic) as upstream_traffic,
                        COUNT(DISTINCT user_account) as user_count
                    FROM traffic_data
                """
                
                if filters:
                    query += f" WHERE {where_clause}"
                
                query += f" GROUP BY app_category_major, app_category_minor ORDER BY upstream_traffic DESC LIMIT {limit}"
                
                app_stats = pd.read_sql(query, conn, params=params)
            
            if app_stats.empty:
                return pd.DataFrame()
            
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
            
            app_stats['major_display'] = app_stats['major_name'].fillna(app_stats['app_category_major'].astype(str))
            app_stats['minor_display'] = app_stats['minor_name'].fillna(app_stats['app_category_minor'].astype(str))
            app_stats['应用名称'] = app_stats['major_display'] + " - " + app_stats['minor_display']
            
            app_stats['upstream_traffic_gb'] = app_stats['upstream_traffic'] / (1024*1024*1024)
            app_stats['upstream_percentage'] = (app_stats['upstream_traffic'] / total_upstream * 100) if total_upstream > 0 else 0
            
            return app_stats
        except Exception as e:
            print(f"获取应用小类分析失败: {e}")
            return pd.DataFrame()

    def get_app_category_top_users(self, limit_categories: int = 10, limit_users: int = 10, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取应用大类TOP10及每个大类中TOP10用户的详细分析 (SQL优化版)"""
        self._load_app_categories()
        
        params = []
        where_clause = ""
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            where_clause = f"WHERE {where_clause}"
        
        try:
            with self.db_manager.get_connection() as conn:
                # Step 1: 获取TOP应用大类
                top_cat_query = f"""
                    SELECT app_category_major, SUM(upstream_traffic) as category_traffic
                    FROM traffic_data {where_clause}
                    GROUP BY app_category_major
                    ORDER BY category_traffic DESC
                    LIMIT {limit_categories}
                """
                top_categories = pd.read_sql(top_cat_query, conn, params=params)
                
                if top_categories.empty:
                    return pd.DataFrame()
                
                # Step 2: 对每个大类获取TOP用户
                all_results = []
                for _, cat_row in top_categories.iterrows():
                    cat_id = cat_row['app_category_major']
                    cat_traffic = cat_row['category_traffic']
                    
                    # 获取类别名称
                    if not self._app_major_categories.empty:
                        name_row = self._app_major_categories[self._app_major_categories['id'] == cat_id]['name']
                        category_name = name_row.iloc[0] if not name_row.empty else f"应用{cat_id}"
                    else:
                        category_name = f"应用{cat_id}"
                    
                    # 查询该类别的TOP用户
                    user_query = f"""
                        SELECT 
                            user_account,
                            SUM(upstream_traffic) as user_upstream_traffic,
                            SUM(downstream_traffic) as user_downstream_traffic,
                            SUM(total_traffic) as user_total_traffic,
                            SUM(new_connections) as connection_count
                        FROM traffic_data
                        WHERE app_category_major = ?
                    """
                    user_params = [cat_id]
                    
                    if filters:
                        user_query += f" AND {where_clause.replace('WHERE ', '')}"
                        user_params.extend(params)
                    
                    user_query += f" GROUP BY user_account ORDER BY user_upstream_traffic DESC LIMIT {limit_users}"
                    
                    users_df = pd.read_sql(user_query, conn, params=user_params)
                    
                    if not users_df.empty:
                        users_df['app_category_major'] = cat_id
                        users_df['category_name'] = category_name
                        users_df['category_total_traffic'] = cat_traffic
                        users_df['user_traffic_percentage'] = (users_df['user_upstream_traffic'] / cat_traffic * 100) if cat_traffic > 0 else 0
                        users_df['user_upstream_gb'] = users_df['user_upstream_traffic'] / (1024*1024*1024)
                        users_df['user_downstream_gb'] = users_df['user_downstream_traffic'] / (1024*1024*1024)
                        users_df['user_total_gb'] = users_df['user_total_traffic'] / (1024*1024*1024)
                        all_results.append(users_df)
                
                if all_results:
                    return pd.concat(all_results, ignore_index=True)
                return pd.DataFrame()
        except Exception as e:
            print(f"获取应用大类TOP用户失败: {e}")
            return pd.DataFrame()

    def get_time_analysis(self, filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取时间分析数据 (SQL优化版)"""
        self._load_app_categories()
        
        query = """
            SELECT 
                stat_time,
                COUNT(*) as record_count,
                COUNT(DISTINCT user_account) as user_count,
                SUM(total_traffic) as total_traffic
            FROM traffic_data
        """
        params = []
        
        if filters:
            where_clause, params = filters.to_sql(self._app_major_mapping)
            query += f" WHERE {where_clause}"
        
        query += " GROUP BY stat_time ORDER BY stat_time"
        
        try:
            with self.db_manager.get_connection() as conn:
                time_stats = pd.read_sql(query, conn, params=params)
            
            if time_stats.empty:
                return pd.DataFrame()
            
            time_stats['total_traffic_gb'] = time_stats['total_traffic'] / (1024*1024*1024)
            return time_stats
        except Exception as e:
            print(f"获取时间分析数据失败: {e}")
            return pd.DataFrame()

    def get_flexible_time_analysis(self, group_by_field: str = 'none', metric_type: str = 'session_count', traffic_type: str = 'total', filters: Optional[FilterConditions] = None) -> pd.DataFrame:
        """获取灵活的时间分析数据 (SQL优化版)"""
        self._load_app_categories()
        
        # 确定指标列
        if metric_type == 'session_count':
            metric_expr = "SUM(new_connections)"
            metric_alias = "value"
        elif metric_type == 'traffic':
            if traffic_type == 'upstream':
                metric_expr = "SUM(upstream_traffic)"
            elif traffic_type == 'downstream':
                metric_expr = "SUM(downstream_traffic)"
            else:
                metric_expr = "SUM(total_traffic)"
            metric_alias = "value"
        elif metric_type == 'session_duration':
            metric_expr = "AVG(duration)"
            metric_alias = "value"
        else:
            metric_expr = "SUM(new_connections)"
            metric_alias = "value"
        
        # 构建分组字段
        if group_by_field == 'none':
            group_expr = "'总体'"
            category_alias = "category"
        elif group_by_field == 'ip_type':
            group_expr = "CASE WHEN ip_type = 0 THEN 'IPv4' ELSE 'IPv6' END"
            category_alias = "category"
        elif group_by_field == 'app_category_major':
            group_expr = "app_category_major"
            category_alias = "category"
        elif group_by_field == 'user_account':
            # 用户分组需要特殊处理：先找TOP10用户
            group_expr = "user_account"
            category_alias = "category"
        else:
            group_expr = "'总体'"
            category_alias = "category"
        
        params = []
        where_clause = ""
        
        if filters:
            wc, params = filters.to_sql(self._app_major_mapping)
            where_clause = f"WHERE {wc}"
        
        try:
            with self.db_manager.get_connection() as conn:
                # 用户分组需要先获取TOP10
                if group_by_field == 'user_account':
                    top_users_query = f"""
                        SELECT user_account FROM traffic_data {where_clause}
                        GROUP BY user_account
                        ORDER BY SUM(total_traffic) DESC
                        LIMIT 10
                    """
                    top_users_df = pd.read_sql(top_users_query, conn, params=params)
                    if top_users_df.empty:
                        return pd.DataFrame()
                    
                    top_user_list = top_users_df['user_account'].tolist()
                    placeholders = ','.join(['?' for _ in top_user_list])
                    
                    if where_clause:
                        user_filter = f" AND user_account IN ({placeholders})"
                    else:
                        user_filter = f"WHERE user_account IN ({placeholders})"
                        where_clause = user_filter
                    
                    # 重新构建查询
                    query = f"""
                        SELECT 
                            DATE(stat_time) as date_key,
                            user_account as category,
                            {metric_expr} as {metric_alias}
                        FROM traffic_data
                        {where_clause}{user_filter if where_clause else ''}
                        GROUP BY date_key, category
                        ORDER BY date_key
                    """
                    all_params = params + top_user_list
                else:
                    query = f"""
                        SELECT 
                            DATE(stat_time) as date_key,
                            {group_expr} as {category_alias},
                            {metric_expr} as {metric_alias}
                        FROM traffic_data
                        {where_clause}
                        GROUP BY date_key, {category_alias}
                        ORDER BY date_key
                    """
                    all_params = params
                
                result = pd.read_sql(query, conn, params=all_params)
            
            if result.empty:
                return pd.DataFrame()
            
            # 应用大类需要名称映射
            if group_by_field == 'app_category_major' and not self._app_major_categories.empty:
                major_name_map = dict(zip(self._app_major_categories['id'], self._app_major_categories['name']))
                result['category'] = result['category'].map(major_name_map).fillna(result['category'].astype(str) + '类应用')
            
            # 单位转换
            if metric_type == 'traffic':
                result['value'] = result['value'] / (1024*1024*1024)
            elif metric_type == 'session_duration':
                result['value'] = result['value'] / 1000000
            
            return result
            
        except Exception as e:
            print(f"获取灵活时间分析失败: {e}")
            return pd.DataFrame()
    
    def create_flexible_time_chart(self, group_by_field: str = 'none', metric_type: str = 'session_count', traffic_type: str = 'total', filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建灵活的时间分析图表"""
        time_data = self.get_flexible_time_analysis(group_by_field, metric_type, traffic_type, filters)
        if time_data.empty: return None
        
        group_labels = {'none': '总体', 'ip_type': 'IP类型', 'app_category_major': '应用大类', 'user_account': '用户'}
        metric_labels = {'session_count': '连接数', 'traffic': '流量(GB)', 'session_duration': '平均连接时长(秒)'}
        traffic_labels = {'total': '总流量', 'upstream': '上行流量', 'downstream': '下行流量'}
        
        group_label = group_labels.get(group_by_field, '总体')
        if metric_type == 'traffic':
            metric_label = traffic_labels.get(traffic_type, '总流量')
        else:
            metric_label = metric_labels.get(metric_type, '连接数')
        
        title = f'时间趋势 - {metric_label}' if group_by_field == 'none' else f'时间趋势 - {metric_label} (按{group_label}分组)'
        
        fig = go.Figure()
        
        if 'category' in time_data.columns and group_by_field != 'none':
            categories = time_data['category'].unique()
            colors = px.colors.qualitative.Set1
            for i, category in enumerate(categories):
                category_data = time_data[time_data['category'] == category]
                color = colors[i % len(colors)]
                fig.add_trace(go.Scatter(x=category_data['date_key'], y=category_data['value'], mode='lines+markers', name=str(category), line=dict(color=color, width=2), marker=dict(color=color, size=6)))
        else:
            fig.add_trace(go.Scatter(x=time_data['date_key'], y=time_data['value'], mode='lines+markers', name=metric_label, line=dict(color='#3498db', width=3), marker=dict(color='#e74c3c', size=8)))
        
        fig.update_layout(title=title, xaxis_title='日期', yaxis_title=metric_labels.get(metric_type, '值'), font=dict(size=12), showlegend=True if 'category' in time_data.columns and len(time_data['category'].unique()) > 1 and group_by_field != 'none' else False, hovermode='x unified')
        return fig
    
    def create_traffic_pie_chart(self, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建上行vs下行流量饼图"""
        traffic_data = self.get_traffic_distribution(filters)
        if traffic_data.empty: return None
        
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

    def create_ip_type_pie_chart(self, filters: Optional[FilterConditions] = None, by_traffic: bool = True) -> Optional[go.Figure]:
        """创建IPv4 vs IPv6饼图"""
        ip_data = self.get_ip_type_distribution(filters)
        if ip_data.empty: return None
        if by_traffic:
            values = ip_data['total_traffic']
            title = "IPv4 vs IPv6 流量分布"
        else:
            values = ip_data['connection_count']
            title = "IPv4 vs IPv6 连接数分布"
        fig = go.Figure(data=[go.Pie(labels=ip_data['ip_type_name'], values=values, hole=0.3)])
        fig.update_layout(title_text=title)
        return fig

    def create_duration_bar_chart(self, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建时长分布柱状图"""
        duration_data = self.get_duration_distribution(filters)
        if duration_data.empty: return None
        
        fig = px.bar(duration_data, x='duration_range', y='count', 
                    title='流量时长分布', 
                    labels={'duration_range': '时长范围', 'count': '记录数'},
                    color='count',
                    color_continuous_scale='Blues')
        fig.update_layout(font=dict(size=12), showlegend=False)
        return fig

    def create_top_users_bar_chart(self, limit: int = 10, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建TOP用户流量柱状图"""
        user_data = self.get_top_traffic_users(limit, filters)
        if user_data.empty: return None
        
        fig = px.bar(user_data.head(limit), x='user_account', y='total_traffic_gb',
                    title=f'TOP {limit}用户流量消耗 (GB)',
                    labels={'user_account': '用户账号', 'total_traffic_gb': '总流量(GB)'},
                    color='total_traffic_gb',
                    color_continuous_scale='Reds')
        fig.update_layout(xaxis_tickangle=45, font=dict(size=10), showlegend=False)
        return fig

    def create_user_activity_pie_chart(self, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建用户活跃度分布饼图"""
        activity_data = self.get_user_activity_distribution(filters)
        if activity_data.empty: return None
        
        fig = px.pie(activity_data, values='user_count', names='activity_level',
                    title='用户活跃度分布',
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57'])
        fig.update_layout(font=dict(size=12), showlegend=True)
        return fig

    def create_user_traffic_bar_chart(self, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建用户流量消耗分布柱状图"""
        traffic_data = self.get_user_traffic_distribution(filters)
        if traffic_data.empty: return None
        
        fig = px.bar(traffic_data, x='traffic_range', y='user_count',
                    title='用户流量消耗分布',
                    labels={'traffic_range': '流量范围', 'user_count': '用户数'},
                    color='user_count',
                    color_continuous_scale='Greens')
        fig.update_layout(font=dict(size=12), showlegend=False)
        return fig

    def create_upload_users_bar_chart(self, limit: int = 10, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建高活跃上传用户柱状图"""
        user_data = self.get_upload_heavy_users(limit, filters)
        if user_data.empty: return None
        
        fig = px.bar(user_data, x='user_account', y='upstream_gb',
                    title=f'高活跃上传用户 TOP {limit}',
                    labels={'upstream_gb': '上行流量(GB)', 'user_account': '用户账号'},
                    color='upstream_gb',
                    color_continuous_scale='Oranges')
        fig.update_layout(xaxis_tickangle=45, font=dict(size=10), showlegend=False)
        return fig

    def create_upload_ratio_scatter_chart(self, limit: int = 20, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建上传比例散点图"""
        user_data = self.get_upload_heavy_users(limit, filters)
        if user_data.empty: return None
        fig = px.scatter(
            user_data, 
            x='upstream_gb', 
            y='upload_ratio', 
            size='total_gb', 
            hover_name='user_account', 
            title=f"上传流量 vs 上传比例 (TOP {limit})", 
            labels={'upstream_gb': '上行流量(GB)', 'upload_ratio': '上传:下载比例', 'total_gb': '总流量(GB)'},
            color_discrete_sequence=['#e74c3c']  # 显式设置红色
        )
        # 确保标记颜色生效
        fig.update_traces(marker=dict(color='#e74c3c'))
        return fig

    def create_app_traffic_bar_chart(self, limit: int = 10, filters: Optional[FilterConditions] = None) -> Optional[go.Figure]:
        """创建应用大类上行流量柱状图（含占比）"""
        app_data = self.get_app_major_analysis(limit, filters)
        if app_data.empty: return None
        
        # 创建自定义文本，包含流量和占比
        app_data['text_label'] = app_data.apply(
            lambda row: f"{row['upstream_traffic_gb']:.1f}GB<br>({row['upstream_percentage']:.1f}%)", 
            axis=1
        )
        
        fig = px.bar(app_data, x='app_name', y='upstream_traffic_gb',
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
        app_data = self.get_app_major_analysis(limit, filters)
        if app_data.empty: return None
        
        # 计算其他应用的占比
        top_apps_percentage = app_data['upstream_percentage'].sum()
        others_percentage = 100 - top_apps_percentage
        
        # 准备饼图数据
        labels = app_data['app_name'].tolist()
        values = app_data['upstream_percentage'].tolist()
        
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
        app_data = self.get_app_major_analysis(limit, filters)
        if app_data.empty: return None
        
        app_data_sorted = app_data.sort_values('user_count', ascending=False)
        fig = px.bar(app_data_sorted, x='app_name', y='user_count',
                    title='应用大类用户数TOP 10',
                    labels={'app_name': '应用大类', 'user_count': '用户数'},
                    color='user_count',
                    color_continuous_scale='Plasma')
        fig.update_layout(xaxis_tickangle=45, font=dict(size=12), showlegend=False)
        return fig
