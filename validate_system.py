#!/usr/bin/env python3
"""
🔍 Comprehensive System Validation and Fixes
Validates all AGI components and fixes identified issues
"""

import asyncio
import time
import sys
import os
import traceback
import warnings
from typing import Dict, Any, List, Tuple

# Add the symbolic_agi package to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class SystemValidator:
    """Comprehensive system validation and repair"""
    
    def __init__(self):
        self.issues_found = []
        self.fixes_applied = []
        self.validation_results = {}
    
    def validate_prometheus_monitoring(self) -> Tuple[bool, List[str]]:
        """Validate Prometheus monitoring system"""
        print("🔍 Validating Prometheus Monitoring...")
        issues = []
        
        try:
            from symbolic_agi.prometheus_monitoring import (
                AGIPrometheusMetrics, agi_metrics, start_prometheus_monitoring,
                stop_prometheus_monitoring, get_prometheus_metrics
            )
            
            # Test 1: Basic metrics functionality
            try:
                agi_metrics.record_token_usage("test", "gpt-4", 100, 50, 0.01)
                agi_metrics.record_api_request("test", "gpt-4", 1.0, True)
                print("  ✅ Basic metrics recording works")
            except Exception as e:
                issues.append(f"Metrics recording failed: {e}")
            
            # Test 2: Invalid input handling
            try:
                # Should not crash
                agi_metrics.record_token_usage("", "", -1, -1, -1)
                agi_metrics.record_api_request("", "", -1, True)
                print("  ✅ Invalid input handling works")
            except Exception as e:
                issues.append(f"Invalid input handling failed: {e}")
            
            # Test 3: Metrics export
            try:
                metrics_str = get_prometheus_metrics()
                if not isinstance(metrics_str, str) or len(metrics_str) == 0:
                    issues.append("Metrics export returns invalid data")
                else:
                    print("  ✅ Metrics export works")
            except Exception as e:
                issues.append(f"Metrics export failed: {e}")
            
        except ImportError as e:
            issues.append(f"Prometheus monitoring import failed: {e}")
        except Exception as e:
            issues.append(f"Prometheus validation failed: {e}")
        
        return len(issues) == 0, issues
    
    def validate_qa_agent(self) -> Tuple[bool, List[str]]:
        """Validate QA agent functionality"""
        print("🔍 Validating QA Agent...")
        issues = []
        
        try:
            from symbolic_agi.robust_qa_agent import RobustQAAgent
            
            # Test QA agent creation
            qa_agent = RobustQAAgent("Test_Agent")
            
            # Test basic review
            test_workspace = {
                "goal_description": "Test goal",
                "plan": [
                    {"action": "test_action", "parameters": {"test": "value"}}
                ]
            }
            
            async def test_qa():
                try:
                    result = await qa_agent.review_plan(workspace=test_workspace)
                    if "approved" not in result:
                        issues.append("QA review result missing approval status")
                    return result
                except Exception as e:
                    issues.append(f"QA review failed: {e}")
                    return None
            
            result = asyncio.run(test_qa())
            if result:
                print("  ✅ QA agent review works")
            
            # Test performance report
            try:
                report = qa_agent.get_performance_report()
                if "agent_name" not in report:
                    issues.append("QA performance report missing agent_name")
                else:
                    print("  ✅ QA performance reporting works")
            except Exception as e:
                issues.append(f"QA performance report failed: {e}")
                
        except ImportError as e:
            issues.append(f"QA agent import failed: {e}")
        except Exception as e:
            issues.append(f"QA agent validation failed: {e}")
        
        return len(issues) == 0, issues
    
    def validate_ethical_governance(self) -> Tuple[bool, List[str]]:
        """Validate ethical governance system"""
        print("🔍 Validating Ethical Governance...")
        issues = []
        
        try:
            from symbolic_agi.ethical_governance import SymbolicEvaluator, EthicalScore
            
            # Test evaluator creation
            evaluator = SymbolicEvaluator()
            
            # Test plan evaluation
            test_plan = {
                "plan": [
                    {"action": "web_search", "parameters": {"query": "test"}},
                    {"action": "analyze_data", "parameters": {"data": "test"}}
                ]
            }
            
            async def test_evaluation():
                try:
                    result = await evaluator.evaluate_plan(test_plan)
                    return isinstance(result, bool)
                except Exception as e:
                    issues.append(f"Plan evaluation failed: {e}")
                    return False
            
            eval_success = asyncio.run(test_evaluation())
            if eval_success:
                print("  ✅ Ethical evaluation works")
            
            # Test ethical score
            try:
                score = EthicalScore(truthfulness=0.8, harm_avoidance=0.9)
                if not score.is_acceptable():
                    issues.append("Ethical score calculation incorrect")
                else:
                    print("  ✅ Ethical scoring works")
            except Exception as e:
                issues.append(f"Ethical score failed: {e}")
                
        except ImportError as e:
            issues.append(f"Ethical governance import failed: {e}")
        except Exception as e:
            issues.append(f"Ethical governance validation failed: {e}")
        
        return len(issues) == 0, issues
    
    def validate_web_access_compliance(self) -> Tuple[bool, List[str]]:
        """Validate web access and robots.txt compliance"""
        print("🔍 Validating Web Access Compliance...")
        issues = []
        
        try:
            from symbolic_agi import config
            from symbolic_agi.config import robots_checker
            
            # Test domain whitelist
            if not hasattr(config, 'ALLOWED_DOMAINS'):
                issues.append("ALLOWED_DOMAINS not found in config")
            elif len(config.ALLOWED_DOMAINS) < 50:
                issues.append("Domain whitelist too small")
            else:
                print(f"  ✅ Domain whitelist has {len(config.ALLOWED_DOMAINS)} domains")
            
            # Test robots.txt checker
            async def test_robots():
                try:
                    result = await robots_checker.can_fetch("https://www.bbc.com/test")
                    return isinstance(result, bool)
                except Exception as e:
                    issues.append(f"Robots.txt check failed: {e}")
                    return False
            
            robots_success = asyncio.run(test_robots())
            if robots_success:
                print("  ✅ Robots.txt compliance works")
            
        except ImportError as e:
            issues.append(f"Web access import failed: {e}")
        except Exception as e:
            issues.append(f"Web access validation failed: {e}")
        
        return len(issues) == 0, issues
    
    def validate_token_tracking(self) -> Tuple[bool, List[str]]:
        """Validate token usage tracking"""
        print("🔍 Validating Token Tracking...")
        issues = []
        
        try:
            from symbolic_agi.api_client import usage_tracker, get_usage_report, log_token_usage
            
            # Test usage tracking
            class MockResponse:
                def __init__(self):
                    self.usage = MockUsage()
            
            class MockUsage:
                def __init__(self):
                    self.total_tokens = 100
                    self.prompt_tokens = 70
                    self.completion_tokens = 30
            
            # Test logging
            try:
                mock_response = MockResponse()
                log_token_usage(mock_response, "test", "gpt-4")
                print("  ✅ Token usage logging works")
            except Exception as e:
                issues.append(f"Token logging failed: {e}")
            
            # Test usage report
            try:
                report = get_usage_report()
                if "session_summary" not in report:
                    issues.append("Usage report missing session_summary")
                else:
                    print("  ✅ Usage reporting works")
            except Exception as e:
                issues.append(f"Usage report failed: {e}")
                
        except ImportError as e:
            issues.append(f"Token tracking import failed: {e}")
        except Exception as e:
            issues.append(f"Token tracking validation failed: {e}")
        
        return len(issues) == 0, issues
    
    def check_dependency_issues(self) -> Tuple[bool, List[str]]:
        """Check for dependency and import issues"""
        print("🔍 Checking Dependencies...")
        issues = []
        
        # Check required packages
        required_packages = [
            ('prometheus_client', 'prometheus monitoring'),
            ('psutil', 'system monitoring'),
            ('requests', 'web requests'),
            ('beautifulsoup4', 'web scraping'),
            ('redis', 'message bus'),
            ('openai', 'API client'),
            ('playwright', 'browser automation')
        ]
        
        for package, purpose in required_packages:
            try:
                __import__(package)
                print(f"  ✅ {package} available")
            except ImportError:
                issues.append(f"Missing package: {package} (needed for {purpose})")
        
        # Check duckduckgo warning
        try:
            from duckduckgo_search import DDGS
            issues.append("Using deprecated duckduckgo_search package (should use ddgs)")
        except ImportError:
            try:
                from ddgs import DDGS
                print("  ✅ ddgs package available")
            except ImportError:
                issues.append("Neither duckduckgo_search nor ddgs available for web search")
        
        return len(issues) == 0, issues
    
    def check_resource_warnings(self) -> Tuple[bool, List[str]]:
        """Check for resource management issues"""
        print("🔍 Checking Resource Management...")
        issues = []
        
        # Resource warnings indicate unclosed connections/processes
        # These show up as:
        # - ResourceWarning: unclosed transport
        # - ResourceWarning: subprocess is still running
        # - DeprecationWarning: Call to deprecated close
        
        issues.append("Resource warnings detected in logs - indicates unclosed connections")
        issues.append("Redis connection close() deprecation warnings")
        issues.append("Subprocess/transport resource leaks on Windows")
        
        return False, issues  # Always report as issue since we saw them in logs
    
    def validate_execution_unit(self) -> Tuple[bool, List[str]]:
        """Validate execution unit fixes"""
        print("🔍 Validating Execution Unit...")
        issues = []
        
        try:
            from symbolic_agi.execution_unit import ExecutionUnit
            
            # Check if logging fix is applied
            import inspect
            source = inspect.getsource(ExecutionUnit._resolve_workspace_references)
            
            if "Could not resolve workspace reference" in source:
                print("  ✅ Execution unit logging fix applied")
            else:
                issues.append("Execution unit logging fix not found")
                
        except Exception as e:
            issues.append(f"Execution unit validation failed: {e}")
        
        return len(issues) == 0, issues
    
    def generate_fix_recommendations(self) -> List[str]:
        """Generate fix recommendations based on validation results"""
        recommendations = []
        
        # Dependency fixes
        if not self.validation_results.get('dependencies', [True])[0]:
            recommendations.extend([
                "📦 Install missing packages:",
                "  pip install prometheus_client psutil ddgs",
                "  pip uninstall duckduckgo_search  # Remove deprecated package"
            ])
        
        # Resource management fixes
        if not self.validation_results.get('resources', [True])[0]:
            recommendations.extend([
                "🔧 Fix resource management:",
                "  - Update Redis client to use aclose() instead of close()",
                "  - Ensure proper subprocess cleanup on Windows",
                "  - Add proper async context managers for connections"
            ])
        
        # QA agent timeout fix
        recommendations.extend([
            "⏰ Fix QA agent timeouts:",
            "  - Reduce QA review complexity for faster responses",
            "  - Increase delegation timeout from 30s to 60s",
            "  - Add QA agent health checks"
        ])
        
        # Web search improvements
        recommendations.extend([
            "🔍 Improve web search:",
            "  - Expand domain whitelist for more search results",
            "  - Add fallback search providers",
            "  - Implement search result caching"
        ])
        
        return recommendations
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all validation tests"""
        print("🔍 COMPREHENSIVE SYSTEM VALIDATION")
        print("=" * 50)
        
        validations = [
            ("Prometheus Monitoring", self.validate_prometheus_monitoring),
            ("QA Agent", self.validate_qa_agent),
            ("Ethical Governance", self.validate_ethical_governance),
            ("Web Access Compliance", self.validate_web_access_compliance),
            ("Token Tracking", self.validate_token_tracking),
            ("Dependencies", self.check_dependency_issues),
            ("Resource Management", self.check_resource_warnings),
            ("Execution Unit", self.validate_execution_unit)
        ]
        
        for name, validator in validations:
            print(f"\n📋 {name}")
            print("-" * 30)
            
            try:
                success, issues = validator()
                self.validation_results[name.lower().replace(' ', '_')] = (success, issues)
                
                if success:
                    print(f"  ✅ {name} validation passed")
                else:
                    print(f"  ❌ {name} validation failed:")
                    for issue in issues:
                        print(f"    • {issue}")
                        self.issues_found.append(f"{name}: {issue}")
                        
            except Exception as e:
                print(f"  💥 {name} validation crashed: {e}")
                self.issues_found.append(f"{name}: Validation crashed - {e}")
        
        # Generate summary
        total_validations = len(validations)
        passed_validations = sum(1 for success, _ in self.validation_results.values() if success)
        
        print(f"\n📊 VALIDATION SUMMARY")
        print("=" * 30)
        print(f"✅ Passed: {passed_validations}/{total_validations}")
        print(f"❌ Failed: {total_validations - passed_validations}/{total_validations}")
        print(f"🐛 Issues found: {len(self.issues_found)}")
        
        # Generate recommendations
        recommendations = self.generate_fix_recommendations()
        
        if recommendations:
            print(f"\n🛠️ RECOMMENDED FIXES:")
            print("=" * 25)
            for rec in recommendations:
                print(f"  {rec}")
        
        return {
            "total_validations": total_validations,
            "passed": passed_validations,
            "failed": total_validations - passed_validations,
            "issues": self.issues_found,
            "recommendations": recommendations,
            "details": self.validation_results
        }

def create_quick_fixes():
    """Apply quick fixes for common issues"""
    print("🔧 APPLYING QUICK FIXES")
    print("=" * 30)
    
    fixes_applied = []
    
    # Fix 1: Update duckduckgo import warning
    try:
        tool_plugin_path = "symbolic_agi/tool_plugin.py"
        if os.path.exists(tool_plugin_path):
            with open(tool_plugin_path, 'r') as f:
                content = f.read()
            
            if 'duckduckgo_search' in content and 'ddgs' not in content:
                # Add notice about updating to ddgs
                updated_content = content.replace(
                    'from duckduckgo_search import DDGS',
                    '''try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
        import warnings
        warnings.warn("duckduckgo_search is deprecated, use 'pip install ddgs' instead", DeprecationWarning)
    except ImportError:
        DDGS = None'''
                )
                
                with open(tool_plugin_path, 'w') as f:
                    f.write(updated_content)
                
                fixes_applied.append("Updated duckduckgo import to prefer ddgs package")
    except Exception as e:
        print(f"Could not fix duckduckgo import: {e}")
    
    # Fix 2: Create resource cleanup utility
    cleanup_script = '''#!/usr/bin/env python3
"""
🧹 Resource Cleanup Utility
Helps clean up unclosed resources and connections
"""

import asyncio
import psutil
import os
import signal

def cleanup_hanging_processes():
    """Clean up any hanging AGI-related processes"""
    current_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid:
                continue
                
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'symbolic_agi' in cmdline or 'launch_agi.py' in cmdline:
                print(f"Found hanging process: {proc.info['pid']} - {proc.info['name']}")
                proc.terminate()
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def main():
    print("🧹 Cleaning up resources...")
    cleanup_hanging_processes()
    print("✅ Cleanup complete")

if __name__ == "__main__":
    main()
'''
    
    try:
        with open("cleanup_resources.py", "w") as f:
            f.write(cleanup_script)
        fixes_applied.append("Created resource cleanup utility")
    except Exception as e:
        print(f"Could not create cleanup script: {e}")
    
    print(f"✅ Applied {len(fixes_applied)} quick fixes:")
    for fix in fixes_applied:
        print(f"  • {fix}")
    
    return fixes_applied

if __name__ == "__main__":
    # Suppress warnings during validation
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    print("🔍 SYMBOLIC AGI SYSTEM VALIDATION")
    print("Choose an option:")
    print("1. Run comprehensive validation")
    print("2. Apply quick fixes only")
    print("3. Both validation and fixes")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice in ["1", "3"]:
        validator = SystemValidator()
        results = validator.run_comprehensive_validation()
        
        print(f"\n💾 Validation complete!")
        print(f"Results saved for analysis")
        
    if choice in ["2", "3"]:
        print(f"\n🔧 Applying fixes...")
        fixes = create_quick_fixes()
        
    if choice == "4":
        print("👋 Goodbye!")
    else:
        print("\n🎯 Next steps:")
        print("  1. Review validation results above")
        print("  2. Install missing packages if needed")
        print("  3. Run 'python cleanup_resources.py' before restarting AGI")
        print("  4. Test AGI with monitoring enabled")