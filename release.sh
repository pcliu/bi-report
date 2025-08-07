#!/bin/bash

# BI报告系统发布脚本
# 使用方法: ./release.sh [major|minor|patch] 或 ./release.sh [version]

set -e

CURRENT_VERSION=$(cat VERSION)
echo "当前版本: ${CURRENT_VERSION}"

# 版本号解析函数
bump_version() {
    local version=$1
    local bump_type=$2
    
    IFS='.' read -ra VERSION_PARTS <<< "$version"
    local major=${VERSION_PARTS[0]}
    local minor=${VERSION_PARTS[1]}
    local patch=${VERSION_PARTS[2]}
    
    case $bump_type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            echo "未知的版本类型: $bump_type"
            exit 1
            ;;
    esac
    
    echo "${major}.${minor}.${patch}"
}

# 确定新版本号
if [ $# -eq 0 ]; then
    echo "使用方法: $0 [major|minor|patch] 或 $0 [version]"
    echo "示例:"
    echo "  $0 patch    # 1.0.0 -> 1.0.1"
    echo "  $0 minor    # 1.0.0 -> 1.1.0"  
    echo "  $0 major    # 1.0.0 -> 2.0.0"
    echo "  $0 1.2.3    # 直接指定版本"
    exit 1
elif [[ $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    NEW_VERSION=$1
elif [[ $1 =~ ^(major|minor|patch)$ ]]; then
    NEW_VERSION=$(bump_version $CURRENT_VERSION $1)
else
    echo "❌ 错误: 无效的版本格式或类型"
    exit 1
fi

echo "新版本: ${NEW_VERSION}"

# 确认发布
read -p "确认发布版本 ${NEW_VERSION}? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 发布已取消"
    exit 1
fi

echo "=========================================="
echo "🚀 开始发布版本 ${NEW_VERSION}"
echo "=========================================="

# 更新版本文件
echo ${NEW_VERSION} > VERSION
echo "✅ 版本文件已更新"

# 构建镜像
echo "📦 构建Docker镜像..."
./build-image.sh ${NEW_VERSION}

# 导出镜像
echo "📤 导出镜像文件..."
./export-images.sh ${NEW_VERSION}

# Git标签 (如果在git仓库中)
if [ -d .git ]; then
    echo "🏷️ 创建Git标签..."
    git add VERSION
    git commit -m "Release version ${NEW_VERSION}" || true
    git tag -a "v${NEW_VERSION}" -m "Release version ${NEW_VERSION}"
    echo "✅ Git标签已创建"
    
    echo ""
    echo "📤 推送到远程仓库:"
    echo "  git push origin main"
    echo "  git push origin v${NEW_VERSION}"
fi

echo ""
echo "🎉 版本 ${NEW_VERSION} 发布完成！"
echo ""
echo "📁 分发文件:"
ls -la docker-images/bi-report-docker-${NEW_VERSION}-*.tar.gz
echo ""
echo "📋 发布总结:"
echo "  - 版本: ${NEW_VERSION}"
echo "  - 镜像: bi-report:${NEW_VERSION}"
echo "  - 部署包: docker-images/bi-report-docker-${NEW_VERSION}-*.tar.gz"
echo ""