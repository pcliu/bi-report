-- 创建BI报告系统所需的所有表
-- Create all tables for BI reporting system

-- 创建主数据表
CREATE TABLE IF NOT EXISTS tbl_statistic_userapp_day (
    user_account String,
    ip_type Int32,
    app_category_major Int32,
    app_category_minor Int32,
    upstream_traffic Float64,
    downstream_traffic Float64,
    total_traffic Float64,
    duration Float64,
    stat_time String
) ENGINE = MergeTree()
ORDER BY (user_account, stat_time);

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