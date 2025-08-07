#!/bin/bash

# BI报告系统镜像导出脚本
# 使用方法: ./export-images.sh [version]

set -e

VERSION=${1:-latest}
IMAGE_NAME="bi-report"
EXPORT_DIR="./docker-images"
DATE_STAMP=$(date +%Y%m%d_%H%M%S)

echo "=========================================="
echo "📤 导出BI报告系统Docker镜像"
echo "版本: ${VERSION}"
echo "=========================================="

# 创建导出目录
mkdir -p ${EXPORT_DIR}

# 检查镜像是否存在
if ! docker images ${IMAGE_NAME}:${VERSION} --format "{{.Repository}}" | grep -q ${IMAGE_NAME}; then
    echo "❌ 错误: 镜像 ${IMAGE_NAME}:${VERSION} 不存在"
    echo "请先运行: ./build-image.sh ${VERSION}"
    exit 1
fi

echo "📦 导出应用镜像..."
docker save ${IMAGE_NAME}:${VERSION} -o ${EXPORT_DIR}/bi-report-app-${VERSION}.tar

echo "📦 导出ClickHouse镜像..."
docker save clickhouse/clickhouse-server:latest -o ${EXPORT_DIR}/clickhouse-server-latest.tar

# 创建完整部署包
PACKAGE_NAME="bi-report-docker-${VERSION}-${DATE_STAMP}"
PACKAGE_DIR="${EXPORT_DIR}/${PACKAGE_NAME}"

echo "📦 创建完整部署包..."
mkdir -p ${PACKAGE_DIR}

# 复制镜像文件
cp ${EXPORT_DIR}/bi-report-app-${VERSION}.tar ${PACKAGE_DIR}/
cp ${EXPORT_DIR}/clickhouse-server-latest.tar ${PACKAGE_DIR}/

# 创建分发专用的docker-compose.yml（去掉build指令并清理空行）
sed '/build: ./d; s/image: bi-report:${BI_VERSION:-latest}/image: bi-report:'${VERSION}'/g' docker-compose.yml > ${PACKAGE_DIR}/docker-compose.yml
cp .env.example ${PACKAGE_DIR}/.env
cp README-Docker.md ${PACKAGE_DIR}/
cp create_app_category_tables.sql ${PACKAGE_DIR}/
cp app_catagory_major.csv ${PACKAGE_DIR}/
cp app_catagory_minor.csv ${PACKAGE_DIR}/

# 创建导入脚本
cat > ${PACKAGE_DIR}/import-images.sh << 'EOF'
#!/bin/bash

echo "=========================================="
echo "📥 导入BI报告系统Docker镜像"
echo "=========================================="

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ 错误: Docker未运行，请先启动Docker"
    exit 1
fi

echo "📥 导入应用镜像..."
docker load -i bi-report-app-*.tar

echo "📥 导入ClickHouse镜像..."
docker load -i clickhouse-server-latest.tar

echo "✅ 镜像导入完成"

echo ""
echo "🚀 启动服务:"
echo "  docker-compose up -d"
echo ""
echo "🌐 访问地址:"
echo "  Web应用: http://localhost:8501"
echo "  ClickHouse: http://localhost:8123"
echo ""
EOF

chmod +x ${PACKAGE_DIR}/import-images.sh

# 创建快速启动脚本
cat > ${PACKAGE_DIR}/quick-start.sh << 'EOF'
#!/bin/bash

echo "=========================================="
echo "🚀 BI报告系统快速启动"
echo "=========================================="

# 导入镜像
echo "📥 导入Docker镜像..."
./import-images.sh

# 清理旧数据确保初始化能正常执行
echo "🧹 清理旧数据卷..."
docker-compose down -v 2>/dev/null || true

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

echo "⏳ 等待服务启动..."
sleep 45

echo ""
echo "✅ 系统启动完成！"
echo ""
echo "🌐 访问地址:"
echo "  📊 Web应用: http://localhost:8501"
echo "  🗄️ ClickHouse: http://localhost:8123"
echo ""
echo "📋 服务状态:"
docker-compose ps
EOF

chmod +x ${PACKAGE_DIR}/quick-start.sh

# 创建停止脚本
cat > ${PACKAGE_DIR}/stop.sh << 'EOF'
#!/bin/bash
echo "🛑 停止BI报告系统..."
docker-compose down
echo "✅ 服务已停止"
EOF

chmod +x ${PACKAGE_DIR}/stop.sh

# 创建使用说明
cat > ${PACKAGE_DIR}/使用说明.txt << 'EOF'
BI报告系统 Docker部署包使用说明
=====================================

📦 包含内容:
- bi-report-app-*.tar       应用镜像文件
- clickhouse-server-latest.tar  ClickHouse镜像文件
- docker-compose.yml        服务编排配置
- .env                      环境变量配置
- README-Docker.md          详细文档

🚀 快速开始:
1. 解压此部署包到目标服务器
2. 确保Docker已安装并运行
3. 执行: ./quick-start.sh

📋 详细步骤:
1. 导入镜像: ./import-images.sh
2. 启动服务: docker-compose up -d
3. 访问应用: http://localhost:8501

🛑 停止服务:
./stop.sh

📚 更多信息请查看 README-Docker.md
EOF

# 打包为tar.gz
echo "📦 打包部署包..."
cd ${EXPORT_DIR}
tar -czf ${PACKAGE_NAME}.tar.gz ${PACKAGE_NAME}/
cd ..

# 显示结果
echo ""
echo "✅ 导出完成！"
echo ""
echo "📁 文件位置:"
echo "  - 完整部署包: ${EXPORT_DIR}/${PACKAGE_NAME}.tar.gz"
echo "  - 应用镜像: ${EXPORT_DIR}/bi-report-app-${VERSION}.tar"
echo "  - ClickHouse镜像: ${EXPORT_DIR}/clickhouse-server-latest.tar"
echo ""

# 显示文件大小
du -h ${EXPORT_DIR}/${PACKAGE_NAME}.tar.gz
du -h ${EXPORT_DIR}/*.tar

echo ""
echo "📤 分发方式:"
echo "  1. 将 ${PACKAGE_NAME}.tar.gz 发送给同事"
echo "  2. 同事解压后运行 ./quick-start.sh 即可使用"
echo ""