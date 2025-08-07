# BI报告系统 Makefile

# 默认版本
VERSION ?= $(shell cat VERSION)

.PHONY: help build export release clean dev stop

# 显示帮助信息
help:
	@echo "BI报告系统 Docker 构建工具"
	@echo ""
	@echo "可用命令:"
	@echo "  build        构建Docker镜像"
	@echo "  build-opt    构建优化镜像"
	@echo "  export       导出镜像文件"  
	@echo "  release      发布新版本 (使用: make release VERSION=1.0.1)"
	@echo "  dev          开发模式启动"
	@echo "  stop         停止服务"
	@echo "  clean        清理镜像和容器"
	@echo "  logs         查看服务日志"
	@echo "  size         查看镜像大小对比"
	@echo ""

# 构建镜像
build:
	@echo "🚀 构建镜像版本: $(VERSION)"
	./build-image.sh $(VERSION)

# 构建优化镜像
build-opt:
	@echo "🚀 构建优化镜像版本: $(VERSION)"
	./build-image.sh $(VERSION) --optimized

# 导出镜像
export:
	@echo "📤 导出镜像版本: $(VERSION)"
	./export-images.sh $(VERSION)

# 发布版本
release:
	@echo "🎉 发布版本: $(VERSION)"
	./release.sh $(VERSION)

# 开发模式
dev:
	@echo "🔧 启动开发环境"
	docker-compose up --build

# 生产模式
prod:
	@echo "🚀 启动生产环境"
	docker-compose up -d

# 停止服务
stop:
	@echo "🛑 停止服务"
	docker-compose down

# 查看日志
logs:
	@echo "📋 查看服务日志"
	docker-compose logs -f

# 清理
clean:
	@echo "🧹 清理Docker资源"
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

# 检查状态
status:
	@echo "📊 服务状态"
	@docker-compose ps
	@echo ""
	@echo "💾 镜像列表"
	@docker images | grep -E "(bi-report|clickhouse)"

# 快速测试
test:
	@echo "🧪 快速测试"
	@curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1 && echo "✅ Web应用正常" || echo "❌ Web应用异常"
	@curl -f http://localhost:8123/ping > /dev/null 2>&1 && echo "✅ ClickHouse正常" || echo "❌ ClickHouse异常"

# 查看镜像大小
size:
	@echo "📏 镜像大小对比"
	@echo "标准镜像:"
	@docker images bi-report:$(VERSION) --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>/dev/null || echo "  未找到标准镜像"
	@echo "优化镜像:"  
	@docker images bi-report:$(VERSION)-opt --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>/dev/null || echo "  未找到优化镜像"