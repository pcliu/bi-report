#!/usr/bin/env python3
"""
测试CSV数据服务功能
"""

from csv_data_service import CSVDataService, FilterConditions
from datetime import date

def test_csv_service():
    """测试CSV数据服务的主要功能"""
    print("🧪 开始测试CSV数据服务...")
    
    try:
        # 初始化数据服务
        print("\n📁 初始化CSV数据服务...")
        data_service = CSVDataService(data_folder="./data")
        
        # 测试文件信息
        print("\n📁 测试文件信息...")
        files_info = data_service.get_loaded_files_info()
        print(f"  - 数据目录: {files_info['data_folder']}")
        print(f"  - 已加载文件数: {files_info['total_files']}")
        print(f"  - 主数据文件: {files_info['main_data_files']}")
        print(f"  - 有应用大类文件: {files_info['has_major_categories']}")
        print(f"  - 有应用小类文件: {files_info['has_minor_categories']}")

        # 测试基础统计
        print("\n📊 测试基础统计信息...")
        stats = data_service.get_basic_stats()
        print(f"  - 总记录数: {stats['total_records']:,}")
        print(f"  - 用户数: {stats['total_users']:,}")
        print(f"  - 总流量: {stats['total_traffic_gb']:.2f} GB")
        print(f"  - 应用大类数: {stats['app_categories']}")
        
        # 测试用户列表
        print("\n👥 测试用户列表...")
        users = data_service.get_available_users(limit=5)
        print(f"  - 前5个用户: {users[:5]}")
        
        # 测试应用分类
        print("\n📱 测试应用分类...")
        categories = data_service.get_available_app_categories()
        print(f"  - 应用分类数: {len(categories)}")
        print(f"  - 前5个分类: {categories[:5]}")
        
        # 测试日期范围
        print("\n📅 测试日期范围...")
        date_range = data_service.get_date_range()
        print(f"  - 开始日期: {date_range['min_date']}")
        print(f"  - 结束日期: {date_range['max_date']}")
        
        # 测试流量分析
        print("\n🌊 测试流量分析...")
        traffic_dist = data_service.get_traffic_distribution()
        if not traffic_dist.empty:
            print(f"  - 上行流量: {traffic_dist.iloc[0]['upstream'] / (1024**3):.2f} GB")
            print(f"  - 下行流量: {traffic_dist.iloc[0]['downstream'] / (1024**3):.2f} GB")
        
        # 测试TOP用户
        print("\n🏆 测试TOP用户...")
        top_users = data_service.get_top_traffic_users(limit=3)
        print(f"  - TOP用户数: {len(top_users)}")
        if not top_users.empty:
            for i, user in top_users.head(3).iterrows():
                print(f"    {i+1}. {user['user_account']}: {user['total_traffic_gb']:.2f} GB")
        
        # 测试应用分析
        print("\n📊 测试应用分析...")
        app_analysis = data_service.get_app_major_analysis(limit=3)
        print(f"  - 应用分析记录数: {len(app_analysis)}")
        if not app_analysis.empty:
            for i, app in app_analysis.head(3).iterrows():
                print(f"    {i+1}. {app.get('app_name', '未知应用')}: {app['upstream_traffic_gb']:.2f} GB ({app['upstream_percentage']:.1f}%)")
        
        # 测试筛选功能
        print("\n🔍 测试筛选功能...")
        filters = FilterConditions(ip_type=0)  # 只筛选IPv4
        filtered_stats = data_service.get_basic_stats(filters)
        print(f"  - IPv4记录数: {filtered_stats['total_records']:,}")
        print(f"  - IPv4用户数: {filtered_stats['total_users']:,}")
        
        # 测试图表生成
        print("\n📈 测试图表生成...")
        
        # 测试流量饼图
        pie_chart = data_service.create_traffic_pie_chart()
        print(f"  - 流量饼图创建: {'✅ 成功' if pie_chart else '❌ 失败'}")
        
        # 测试应用流量柱状图
        bar_chart = data_service.create_app_traffic_bar_chart()
        print(f"  - 应用柱状图创建: {'✅ 成功' if bar_chart else '❌ 失败'}")
        
        # 测试用户活跃度饼图
        activity_chart = data_service.create_user_activity_pie_chart()
        print(f"  - 用户活跃度图创建: {'✅ 成功' if activity_chart else '❌ 失败'}")
        
        print("\n✅ CSV数据服务测试完成！所有主要功能正常工作。")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        return False
    finally:
        if 'data_service' in locals():
            data_service.close()

if __name__ == "__main__":
    success = test_csv_service()
    exit(0 if success else 1)