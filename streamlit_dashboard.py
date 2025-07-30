#!/usr/bin/env python3
"""
ClickHouse数据可视化Dashboard
基于Streamlit构建的互动式数据分析报表 - 重构版
使用DataService统一数据接口
"""

import streamlit as st
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

/* 标签页文字样式 - 使用更具体的选择器 */
.stTabs [data-baseweb="tab"] > div {
    font-size: 24px !important;
    font-weight: 600 !important;
    line-height: 1.2 !important;
    color: #262730 !important;
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
    font-size: 24px !important;
    font-weight: 600 !important;
    line-height: 1.2 !important;
}

/* 强制覆盖所有可能的样式 */
div[data-baseweb="tab"] {
    font-size: 24px !important;
}

div[data-baseweb="tab"] > * {
    font-size: 24px !important;
    font-weight: 600 !important;
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
        
        # 如果是字符串，转换为date对象
        if isinstance(min_date, str):
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
                
        if isinstance(max_date, str):
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
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("开始日期", 
                                     value=min_date,
                                     key=f"start_date_{st.session_state.reset_counter}")
        with col2:
            end_date = st.date_input("结束日期",
                                   value=max_date,
                                   key=f"end_date_{st.session_state.reset_counter}")
    else:
        start_date = None
        end_date = None
    
    # 应用大类筛选
    app_categories = ["全部"] + data_service.get_available_app_categories()
    selected_app_category = st.sidebar.selectbox("应用大类", app_categories, index=0, key=f"app_category_filter_{st.session_state.reset_counter}")
    app_category_filter = selected_app_category if selected_app_category and selected_app_category != "全部" else None
    
    # 创建筛选条件
    filters = FilterConditions(
        user_account=user_filter,
        ip_type=ip_type_filter,
        start_date=start_date,
        end_date=end_date,
        app_category_major=app_category_filter
    )
    
    #st.sidebar.markdown("---")
    
    # 显示当前筛选条件
    has_filters = any([user_filter, ip_type_filter is not None, app_category_filter])
    if has_filters:
        #st.sidebar.info(f"📋 {filters.get_description()}")
        if st.sidebar.button("🔄 清除所有筛选", key="clear_button"):
            # 增加重置计数器，强制重新创建所有控件
            st.session_state.reset_counter += 1
            st.rerun()
    
    return filters

def main():
    # 使用更大的标题
    st.markdown("# 📊 用户流量分析Dashboard")

    st.markdown("---")
    
    # 侧边栏 - 专注于筛选和操作
    st.sidebar.title("🎛️ 控制面板")
    
    # 获取数据服务
    data_service = get_data_service()
    if not data_service:
        return
    
    # 创建筛选面板
    filters = create_filter_panel(data_service)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📄 报告导出")
    
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
    
    st.sidebar.info("📊 此PDF包含所有Dashboard页面的图表和数据分析")
    st.sidebar.markdown("---")
    
    try:
        # 基础统计信息 - 使用二级标题，与主标题协调
        st.markdown("## 📈 基础统计信息")
        
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
        
        # 使用标签页进行导航 - 放在基础统计信息下面
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
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("上行vs下行流量分布")
            fig = data_service.create_traffic_pie_chart(filters)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
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
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("应用大类流量TOP 10")
            fig = data_service.create_app_traffic_bar_chart(10, filters)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("应用大类用户数TOP 10")
            fig = data_service.create_app_users_bar_chart(10, filters)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        # 应用小类分析
        st.subheader("热门应用小类TOP 20")
        app_minor = data_service.get_app_minor_analysis(20, filters)
        
        if not app_minor.empty:
            # 重命名列以便更好理解
            display_df = app_minor[['应用标识', 'app_category_major', 'app_category_minor', 'total_traffic_gb', 'user_count']].copy()
            display_df.columns = ['应用标识', '大类编号', '小类编号', '流量(GB)', '用户数']
            st.dataframe(display_df)
            
            st.info("📋 **表格说明**: 应用标识格式为'大类-小类'，如'4-17649'表示大类4下的小类17649应用。")
    
    except Exception as e:
        st.error(f"应用分析数据获取失败: {str(e)}")

def show_time_analysis(data_service, filters):
    """时间分析页面"""
    #st.markdown("### ⏰ 时间分析")
    
    try:
        st.subheader("数据统计时间分布")
        fig = data_service.create_time_series_chart(filters)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        
        time_data = data_service.get_time_analysis(filters)
        if not time_data.empty:
            st.dataframe(time_data)
    
    except Exception as e:
        st.error(f"时间分析数据获取失败: {str(e)}")

if __name__ == "__main__":
    main()