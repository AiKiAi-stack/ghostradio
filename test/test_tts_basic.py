#!/usr/bin/env python3
"""
Simple TTS Provider Tests
Basic functionality tests without complex mocking
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.tts_generator import TTSGenerator
    from src.tts_providers import create_tts_provider
except ImportError as e:
    print(f"Import error: {e}")
    print("Some dependencies may be missing. Install with: pip install -r requirements.txt")
    sys.exit(1)


class TestTTSProviderBasic(unittest.TestCase):
    """Basic TTS Provider tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_config = {
            'provider': 'edge-tts',  # Use free provider
            'voice': 'en-US-AriaNeural'
        }
        self.test_text = "Hello, this is a simple test."
        self.test_output = "test_simple.wav"
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_output):
            os.remove(self.test_output)
    
    def test_tts_provider_creation(self):
        """Test basic TTS provider creation"""
        try:
            provider = create_tts_provider(self.test_config)
            self.assertIsNotNone(provider)
            self.assertEqual(provider.get_provider_name(), 'edge-tts')
        except ImportError:
            self.skipTest("Edge TTS not available")
        except Exception as e:
            self.fail(f"Failed to create TTS provider: {str(e)}")
    
    @unittest.skipUnless(os.getenv('RUN_BASIC_TESTS'), 
                        "Set RUN_BASIC_TESTS to run basic tests")
    def test_simple_synthesis(self):
        """Test simple TTS synthesis"""
        try:
            provider = create_tts_provider(self.test_config)
            
            result = provider.synthesize(self.test_text, self.test_output)
            
            if result['success']:
                self.assertTrue(os.path.exists(self.test_output))
                self.assertGreater(result.get('duration', 0), 0)
                print(f"+ TTS synthesis successful: {result.get('duration')}s duration")
            else:
                self.fail(f"TTS synthesis failed: {result.get('error')}")
                
        except ImportError:
            self.skipTest("Edge TTS not available")
        except Exception as e:
            self.fail(f"TTS synthesis test failed: {str(e)}")
    
    def test_provider_info(self):
        """Test provider info retrieval"""
        try:
            provider = create_tts_provider(self.test_config)
            
            provider_name = provider.get_provider_name()
            voice_list = provider.get_voice_list()
            
            self.assertIsInstance(provider_name, str)
            self.assertIsInstance(voice_list, list)
            
            print(f"+ Provider: {provider_name}")
            print(f"+ Available voices: {len(voice_list)}")
            
        except ImportError:
            self.skipTest("Edge TTS not available")
        except Exception as e:
            self.fail(f"Provider info test failed: {str(e)}")


class TestTTSGeneratorBasic(unittest.TestCase):
    """Basic TTS Generator tests"""
    
    @patch('src.tts_generator.get_health_checker')
    def test_tts_generator_mock_init(self, mock_health):
        """Test TTS Generator initialization with mock health checker"""
        # Mock the health checker
        mock_health.return_value.get_tts_config.return_value = {
            'provider': 'edge-tts',
            'voice': 'en-US-AriaNeural'
        }
        
        try:
            generator = TTSGenerator({})
            self.assertIsNotNone(generator)
            print("+ TTS Generator initialization successful")
        except Exception as e:
            self.fail(f"TTS Generator init failed: {str(e)}")


if __name__ == '__main__':
    print("Running basic TTS Provider tests...")
    print("Note: Some tests may be skipped if dependencies are missing.")
    print("Set RUN_BASIC_TESTS=1 to run actual synthesis tests.")
    print()
    
    # Run tests
    unittest.main(verbosity=2)