#!/usr/bin/env python3
"""
测试日期筛选功能
"""
from datetime import date
from data_service import DataService, FilterConditions

def test_date_filtering():
    """测试日期筛选功能"""
    ds = DataService()
    
    print("=== 测试日期筛选功能 ===")
    
    # 获取数据库中的日期范围
    date_range = ds.get_date_range()
    print(f"数据库日期范围: {date_range}")
    
    # 获取未筛选的基础统计
    print("\n1. 无筛选条件:")
    stats = ds.get_basic_stats()
    print(f"总记录数: {stats['total_records']}")
    
    # 测试只有开始日期的筛选
    print("\n2. 只有开始日期 (2025-07-09):")
    filters = FilterConditions(start_date=date(2025, 7, 9))
    print(f"WHERE子句: {filters.build_where_clause()}")
    stats = ds.get_basic_stats(filters)
    print(f"总记录数: {stats['total_records']}")
    
    # 测试只有结束日期的筛选
    print("\n3. 只有结束日期 (2025-07-09):")
    filters = FilterConditions(end_date=date(2025, 7, 9))
    print(f"WHERE子句: {filters.build_where_clause()}")
    stats = ds.get_basic_stats(filters)
    print(f"总记录数: {stats['total_records']}")
    
    # 测试开始和结束日期都有的筛选
    print("\n4. 开始和结束日期都有 (2025-07-09 到 2025-07-09):")
    filters = FilterConditions(start_date=date(2025, 7, 9), end_date=date(2025, 7, 9))
    print(f"WHERE子句: {filters.build_where_clause()}")
    stats = ds.get_basic_stats(filters)
    print(f"总记录数: {stats['total_records']}")
    
    # 测试超出范围的日期筛选
    print("\n5. 超出范围的日期筛选 (2025-07-10):")
    filters = FilterConditions(start_date=date(2025, 7, 10))
    print(f"WHERE子句: {filters.build_where_clause()}")
    stats = ds.get_basic_stats(filters)
    print(f"总记录数: {stats['total_records']}")
    
    # 测试早于数据日期的筛选
    print("\n6. 早于数据日期的筛选 (2025-07-08):")
    filters = FilterConditions(end_date=date(2025, 7, 8))
    print(f"WHERE子句: {filters.build_where_clause()}")
    stats = ds.get_basic_stats(filters)
    print(f"总记录数: {stats['total_records']}")
    
    ds.close()

if __name__ == "__main__":
    test_date_filtering()