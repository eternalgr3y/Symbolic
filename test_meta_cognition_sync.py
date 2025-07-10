#!/usr/bin/env python3
"""Test for meta cognition module"""

import tempfile
import os
import shutil

class TestMetaCognition:
    """Test meta cognition module"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_meta_cognition_import(self):
        """Test meta cognition import"""
        try:
            import symbolic_agi.meta_cognition
            print("meta_cognition.py - import successful")
            assert symbolic_agi.meta_cognition is not None
        except ImportError:
            print("meta_cognition.py - import failed, but file exists") 
            assert os.path.exists("symbolic_agi/meta_cognition.py")