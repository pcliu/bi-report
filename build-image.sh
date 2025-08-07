#!/bin/bash

# BI报告系统镜像构建脚本
# 使用方法: ./build-image.sh [version] [--optimized]

set -e

# 解析参数
VERSION=""
OPTIMIZED=false

for arg in "$@"; do
    case $arg in
        --optimized)
            OPTIMIZED=true
            shift
            ;;
        *)
            if [ -z "$VERSION" ]; then
                VERSION=$arg
            fi
            shift
            ;;
    esac
done

# 获取版本号，默认使用当前日期
VERSION=${VERSION:-$(date +%Y%m%d)}
IMAGE_NAME="bi-report"
FULL_IMAGE_NAME="${IMAGE_NAME}:${VERSION}"

# 选择Dockerfile
if [ "$OPTIMIZED" = true ]; then
    DOCKERFILE="Dockerfile.optimized"
    DOCKERIGNORE=".dockerignore.optimized"
    echo "使用优化构建模式"
else
    DOCKERFILE="Dockerfile"
    DOCKERIGNORE=".dockerignore"
    echo "使用标准构建模式"
fi

echo "=========================================="
echo "🚀 构建BI报告系统Docker镜像"
echo "镜像名称: ${FULL_IMAGE_NAME}"
echo "=========================================="

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ 错误: Docker未运行，请先启动Docker"
    exit 1
fi

# 临时备份并使用指定的dockerignore
if [ -f "${DOCKERIGNORE}" ] && [ "${DOCKERIGNORE}" != ".dockerignore" ]; then
    if [ -f ".dockerignore" ]; then
        cp .dockerignore .dockerignore.backup
    fi
    cp ${DOCKERIGNORE} .dockerignore
fi

# 构建应用镜像
echo "📦 构建应用镜像..."
docker build -f ${DOCKERFILE} -t ${FULL_IMAGE_NAME} .
docker tag ${FULL_IMAGE_NAME} ${IMAGE_NAME}:latest

# 恢复原始dockerignore
if [ -f ".dockerignore.backup" ]; then
    mv .dockerignore.backup .dockerignore
elif [ "${DOCKERIGNORE}" != ".dockerignore" ]; then
    git checkout .dockerignore 2>/dev/null || rm .dockerignore
fi

echo "✅ 应用镜像构建完成: ${FULL_IMAGE_NAME}"

# 拉取ClickHouse官方镜像
echo "📦 拉取ClickHouse镜像..."
docker pull clickhouse/clickhouse-server:latest

echo "✅ ClickHouse镜像拉取完成"

# 显示镜像信息
echo ""
echo "📋 镜像信息:"
echo "--------------------------------------------"
docker images | grep -E "(${IMAGE_NAME}|clickhouse/clickhouse-server)" | head -5

# 计算镜像大小
APP_SIZE=$(docker images ${FULL_IMAGE_NAME} --format "{{.Size}}")
CH_SIZE=$(docker images clickhouse/clickhouse-server:latest --format "{{.Size}}")

echo ""
echo "📏 镜像大小:"
echo "  - 应用镜像: ${APP_SIZE}"
echo "  - ClickHouse镜像: ${CH_SIZE}"

echo ""
echo "🎉 镜像构建完成！"
echo ""
echo "📤 分发选项:"
echo "  1. 导出镜像文件: ./export-images.sh ${VERSION}"
echo "  2. 推送到Registry: docker push ${FULL_IMAGE_NAME}"
echo "  3. 直接使用: docker-compose up -d"
echo ""