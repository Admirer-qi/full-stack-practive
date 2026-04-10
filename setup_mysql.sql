-- MySQL数据库初始化脚本
-- 请在MySQL中执行此脚本（需要root权限）

-- 创建数据库
CREATE DATABASE IF NOT EXISTS todo_app
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- 创建用户（请将 'your_password' 替换为强密码）
CREATE USER IF NOT EXISTS 'todo_user'@'localhost' IDENTIFIED BY 'your_password';

-- 授予权限
GRANT ALL PRIVILEGES ON todo_app.* TO 'todo_user'@'localhost';

-- 刷新权限
FLUSH PRIVILEGES;

-- 查看创建结果
SELECT '数据库创建完成' AS message;
SHOW DATABASES LIKE 'todo_app';
SELECT user, host FROM mysql.user WHERE user = 'todo_user';