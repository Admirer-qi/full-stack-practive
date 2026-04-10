"""
数据访问层（Repository模式）
封装所有数据库操作，提供与现有JSON API兼容的接口
"""
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from database import db
from models import User, Todo, TodoTag
from werkzeug.security import generate_password_hash, check_password_hash


class UserRepository:
    """用户数据访问层"""

    @staticmethod
    def get_all() -> List[User]:
        """获取所有用户"""
        return User.query.all()

    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return User.query.get(user_id)

    @staticmethod
    def get_by_username(username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return User.query.filter_by(username=username).first()

    @staticmethod
    def create(username: str, password: str) -> User:
        """创建新用户"""
        # 检查用户名是否已存在
        if UserRepository.get_by_username(username):
            raise ValueError(f"用户名 '{username}' 已存在")

        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def authenticate(username: str, password: str) -> Optional[User]:
        """验证用户凭据"""
        user = UserRepository.get_by_username(username)
        if user and check_password_hash(user.password_hash, password):
            return user
        return None

    @staticmethod
    def delete(user_id: int) -> bool:
        """删除用户"""
        user = UserRepository.get_by_id(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            return True
        return False


class TodoRepository:
    """待办事项数据访问层"""

    @staticmethod
    def get_all_by_user(user_id: int) -> List[Todo]:
        """获取用户的所有待办事项"""
        return Todo.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_by_id(todo_id: int, user_id: int = None) -> Optional[Todo]:
        """根据ID获取待办事项（可选用户ID过滤）"""
        query = Todo.query.filter_by(id=todo_id)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        return query.first()

    @staticmethod
    def create(user_id: int, title: str, description: str = '',
               due_date: date = None, tags: List[str] = None) -> Todo:
        """创建新的待办事项"""
        # 验证标签
        valid_tags = ['work', 'study', 'life']
        if tags:
            tags = [tag for tag in tags if tag in valid_tags]
        else:
            tags = []

        todo = Todo(
            user_id=user_id,
            title=title,
            description=description,
            due_date=due_date
        )
        db.session.add(todo)
        db.session.flush()  # 获取todo.id

        # 添加标签
        for tag in tags:
            todo_tag = TodoTag(todo_id=todo.id, tag=tag)
            db.session.add(todo_tag)

        db.session.commit()
        return todo

    @staticmethod
    def update(todo_id: int, user_id: int, **kwargs) -> Optional[Todo]:
        """更新待办事项"""
        todo = TodoRepository.get_by_id(todo_id, user_id)
        if not todo:
            return None

        # 更新字段
        if 'title' in kwargs:
            todo.title = kwargs['title']
        if 'description' in kwargs:
            todo.description = kwargs['description']
        if 'due_date' in kwargs:
            due_date = kwargs['due_date']
            if due_date:
                if isinstance(due_date, str):
                    due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                todo.due_date = due_date
            else:
                todo.due_date = None
        if 'completed' in kwargs:
            todo.completed = kwargs['completed']

        # 更新标签
        if 'tags' in kwargs:
            # 删除现有标签
            TodoTag.query.filter_by(todo_id=todo.id).delete()

            # 添加新标签
            tags = kwargs['tags']
            valid_tags = ['work', 'study', 'life']
            if tags:
                tags = [tag for tag in tags if tag in valid_tags]
                for tag in tags:
                    todo_tag = TodoTag(todo_id=todo.id, tag=tag)
                    db.session.add(todo_tag)

        db.session.commit()
        return todo

    @staticmethod
    def delete(todo_id: int, user_id: int) -> bool:
        """删除待办事项"""
        todo = TodoRepository.get_by_id(todo_id, user_id)
        if todo:
            db.session.delete(todo)
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_stats(user_id: int) -> dict:
        """获取用户待办事项统计信息"""
        todos = TodoRepository.get_all_by_user(user_id)
        total = len(todos)
        completed = sum(1 for todo in todos if todo.completed)
        active = total - completed

        return {
            'total': total,
            'completed': completed,
            'active': active
        }

    @staticmethod
    def get_with_tags(user_id: int, tag: str = None) -> List[Todo]:
        """获取用户的待办事项（可选标签过滤）"""
        query = Todo.query.options(joinedload(Todo.tags)).filter_by(user_id=user_id)

        if tag:
            # 通过标签过滤
            query = query.join(TodoTag).filter(TodoTag.tag == tag)

        # 按created_at排序
        query = query.order_by(Todo.created_at.desc())

        return query.all()


class TagRepository:
    """标签数据访问层"""

    @staticmethod
    def get_all_tags(user_id: int) -> List[str]:
        """获取用户的所有唯一标签"""
        # 使用原始SQL或子查询获取用户的所有唯一标签
        from sqlalchemy import distinct
        tags = db.session.query(distinct(TodoTag.tag)).join(Todo).filter(
            Todo.user_id == user_id
        ).all()
        return [tag[0] for tag in tags if tag[0]]

    @staticmethod
    def get_todos_by_tag(user_id: int, tag: str) -> List[Todo]:
        """根据标签获取用户的待办事项"""
        return Todo.query.join(TodoTag).filter(
            and_(Todo.user_id == user_id, TodoTag.tag == tag)
        ).all()