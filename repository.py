"""
数据访问层（Repository模式）
封装所有数据库操作，提供与现有JSON API兼容的接口
"""
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from database import db
from models import User, Todo, TodoTag, AiAgentCall, ChatHistory
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
        valid_tags = ['work', 'study', 'life', 'health', 'fitness', 'sports', 'shopping', 'personal', 'urgent', 'important']
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
            valid_tags = ['work', 'study', 'life', 'health', 'fitness', 'sports', 'shopping', 'personal', 'urgent', 'important']
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


class AiAgentCallRepository:
    """AI代理调用记录数据访问层"""

    @staticmethod
    def record_call(user_id: int, ip_address: str = None, endpoint: str = 'todo_agent') -> AiAgentCall:
        """记录一次AI代理调用"""
        call = AiAgentCall(
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint
        )
        db.session.add(call)
        db.session.commit()
        return call

    @staticmethod
    def get_recent_calls_count(user_id: int, seconds: int) -> int:
        """获取用户最近N秒内的调用次数"""
        time_threshold = datetime.utcnow() - timedelta(seconds=seconds)
        count = AiAgentCall.query.filter(
            AiAgentCall.user_id == user_id,
            AiAgentCall.called_at >= time_threshold
        ).count()
        return count

    @staticmethod
    def get_today_calls_count(user_id: int) -> int:
        """获取用户今日调用次数（基于UTC日期）"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count = AiAgentCall.query.filter(
            AiAgentCall.user_id == user_id,
            AiAgentCall.called_at >= today_start
        ).count()
        return count

    @staticmethod
    def can_make_call(user_id: int, ip_address: str = None,
                      rate_limit_per_minute: int = 10, daily_limit: int = 100) -> Tuple[bool, str]:
        """
        检查用户是否可以调用AI代理

        返回: (是否可以调用, 错误消息)
        """
        # 检查每分钟速率限制
        recent_calls = AiAgentCallRepository.get_recent_calls_count(user_id, seconds=60)
        if recent_calls >= rate_limit_per_minute:
            return False, f'Rate limit exceeded. Too many requests in the last minute. Please wait a moment.'

        # 检查每日限制
        today_calls = AiAgentCallRepository.get_today_calls_count(user_id)
        if today_calls >= daily_limit:
            return False, f'Daily limit exceeded. You have used {today_calls} calls today. Limit is {daily_limit} calls per day.'

        return True, ''


class ChatHistoryRepository:
    """对话历史数据访问层"""

    @staticmethod
    def _get_user_key(user_id=None, session=None):
        """获取用户标识符（与app.py中的逻辑一致）"""
        if user_id:
            return str(user_id)
        elif session:
            session_id = session.get('_id', 'anonymous')
            return f'anonymous_{session_id}'
        else:
            return 'anonymous'

    @staticmethod
    def get_messages(user_key, endpoint=None, limit=20):
        """获取用户的对话历史消息"""
        query = ChatHistory.query.filter_by(user_key=user_key).order_by(ChatHistory.created_at.asc())

        if endpoint:
            query = query.filter_by(endpoint=endpoint)

        # 限制返回数量，避免历史过长
        if limit:
            # 先获取总数量，然后取最后limit条
            total = query.count()
            if total > limit:
                offset = total - limit
                query = query.offset(offset)

        return query.all()

    @staticmethod
    def add_message(user_key, role, content, endpoint='chat'):
        """添加一条消息到对话历史"""
        message = ChatHistory(
            user_key=user_key,
            role=role,
            content=content,
            endpoint=endpoint
        )
        db.session.add(message)
        db.session.commit()
        return message

    @staticmethod
    def add_system_message(user_key, content, endpoint='chat'):
        """添加系统消息"""
        # 先清除现有的系统消息（通常只有一个）
        ChatHistory.query.filter_by(
            user_key=user_key,
            role='system',
            endpoint=endpoint
        ).delete()

        # 添加新的系统消息
        return ChatHistoryRepository.add_message(user_key, 'system', content, endpoint)

    @staticmethod
    def clear_history(user_key, endpoint=None):
        """清除对话历史"""
        query = ChatHistory.query.filter_by(user_key=user_key)

        if endpoint:
            query = query.filter_by(endpoint=endpoint)

        deleted_count = query.delete()
        db.session.commit()
        return deleted_count

    @staticmethod
    def get_messages_for_ai(user_key, endpoint=None, max_messages=10):
        """获取用于AI API的消息格式"""
        messages = ChatHistoryRepository.get_messages(user_key, endpoint, limit=max_messages*2)  # 获取更多以便过滤

        # 转换为AI消息格式
        ai_messages = []
        for msg in messages:
            ai_messages.append({
                'role': msg.role,
                'content': msg.content
            })

        # 限制消息数量，确保不超过token限制
        # 保留系统消息（通常在第一行）和最新的用户/助手消息
        if len(ai_messages) > max_messages:
            # 查找系统消息
            system_messages = [msg for msg in ai_messages if msg['role'] == 'system']
            other_messages = [msg for msg in ai_messages if msg['role'] != 'system']

            # 保留系统消息和最新的其他消息
            if system_messages:
                ai_messages = system_messages + other_messages[-max_messages+1:]
            else:
                ai_messages = other_messages[-max_messages:]

        return ai_messages