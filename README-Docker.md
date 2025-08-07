# BI报告系统 Docker 部署指南

这个文档介绍如何使用Docker容器部署BI报告系统，包括ClickHouse数据库和Streamlit Web应用。

## 系统架构

- **ClickHouse数据库**: 数据存储和查询
- **Python Web应用**: Streamlit仪表板
- **容器化部署**: Docker + Docker Compose

## 端口映射

| 服务 | 端口 | 说明 |
|------|------|------|
| Streamlit Web应用 | 8501 | Web界面访问 |
| ClickHouse HTTP | 8123 | 数据库Web客户端（Tabix） |
| ClickHouse Native | 9000 | 原生客户端连接 |

## 快速开始

### 1. 构建和启动服务

```bash
# 构建并启动所有服务
docker-compose up --build -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 2. 访问服务

- **Web应用**: http://localhost:8501
- **ClickHouse**: http://localhost:8123 (用于Tabix等客户端)

### 3. 停止服务

```bash
# 停止服务
docker-compose down

# 停止服务并删除数据卷（谨慎使用）
docker-compose down -v
```

## 数据管理

### 导入CSV数据

1. 将CSV文件放在项目根目录
2. 进入应用容器：
```bash
docker-compose exec bi-app bash
```

3. 运行导入脚本：
```bash
python import_csv_to_clickhouse.py
```

### 数据持久化

- ClickHouse数据存储在Docker卷 `clickhouse_data` 中
- 应用数据存储在 `./data` 目录
- 日志文件存储在 `./logs` 目录

## 配置说明

### 环境变量

在 `docker-compose.yml` 中可以修改以下配置：

```yaml
environment:
  - CLICKHOUSE_HOST=clickhouse
  - CLICKHOUSE_PORT=8123
  - CLICKHOUSE_USER=default
  - CLICKHOUSE_PASSWORD=12345678
  - CLICKHOUSE_DATABASE=default
```

### ClickHouse配置

默认配置：
- 用户名: `default`
- 密码: `12345678`
- 数据库: `default`

## Windows虚拟机部署

### 系统要求

- Windows虚拟机
- Docker Desktop 或 Docker Engine
- 至少4GB内存
- 10GB可用磁盘空间

### 部署步骤

1. **安装Docker**
   ```bash
   # 在虚拟机中安装Docker Desktop或Docker Engine
   ```

2. **复制项目文件**
   ```bash
   # 将项目文件复制到虚拟机中
   ```

3. **启动服务**
   ```bash
   cd bi-report
   docker-compose up --build -d
   ```

4. **配置网络（如果需要）**
   ```bash
   # 确保虚拟机网络可以从宿主机访问
   # 可能需要配置端口转发或桥接网络
   ```

### 从Windows宿主机访问

- 获取虚拟机IP地址
- 访问 `http://[虚拟机IP]:8501` 使用Web应用
- 访问 `http://[虚拟机IP]:8123` 使用Tabix等数据库客户端

## 使用Tabix连接ClickHouse

1. 打开浏览器访问 http://ui.tabix.io/
2. 连接设置：
   - Host: `[虚拟机IP]` 或 `localhost`
   - Port: `8123`
   - User: `default`
   - Password: `12345678`
   - Database: `default`

## 故障排除

### 1. ClickHouse启动失败

```bash
# 查看ClickHouse日志
docker-compose logs clickhouse

# 检查磁盘空间
df -h

# 重启服务
docker-compose restart clickhouse
```

### 2. Web应用无法连接数据库

```bash
# 检查网络连接
docker-compose exec bi-app ping clickhouse

# 查看应用日志
docker-compose logs bi-app

# 重启应用
docker-compose restart bi-app
```

### 3. 内存不足

```bash
# 查看资源使用
docker stats

# 增加虚拟机内存或调整Docker资源限制
```

### 4. 端口冲突

```bash
# 检查端口占用
ss -tlnp | grep :8501
ss -tlnp | grep :8123

# 修改docker-compose.yml中的端口映射
```

## 数据备份与恢复

### 备份

```bash
# 停止服务
docker-compose stop

# 备份ClickHouse数据
docker run --rm -v bi-report_clickhouse_data:/data -v $(pwd):/backup ubuntu tar czf /backup/clickhouse-backup.tar.gz /data

# 备份应用数据
tar czf app-data-backup.tar.gz ./data ./logs
```

### 恢复

```bash
# 恢复ClickHouse数据
docker run --rm -v bi-report_clickhouse_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/clickhouse-backup.tar.gz -C /

# 恢复应用数据
tar xzf app-data-backup.tar.gz

# 启动服务
docker-compose up -d
```

## 性能优化

### 1. 系统资源

- 建议至少分配4GB内存给Docker
- 使用SSD存储以提高I/O性能
- 确保有足够的磁盘空间用于数据存储

### 2. ClickHouse调优

- 根据数据量调整内存设置
- 优化表结构和索引
- 定期清理旧数据

### 3. 应用优化

- 使用数据缓存减少查询次数
- 优化查询语句
- 合理设置图表刷新频率

## 更新和维护

### 1. 更新应用

```bash
# 拉取最新代码
git pull

# 重建并重启服务
docker-compose up --build -d
```

### 2. 更新依赖

```bash
# 更新requirements.txt后重建镜像
docker-compose build --no-cache bi-app
docker-compose up -d
```

### 3. 清理磁盘空间

```bash
# 清理未使用的Docker镜像
docker system prune -a

# 清理旧的数据文件
# 注意：请谨慎操作，确保已备份重要数据
```