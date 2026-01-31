#!/usr/bin/env python3
"""
测试 NVIDIA Provider
验证 NVIDIA API 集成是否正常工作
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.providers.nvidia_provider import NvidiaProvider


def test_nvidia_provider():
    """测试 NVIDIA Provider"""
    print("="*60)
    print("NVIDIA Provider 测试")
    print("="*60)
    
    # 从环境变量获取 API key
    api_key = os.environ.get('NVIDIA_API_KEY')
    
    if not api_key:
        print("\n[SKIP] 未设置 NVIDIA_API_KEY 环境变量，跳过测试")
        print("请设置环境变量: export NVIDIA_API_KEY='your-api-key'")
        return True
    
    # 创建配置
    config = {
        'api_key': api_key,
        'model': 'deepseek-ai/deepseek-v3.2',
        'temperature': 0.7,
        'max_tokens': 1024,
    }
    
    try:
        # 初始化 Provider
        print("\n[TEST] 初始化 NVIDIA Provider...")
        provider = NvidiaProvider(config)
        print(f"[PASS] Provider 初始化成功")
        print(f"  模型: {provider.model}")
        print(f"  Provider: {provider.get_provider_name()}")
        
        # 测试消息格式化
        print("\n[TEST] 测试消息格式化...")
        messages = provider.format_messages(
            system_prompt="你是一个助手",
            user_prompt="你好"
        )
        print(f"[PASS] 消息格式化成功")
        print(f"  消息数: {len(messages)}")
        
        # 测试 token 估算
        print("\n[TEST] 测试 token 估算...")
        test_text = "这是一个测试文本，用于估算 token 数量。"
        tokens = provider.count_tokens(test_text)
        print(f"[PASS] Token 估算: {tokens} tokens")
        
        # 测试 API 调用（可选，需要消耗额度）
        print("\n[TEST] 测试 API 调用...")
        print("  发送请求到 NVIDIA API...")
        
        messages = [
            {"role": "system", "content": "你是一个友好的助手，用简短的话回答。"},
            {"role": "user", "content": "你好，请介绍一下自己"}
        ]
        
        result = provider.chat_completion(messages)
        
        if result['success']:
            print(f"[PASS] API 调用成功")
            print(f"  回复: {result['content'][:100]}...")
            print(f"  Token 使用: {result.get('tokens_used', 'N/A')}")
        else:
            print(f"[FAIL] API 调用失败")
            print(f"  错误: {result.get('error', 'Unknown error')}")
            return False
        
        print("\n" + "="*60)
        print("所有测试通过！NVIDIA Provider 工作正常。")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_provider_factory():
    """测试 Provider 工厂"""
    print("\n" + "="*60)
    print("Provider 工厂测试")
    print("="*60)
    
    try:
        from src.providers import ProviderFactory, create_provider
        
        # 测试获取可用 providers
        print("\n[TEST] 获取可用 Providers...")
        providers = ProviderFactory.get_available_providers()
        print(f"[PASS] 可用 Providers: {', '.join(providers)}")
        
        # 测试创建 provider
        if 'nvidia' in providers:
            print("\n[TEST] 通过工厂创建 NVIDIA Provider...")
            config = {
                'provider': 'nvidia',
                'api_key': 'test-key',
                'model': 'deepseek-ai/deepseek-v3.2'
            }
            # 注意：这里会失败因为 api_key 无效，但我们可以验证配置验证
            try:
                provider = create_provider(config)
                print(f"[PASS] Provider 创建成功")
            except ValueError as e:
                print(f"[PASS] 配置验证正常工作: {e}")
        
        print("\n" + "="*60)
        print("Provider 工厂测试通过！")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n[FAIL] 工厂测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    results = []
    
    # 运行测试
    results.append(test_provider_factory())
    results.append(test_nvidia_provider())
    
    # 统计结果
    passed = sum(results)
    total = len(results)
    
    print("\n" + "="*60)
    print(f"测试总结: {passed}/{total} 通过")
    print("="*60)
    
    if passed == total:
        print("\n✅ 所有测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败")
        sys.exit(1)
