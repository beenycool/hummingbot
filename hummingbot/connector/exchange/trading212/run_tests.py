#!/usr/bin/env python3
"""
Test Runner for Trading212 Connector

This script runs all tests for the Trading212 connector.
"""

import sys
import os
import unittest
import asyncio

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

def run_unit_tests():
    """Run unit tests."""
    print("Running unit tests...")
    
    # Discover and run unit tests
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir="tests/connector/exchange/trading212",
        pattern="test_trading212_connector.py"
    )
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_integration_tests():
    """Run integration tests."""
    print("Running integration tests...")
    print("Note: Integration tests require a valid API key and are skipped by default.")
    
    # Discover and run integration tests
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir="tests/connector/exchange/trading212",
        pattern="test_trading212_integration.py"
    )
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def main():
    """Main test runner function."""
    print("Trading212 Connector Test Runner")
    print("=" * 40)
    
    # Run unit tests
    unit_success = run_unit_tests()
    
    print("\n" + "=" * 40)
    
    # Run integration tests
    integration_success = run_integration_tests()
    
    print("\n" + "=" * 40)
    print("Test Results:")
    print(f"Unit Tests: {'PASSED' if unit_success else 'FAILED'}")
    print(f"Integration Tests: {'PASSED' if integration_success else 'FAILED'}")
    
    if unit_success and integration_success:
        print("\nAll tests passed!")
        return 0
    else:
        print("\nSome tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())