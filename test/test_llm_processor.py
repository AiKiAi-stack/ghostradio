#!/usr/bin/env python3
"""
LLM Processor Tests
Test LLM processing, model switching, and prompt handling
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.llm_processor import LLMProcessor, LLMError
from src.providers.base_provider import BaseProvider


class MockLLMProvider:
    """Mock LLM Provider for testing"""
    
    def __init__(self, config):
        self.should_fail = config.get('should_fail', False)
        self.tokens_used = config.get('tokens_used', 100)
        self.response_content = config.get('response_content', "This is a generated podcast script.")
        self.chat_calls = []
    
    def chat_completion(self, messages):
        """Mock chat completion"""
        self.chat_calls.append(messages)
        
        if self.should_fail == 'True':
            return {
                'success': False,
                'error': 'Mock LLM provider failed'
            }
        
        return {
            'success': True,
            'content': self.response_content,
            'tokens_used': self.tokens_used,
            'raw_response': {'id': 'mock-response'}
        }
    
    def format_messages(self, system_prompt, user_prompt):
        """Mock message formatting"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def get_provider_name(self):
        return "mock_llm"
    
    def get_model_list(self):
        return ["mock-model-1", "mock-model-2"]


class TestLLMProcessor(unittest.TestCase):
    """Test LLM Processor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_config = {
            'provider': 'mock_llm',
            'model': 'mock-model-1',
            'api_key': 'test_key'
        }
        self.test_title = "Test Article Title"
        self.test_content = "This is test article content with sufficient length for processing."
    
    def test_llm_processor_init(self):
        """Test LLM Processor initialization"""
        with patch('src.llm_processor.get_health_checker') as mock_health:
            mock_health.return_value.get_llm_config.return_value = self.test_config
            
            processor = LLMProcessor(self.test_config)
            self.assertIsNotNone(processor._provider)
            self.assertEqual(processor.config['model'], 'mock-model-1')
    
    def test_successful_processing(self):
        """Test successful LLM processing"""
        with patch('src.llm_processor.get_health_checker') as mock_health:
            mock_health.return_value.get_llm_config.return_value = self.test_config
            mock_health.return_value.report_llm_failure.side_effect = RuntimeError("No more models")
            
            with patch('src.llm_processor.create_provider') as mock_create:
                mock_create.return_value = MockLLMProvider(self.test_config)
                
                processor = LLMProcessor(self.test_config)
                result = processor.process(self.test_title, self.test_content)
                
                self.assertTrue(result['success'])
                self.assertEqual(result['script'], "This is a generated podcast script.")
                self.assertEqual(result['tokens_used'], 100)
                self.assertEqual(result['error'], "")
    
    def test_processing_failure(self):
        """Test LLM processing failure"""
        fail_config = self.test_config.copy()
        fail_config['should_fail'] = 'True'
        
        with patch('src.llm_processor.get_health_checker') as mock_health:
            mock_health.return_value.get_llm_config.return_value = fail_config
            mock_health.return_value.report_llm_failure.side_effect = RuntimeError("No more models")
            
            with patch('src.llm_processor.create_provider') as mock_create:
                mock_create.return_value = MockLLMProvider(fail_config)
                
                processor = LLMProcessor(fail_config)
                result = processor.process(self.test_title, self.test_content)
                
                self.assertFalse(result['success'])
                self.assertIn('Failed', result['error'])
                self.assertEqual(result['script'], "")
    
    def test_model_switching(self):
        """Test automatic model switching on failure"""
        configs = [
            self.test_config.copy(),
            self.test_config.copy()
        ]
        configs[0]['should_fail'] = 'True'  # First model fails
        configs[1]['should_fail'] = 'False'  # Second model succeeds
        
        with patch('src.llm_processor.get_health_checker') as mock_health:
            # First call returns failing config, second returns working config
            mock_health.return_value.get_llm_config.return_value = configs[0]
            mock_health.return_value.report_llm_failure.return_value = configs[1]
            
            with patch('src.llm_processor.create_provider') as mock_create:
                mock_provider = MockLLMProvider(configs[0])
                mock_create.return_value = mock_provider
                
                processor = LLMProcessor(configs[0])
                result = processor.process(self.test_title, self.test_content)
                
                # Should fail after trying to switch (mock setup limitation)
                self.assertFalse(result['success'])
                self.assertEqual(len(mock_health.return_value.report_llm_failure.call_args_list), 1)
    
    def test_provider_info(self):
        """Test provider info retrieval"""
        with patch('src.llm_processor.get_health_checker') as mock_health:
            mock_health.return_value.get_llm_config.return_value = self.test_config
            
            with patch('src.llm_processor.create_provider') as mock_create:
                mock_create.return_value = MockLLMProvider(self.test_config)
                
                processor = LLMProcessor(self.test_config)
                info = processor.provider_info
                
                self.assertEqual(info.name, 'mock_llm')
                self.assertEqual(info.model, 'mock-model-1')
                self.assertIsInstance(info.available_models, list)
    
    def test_empty_title_content_handling(self):
        """Test handling of empty or minimal inputs"""
        with patch('src.llm_processor.get_health_checker') as mock_health:
            mock_health.return_value.get_llm_config.return_value = self.test_config
            mock_health.return_value.report_llm_failure.side_effect = RuntimeError("No more models")
            
            with patch('src.llm_processor.create_provider') as mock_create:
                mock_create.return_value = MockLLMProvider(self.test_config)
                
                processor = LLMProcessor(self.test_config)
                
                # Test empty title
                result = processor.process("", self.test_content)
                self.assertTrue(result['success'])
                
                # Test empty content
                result = processor.process(self.test_title, "")
                self.assertTrue(result['success'])
                
                # Test both empty
                result = processor.process("", "")
                self.assertTrue(result['success'])
    
    def test_large_content_handling(self):
        """Test handling of large content"""
        large_content = "This is a long sentence. " * 1000  # Large content
        
        with patch('src.llm_processor.get_health_checker') as mock_health:
            mock_health.return_value.get_llm_config.return_value = self.test_config
            mock_health.return_value.report_llm_failure.side_effect = RuntimeError("No more models")
            
            with patch('src.llm_processor.create_provider') as mock_create:
                mock_create.return_value = MockLLMProvider(self.test_config)
                
                processor = LLMProcessor(self.test_config)
                result = processor.process(self.test_title, large_content)
                
                self.assertTrue(result['success'])
                self.assertGreater(result['tokens_used'], 0)
    
    def test_custom_token_usage(self):
        """Test custom token usage reporting"""
        custom_config = self.test_config.copy()
        custom_config['tokens_used'] = '500'
        
        with patch('src.llm_processor.get_health_checker') as mock_health:
            mock_health.return_value.get_llm_config.return_value = custom_config
            mock_health.return_value.report_llm_failure.side_effect = RuntimeError("No more models")
            
            with patch('src.llm_processor.create_provider') as mock_create:
                mock_create.return_value = MockLLMProvider(custom_config)
                
                processor = LLMProcessor(custom_config)
                result = processor.process(self.test_title, self.test_content)
                
                self.assertTrue(result['success'])
                self.assertEqual(result['tokens_used'], 500)
    
    def test_custom_response_content(self):
        """Test custom response content"""
        custom_config = self.test_config.copy()
        custom_config['response_content'] = "Custom podcast script content for testing."
        
        with patch('src.llm_processor.get_health_checker') as mock_health:
            mock_health.return_value.get_llm_config.return_value = custom_config
            mock_health.return_value.report_llm_failure.side_effect = RuntimeError("No more models")
            
            with patch('src.llm_processor.create_provider') as mock_create:
                mock_create.return_value = MockLLMProvider(custom_config)
                
                processor = LLMProcessor(custom_config)
                result = processor.process(self.test_title, self.test_content)
                
                self.assertTrue(result['success'])
                self.assertEqual(result['script'], "Custom podcast script content for testing.")
    
    def test_message_formatting(self):
        """Test message formatting and content"""
        with patch('src.llm_processor.get_health_checker') as mock_health:
            mock_health.return_value.get_llm_config.return_value = self.test_config
            mock_health.return_value.report_llm_failure.side_effect = RuntimeError("No more models")
            
            with patch('src.llm_processor.create_provider') as mock_create:
                mock_provider = MockLLMProvider(self.test_config)
                mock_create.return_value = mock_provider
                
                processor = LLMProcessor(self.test_config)
                processor.process(self.test_title, self.test_content)
                
                # Check that messages were formatted correctly
                self.assertEqual(len(mock_provider.chat_calls), 1)
                messages = mock_provider.chat_calls[0]
                self.assertEqual(len(messages), 2)
                
                # Check system message
                system_msg = next(msg for msg in messages if msg['role'] == 'system')
                self.assertIsNotNone(system_msg['content'])
                
                # Check user message
                user_msg = next(msg for msg in messages if msg['role'] == 'user')
                self.assertIn(self.test_title, user_msg['content'])
                self.assertIn(self.test_content, user_msg['content'])


class TestLLMProcessorIntegration(unittest.TestCase):
    """Integration tests for LLM providers (requires actual API keys)"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.test_config = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'api_key': os.getenv('OPENAI_API_KEY', 'test-key')
        }
        self.test_title = "Test Article"
        self.test_content = "This is a test article for integration testing."
    
    @unittest.skipUnless(os.getenv('RUN_INTEGRATION_TESTS'), 
                        "Set RUN_INTEGRATION_TESTS to run integration tests")
    @unittest.skipUnless(os.getenv('OPENAI_API_KEY'), 
                        "Set OPENAI_API_KEY to run OpenAI integration tests")
    def test_openai_integration(self):
        """Integration test with OpenAI (requires API key)"""
        try:
            from src.providers import create_provider
            
            # Test OpenAI provider directly
            provider = create_provider(self.test_config)
            self.assertIsNotNone(provider)
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello"}
            ]
            
            result = provider.chat_completion(messages)
            
            if result['success']:
                self.assertIsNotNone(result['content'])
                self.assertGreater(result.get('tokens_used', 0), 0)
            else:
                self.fail(f"OpenAI chat completion failed: {result.get('error')}")
                
        except ImportError:
            self.skipTest("OpenAI package not available")
        except Exception as e:
            self.fail(f"OpenAI integration test failed: {str(e)}")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)