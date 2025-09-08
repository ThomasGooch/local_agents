#!/usr/bin/env python3
"""
Comprehensive test runner for Local Agents project.

This script provides various testing modes and options to run the complete
test suite with different configurations and reporting options.
"""

import sys
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any


class TestRunner:
    """Manages test execution with various configurations."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_results: Dict[str, Any] = {}
        
    def run_command(self, cmd: List[str], description: str) -> bool:
        """Run a command and capture results."""
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"Command: {' '.join(cmd)}")
        print('='*60)
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            print(f"Exit code: {result.returncode}")
            print(f"Execution time: {execution_time:.2f} seconds")
            
            if result.stdout:
                print(f"\nSTDOUT:\n{result.stdout}")
            
            if result.stderr:
                print(f"\nSTDERR:\n{result.stderr}")
            
            self.test_results[description] = {
                'success': result.returncode == 0,
                'execution_time': execution_time,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT: {description} took longer than 10 minutes")
            self.test_results[description] = {
                'success': False,
                'execution_time': 600,
                'error': 'timeout'
            }
            return False
            
        except Exception as e:
            print(f"ERROR running {description}: {e}")
            self.test_results[description] = {
                'success': False,
                'execution_time': time.time() - start_time,
                'error': str(e)
            }
            return False
    
    def run_linting(self) -> bool:
        """Run code linting checks."""
        success = True
        
        # Flake8 linting
        cmd = ['flake8', 'src/local_agents', 'tests', '--max-line-length=88', '--extend-ignore=E203,W503']
        success &= self.run_command(cmd, "Code linting (flake8)")
        
        # Type checking
        cmd = ['mypy', 'src/local_agents', '--ignore-missing-imports', '--check-untyped-defs']
        success &= self.run_command(cmd, "Type checking (mypy)")
        
        # Black formatting check
        cmd = ['black', '--check', 'src/local_agents', 'tests']
        success &= self.run_command(cmd, "Code formatting check (black)")
        
        # isort import sorting check
        cmd = ['isort', '--check-only', 'src/local_agents', 'tests']
        success &= self.run_command(cmd, "Import sorting check (isort)")
        
        return success
    
    def run_security_checks(self) -> bool:
        """Run security vulnerability checks."""
        success = True
        
        # Bandit security linting
        cmd = ['bandit', '-r', 'src/local_agents', '-ll']
        success &= self.run_command(cmd, "Security scanning (bandit)")
        
        # Safety dependency scanning
        cmd = ['safety', 'check']
        success &= self.run_command(cmd, "Dependency vulnerability scanning (safety)")
        
        return success
    
    def run_unit_tests(self, coverage: bool = True, verbose: bool = True) -> bool:
        """Run unit tests."""
        cmd = ['pytest', 'tests/unit']
        
        if verbose:
            cmd.append('-v')
        
        if coverage:
            cmd.extend([
                '--cov=src/local_agents',
                '--cov-report=term-missing',
                '--cov-report=html:htmlcov',
                '--cov-fail-under=80'
            ])
        
        cmd.extend([
            '--tb=short',
            '-m', 'not slow',
            '--durations=10'
        ])
        
        return self.run_command(cmd, "Unit tests")
    
    def run_integration_tests(self, verbose: bool = True) -> bool:
        """Run integration tests."""
        cmd = ['pytest', 'tests/integration']
        
        if verbose:
            cmd.append('-v')
        
        cmd.extend([
            '--tb=short',
            '-m', 'not slow',
            '--timeout=300',
            '--durations=10'
        ])
        
        return self.run_command(cmd, "Integration tests")
    
    def run_performance_tests(self, verbose: bool = True) -> bool:
        """Run performance benchmarking tests."""
        cmd = ['pytest', 'tests/performance']
        
        if verbose:
            cmd.append('-v')
        
        cmd.extend([
            '--tb=short',
            '-m', 'performance',
            '--timeout=600',
            '--durations=10'
        ])
        
        return self.run_command(cmd, "Performance benchmarks")
    
    def run_cli_tests(self, verbose: bool = True) -> bool:
        """Run CLI integration tests."""
        cmd = ['pytest', 'tests/integration/test_cli_integration.py']
        
        if verbose:
            cmd.append('-v')
        
        cmd.extend([
            '--tb=short',
            '--timeout=300'
        ])
        
        return self.run_command(cmd, "CLI integration tests")
    
    def run_workflow_tests(self, verbose: bool = True) -> bool:
        """Run workflow orchestration tests."""
        cmd = ['pytest', 'tests/integration/test_workflows.py', 'tests/unit/test_orchestrator.py']
        
        if verbose:
            cmd.append('-v')
        
        cmd.extend([
            '--tb=short',
            '--timeout=300'
        ])
        
        return self.run_command(cmd, "Workflow tests")
    
    def run_all_tests(self, skip_slow: bool = True, coverage: bool = True) -> bool:
        """Run the complete test suite."""
        cmd = ['pytest', 'tests/']
        
        cmd.extend([
            '-v',
            '--tb=short',
            '--timeout=600',
            '--durations=20'
        ])
        
        if skip_slow:
            cmd.extend(['-m', 'not slow'])
        
        if coverage:
            cmd.extend([
                '--cov=src/local_agents',
                '--cov-report=term-missing',
                '--cov-report=html:htmlcov',
                '--cov-report=xml',
                '--cov-fail-under=80'
            ])
        
        return self.run_command(cmd, "Complete test suite")
    
    def generate_report(self):
        """Generate a comprehensive test report."""
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result['success'])
        total_time = sum(result['execution_time'] for result in self.test_results.values())
        
        print(f"\nOverall Results:")
        print(f"  Total test suites: {total_tests}")
        print(f"  Successful: {successful_tests}")
        print(f"  Failed: {total_tests - successful_tests}")
        print(f"  Total execution time: {total_time:.2f} seconds")
        print(f"  Success rate: {(successful_tests / total_tests * 100):.1f}%")
        
        print(f"\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            time_str = f"{result['execution_time']:.2f}s"
            print(f"  {status} {test_name:<40} {time_str:>8}")
            
            if not result['success'] and 'error' in result:
                print(f"    Error: {result['error']}")
        
        print("\n" + "="*80)
        
        # Return overall success
        return successful_tests == total_tests


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Local Agents Test Runner")
    
    parser.add_argument(
        '--mode',
        choices=['quick', 'full', 'unit', 'integration', 'performance', 'lint', 'security', 'cli', 'workflow'],
        default='quick',
        help='Test mode to run (default: quick)'
    )
    
    parser.add_argument(
        '--no-coverage',
        action='store_true',
        help='Skip coverage reporting'
    )
    
    parser.add_argument(
        '--include-slow',
        action='store_true',
        help='Include slow tests in execution'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Reduce output verbosity'
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    overall_success = True
    
    print("Starting Local Agents Test Suite")
    print(f"Mode: {args.mode}")
    print(f"Coverage: {'disabled' if args.no_coverage else 'enabled'}")
    print(f"Slow tests: {'included' if args.include_slow else 'excluded'}")
    
    if args.mode == 'lint':
        overall_success = runner.run_linting()
        
    elif args.mode == 'security':
        overall_success = runner.run_security_checks()
        
    elif args.mode == 'unit':
        overall_success = runner.run_unit_tests(
            coverage=not args.no_coverage,
            verbose=not args.quiet
        )
        
    elif args.mode == 'integration':
        overall_success = runner.run_integration_tests(verbose=not args.quiet)
        
    elif args.mode == 'performance':
        overall_success = runner.run_performance_tests(verbose=not args.quiet)
        
    elif args.mode == 'cli':
        overall_success = runner.run_cli_tests(verbose=not args.quiet)
        
    elif args.mode == 'workflow':
        overall_success = runner.run_workflow_tests(verbose=not args.quiet)
        
    elif args.mode == 'quick':
        # Quick test suite: linting + unit tests + basic integration
        overall_success &= runner.run_linting()
        overall_success &= runner.run_unit_tests(
            coverage=not args.no_coverage,
            verbose=not args.quiet
        )
        overall_success &= runner.run_cli_tests(verbose=not args.quiet)
        
    elif args.mode == 'full':
        # Complete test suite
        overall_success &= runner.run_linting()
        overall_success &= runner.run_security_checks()
        overall_success &= runner.run_all_tests(
            skip_slow=not args.include_slow,
            coverage=not args.no_coverage
        )
        overall_success &= runner.run_performance_tests(verbose=not args.quiet)
    
    # Generate final report
    final_success = runner.generate_report()
    overall_success &= final_success
    
    if overall_success:
        print("\n🎉 All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Check the report above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()