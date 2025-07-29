#!/usr/bin/env python3
"""
CSV数据导入ClickHouse脚本
"""

import pandas as pd
import clickhouse_connect
from datetime import datetime

def main():
    # ClickHouse连接配置
    host = '127.0.0.1'
    port = 8123
    username = 'default'
    password = '12345678'
    
    # CSV文件路径
    csv_file = 'tbl_statistic_userapp_day_2025-07-09_00_00_00.csv'
    
    # 表名
    table_name = 'tbl_statistic_userapp_day'
    
    try:
        # 连接ClickHouse
        client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password
        )
        
        print(f"成功连接到ClickHouse: {host}:{port}")
        
        # 读取CSV文件
        df = pd.read_csv(csv_file, encoding='utf-8')
        print(f"成功读取CSV文件，共 {len(df)} 行数据")
        
        # 检查数据类型
        print("\n数据类型信息:")
        print(df.dtypes)
        
        # 检查是否有缺失值
        print("\n缺失值检查:")
        print(df.isnull().sum())
        
        # 显示前几行数据
        print("\n数据预览:")
        print(df.head())
        
        # 先删除已存在的表，然后重新创建
        #drop_table_sql = f"DROP TABLE IF EXISTS {table_name}"
        #client.command(drop_table_sql)
        #print(f"已删除表 {table_name}")
        
        # 创建新表，流量字段使用Float64类型
        #create_table_sql = f"""
        #CREATE TABLE {table_name} (
        #    user_account String,
        #    ip_type Int32,
        #    app_category_major Int32,
        #    app_category_minor Int32,
        #    upstream_traffic Float64,
        #    downstream_traffic Float64,
        #    total_traffic Float64,
        #    duration Float64,
        #    stat_time String
        #) ENGINE = MergeTree()
        #ORDER BY (user_account, stat_time)
        #"""
        
        #client.command(create_table_sql)
        #print(f"表 {table_name} 创建成功或已存在")
        
        # 准备数据列名映射
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
        
        # 重命名列
        df_renamed = df.rename(columns=column_mapping)
        
        # 数据类型转换和清理
        print("\n处理数据类型...")
        
        # 确保整数列的数据类型正确
        int_columns = ['ip_type', 'app_category_major', 'app_category_minor']
        for col in int_columns:
            if col in df_renamed.columns:
                df_renamed[col] = df_renamed[col].fillna(0).astype('int32')
        
        # 确保浮点数列的数据类型正确
        float_columns = ['upstream_traffic', 'downstream_traffic', 'total_traffic', 'duration']
        for col in float_columns:
            if col in df_renamed.columns:
                df_renamed[col] = df_renamed[col].fillna(0.0).astype('float64')
        
        # 确保字符串列正确
        if 'user_account' in df_renamed.columns:
            df_renamed['user_account'] = df_renamed['user_account'].astype(str)
        if 'stat_time' in df_renamed.columns:
            df_renamed['stat_time'] = df_renamed['stat_time'].astype(str)
        
        print("数据类型处理完成")
        
        # 数据插入
        print("\n开始插入数据...")
        
        # 批量插入数据
        client.insert_df(table_name, df_renamed)
        
        print(f"数据插入成功！共插入 {len(df)} 行数据")
        
        # 验证插入结果
        count_result = client.query(f"SELECT COUNT(*) as count FROM {table_name}")
        total_count = count_result.result_rows[0][0]
        print(f"表中总数据行数: {total_count}")
        
        # 查看前几行数据
        sample_result = client.query(f"SELECT * FROM {table_name} LIMIT 5")
        print("\n插入后的数据样本:")
        for row in sample_result.result_rows:
            print(row)
            
    except Exception as e:
        print(f"出现错误: {str(e)}")
        raise
    finally:
        if 'client' in locals():
            client.close()
            print("\n数据库连接已关闭")

if __name__ == "__main__":
    main()