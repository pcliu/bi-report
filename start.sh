#!/bin/bash

# 等待ClickHouse服务启动
echo "等待ClickHouse服务启动..."

# 等待ClickHouse健康检查通过
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f --max-time 5 http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/ping > /dev/null 2>&1; then
        echo "ClickHouse服务已启动"
        break
    else
        echo "等待ClickHouse启动... (尝试 $attempt/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    echo "错误：ClickHouse服务启动超时"
    exit 1
fi

# 等待额外时间确保ClickHouse完全就绪
sleep 10

# 检查并创建应用分类表（如果不存在）
echo "检查并创建应用分类表..."
python3 -c "
import sys
sys.path.append('/app')
from data_service import DataService

try:
    ds = DataService()
    # 检查app_category_major表是否存在
    result = ds.execute_query('SHOW TABLES LIKE \'app_category_major\'')
    if result.empty:
        print('创建app_category_major表...')
        create_major_sql = '''
        CREATE TABLE IF NOT EXISTS app_category_major (
            id UInt32,
            name String
        ) ENGINE = MergeTree()
        ORDER BY id
        '''
        ds.client.command(create_major_sql)
    
    # 检查app_category_minor表是否存在
    result = ds.execute_query('SHOW TABLES LIKE \'app_category_minor\'')
    if result.empty:
        print('创建app_category_minor表...')
        create_minor_sql = '''
        CREATE TABLE IF NOT EXISTS app_category_minor (
            id UInt32,
            name String
        ) ENGINE = MergeTree()
        ORDER BY id
        '''
        ds.client.command(create_minor_sql)
    
    print('应用分类表检查完成')
except Exception as e:
    print(f'创建表时出错: {e}')
"

# 导入应用分类数据（如果表为空）
echo "检查并导入应用分类数据..."
python3 -c "
import sys
sys.path.append('/app')
from data_service import DataService
import pandas as pd

try:
    ds = DataService()
    
    # 检查app_category_major表是否有数据
    result = ds.execute_query('SELECT COUNT(*) as count FROM app_category_major')
    if result.iloc[0]['count'] == 0:
        print('导入应用大类数据...')
        try:
            df_major = pd.read_csv('/app/app_catagory_major.csv', header=None, names=['id', 'name'])
            ds.client.insert_df('app_category_major', df_major)
            print(f'导入了 {len(df_major)} 条应用大类数据')
        except FileNotFoundError:
            print('未找到app_catagory_major.csv文件')
        except Exception as e:
            print(f'导入应用大类数据失败: {e}')
    
    # 检查app_category_minor表是否有数据
    result = ds.execute_query('SELECT COUNT(*) as count FROM app_category_minor')
    if result.iloc[0]['count'] == 0:
        print('导入应用小类数据...')
        try:
            df_minor = pd.read_csv('/app/app_catagory_minor.csv', header=None, names=['id', 'name'])
            ds.client.insert_df('app_category_minor', df_minor)
            print(f'导入了 {len(df_minor)} 条应用小类数据')
        except FileNotFoundError:
            print('未找到app_catagory_minor.csv文件')
        except Exception as e:
            print(f'导入应用小类数据失败: {e}')
    
    print('应用分类数据检查完成')
except Exception as e:
    print(f'导入数据时出错: {e}')
"


# 启动Streamlit应用
echo "启动Streamlit应用..."
exec streamlit run streamlit_dashboard.py --server.address 0.0.0.0 --server.port 8501