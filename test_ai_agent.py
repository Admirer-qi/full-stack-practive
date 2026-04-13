#!/usr/bin/env python3
"""
测试AI自动管理Todo Agent端点
"""
import requests
import json
import time

BASE_URL = 'http://localhost:5000/api'

def print_response(response):
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print(response.text)

def test_authentication():
    """测试身份验证"""
    print("=== 测试身份验证 ===")

    # 尝试未认证访问AI代理端点
    response = requests.post(f'{BASE_URL}/ai/todo-agent', json={'message': 'hello'})
    print("未认证访问:")
    print_response(response)
    print()

def test_rate_limit():
    """测试速率限制"""
    print("=== 测试速率限制 ===")

    # 先注册一个测试用户
    username = f'testuser_{int(time.time())}'
    password = 'testpass123'

    response = requests.post(f'{BASE_URL}/register', json={
        'username': username,
        'password': password
    })
    print("注册响应:")
    print_response(response)

    if response.status_code != 201:
        print("注册失败，跳过速率限制测试")
        return None

    user_data = response.json()
    user_id = user_data['id']

    # 登录获取session（使用requests的session保持cookie）
    session = requests.Session()
    response = session.post(f'{BASE_URL}/login', json={
        'username': username,
        'password': password
    })
    print("登录响应:")
    print_response(response)

    if response.status_code != 200:
        print("登录失败，跳过速率限制测试")
        return None

    # 快速连续调用10次以上，触发速率限制
    print("\n快速连续调用测试速率限制...")
    for i in range(12):
        response = session.post(f'{BASE_URL}/ai/todo-agent', json={
            'message': f'创建待办事项 {i}'
        })
        print(f"调用 {i+1}: 状态码 {response.status_code}")
        if response.status_code == 429:
            print("触发速率限制!")
            break
        time.sleep(0.1)

    return session

def test_todo_agent_operations(session):
    """测试AI代理的待办事项操作"""
    print("\n=== 测试AI代理操作 ===")

    # 测试创建待办事项
    print("测试创建待办事项...")
    response = session.post(f'{BASE_URL}/ai/todo-agent', json={
        'message': '创建一个标题为"购买牛奶"的待办事项，标签为life，截止日期明天'
    })
    print_response(response)

    # 测试列出待办事项
    print("\n测试列出待办事项...")
    response = session.post(f'{BASE_URL}/ai/todo-agent', json={
        'message': '列出我的所有待办事项'
    })
    print_response(response)

    # 解析响应，获取待办事项ID（如果有）
    if response.status_code == 200:
        data = response.json()
        if 'todos' in data and len(data['todos']) > 0:
            todo_id = data['todos'][0]['id']

            # 测试标记完成
            print(f"\n测试标记待办事项完成 (ID: {todo_id})...")
            response = session.post(f'{BASE_URL}/ai/todo-agent', json={
                'message': f'将待办事项 {todo_id} 标记为完成'
            })
            print_response(response)

            # 测试删除
            print(f"\n测试删除待办事项 (ID: {todo_id})...")
            response = session.post(f'{BASE_URL}/ai/todo-agent', json={
                'message': f'删除待办事项 {todo_id}'
            })
            print_response(response)

def test_daily_limit():
    """测试每日调用次数限制（模拟）"""
    print("\n=== 测试每日调用次数限制 ===")
    print("注意：需要修改每日限制为较小值进行测试，此处仅打印当前调用次数")

    # 这里可以调用一个统计端点（如果有）
    # 暂时跳过

def main():
    """主测试函数"""
    print("启动AI自动管理Todo Agent测试")
    print("=" * 50)

    # 确保应用正在运行
    try:
        response = requests.get(f'{BASE_URL}/ai/status', timeout=5)
        print(f"应用状态: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("错误: 应用未运行！请先启动Flask应用:")
        print("  cd e:\\cc_test && python app.py")
        return

    # 运行测试
    test_authentication()

    session = test_rate_limit()
    if session:
        test_todo_agent_operations(session)

    test_daily_limit()

    print("\n=== 测试完成 ===")

if __name__ == '__main__':
    main()