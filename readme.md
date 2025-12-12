# BI 报告系统

## 你能用它做什么
- 基于 Streamlit 的交互式网络流量分析仪表板，可导出 PDF。
- 直接读取 `data/` 下的 CSV，自动导入 SQLite 并做聚合分析。
- 内置应用/用户/时间多维度筛选，含 16+ 图表和 PDF 报告生成功能。

## 快速开始（最短路径）
```bash
# 1) 创建并激活虚拟环境
python3 -m venv .venv && source .venv/bin/activate  # Windows 用 .venv\Scripts\activate

# 2) 安装依赖（推荐 uv）
pip install uv && uv sync  # 或 pip install -r requirements.txt

# 3) 放置 CSV 至 data/ 目录
#    必需：tbl_statistic_userapp_day*.csv、app_catagory_major.csv、app_catagory_minor.csv

# 4) 启动
streamlit run streamlit_dashboard.py
```
打开后自动加载数据，需刷新时点击侧边栏 “🔄 从磁盘重新加载数据”。

## 数据与 Schema
- `traffic_data` 表：用户账号、IP 类型、应用大/小类、上下行/总流量、时长、统计时间等字段，含时间/用户/应用/类型等索引，所有聚合在数据库完成。
- CSV 格式：
  - `tbl_statistic_userapp_day*.csv`（无表头）：`user_account,ip_type,app_category_major,app_category_minor,upstream_traffic,downstream_traffic,total_traffic,duration,stat_time`
  - `app_catagory_{major,minor}.csv`（无表头）：`ID,名称`

## 目录速览
```
bi-report/
├── streamlit_dashboard.py   # Web 应用入口
├── data_service.py          # 数据查询/图表生成
├── db_manager.py            # SQLite 初始化与索引
├── pdf_generator.py         # PDF 导出
├── data/                    # CSV 数据目录
└── bi_report.db             # 自动生成的数据库
```

## 更多
- 部署/运维请看 `INSTALL.md`
- 面向业务用户的操作说明请看 `用户使用文档.md`