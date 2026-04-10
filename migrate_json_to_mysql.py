#!/usr/bin/env python3
"""
数据迁移脚本：将JSON文件数据迁移到MySQL数据库

使用方法：
1. 确保MySQL数据库已配置并运行
2. 设置环境变量 DATABASE_URL 或编辑此脚本中的配置
3. 运行: python migrate_json_to_mysql.py
"""
import json
import os
import sys
from datetime import datetime, date

def load_env_file():
    """加载.env文件中的环境变量"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 移除值中的引号
                    if value and value[0] in ('"', "'") and value[-1] == value[0]:
                        value = value[1:-1]
                    os.environ[key] = value

# 加载.env文件
load_env_file()

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from database import init_app, db
from models import User, Todo, TodoTag

# JSON文件路径
DATA_DIR = 'data'
TODOS_FILE = os.path.join(DATA_DIR, 'todos.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

def create_app():
    """创建Flask应用实例"""
    app = Flask(__name__)
    init_app(app)
    return app

def migrate_users(app):
    """迁移用户数据"""
    print("正在迁移用户数据...")

    if not os.path.exists(USERS_FILE):
        print(f"警告: 用户文件 {USERS_FILE} 不存在")
        return 0

    with app.app_context():
        # 读取JSON数据
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        users_data = data.get('users', [])
        migrated_count = 0

        for user_data in users_data:
            # 检查是否已存在
            existing_user = User.query.get(user_data['id'])
            if existing_user:
                print(f"用户 ID {user_data['id']} 已存在，跳过")
                continue

            # 创建用户
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                password_hash=user_data['password_hash']
            )
            db.session.add(user)
            migrated_count += 1

        db.session.commit()
        print(f"用户数据迁移完成: {migrated_count} 条记录")
        return migrated_count

def migrate_todos(app):
    """迁移待办事项数据"""
    print("正在迁移待办事项数据...")

    if not os.path.exists(TODOS_FILE):
        print(f"警告: 待办事项文件 {TODOS_FILE} 不存在")
        return 0

    with app.app_context():
        # 读取JSON数据
        with open(TODOS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        todos_data = data.get('todos', [])
        migrated_count = 0
        tag_count = 0

        for todo_data in todos_data:
            # 检查是否已存在
            existing_todo = Todo.query.get(todo_data['id'])
            if existing_todo:
                print(f"待办事项 ID {todo_data['id']} 已存在，跳过")
                continue

            # 处理created_at
            created_at = todo_data.get('created_at')
            if created_at:
                try:
                    # 处理ISO格式字符串
                    created_at = created_at.replace('Z', '+00:00')
                    created_at = datetime.fromisoformat(created_at)
                except Exception as e:
                    print(f"警告: 无法解析created_at '{created_at}', 使用当前时间: {e}")
                    created_at = datetime.utcnow()
            else:
                created_at = datetime.utcnow()

            # 处理due_date
            due_date = todo_data.get('due_date')
            if due_date:
                try:
                    due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                except Exception as e:
                    print(f"警告: 无法解析due_date '{due_date}', 设为None: {e}")
                    due_date = None

            # 处理user_id：如果为0，则设为1（第一个用户）
            user_id = todo_data.get('user_id', 0)
            if user_id == 0:
                user_id = 1
                print(f"注意: 待办事项 ID {todo_data['id']} 的user_id从0调整为1")

            # 创建待办事项
            todo = Todo(
                id=todo_data['id'],
                user_id=user_id,
                title=todo_data['title'],
                description=todo_data.get('description', ''),
                completed=todo_data.get('completed', False),
                created_at=created_at,
                due_date=due_date
            )
            db.session.add(todo)
            db.session.flush()  # 获取todo.id

            # 迁移标签
            tags = todo_data.get('tags', [])
            valid_tags = ['work', 'study', 'life']
            for tag in tags:
                if tag in valid_tags:
                    todo_tag = TodoTag(todo_id=todo.id, tag=tag)
                    db.session.add(todo_tag)
                    tag_count += 1

            migrated_count += 1

        db.session.commit()
        print(f"待办事项数据迁移完成: {migrated_count} 条记录, {tag_count} 个标签")
        return migrated_count

def verify_migration(app):
    """验证迁移结果"""
    print("\n验证迁移结果...")

    with app.app_context():
        # 验证用户
        users_count = User.query.count()
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users_json = json.load(f).get('users', [])
        users_json_count = len(users_json)

        print(f"JSON用户数: {users_json_count}, 数据库用户数: {users_count}")
        if users_count == users_json_count:
            print("[OK] 用户数据迁移验证通过")
        else:
            print(f"[ERROR] 用户数据迁移验证失败: 数量不匹配")

        # 验证待办事项
        todos_count = Todo.query.count()
        with open(TODOS_FILE, 'r', encoding='utf-8') as f:
            todos_json = json.load(f).get('todos', [])
        todos_json_count = len(todos_json)

        print(f"JSON待办事项数: {todos_json_count}, 数据库待办事项数: {todos_count}")
        if todos_count == todos_json_count:
            print("[OK]待办事项数据迁移验证通过")
        else:
            print(f"[ERROR]待办事项数据迁移验证失败: 数量不匹配")

        # 验证标签
        tags_count = TodoTag.query.count()
        total_tags = 0
        for todo in todos_json:
            total_tags += len(todo.get('tags', []))

        print(f"JSON标签数: {total_tags}, 数据库标签数: {tags_count}")
        if tags_count == total_tags:
            print("[OK]标签数据迁移验证通过")
        else:
            print(f"[ERROR]标签数据迁移验证失败: 数量不匹配")

        return users_count == users_json_count and todos_count == todos_json_count

def main():
    """主函数"""
    print("开始数据迁移...")
    print(f"待办事项文件: {TODOS_FILE}")
    print(f"用户文件: {USERS_FILE}")

    # 检查JSON文件是否存在
    if not os.path.exists(TODOS_FILE):
        print(f"错误: 待办事项文件 {TODOS_FILE} 不存在")
        return 1

    if not os.path.exists(USERS_FILE):
        print(f"错误: 用户文件 {USERS_FILE} 不存在")
        return 1

    # 创建应用
    app = create_app()

    try:
        # 执行迁移
        users_migrated = migrate_users(app)
        todos_migrated = migrate_todos(app)

        # 验证迁移
        success = verify_migration(app)

        if success:
            print("\n[SUCCESS] 数据迁移成功完成!")
            print(f"迁移统计: {users_migrated} 用户, {todos_migrated} 待办事项")
        else:
            print("\n[WARNING] 数据迁移完成，但验证失败，请检查数据完整性")
            return 1

    except Exception as e:
        print(f"\n[ERROR] 数据迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())