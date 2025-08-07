# 🚀 BI报告系统镜像分发指南

这个文档介绍如何构建、导出和分发BI报告系统的Docker镜像给团队成员。

## 📦 分发方式对比

| 方式 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **Docker Hub** | 简单方便，自动更新 | 需要网络，公开仓库 | 公开项目，网络良好 |
| **私有Registry** | 安全，集中管理 | 需要搭建服务器 | 企业内部，大团队 |
| **文件分发** | 离线可用，无需注册 | 文件较大，手动更新 | 小团队，内网环境 |

## 🔧 构建和发布流程

### 1. 构建镜像（开发者）

```bash
# 构建最新版本
./build-image.sh

# 构建指定版本
./build-image.sh v1.0.1

# 完整发布流程（推荐）
./release.sh patch  # 版本号自动递增
```

### 2. 导出镜像文件

```bash
# 导出当前版本
./export-images.sh

# 导出指定版本
./export-images.sh v1.0.1
```

这会创建包含以下内容的完整部署包：
- `bi-report-app-*.tar` - 应用镜像
- `clickhouse-server-latest.tar` - 数据库镜像
- `docker-compose.yml` - 服务配置
- `quick-start.sh` - 快速启动脚本
- `使用说明.txt` - 详细说明

### 3. 分发给同事

**方式一：文件分发**
```bash
# 发送 docker-images/bi-report-docker-*.tar.gz 给同事
# 同事解压后运行 ./quick-start.sh 即可
```

**方式二：Docker Hub**
```bash
# 推送到Docker Hub（需要先登录）
docker login
docker tag bi-report:latest your-username/bi-report:latest
docker push your-username/bi-report:latest

# 同事使用
docker pull your-username/bi-report:latest
```

## 👥 同事使用指南

### 方式一：使用分发包（推荐）

1. **解压部署包**
   ```bash
   tar -xzf bi-report-docker-*.tar.gz
   cd bi-report-docker-*/
   ```

2. **快速启动**
   ```bash
   ./quick-start.sh
   ```

3. **访问系统**
   - Web应用: http://localhost:8501
   - ClickHouse: http://localhost:8123

### 方式二：从Registry拉取

1. **创建配置**
   ```bash
   # 创建 docker-compose.yml（使用镜像而非构建）
   version: '3.8'
   services:
     bi-app:
       image: your-username/bi-report:latest  # 使用Registry镜像
       # ... 其他配置
   ```

2. **启动服务**
   ```bash
   docker-compose up -d
   ```

## 📋 版本管理

### 版本号规则
- `major.minor.patch` (如: 1.0.0)
- **patch**: 修复bug，向后兼容
- **minor**: 新功能，向后兼容  
- **major**: 重大变更，可能不兼容

### 版本发布
```bash
./release.sh patch  # 1.0.0 -> 1.0.1
./release.sh minor  # 1.0.0 -> 1.1.0
./release.sh major  # 1.0.0 -> 2.0.0
./release.sh 1.2.3  # 直接指定版本
```

## 🛠️ 自定义镜像

### 修改代码后重新构建
```bash
# 修改代码后
./build-image.sh
./export-images.sh
```

### 配置修改
同事可以修改分发包中的配置文件：
- `.env` - 环境变量
- `docker-compose.yml` - 服务配置

## 📊 镜像大小优化

### 当前镜像大小
- 应用镜像: ~800MB
- ClickHouse镜像: ~500MB
- 总大小: ~1.3GB

### 优化建议
```bash
# 使用多阶段构建
FROM python:3.11-slim as builder
# ... 构建步骤

FROM python:3.11-slim
# ... 最终镜像
```

## 🔍 故障排除

### 常见问题

1. **镜像加载失败**
   ```bash
   # 检查Docker是否运行
   docker info
   
   # 重新加载镜像
   docker load -i bi-report-app-*.tar
   ```

2. **服务启动失败**
   ```bash
   # 查看日志
   docker-compose logs
   
   # 重启服务
   docker-compose restart
   ```

3. **端口冲突**
   ```bash
   # 修改docker-compose.yml中的端口映射
   ports:
     - "8502:8501"  # 改为其他端口
   ```

### 清理命令
```bash
# 清理旧镜像
docker system prune -a

# 停止并删除所有容器
docker-compose down -v
```

## 📞 技术支持

如果同事在使用过程中遇到问题：

1. 查看 `README-Docker.md` 详细文档
2. 检查 `使用说明.txt` 快速指南
3. 联系技术支持团队

## 🔄 更新流程

### 推送更新
1. 开发者发布新版本：`./release.sh patch`
2. 生成新的分发包
3. 通知团队成员更新

### 接收更新
1. 停止当前服务：`./stop.sh`
2. 导入新镜像：`./import-images.sh` (此脚本在分发包中)
3. 启动新版本：`docker-compose up -d`

---

**提示**: 建议在团队内部建立镜像分发的标准流程，确保所有成员使用相同的版本。