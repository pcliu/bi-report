# 🚀 BI报告系统 - 快速开始指南

## 📦 镜像构建和分发 (适合分发给同事)

### 1. 在Mac上构建镜像

```bash
# 标准构建
./build-image.sh

# 优化构建 (更小的镜像)
./build-image.sh --optimized

# 或使用Make工具
make build         # 标准构建
make build-opt     # 优化构建
```

### 2. 导出镜像分发包

```bash
# 导出完整分发包
./export-images.sh

# 这会生成 docker-images/bi-report-docker-*.tar.gz 文件
# 将此文件发送给同事即可
```

### 3. 同事使用分发包

```bash
# 解压分发包
tar -xzf bi-report-docker-*.tar.gz
cd bi-report-docker-*/

# 一键启动
./quick-start.sh

# 或手动启动
./import-images.sh  # 这个脚本在分发包里
docker-compose up -d
```

## 🔧 开发模式 (Mac本地开发)

```bash
# 直接启动开发环境
docker-compose up --build

# 或使用Make工具
make dev
```

## 📋 常用命令

```bash
# 使用Make工具 (推荐)
make help           # 查看所有命令
make build          # 构建镜像
make export         # 导出镜像
make dev            # 开发模式
make stop           # 停止服务
make logs           # 查看日志
make status         # 查看状态
make clean          # 清理资源

# 或直接使用脚本
./build-image.sh [version]      # 构建镜像
./export-images.sh [version]    # 导出镜像  
./release.sh [patch|minor|major] # 发布版本
```

## 🌐 访问地址

启动成功后：
- **Web应用**: http://localhost:8501
- **ClickHouse**: http://localhost:8123 (用于Tabix客户端)

## 📚 完整文档

- `README-Docker.md` - 详细部署指南
- `DISTRIBUTION.md` - 镜像分发指南  
- `CLAUDE.md` - 项目开发文档

## ⚡ 一键体验

```bash
# 最快启动方式
make dev

# 访问 http://localhost:8501 即可使用
```

---

**提示**: 如果是为了分发给同事，建议使用 `./export-images.sh` 生成分发包。