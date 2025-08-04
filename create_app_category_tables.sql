-- 创建应用分类表的SQL脚本
-- Create application category tables

-- 创建应用大类表
CREATE TABLE IF NOT EXISTS app_category_major (
    id UInt32,
    name String
) ENGINE = MergeTree()
ORDER BY id;

-- 创建应用小类表  
CREATE TABLE IF NOT EXISTS app_category_minor (
    id UInt32,
    name String
) ENGINE = MergeTree()
ORDER BY id;