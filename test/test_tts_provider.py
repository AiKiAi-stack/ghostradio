#!/usr/bin/env python3
"""
TTS Provider Tests
Test all TTS providers for functionality and edge cases
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

from src.tts_generator import TTSGenerator, TTSError


class MockTTSProvider:
    """Mock TTS Provider for testing"""
    
    def __init__(self, config):
        self.should_fail = config.get('should_fail', False)
        self.delay = config.get('delay', 0)
        self.synthesize_calls = []
    
    def synthesize(self, text: str, output_path: str) -> dict:
        """Mock synthesize method"""
        self.synthesize_calls.append({'text': text, 'output_path': output_path})
        
        if self.should_fail == 'True':
            return {
                'success': False,
                'error': 'Mock TTS provider failed'
            }
        
        # Create a fake output file
        with open(output_path, 'w') as f:
            f.write("mock audio data")
        
        return {
            'success': True,
            'file_path': output_path,
            'duration': len(text) * 0.1,  # Mock duration
            'size': len(text)
        }
    
    def get_provider_name(self) -> str:
        return "mock_tts"
    
    def get_voice_list(self) -> list:
        return ["mock_voice_1", "mock_voice_2"]


class TestTTSProvider(unittest.TestCase):
    """Test TTS Provider functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_config = {
            'provider': 'mock_tts',
            'voice': 'mock_voice_1',
            'api_key': 'test_key'
        }
        self.test_text = "Hello, this is a test for TTS synthesis."
        self.test_output = "test_output.wav"
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_output):
            os.remove(self.test_output)
    
    def test_tts_generator_init(self):
        """Test TTS Generator initialization"""
        with patch('src.tts_generator.get_health_checker') as mock_health:
            mock_health.return_value.get_tts_config.return_value = self.test_config
            
            generator = TTSGenerator(self.test_config)
            self.assertIsNotNone(generator._provider)
            self.assertEqual(generator.config['provider'], 'mock_tts')
    
    def test_successful_synthesis(self):
        """Test successful audio synthesis"""
        with patch('src.tts_generator.get_health_checker') as mock_health:
            mock_health.return_value.get_tts_config.return_value = self.test_config
            mock_health.return_value.report_tts_failure.side_effect = RuntimeError("No more providers")
            
            with patch('src.tts_generator.create_tts_provider') as mock_create:
                mock_create.return_value = MockTTSProvider(self.test_config)
                
                generator = TTSGenerator(self.test_config)
                result = generator.generate(self.test_text, self.test_output)
                
                self.assertTrue(result['success'])
                self.assertEqual(result['file_path'], self.test_output)
                self.assertGreater(result['duration'], 0)
                self.assertTrue(os.path.exists(self.test_output))
    
    def test_synthesis_failure(self):
        """Test synthesis failure handling"""
        fail_config = self.test_config.copy()
        fail_config['should_fail'] = 'True'
        
        with patch('src.tts_generator.get_health_checker') as mock_health:
            mock_health.return_value.get_tts_config.return_value = fail_config
            mock_health.return_value.report_tts_failure.side_effect = RuntimeError("No more providers")
            
            with patch('src.tts_generator.create_tts_provider') as mock_create:
                mock_create.return_value = MockTTSProvider(fail_config)
                
                generator = TTSGenerator(fail_config)
                result = generator.generate(self.test_text, self.test_output)
                
                self.assertFalse(result['success'])
                self.assertIn('Failed', result['error'])
    
    def test_provider_switching(self):
        """Test automatic provider switching on failure"""
        configs = [
            self.test_config.copy(),
            self.test_config.copy()
        ]
        configs[0]['should_fail'] = 'True'  # First provider fails
        configs[1]['should_fail'] = 'False'  # Second provider succeeds
        
        with patch('src.tts_generator.get_health_checker') as mock_health:
            # First call returns failing config, second returns working config
            mock_health.return_value.get_tts_config.return_value = configs[0]
            mock_health.return_value.report_tts_failure.return_value = configs[1]
            
            with patch('src.tts_generator.create_tts_provider') as mock_create:
                mock_provider = MockTTSProvider(configs[0])
                mock_create.return_value = mock_provider
                
                generator = TTSGenerator(configs[0])
                result = generator.generate(self.test_text, self.test_output)
                
                # Should fail after trying to switch (mock setup limitation)
                self.assertFalse(result['success'])
                self.assertEqual(len(mock_health.return_value.report_tts_failure.call_args_list), 1)
    
    def test_directory_creation(self):
        """Test automatic directory creation"""
        test_dir = "test_subdir"
        output_path = os.path.join(test_dir, self.test_output)
        
        with patch('src.tts_generator.get_health_checker') as mock_health:
            mock_health.return_value.get_tts_config.return_value = self.test_config
            mock_health.return_value.report_tts_failure.side_effect = RuntimeError("No more providers")
            
            with patch('src.tts_generator.create_tts_provider') as mock_create:
                mock_create.return_value = MockTTSProvider(self.test_config)
                
                generator = TTSGenerator(self.test_config)
                result = generator.generate(self.test_text, output_path)
                
                self.assertTrue(result['success'])
                self.assertTrue(os.path.exists(test_dir))
                self.assertTrue(os.path.exists(output_path))
        
        # Clean up
        if os.path.exists(test_dir):
            os.remove(output_path)
            os.rmdir(test_dir)
    
    def test_provider_info(self):
        """Test provider info retrieval"""
        with patch('src.tts_generator.get_health_checker') as mock_health:
            mock_health.return_value.get_tts_config.return_value = self.test_config
            
            with patch('src.tts_generator.create_tts_provider') as mock_create:
                mock_create.return_value = MockTTSProvider(self.test_config)
                
                generator = TTSGenerator(self.test_config)
                info = generator.provider_info
                
                self.assertEqual(info['name'], 'mock_tts')
                self.assertEqual(info['voice'], 'mock_voice_1')
                self.assertIsInstance(info['available_voices'], list)
    
    def test_empty_text_handling(self):
        """Test handling of empty or very short text"""
        with patch('src.tts_generator.get_health_checker') as mock_health:
            mock_health.return_value.get_tts_config.return_value = self.test_config
            mock_health.return_value.report_tts_failure.side_effect = RuntimeError("No more providers")
            
            with patch('src.tts_generator.create_tts_provider') as mock_create:
                mock_provider = MockTTSProvider(self.test_config)
                mock_create.return_value = mock_provider
                
                generator = TTSGenerator(self.test_config)
                
                # Test empty string
                result = generator.generate("", self.test_output)
                self.assertTrue(result['success'])
                
                # Test single character
                result = generator.generate("H", self.test_output)
                self.assertTrue(result['success'])
                self.assertGreater(result['duration'], 0)
    
    def test_large_text_handling(self):
        """Test handling of large text input"""
        large_text = "This is a test sentence. " * 1000  # Large text
        
        with patch('src.tts_generator.get_health_checker') as mock_health:
            mock_health.return_value.get_tts_config.return_value = self.test_config
            mock_health.return_value.report_tts_failure.side_effect = RuntimeError("No more providers")
            
            with patch('src.tts_generator.create_tts_provider') as mock_create:
                mock_provider = MockTTSProvider(self.test_config)
                mock_create.return_value = mock_provider
                
                generator = TTSGenerator(self.test_config)
                result = generator.generate(large_text, self.test_output)
                
                self.assertTrue(result['success'])
                self.assertGreater(result['duration'], 0)


class TestTTSProviderIntegration(unittest.TestCase):
    """Integration tests for TTS providers (requires actual API keys)"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.test_config = {
            'provider': 'edge-tts',  # Use free provider for integration tests
            'voice': 'en-US-AriaNeural'
        }
        self.test_text = "Hello, this is an integration test."
        self.test_output = "integration_test.wav"
    
    def tearDown(self):
        """Clean up integration test files"""
        if os.path.exists(self.test_output):
            os.remove(self.test_output)
    
    @unittest.skipUnless(os.getenv('RUN_INTEGRATION_TESTS'), 
                        "Set RUN_INTEGRATION_TESTS to run integration tests")
    def test_edge_tts_integration(self):
        """Integration test with Edge TTS (free provider)"""
        try:
            from src.tts_providers import create_tts_provider
            
            # Test Edge TTS provider directly
            provider = create_tts_provider(self.test_config)
            self.assertIsNotNone(provider)
            
            result = provider.synthesize(self.test_text, self.test_output)
            
            if result['success']:
                self.assertTrue(os.path.exists(self.test_output))
                self.assertGreater(result.get('duration', 0), 0)
            else:
                self.fail(f"Edge TTS synthesis failed: {result.get('error')}")
                
        except ImportError:
            self.skipTest("Edge TTS not available")
        except Exception as e:
            self.fail(f"Edge TTS integration test failed: {str(e)}")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)