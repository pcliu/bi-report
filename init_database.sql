-- BI报告系统数据库初始化SQL脚本
-- Database initialization SQL script for BI reporting system

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

-- 插入应用大类数据
INSERT INTO app_category_major FORMAT Values
(1, 'P2P文件下载'),
(2, '网络语音'),
(3, '即时通讯'),
(4, 'Web浏览'),
(5, '文件访问协议'),
(6, 'HTTP视频流量'),
(7, '股票'),
(8, '游戏'),
(9, '隧道协议'),
(10, '网络攻击'),
(11, '邮件收发'),
(12, '数据库'),
(13, '网管协议'),
(14, '远程控制'),
(15, '其他');

-- 插入应用小类数据
INSERT INTO app_category_minor FORMAT Values
(1100, '拉流地址封堵'),
(7001, 'ICMP'),
(7002, 'IGMP'),
(7004, 'IP_IN_IP'),
(7006, 'TCP'),
(7008, 'EGP'),
(7017, 'UDP'),
(7047, 'GRE'),
(7089, 'OSPF'),
(7132, 'SCTP');