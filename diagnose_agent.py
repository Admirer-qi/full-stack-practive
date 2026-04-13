#!/usr/bin/env python3
"""
诊断AI代理问题：长期记忆和待办事项添加失败
"""
import requests
import json
import time
import sys
import os
from datetime import datetime

BASE_URL = 'http://localhost:5000/api'

def print_response(label, response):
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print(f"Raw response: {response.text[:500]}")

def test_api_configuration():
    """测试API配置状态"""
    print("=== 测试API配置状态 ===")

    # 检查AI状态端点
    response = requests.get(f'{BASE_URL}/ai/status', timeout=5)
    print_response("AI状态检查", response)

    # 检查AI测试端点
    if response.status_code == 200 and response.json().get('configured'):
        response = requests.get(f'{BASE_URL}/ai/test', timeout=10)
        print_response("AI连接测试", response)

    return response.status_code == 200 and response.json().get('configured')

def test_database_connection():
    """测试数据库连接"""
    print("\n=== 测试数据库连接 ===")

    # 需要先注册登录
    username = f'diagnose_{int(time.time())}'
    password = 'diagnose123'

    # 注册用户
    response = requests.post(f'{BASE_URL}/register', json={
        'username': username,
        'password': password
    })
    print_response("注册用户", response)

    if response.status_code != 201:
        print("注册失败，跳过数据库测试")
        return None

    user_data = response.json()
    user_id = user_data['id']

    # 登录获取session
    session = requests.Session()
    response = session.post(f'{BASE_URL}/login', json={
        'username': username,
        'password': password
    })
    print_response("用户登录", response)

    if response.status_code != 200:
        print("登录失败，跳过数据库测试")
        return None

    # 测试标准待办事项API（直接创建，不通过AI）
    print("\n=== 测试标准待办事项API ===")
    todo_data = {
        'title': '手动测试待办事项',
        'description': '这是通过标准API创建的测试项',
        'tags': ['health', 'fitness']
    }

    response = session.post(f'{BASE_URL}/todos', json=todo_data)
    print_response("创建待办事项（标准API）", response)

    if response.status_code == 201:
        todo_id = response.json().get('id')
        print(f"成功创建待办事项，ID: {todo_id}")

        # 验证待办事项存在
        response = session.get(f'{BASE_URL}/todos')
        print_response("获取所有待办事项", response)

    return session

def test_ai_agent_with_memory(session):
    """测试AI代理的记忆功能"""
    print("\n=== 测试AI代理记忆功能 ===")

    if not session:
        print("无有效会话，跳过AI代理测试")
        return

    # 测试1: 创建第一个待办事项
    print("\n--- 测试1: 创建健身待办事项 ---")
    response = session.post(f'{BASE_URL}/ai/todo-agent', json={
        'message': '创建一个标题为"明天去健身房"的待办事项，标签为fitness，截止日期明天'
    })
    print_response("AI代理创建待办事项", response)

    # 检查响应中的intent
    if response.status_code == 200:
        data = response.json()
        intent = data.get('intent')
        print(f"AI识别意图: {intent}")

        if intent == 'create_todo' and 'todo' in data:
            todo_id = data['todo'].get('id')
            print(f"成功创建待办事项，ID: {todo_id}")
        elif intent == 'chat':
            print(f"AI返回聊天响应: {data.get('response', '')}")
        elif intent == 'clarify':
            print(f"AI请求澄清: {data.get('question', '')}")

    # 等待2秒
    time.sleep(2)

    # 测试2: 列出待办事项（检查记忆）
    print("\n--- 测试2: 列出待办事项验证持久化 ---")
    response = session.post(f'{BASE_URL}/ai/todo-agent', json={
        'message': '列出我的所有待办事项'
    })
    print_response("AI代理列出待办事项", response)

    # 测试3: 创建第二个待办事项
    print("\n--- 测试3: 创建第二个待办事项 ---")
    response = session.post(f'{BASE_URL}/ai/todo-agent', json={
        'message': '再创建一个标题为"购买蛋白粉"的待办事项，标签为shopping'
    })
    print_response("AI代理创建第二个待办事项", response)

    # 测试4: 使用标准API验证待办事项确实存在
    print("\n--- 测试4: 使用标准API验证待办事项 ---")
    response = session.get(f'{BASE_URL}/todos')
    print_response("标准API获取所有待办事项", response)

    if response.status_code == 200:
        todos = response.json()
        print(f"\n数据库中共有 {len(todos)} 个待办事项:")
        for i, todo in enumerate(todos, 1):
            print(f"{i}. ID:{todo.get('id')} 标题:{todo.get('title')} 完成:{todo.get('completed')} 标签:{todo.get('tags', [])}")

def test_chat_history_persistence():
    """测试对话历史持久化问题"""
    print("\n=== 测试对话历史持久化 ===")
    print("注意：当前的chat_histories存储在内存中，重启应用后会丢失")
    print("需要实现数据库存储才能持久化对话历史")

    # 这里可以展示当前chat_histories的实现方式
    print("\n当前实现: chat_histories = {} (内存字典)")
    print("重启应用后，所有对话历史都会丢失")
    print("建议: 将对话历史存储到数据库表中")

def check_database_tables():
    """检查数据库表结构"""
    print("\n=== 检查数据库表结构 ===")

    try:
        # 尝试导入数据库模型来检查表
        import sys
        sys.path.append('.')
        from models import db, User, Todo, TodoTag, AiAgentCall

        print("数据库模型加载成功")
        print("已定义的模型类:")
        print(f"  1. User - 用户表")
        print(f"  2. Todo - 待办事项表")
        print(f"  3. TodoTag - 待办事项标签表")
        print(f"  4. AiAgentCall - AI代理调用记录表")

        # 注意：需要数据库连接才能检查实际表
        print("\n注意：需要Flask应用上下文来检查实际表结构")

    except Exception as e:
        print(f"加载数据库模型失败: {e}")

def analyze_common_issues():
    """分析常见问题"""
    print("\n=== 常见问题分析 ===")

    issues = [
        {
            "问题": "API密钥未配置",
            "症状": "AI代理返回500错误或401错误",
            "检查": "检查.env文件中的DEEPSEEK_API_KEY",
            "解决": "获取有效API密钥并设置"
        },
        {
            "问题": "标签限制",
            "症状": "待办事项创建但标签为空",
            "检查": "检查repository.py中的valid_tags列表",
            "解决": "扩展valid_tags列表或修改验证逻辑"
        },
        {
            "问题": "对话历史丢失",
            "症状": "重启应用后AI忘记之前的对话",
            "检查": "chat_histories是内存字典",
            "解决": "实现数据库存储对话历史"
        },
        {
            "问题": "日期解析错误",
            "症状": "AI返回的日期格式不正确",
            "检查": "AI响应中的due_date格式",
            "解决": "在后端验证和修正日期格式"
        },
        {
            "问题": "速率限制",
            "症状": "返回429错误",
            "检查": "每分钟调用次数",
            "解决": "等待或调整限制参数"
        }
    ]

    for i, issue in enumerate(issues, 1):
        print(f"\n{i}. {issue['问题']}")
        print(f"   症状: {issue['症状']}")
        print(f"   检查: {issue['检查']}")
        print(f"   解决: {issue['解决']}")

def main():
    """主诊断函数"""
    print("开始诊断AI代理问题")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 检查应用是否运行
    try:
        response = requests.get(f'{BASE_URL}/ai/status', timeout=5)
        print(f"应用状态: 运行中 (状态码: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("错误: 应用未运行！请先启动Flask应用:")
        print("  cd e:\\cc_test && python app.py")
        return
    except Exception as e:
        print(f"连接错误: {e}")
        return

    # 运行诊断测试
    api_configured = test_api_configuration()

    if not api_configured:
        print("\n警告: API密钥未配置或无效")
        print("这是最可能的问题原因！")
        print("请在.env文件中设置有效的DEEPSEEK_API_KEY")

    session = test_database_connection()

    if session:
        test_ai_agent_with_memory(session)
    else:
        print("\n⚠️ 数据库连接测试失败，跳过AI代理测试")

    test_chat_history_persistence()
    check_database_tables()
    analyze_common_issues()

    print("\n" + "=" * 80)
    print("诊断完成")

    # 总结建议
    print("\n💡 建议的解决步骤:")
    print("1. 设置有效的DeepSeek API密钥到.env文件")
    print("2. 重启Flask应用")
    print("3. 运行此诊断脚本验证问题是否解决")
    print("4. 如需长期记忆，需要实现对话历史数据库存储")

if __name__ == '__main__':
    main()