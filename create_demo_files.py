#!/usr/bin/env python3
"""
创建演示用的多日期CSV文件
"""

import pandas as pd
import random
from pathlib import Path
from datetime import datetime, timedelta

def create_demo_files():
    """创建一些演示用的多日期文件"""
    data_dir = Path("./data")
    
    # 检查是否已经有主数据文件
    existing_files = list(data_dir.glob("tbl_statistic_userapp_day*.csv"))
    if not existing_files:
        print("未找到现有数据文件，无法创建演示文件")
        return
    
    # 读取现有的第一个文件作为模板
    template_file = existing_files[0]
    print(f"📄 使用模板文件: {template_file}")
    
    # 读取模板数据
    df_template = pd.read_csv(template_file, names=[
        'user_account', 'ip_type', 'app_category_major', 'app_category_minor',
        'upstream_traffic', 'downstream_traffic', 'total_traffic', 'duration', 'stat_time'
    ], header=None)
    
    print(f"📊 模板文件包含 {len(df_template)} 行数据")
    
    # 创建未来几天的文件
    base_date = datetime(2025, 7, 12)
    
    for i in range(1, 4):  # 创建3个额外的日期文件
        new_date = base_date + timedelta(days=i)
        new_date_str = new_date.strftime('%Y-%m-%d')
        new_file_name = f"tbl_statistic_userapp_day_{new_date_str.replace('-', '-')}_00_00_00.csv"
        new_file_path = data_dir / new_file_name
        
        # 如果文件已存在，跳过
        if new_file_path.exists():
            print(f"⏭️  文件已存在，跳过: {new_file_name}")
            continue
        
        # 创建新数据：从模板中随机采样部分数据，并修改时间和流量
        sample_size = min(1000, len(df_template))  # 采样1000行或全部数据
        df_new = df_template.sample(n=sample_size).copy()
        
        # 修改时间
        df_new['stat_time'] = f"{new_date_str} 00:00:00"
        
        # 随机调整流量数据（在原值的0.5-1.5倍之间）
        traffic_cols = ['upstream_traffic', 'downstream_traffic', 'total_traffic']
        for col in traffic_cols:
            df_new[col] = df_new[col] * (0.5 + random.random())
        
        # 保存新文件
        df_new.to_csv(new_file_path, index=False, header=False)
        print(f"✅ 创建演示文件: {new_file_name} ({len(df_new)} 行)")
    
    print(f"\n🎉 演示文件创建完成！现在data目录中有:")
    all_files = list(data_dir.glob("tbl_statistic_userapp_day*.csv"))
    for file in sorted(all_files):
        print(f"  • {file.name}")

if __name__ == "__main__":
    create_demo_files()