#!/usr/bin/env python3
"""
ClickHouse数据可视化Dashboard
基于Streamlit构建的互动式数据分析报表 - 重构版
使用DataService统一数据接口
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime, date
from data_service import DataService, FilterConditions
from pdf_generator import generate_complete_pdf_report

# 页面配置
st.set_page_config(
    page_title="用户流量分析Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式 - 放大标签页字体和图标
st.markdown("""
<style>
/* 标签页容器样式 */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}

/* 标签页基础样式 */
.stTabs [data-baseweb="tab"] {
    height: 60px;
    white-space: pre-wrap;
    background-color: #f0f2f6;
    border-radius: 8px 8px 0px 0px;
    gap: 8px;
    padding: 10px 16px;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

/* 选中状态的标签页 */
.stTabs [aria-selected="true"] {
    background-color: #ffffff;
    border-bottom: 3px solid #ff4b4b;
}



/* 选中状态的文字颜色 */
.stTabs [aria-selected="true"] > div {
    color: #ff4b4b !important;
}

/* 如果还有span元素，也确保样式生效 */
.stTabs [data-baseweb="tab"] span,
.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] div,
.stTabs [data-baseweb="tab"] * {
    font-size: 16px !important;
    font-weight: 600 !important;
    line-height: 1.2 !important;
}

</style>
""", unsafe_allow_html=True)

# 获取数据服务实例
@st.cache_resource
def get_data_service():
    """获取数据服务实例"""
    try:
        return DataService()
    except Exception as e:
        st.error(f"无法连接到数据服务: {str(e)}")
        return None


def create_filter_panel(data_service: DataService) -> FilterConditions:
    """创建筛选面板并返回筛选条件"""
    st.sidebar.markdown("## 🔍 筛选条件")
    

    
    # 初始化重置计数器
    if 'reset_counter' not in st.session_state:
        st.session_state.reset_counter = 0
    
    # 用户筛选
    user_options = ["全部"] + data_service.get_available_users(50)
    selected_user = st.sidebar.selectbox("选择用户", user_options, index=0, key=f"user_filter_{st.session_state.reset_counter}")
    user_filter = selected_user if selected_user and selected_user != "全部" else None
    
    # IP类型筛选
    ip_type_options = ["全部", "IPv4", "IPv6"]
    selected_ip_type = st.sidebar.selectbox("IP类型", ip_type_options, index=0, key=f"ip_type_filter_{st.session_state.reset_counter}")
    ip_type_filter = None
    if selected_ip_type == "IPv4":
        ip_type_filter = 0
    elif selected_ip_type == "IPv6":
        ip_type_filter = 1
    
    # 日期筛选
    date_range = data_service.get_date_range()
    if date_range['min_date'] and date_range['max_date']:
        # 确保日期格式正确
        min_date = date_range['min_date']
        max_date = date_range['max_date']
        
        # 转换为date对象
        if hasattr(min_date, 'date'):
            # 如果是pandas Timestamp或datetime对象
            min_date = min_date.date()
        elif isinstance(min_date, str):
            try:
                # 尝试多种日期格式
                for fmt in ['%Y/%m/%d %H:%M', '%Y-%m-%d', '%Y/%m/%d']:
                    try:
                        min_date = datetime.strptime(min_date, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    # 如果所有格式都失败，使用默认日期
                    min_date = datetime.now().date()
            except:
                min_date = datetime.now().date()
                
        if hasattr(max_date, 'date'):
            # 如果是pandas Timestamp或datetime对象
            max_date = max_date.date()
        elif isinstance(max_date, str):
            try:
                # 尝试多种日期格式
                for fmt in ['%Y/%m/%d %H:%M', '%Y-%m-%d', '%Y/%m/%d']:
                    try:
                        max_date = datetime.strptime(max_date, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    # 如果所有格式都失败，使用默认日期
                    max_date = datetime.now().date()
            except:
                max_date = datetime.now().date()
        
        # 添加日期范围信息显示
        #st.sidebar.markdown(f"**数据日期范围**: {min_date} 至 {max_date}")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            # 默认选择数据库的最小日期
            start_date = st.date_input("开始日期", 
                                     value=min_date,
                                     min_value=min_date,
                                     max_value=max_date,
                                     key=f"start_date_{st.session_state.reset_counter}")
        with col2:
            # 默认选择数据库的最大日期
            # 如果用户选择了开始日期，则结束日期的最小值应该是开始日期
            end_min_date = start_date if start_date and start_date >= min_date else min_date
            end_date = st.date_input("结束日期",
                                   value=max_date,
                                   min_value=end_min_date,
                                   max_value=max_date,
                                   key=f"end_date_{st.session_state.reset_counter}")
    else:
        start_date = None
        end_date = None
    
    # 应用大类筛选
    app_categories = ["全部"] + data_service.get_available_app_categories()
    selected_app_category = st.sidebar.selectbox("应用大类", app_categories, index=0, key=f"app_category_filter_{st.session_state.reset_counter}")
    app_category_filter = selected_app_category if selected_app_category and selected_app_category != "全部" else None
    
    # 日期筛选逻辑：只有当用户选择的日期范围不是完整范围时才应用筛选
    date_filter_active = False
    filter_start_date = None
    filter_end_date = None
    
    if date_range['min_date'] and date_range['max_date']:
        # 获取数据库的实际日期范围用于比较
        db_min_date = min_date
        db_max_date = max_date
        
        # 只有当用户选择的日期不是完整数据库范围时才应用筛选
        if start_date != db_min_date or end_date != db_max_date:
            filter_start_date = start_date
            filter_end_date = end_date
            date_filter_active = True
    
    # 创建筛选条件
    filters = FilterConditions(
        user_account=user_filter,
        ip_type=ip_type_filter,
        start_date=filter_start_date,
        end_date=filter_end_date,
        app_category_major=app_category_filter
    )
    
    #st.sidebar.markdown("---")
    
    # 显示当前筛选条件
    has_filters = any([user_filter, ip_type_filter is not None, app_category_filter, date_filter_active])
    if has_filters:
        #st.sidebar.info(f"📋 {filters.get_description()}")
        if st.sidebar.button("🔄 清除所有筛选", key="clear_button"):
            # 增加重置计数器，强制重新创建所有控件
            st.session_state.reset_counter += 1
            st.rerun()
    
    return filters

def import_csv_data(uploaded_file, data_service: DataService):
    """导入CSV数据到ClickHouse数据库"""
    try:
        # 读取上传的CSV文件
        content = uploaded_file.read()
        csv_content = content.decode('utf-8')
        
        # 创建DataFrame，指定列名
        column_names = [
            'user_account', 'ip_type', 'app_category_major', 'app_category_minor',
            'upstream_traffic', 'downstream_traffic', 'total_traffic', 
            'duration', 'stat_time'
        ]
        
        # 使用StringIO读取CSV数据
        df = pd.read_csv(io.StringIO(csv_content), header=None, names=column_names)
        
        # 数据验证和类型转换
        df['ip_type'] = pd.to_numeric(df['ip_type'], errors='coerce')
        df['app_category_major'] = pd.to_numeric(df['app_category_major'], errors='coerce')
        df['app_category_minor'] = pd.to_numeric(df['app_category_minor'], errors='coerce')
        df['upstream_traffic'] = pd.to_numeric(df['upstream_traffic'], errors='coerce')
        df['downstream_traffic'] = pd.to_numeric(df['downstream_traffic'], errors='coerce')
        df['total_traffic'] = pd.to_numeric(df['total_traffic'], errors='coerce')
        df['duration'] = pd.to_numeric(df['duration'], errors='coerce')
        
        # 处理空值
        df = df.dropna()
        
        if df.empty:
            return {'success': False, 'error': 'CSV文件中没有有效数据'}
        
        # 准备数据
        data_tuples = []
        for _, row in df.iterrows():
            data_tuples.append((
                row['user_account'],
                int(row['ip_type']),
                int(row['app_category_major']),
                int(row['app_category_minor']),
                int(row['upstream_traffic']),
                int(row['downstream_traffic']),
                int(row['total_traffic']),
                int(row['duration']),
                row['stat_time']
            ))
        
        # 执行批量插入
        data_service.client.insert('default.tbl_statistic_userapp_day', data_tuples)
        
        return {'success': True, 'count': len(data_tuples)}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    # 使用更大的标题
    st.markdown("## 📊 用户流量分析Dashboard")

    st.markdown("---")
    
    # 侧边栏 - 专注于筛选和操作
    st.sidebar.markdown("# 🎛️ 控制面板")
    st.sidebar.markdown("---")
    
    # 获取数据服务
    data_service = get_data_service()
    if not data_service:
        return
    
    # 创建筛选面板
    filters = create_filter_panel(data_service)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📄 报告导出",help="生成包含所有Dashboard页面图表和数据分析的完整PDF报告。报告将根据当前筛选条件生成，包含基础统计信息、流量分析、用户分析、应用分析和时间分析等所有模块。")
    
    # 添加PDF导出按钮
    if st.sidebar.button("📄 导出完整PDF报告", type="primary"):
        with st.spinner("正在生成完整PDF报告（包含所有图表）..."):
            try:
                pdf_buffer = generate_complete_pdf_report(filters)
                
                st.sidebar.success("完整PDF报告生成成功！")
                st.sidebar.download_button(
                    label="⬇️ 下载PDF报告",
                    data=pdf_buffer.getvalue(),
                    file_name=f"用户流量分析完整报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.sidebar.error(f"PDF生成失败: {str(e)}")
    
    st.sidebar.markdown("---")
    
    # CSV数据导入功能
    st.sidebar.markdown("### 📂 数据导入")
    uploaded_file = st.sidebar.file_uploader(
        "选择CSV文件导入", 
        type=['csv'],
        help="上传无表头的CSV文件，数据格式：user_account,ip_type,app_category_major,app_category_minor,upstream_traffic,downstream_traffic,total_traffic,duration,stat_time"
    )
    
    if uploaded_file is not None:
        # 预览CSV数据
        try:
            content = uploaded_file.read()
            csv_content = content.decode('utf-8')
            uploaded_file.seek(0)  # 重置文件指针
            
            # 只显示前几行作为预览
            lines = csv_content.strip().split('\n')[:3]
            st.sidebar.markdown("**📋 数据预览 (前3行):**")
            for i, line in enumerate(lines, 1):
                st.sidebar.text(f"{i}: {line[:50]}...")
            
            line_count = len(csv_content.strip().split('\n'))
            st.sidebar.markdown(f"**📊 文件信息:** 共 {line_count} 行数据")
            
        except Exception as e:
            st.sidebar.error(f"文件预览失败: {str(e)}")
        
        # 导入按钮
        if st.sidebar.button("🚀 导入数据到数据库", type="primary"):
            with st.spinner("正在导入CSV数据到ClickHouse数据库..."):
                try:
                    # 导入CSV数据
                    result = import_csv_data(uploaded_file, data_service)
                    if result['success']:
                        st.sidebar.success(f"✅ 数据导入成功！共导入 {result['count']} 条记录")
                        # 清除缓存以更新数据
                        st.cache_resource.clear()
                        st.rerun()
                    else:
                        st.sidebar.error(f"❌ 数据导入失败：{result['error']}")
                except Exception as e:
                    st.sidebar.error(f"❌ 数据导入失败：{str(e)}")
    
    st.sidebar.markdown("---")
    
    try:
        # 基础统计信息 - 使用二级标题，与主标题协调
        st.markdown("### 📈 基础统计信息")
        
        basic_stats = data_service.get_basic_stats(filters)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总记录数", f"{basic_stats['total_records']:,}")
        
        with col2:
            st.metric("用户总数", f"{basic_stats['total_users']:,}")
        
        with col3:
            st.metric("总流量", f"{basic_stats['total_traffic_gb']:.2f} GB")
        
        with col4:
            st.metric("应用大类数", f"{basic_stats['app_categories']:,}")
        
        st.markdown("---")
        
        # 使用标签页进行导航
        tab1, tab2, tab3, tab4 = st.tabs(["🌊 流量分析", "👥 用户分析", "📱 应用分析", "⏰ 时间分析"])
        
        with tab1:
            show_traffic_analysis(data_service, filters)
        with tab2:
            show_user_analysis(data_service, filters)
        with tab3:
            show_app_analysis(data_service, filters)
        with tab4:
            show_time_analysis(data_service, filters)
            
    except Exception as e:
        st.error(f"获取基础统计失败: {str(e)}")

def show_traffic_analysis(data_service, filters):
    """流量分析页面"""
    #st.markdown("### 🌊 流量分析")
    
    try:
        # 第一行：上行vs下行流量分布 和 IPv4 vs IPv6分布
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("上行vs下行流量分布")
            fig = data_service.create_traffic_pie_chart(filters)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("IPv4 vs IPv6 流量分布")
            fig = data_service.create_ip_type_pie_chart(filters, by_traffic=True)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        with col3:
            st.subheader("流量时长分布")
            fig = data_service.create_duration_bar_chart(filters)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        # 流量TOP排行
        st.subheader("🏆 流量TOP 20用户")
        top_users = data_service.get_top_traffic_users(20, filters)
        
        if not top_users.empty:
            fig = data_service.create_top_users_bar_chart(10, filters)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(top_users[['user_account', 'total_traffic_gb', 'upstream_gb', 'downstream_gb', 'sessions']])
        
    except Exception as e:
        st.error(f"流量分析数据获取失败: {str(e)}")

def show_user_analysis(data_service, filters):
    """用户分析页面"""
    #st.markdown("### 👥 用户分析")
    
    try:
        # 用户活跃度分析
        st.subheader("用户活跃度分析")
        fig = data_service.create_user_activity_pie_chart(filters)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        
        # 用户流量消耗分布
        st.subheader("用户流量消耗分布")
        fig = data_service.create_user_traffic_bar_chart(filters)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        
        # 高活跃且上行流量为主的用户分析
        st.subheader("🔍 高活跃上传用户分析")
        st.markdown("**分析条件**: 活跃用户(会话数≥5) + 上行流量>下行流量 + 上行流量≥100MB")
        
        upload_heavy_users = data_service.get_upload_heavy_users(20, filters)
        
        if not upload_heavy_users.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # 上行流量TOP用户柱状图
                fig = data_service.create_upload_users_bar_chart(10, filters)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # 上传比例散点图
                fig = data_service.create_upload_ratio_scatter_chart(20, filters)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            
            # 详细数据表格
            st.subheader("📋 高活跃上传用户详细数据")
            display_df = upload_heavy_users[['user_account', 'session_count', 'upstream_gb', 
                                           'downstream_gb', 'total_gb', 'upload_ratio']].copy()
            display_df.columns = ['用户账号', '会话数', '上行流量(GB)', '下行流量(GB)', '总流量(GB)', '上传比例']
            
            # 格式化上传比例显示
            display_df['上传比例'] = display_df['上传比例'].apply(
                lambda x: "仅上传" if x >= 999 else f"{x:.1f}:1"
            )
            
            # 添加风险等级（使用原始数值进行判断）
            def get_risk_level(row):
                ratio = upload_heavy_users.loc[row.name, 'upload_ratio'] 
                upstream_gb = row['上行流量(GB)']
                
                if (ratio >= 999 or ratio >= 10) and upstream_gb >= 5:
                    return "🔴 高风险"
                elif (ratio >= 999 or ratio >= 5) and upstream_gb >= 1:
                    return "🟡 中风险" 
                else:
                    return "🟢 低风险"
            
            display_df['风险等级'] = display_df.apply(get_risk_level, axis=1)
            st.dataframe(display_df, use_container_width=True)
            
            # 统计摘要
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("符合条件用户数", len(upload_heavy_users))
            with col2:
                avg_ratio = upload_heavy_users['upload_ratio'].mean()
                st.metric("平均上传比例", f"{avg_ratio:.1f}:1")
            with col3:
                total_upstream = upload_heavy_users['upstream_gb'].sum()
                st.metric("总上行流量", f"{total_upstream:.1f} GB")
            with col4:
                high_risk_count = len(display_df[display_df['风险等级'] == '🔴 高风险'])
                st.metric("高风险用户数", high_risk_count)
            
            st.info("""
            📊 **分析说明**: 
            - **高活跃**: 会话数≥5次，表示用户使用频繁
            - **上传为主**: 上行流量>下行流量，可能涉及内容上传、数据同步等行为
            - **上传比例**: "仅上传"表示下行流量为0，其他显示为上传:下载的比例
            - **风险等级**: 基于上传比例和流量大小综合评估，"仅上传"用户自动视为高风险
            - **业务建议**: 关注高风险用户的使用行为，确保合规使用
            """)
        else:
            st.warning("未找到符合条件的高活跃上传用户")
    
    except Exception as e:
        st.error(f"用户分析数据获取失败: {str(e)}")

def show_app_analysis(data_service, filters):
    """应用分析页面"""
    #st.markdown("### 📱 应用分析")
    
    try:
        # 第一行：柱状图和饼图
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("应用大类上行流量TOP 10")
            fig = data_service.create_app_traffic_bar_chart(10, filters)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("上行流量占比分布")
            fig_pie = data_service.create_app_traffic_pie_chart(10, filters)
            if fig_pie:
                st.plotly_chart(fig_pie, use_container_width=True)
        
        # 第二行：用户数分析
        st.subheader("应用大类用户数TOP 10")
        fig_users = data_service.create_app_users_bar_chart(10, filters)
        if fig_users:
            st.plotly_chart(fig_users, use_container_width=True)
        
        # 应用小类分析
        st.subheader("热门应用上行流量详情TOP 20")
        app_minor = data_service.get_app_minor_analysis(20, filters)
        
        if not app_minor.empty:
            # 显示应用名称、上行流量和占比
            display_df = app_minor[['应用名称', 'major_display', 'minor_display', 'upstream_traffic_gb', 'upstream_percentage', 'user_count']].copy()
            display_df.columns = ['应用名称', '大类', '小类', '上行流量(GB)', '占比(%)', '用户数']
            # 格式化数据
            display_df['上行流量(GB)'] = display_df['上行流量(GB)'].round(2)
            display_df['占比(%)'] = display_df['占比(%)'].round(2)
            st.dataframe(display_df, use_container_width=True)
            
            st.info("📋 **表格说明**: 显示上行流量消耗最大的前20个应用，包含具体的应用名称、分类信息和在指定时间内的流量占比。")
        
        # 应用大类TOP10及其客户TOP10分析
        st.subheader("📊 应用大类TOP10 & 客户流量详情")
        category_users = data_service.get_app_category_top_users(10, 10, filters)
        
        if not category_users.empty:
            # 按应用大类分组显示
            categories = category_users['category_name'].unique()
            
            for category in categories:
                category_data = category_users[category_users['category_name'] == category]
                
                if not category_data.empty:
                    # 获取大类总流量
                    category_total_gb = category_data.iloc[0]['category_total_traffic'] / (1024*1024*1024)
                    
                    # 创建可展开的部分
                    with st.expander(f"🔍 {category} (总上行流量: {category_total_gb:.2f}GB)", expanded=False):
                        # 显示该大类中的TOP10用户
                        display_df = category_data[['user_account', 'user_upstream_gb', 'user_downstream_gb', 
                                                  'user_total_gb', 'session_count', 'user_traffic_percentage']].copy()
                        display_df.columns = ['用户账号', '上行流量(GB)', '下行流量(GB)', '总流量(GB)', '会话数', '占大类比例(%)']
                        
                        # 格式化数据
                        display_df['上行流量(GB)'] = display_df['上行流量(GB)'].round(3)
                        display_df['下行流量(GB)'] = display_df['下行流量(GB)'].round(3)
                        display_df['总流量(GB)'] = display_df['总流量(GB)'].round(3)
                        display_df['占大类比例(%)'] = display_df['占大类比例(%)'].round(2)
                        
                        st.dataframe(display_df, use_container_width=True)
                        
                        # 添加统计信息
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("TOP10用户数", len(category_data))
                        with col2:
                            top10_upstream = category_data['user_upstream_gb'].sum()
                            st.metric("TOP10总上行流量", f"{top10_upstream:.2f}GB")
                        with col3:
                            top10_percentage = (top10_upstream / category_total_gb * 100) if category_total_gb > 0 else 0
                            st.metric("TOP10占大类比例", f"{top10_percentage:.1f}%")
            
            st.info("📋 **表格说明**: 显示上行流量TOP10的应用大类，以及每个大类中上行流量TOP10的用户详情。点击展开可查看具体用户数据。")
        else:
            st.warning("未找到符合条件的应用大类和用户数据")
    
    except Exception as e:
        st.error(f"应用分析数据获取失败: {str(e)}")

def show_time_analysis(data_service, filters):
    """时间分析页面"""
    #st.markdown("### ⏰ 时间分析")
    
    try:
        # 检查data_service是否有新方法
        if not hasattr(data_service, 'create_flexible_time_chart'):
            st.error("数据服务缺少新的时间分析方法，请重启应用")
            return
        
        # 时间分析主体布局：左侧图表+表格，右侧控制面板
        # st.subheader("📈 时间趋势分析")
        
        # 创建左右三列：左侧内容区，中间分隔线，右侧控制面板
        content_col, divider_col, control_col = st.columns([3, 0.05, 1])
        
        # 中间分隔线
        with divider_col:
            st.markdown("""
            <div style="
                border-left: 1px solid #ddd; 
                height: 800px; 
                margin: 0 auto;
            "></div>
            """, unsafe_allow_html=True)
        
        # 右侧控制面板
        with control_col:
            st.markdown("### 参数设置")
            
            # 分组字段选择
            group_options = {
                'none': '无分组(总体)',
                'ip_type': 'IP类型',
                'app_category_major': '应用大类',
                'user_account': '用户(TOP10)'
            }
            selected_group = st.selectbox(
                "分组字段",
                options=list(group_options.keys()),
                format_func=lambda x: group_options[x],
                key="time_analysis_group",
                index=0
            )
            
            # 指标类型选择
            metric_options = {
                'session_count': '会话数',
                'traffic': '流量',
                'session_duration': '平均会话时长'
            }
            selected_metric = st.selectbox(
                "纵轴指标",
                options=list(metric_options.keys()),
                format_func=lambda x: metric_options[x],
                key="time_analysis_metric",
                index=0
            )
            
            # 流量类型选择（仅当指标为流量时显示）
            if selected_metric == 'traffic':
                traffic_options = {
                    'total': '总流量',
                    'upstream': '上行流量',
                    'downstream': '下行流量'
                }
                selected_traffic = st.selectbox(
                    "流量类型",
                    options=list(traffic_options.keys()),
                    format_func=lambda x: traffic_options[x],
                    key="time_analysis_traffic",
                    index=0
                )
            else:
                selected_traffic = 'total'
            
            # 显示说明信息
            st.markdown("**💡 说明**")
            if selected_group == 'user_account':
                st.info("用户分组显示流量TOP10的用户，避免图表过于复杂。")
            else:
                st.info("横轴：日期时间\n纵轴：所选指标")
        
        with content_col:
            # 图表区域
            st.markdown("#### 📈 趋势图表")
            fig = data_service.create_flexible_time_chart(
                group_by_field=selected_group,
                metric_type=selected_metric,
                traffic_type=selected_traffic,
                filters=filters
            )
            
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("没有找到符合条件的数据")
            
            # 表格区域
            st.markdown("#### 📋 详细数据")
            time_data = data_service.get_flexible_time_analysis(
                group_by_field=selected_group,
                metric_type=selected_metric,
                traffic_type=selected_traffic,
                filters=filters
            )
            
            if not time_data.empty:
                # 格式化显示
                display_df = time_data.copy()
                if 'value' in display_df.columns:
                    if selected_metric == 'traffic':
                        display_df['value'] = display_df['value'].round(3)
                        display_df.rename(columns={'value': f'{metric_options[selected_metric]}(GB)'}, inplace=True)
                    elif selected_metric == 'session_duration':
                        display_df['value'] = display_df['value'].round(2)
                        display_df.rename(columns={'value': f'{metric_options[selected_metric]}(秒)'}, inplace=True)
                    else:
                        display_df.rename(columns={'value': metric_options[selected_metric]}, inplace=True)
                
                if 'date_key' in display_df.columns:
                    display_df.rename(columns={'date_key': '日期'}, inplace=True)
                if 'category' in display_df.columns:
                    display_df.rename(columns={'category': '分组'}, inplace=True)
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.warning("没有找到符合条件的数据")
        
    
    except Exception as e:
        st.error(f"时间分析数据获取失败: {str(e)}")

if __name__ == "__main__":
    main()