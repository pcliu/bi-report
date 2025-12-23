# 安装部署指南

## 系统要求

- **操作系统**: Windows / macOS / Linux
- **Python**: 3.8 或更高版本
- **磁盘空间**: 至少 500MB（用于虚拟环境和数据）

## 快速安装

### 1. 获取代码

```bash
# 克隆项目（或下载 ZIP 解压）
git clone <repository-url>
cd bi-report
```

### 2. 创建虚拟环境

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

### 3. 安装依赖

**推荐方式（使用 uv，速度更快）:**
```bash
pip install uv
uv sync
```

**备选方式（使用 pip）:**
```bash
pip install -r requirements.txt
```

### 4. 验证安装

```bash
python -c "import streamlit, pandas, plotly, reportlab; print('✅ 所有依赖安装成功')"
```

## 数据准备

### 创建数据目录

```bash
mkdir -p data
```

### 放置 CSV 文件

将以下文件复制到 `data/` 目录：

| 文件名模式 | 说明 | 必需 |
|-----------|------|------|
| `tbl_statistic_userapp_day*.csv` | 流量数据文件 | ✅ 是 |
| `app_catagory_major.csv` | 应用大类映射 | ✅ 是 |
| `app_catagory_minor.csv` | 应用小类映射 | ✅ 是 |

**示例目录结构：**
```
data/
├── tbl_statistic_userapp_day_2025-12-08_00_00_00.csv
├── tbl_statistic_userapp_day_2025-12-10_00_00_00.csv
├── app_catagory_major.csv
└── app_catagory_minor.csv
```

### CSV 文件格式

**流量数据文件** (无标题行，逗号分隔)：
```
用户账号,IP类型,应用大类ID,应用小类ID,上行流量,下行流量,总流量,时长,统计时间,新建连接数,拆除连接数
```

**应用分类文件** (无标题行)：
```
ID,名称
```

## 启动服务

```bash
# 确保虚拟环境已激活
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate      # Windows

# 启动 Web 服务
streamlit run streamlit_dashboard.py
```

服务启动后，浏览器访问：**http://localhost:8501**

## 后台运行（Linux/macOS）

```bash
# 使用 nohup 后台运行
nohup streamlit run streamlit_dashboard.py --server.port 8501 > app.log 2>&1 &

# 查看运行状态
ps aux | grep streamlit

# 停止服务
pkill -f streamlit
```

## 常见问题

### Q: 启动时报错 "ModuleNotFoundError"
**A:** 确保已激活虚拟环境：
```bash
source .venv/bin/activate
```

### Q: 页面显示为空
**A:** 检查 `data/` 目录是否包含正确的 CSV 文件，或点击侧边栏的 "🔄 从磁盘重新加载数据"。

### Q: PDF 导出失败
**A:** 确保已安装 kaleido：
```bash
pip install kaleido
```

### Q: 端口 8501 被占用
**A:** 使用其他端口启动：
```bash
streamlit run streamlit_dashboard.py --server.port 8502
```

## 升级更新

```bash
# 拉取最新代码
git pull

# 更新依赖
source .venv/bin/activate
pip install -r requirements.txt --upgrade
```
