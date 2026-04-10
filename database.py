"""
数据库配置模块
配置SQLAlchemy和数据库连接
"""
import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# 创建SQLAlchemy实例
db = SQLAlchemy(model_class=Base)

def init_app(app):
    """
    初始化Flask应用的数据库配置

    Args:
        app: Flask应用实例
    """
    # 从环境变量获取数据库连接URL
    # 格式: mysql+pymysql://username:password@host:port/database_name
    database_url = os.environ.get('DATABASE_URL')

    if not database_url:
        # 默认本地MySQL配置
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '3306')
        db_name = os.environ.get('DB_NAME', 'todo_app')
        db_user = os.environ.get('DB_USER', 'root')
        db_password = os.environ.get('DB_PASSWORD', '')

        database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    # 配置SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }

    # 初始化数据库
    db.init_app(app)

    # 输出数据库配置信息（隐藏密码）
    safe_url = database_url
    if '@' in safe_url:
        # 隐藏密码
        parts = safe_url.split('@')
        auth_part = parts[0]
        if ':' in auth_part:
            user_pass = auth_part.split(':')
            if len(user_pass) == 3:  # mysql+pymysql://user:pass@host
                user = user_pass[1]
                safe_url = f"{user_pass[0]}:{user}:***@{parts[1]}"
            elif len(user_pass) == 2:  # mysql+pymysql://user@host
                safe_url = f"{user_pass[0]}:***@{parts[1]}"

    print(f"数据库配置: {safe_url}")

    # 创建所有表（如果不存在）
    with app.app_context():
        db.create_all()
        print("数据库表已初始化")