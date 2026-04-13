"""
数据模型定义
"""
from datetime import datetime, date
from database import db

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    todos = db.relationship('Todo', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        """转换为字典格式（与现有JSON格式兼容）"""
        return {
            'id': self.id,
            'username': self.username,
            'password_hash': self.password_hash
        }


class Todo(db.Model):
    """待办事项模型"""
    __tablename__ = 'todos'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default='')
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=True)

    # 关系
    tags = db.relationship('TodoTag', backref='todo', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Todo {self.id}: {self.title}>'

    def to_dict(self):
        """转换为字典格式（与现有JSON格式兼容）"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'completed': self.completed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'tags': [tag.tag for tag in self.tags]
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建Todo实例"""
        # 处理created_at
        created_at = data.get('created_at')
        if created_at:
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = datetime.utcnow()
        else:
            created_at = datetime.utcnow()

        # 处理due_date
        due_date = data.get('due_date')
        if due_date:
            try:
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            except:
                due_date = None

        todo = cls(
            id=data.get('id'),
            user_id=data.get('user_id', 0),
            title=data['title'],
            description=data.get('description', ''),
            completed=data.get('completed', False),
            created_at=created_at,
            due_date=due_date
        )
        return todo


class TodoTag(db.Model):
    """待办事项标签模型"""
    __tablename__ = 'todo_tags'

    id = db.Column(db.Integer, primary_key=True)
    todo_id = db.Column(db.Integer, db.ForeignKey('todos.id', ondelete='CASCADE'), nullable=False)
    tag = db.Column(db.String(50), nullable=False)

    # 唯一约束
    __table_args__ = (
        db.UniqueConstraint('todo_id', 'tag', name='unique_todo_tag'),
    )

    def __repr__(self):
        return f'<TodoTag todo:{self.todo_id} tag:{self.tag}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'todo_id': self.todo_id,
            'tag': self.tag
        }


class AiAgentCall(db.Model):
    """AI代理调用记录模型"""
    __tablename__ = 'ai_agent_calls'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    called_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # 支持IPv6
    endpoint = db.Column(db.String(50), default='todo_agent', nullable=False)  # 端点名称，便于扩展

    # 关系
    user = db.relationship('User', backref='ai_agent_calls', lazy=True)

    def __repr__(self):
        return f'<AiAgentCall user:{self.user_id} at {self.called_at}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'called_at': self.called_at.isoformat() if self.called_at else None,
            'ip_address': self.ip_address,
            'endpoint': self.endpoint
        }


class ChatHistory(db.Model):
    """对话历史模型"""
    __tablename__ = 'chat_histories'

    id = db.Column(db.Integer, primary_key=True)
    user_key = db.Column(db.String(100), nullable=False, index=True)  # 用户标识符：user_id 或 anonymous_session_id
    role = db.Column(db.String(20), nullable=False)  # 'system', 'user', 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    endpoint = db.Column(db.String(50), default='chat', nullable=False)  # 'chat' 或 'todo_agent'

    def __repr__(self):
        return f'<ChatHistory {self.user_key} {self.role} {self.created_at}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_key': self.user_key,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'endpoint': self.endpoint
        }

    @classmethod
    def to_message_format(cls, chat_history):
        """转换为消息格式（用于AI API）"""
        return {
            'role': chat_history.role,
            'content': chat_history.content
        }