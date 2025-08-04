#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入应用分类数据到ClickHouse数据库
Import application category data to ClickHouse database
"""

import pandas as pd
import clickhouse_connect
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_to_clickhouse():
    """连接到ClickHouse数据库"""
    try:
        client = clickhouse_connect.get_client(
            host='127.0.0.1',
            port=8123,
            username='default',
            password='12345678',
            database='default'
        )
        logger.info("成功连接到ClickHouse数据库")
        return client
    except Exception as e:
        logger.error(f"连接ClickHouse失败: {e}")
        raise

def parse_csv_data(file_path):
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

def import_data_to_table(client, table_name, data):
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

def main():
    """主函数"""
    try:
        # 连接数据库
        client = connect_to_clickhouse()
        
        # 创建表
        with open('create_app_category_tables.sql', 'r', encoding='utf-8') as f:
            sql_commands = f.read()
        
        for command in sql_commands.split(';'):
            command = command.strip()
            if command and not command.startswith('--'):
                client.command(command)
        
        logger.info("数据库表创建完成")
        
        # 导入应用大类数据
        major_data = parse_csv_data('app_catagory_major.csv')
        import_data_to_table(client, 'app_category_major', major_data)
        
        # 导入应用小类数据  
        minor_data = parse_csv_data('app_catagory_minor.csv')
        import_data_to_table(client, 'app_category_minor', minor_data)
        
        logger.info("所有数据导入完成!")
        
        # 显示样本数据
        logger.info("\n=== 应用大类样本数据 ===")
        result = client.query("SELECT * FROM app_category_major ORDER BY id LIMIT 5")
        for row in result.result_rows:
            logger.info(f"ID: {row[0]}, 名称: {row[1]}")
            
        logger.info("\n=== 应用小类样本数据 ===")
        result = client.query("SELECT * FROM app_category_minor ORDER BY id LIMIT 5")
        for row in result.result_rows:
            logger.info(f"ID: {row[0]}, 名称: {row[1]}")
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("应用分类数据导入成功!")
    else:
        print("应用分类数据导入失败!")
        exit(1)