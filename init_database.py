#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
用于创建BI报告系统所需的表结构并导入基础数据
Database initialization script for BI reporting system
"""

import pandas as pd
import clickhouse_connect
import logging
import os
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_to_clickhouse():
    """连接到ClickHouse数据库"""
    try:
        # 从环境变量获取连接配置，如果没有则使用默认值
        host = os.environ.get('CLICKHOUSE_HOST', '127.0.0.1')
        port = int(os.environ.get('CLICKHOUSE_PORT', '8123'))
        username = os.environ.get('CLICKHOUSE_USERNAME', 'default')
        password = os.environ.get('CLICKHOUSE_PASSWORD', '12345678')
        database = os.environ.get('CLICKHOUSE_DATABASE', 'default')
        
        client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password,
            database=database
        )
        logger.info(f"成功连接到ClickHouse数据库 {host}:{port}")
        return client
    except Exception as e:
        logger.error(f"连接ClickHouse失败: {e}")
        raise

def create_tables(client):
    """创建所有必要的表"""
    try:
        # 创建主数据表
        create_main_table_sql = """
        CREATE TABLE IF NOT EXISTS tbl_statistic_userapp_day (
            user_account String,
            ip_type Int32,
            app_category_major Int32,
            app_category_minor Int32,
            upstream_traffic Float64,
            downstream_traffic Float64,
            total_traffic Float64,
            duration Float64,
            stat_time String
        ) ENGINE = MergeTree()
        ORDER BY (user_account, stat_time)
        """
        
        # 创建应用大类表
        create_major_table_sql = """
        CREATE TABLE IF NOT EXISTS app_category_major (
            id UInt32,
            name String
        ) ENGINE = MergeTree()
        ORDER BY id
        """
        
        # 创建应用小类表
        create_minor_table_sql = """
        CREATE TABLE IF NOT EXISTS app_category_minor (
            id UInt32,
            name String
        ) ENGINE = MergeTree()
        ORDER BY id
        """
        
        # 执行创建表语句
        client.command(create_main_table_sql)
        logger.info("创建主数据表 tbl_statistic_userapp_day 完成")
        
        client.command(create_major_table_sql)
        logger.info("创建应用大类表 app_category_major 完成")
        
        client.command(create_minor_table_sql)
        logger.info("创建应用小类表 app_category_minor 完成")
        
    except Exception as e:
        logger.error(f"创建表失败: {e}")
        raise

def parse_csv_data(file_path: str) -> List[Dict[str, Any]]:
    """解析CSV文件数据"""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # 检查是否是带序号的格式: "序号→ID,名称"
                    if '→' in line:
                        parts = line.split('→', 1)
                        if len(parts) == 2:
                            id_name_part = parts[1]
                        else:
                            logger.warning(f"第{line_num}行格式不正确: {line}")
                            continue
                    else:
                        # 直接是 "ID,名称" 格式
                        id_name_part = line
                    
                    # 分离ID和名称
                    id_name_parts = id_name_part.split(',', 1)
                    if len(id_name_parts) != 2:
                        logger.warning(f"第{line_num}行ID和名称分离失败: {line}")
                        continue
                    
                    app_id = int(id_name_parts[0])
                    app_name = id_name_parts[1]
                    
                    data.append({'id': app_id, 'name': app_name})
                    
                except ValueError as e:
                    logger.warning(f"第{line_num}行数据解析失败: {line}, 错误: {e}")
                    continue
                    
        logger.info(f"成功解析 {len(data)} 条数据从文件 {file_path}")
        return data
        
    except Exception as e:
        logger.error(f"读取文件失败 {file_path}: {e}")
        raise

def import_data_to_table(client, table_name: str, data: List[Dict[str, Any]]):
    """导入数据到指定表"""
    try:
        if not data:
            logger.warning(f"没有数据导入到表 {table_name}")
            return
        
        # 删除现有数据
        client.command(f"TRUNCATE TABLE {table_name}")
        logger.info(f"清空表 {table_name}")
        
        # 准备数据
        df = pd.DataFrame(data)
        
        # 插入数据
        client.insert_df(table_name, df)
        logger.info(f"成功导入 {len(data)} 条数据到表 {table_name}")
        
        # 验证导入结果
        count = client.command(f"SELECT COUNT(*) FROM {table_name}")
        logger.info(f"表 {table_name} 当前记录数: {count}")
        
    except Exception as e:
        logger.error(f"导入数据到表 {table_name} 失败: {e}")
        raise

def get_default_app_major_data() -> List[Dict[str, Any]]:
    """获取默认应用大类数据"""
    return [
        {'id': 1, 'name': 'P2P文件下载'},
        {'id': 2, 'name': '网络语音'},
        {'id': 3, 'name': '即时通讯'},
        {'id': 4, 'name': 'Web浏览'},
        {'id': 5, 'name': '文件访问协议'},
        {'id': 6, 'name': 'HTTP视频流量'},
        {'id': 7, 'name': '股票'},
        {'id': 8, 'name': '游戏'},
        {'id': 9, 'name': '隧道协议'},
        {'id': 10, 'name': '网络攻击'},
        {'id': 11, 'name': '邮件收发'},
        {'id': 12, 'name': '数据库'},
        {'id': 13, 'name': '网管协议'},
        {'id': 14, 'name': '远程控制'},
        {'id': 15, 'name': '其他'}
    ]

def get_default_app_minor_data() -> List[Dict[str, Any]]:
    """获取默认应用小类数据（部分示例）"""
    return [
        {'id': 1100, 'name': '拉流地址封堵'},
        {'id': 7001, 'name': 'ICMP'},
        {'id': 7002, 'name': 'IGMP'},
        {'id': 7004, 'name': 'IP_IN_IP'},
        {'id': 7006, 'name': 'TCP'},
        {'id': 7008, 'name': 'EGP'},
        {'id': 7017, 'name': 'UDP'},
        {'id': 7047, 'name': 'GRE'},
        {'id': 7089, 'name': 'OSPF'},
        {'id': 7132, 'name': 'SCTP'}
    ]

def main():
    """主函数"""
    try:
        logger.info("开始数据库初始化...")
        
        # 连接数据库
        client = connect_to_clickhouse()
        
        # 创建表
        logger.info("创建数据库表...")
        create_tables(client)
        
        # 导入应用大类数据
        logger.info("导入应用大类数据...")
        if os.path.exists('app_catagory_major.csv'):
            # 从CSV文件导入
            major_data = parse_csv_data('app_catagory_major.csv')
        else:
            # 使用默认数据
            logger.info("未找到app_catagory_major.csv文件，使用默认数据")
            major_data = get_default_app_major_data()
        
        import_data_to_table(client, 'app_category_major', major_data)
        
        # 导入应用小类数据  
        logger.info("导入应用小类数据...")
        if os.path.exists('app_catagory_minor.csv'):
            # 从CSV文件导入
            minor_data = parse_csv_data('app_catagory_minor.csv')
        else:
            # 使用默认数据
            logger.info("未找到app_catagory_minor.csv文件，使用默认数据")
            minor_data = get_default_app_minor_data()
            
        import_data_to_table(client, 'app_category_minor', minor_data)
        
        logger.info("数据库初始化完成!")
        
        # 显示样本数据
        logger.info("\n=== 应用大类样本数据 ===")
        result = client.query("SELECT * FROM app_category_major ORDER BY id LIMIT 5")
        for row in result.result_rows:
            logger.info(f"ID: {row[0]}, 名称: {row[1]}")
            
        logger.info("\n=== 应用小类样本数据 ===")
        result = client.query("SELECT * FROM app_category_minor ORDER BY id LIMIT 5")
        for row in result.result_rows:
            logger.info(f"ID: {row[0]}, 名称: {row[1]}")
        
        # 显示统计信息
        major_count = client.command("SELECT COUNT(*) FROM app_category_major")
        minor_count = client.command("SELECT COUNT(*) FROM app_category_minor")
        
        logger.info(f"\n=== 数据统计 ===")
        logger.info(f"应用大类记录数: {major_count}")
        logger.info(f"应用小类记录数: {minor_count}")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("数据库初始化成功!")
    else:
        print("数据库初始化失败!")
        exit(1)