import sqlite3
import os
from pathlib import Path

DB_NAME = "bi_report.db"

class DBManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            self.db_path = os.path.join(os.getcwd(), DB_NAME)
        else:
            self.db_path = db_path
        
        self.init_db()

    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_db(self):
        """初始化数据库表"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 流量数据表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS traffic_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_account TEXT,
            ip_type INTEGER,
            app_category_major INTEGER,
            app_category_minor INTEGER,
            upstream_traffic REAL,
            downstream_traffic REAL,
            total_traffic REAL,
            duration REAL,
            stat_time TEXT,
            import_batch_id TEXT,
            new_connections INTEGER,
            removed_connections INTEGER
        )
        ''')

        # 创建索引 - 单列索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stat_time ON traffic_data(stat_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_account ON traffic_data(user_account)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_app_major ON traffic_data(app_category_major)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip_type ON traffic_data(ip_type)')
        
        # 复合索引 - 加速时间分析查询
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_user ON traffic_data(stat_time, user_account)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_ip ON traffic_data(stat_time, ip_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_app ON traffic_data(stat_time, app_category_major)')

        # 应用大类表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_major_categories (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
        ''')

        # 应用小类表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_minor_categories (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
        ''')

        conn.commit()
        conn.close()
        print(f"✅ 数据库已初始化: {self.db_path}")

    def get_db_path(self):
        return self.db_path
