#!/usr/bin/env python3
"""
Test runner for Danish Audio Downloader application.
This script runs all tests and provides a comprehensive test report.
"""

import unittest
import sys
import os
import time
from io import StringIO

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import test modules
try:
    import test_danish_audio_downloader
    import test_gui_components
except ImportError as e:
    print(f"Error importing test modules: {e}")
    print("Make sure all required dependencies are installed:")
    print("pip install PyQt5 requests beautifulsoup4 openai")
    sys.exit(1)


class CustomTestResult(unittest.TextTestResult):
    """Custom test result class to collect detailed information."""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.test_results = []
        self.start_time = None
        self.end_time = None
    
    def startTest(self, test):
        super().startTest(test)
        self.start_time = time.time()
    
    def stopTest(self, test):
        super().stopTest(test)
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        status = "PASS"
        if test in [failure[0] for failure in self.failures]:
            status = "FAIL"
        elif test in [error[0] for error in self.errors]:
            status = "ERROR"
        elif test in [skip[0] for skip in self.skipped]:
            status = "SKIP"
        
        self.test_results.append({
            'test': str(test),
            'status': status,
            'duration': duration
        })


class CustomTestRunner:
    """Custom test runner with detailed reporting."""
    
    def __init__(self, verbosity=2):
        self.verbosity = verbosity
    
    def run(self, test_suite):
        """Run the test suite and return results."""
        stream = StringIO()
        runner = unittest.TextTestRunner(
            stream=stream,
            verbosity=self.verbosity,
            resultclass=CustomTestResult
        )
        
        print("=" * 70)
        print("Danish Audio Downloader - Test Suite")
        print("=" * 70)
        
        start_time = time.time()
        result = runner.run(test_suite)
        end_time = time.time()
        
        # Print the test output
        stream.seek(0)
        output = stream.read()
        print(output)
        
        # Print summary
        self._print_summary(result, end_time - start_time)
        
        return result
    
    def _print_summary(self, result, total_time):
        """Print a detailed test summary."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped)
        passed = total_tests - failures - errors - skipped
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failures}")
        print(f"Errors: {errors}")
        print(f"Skipped: {skipped}")
        print(f"Total Time: {total_time:.2f} seconds")
        
        if hasattr(result, 'test_results'):
            print(f"Average Test Time: {total_time/total_tests:.4f} seconds")
        
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Print failures and errors
        if result.failures:
            print("\n" + "-" * 70)
            print("FAILURES:")
            print("-" * 70)
            for test, traceback in result.failures:
                print(f"\n{test}:")
                print(traceback)
        
        if result.errors:
            print("\n" + "-" * 70)
            print("ERRORS:")
            print("-" * 70)
            for test, traceback in result.errors:
                print(f"\n{test}:")
                print(traceback)
        
        # Overall result
        print("\n" + "=" * 70)
        if result.wasSuccessful():
            print("RESULT: ALL TESTS PASSED! ✅")
        else:
            print("RESULT: SOME TESTS FAILED! ❌")
        print("=" * 70)


def discover_tests():
    """Discover and load all test cases."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test modules
    try:
        # Core functionality tests
        core_tests = loader.loadTestsFromModule(test_danish_audio_downloader)
        suite.addTest(core_tests)
        print("✓ Loaded core functionality tests")
        
        # GUI component tests (may fail if no display available)
        try:
            gui_tests = loader.loadTestsFromModule(test_gui_components)
            suite.addTest(gui_tests)
            print("✓ Loaded GUI component tests")
        except Exception as e:
            print(f"⚠ Warning: Could not load GUI tests: {e}")
            print("  This is normal if running in a headless environment")
    
    except Exception as e:
        print(f"Error loading tests: {e}")
        return None
    
    return suite


def main():
    """Main test runner function."""
    print("Danish Audio Downloader - Test Suite Runner")
    print("Initializing tests...\n")
    
    # Discover tests
    test_suite = discover_tests()
    if test_suite is None:
        print("Failed to load tests!")
        return 1
    
    # Run tests
    runner = CustomTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
