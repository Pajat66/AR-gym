-- 创建新用户并授予远程访问权限的SQL脚本
-- 在MySQL服务器上执行此脚本

-- 方案1：创建新用户 Zbp42682600（如果不存在）
CREATE USER IF NOT EXISTS 'Zbp42682600'@'%' IDENTIFIED BY 'Zbp42682600';
GRANT ALL PRIVILEGES ON exercise.* TO 'Zbp42682600'@'%';
FLUSH PRIVILEGES;

-- 方案2：如果project用户密码不是Zbp42682600，可以重置密码
-- ALTER USER 'project'@'%' IDENTIFIED BY 'Zbp42682600';
-- FLUSH PRIVILEGES;

-- 方案3：授予project用户对exercise数据库的所有权限（如果还没有）
-- GRANT ALL PRIVILEGES ON exercise.* TO 'project'@'%';
-- FLUSH PRIVILEGES;

-- 查看用户权限
-- SHOW GRANTS FOR 'project'@'%';
-- SHOW GRANTS FOR 'Zbp42682600'@'%';

