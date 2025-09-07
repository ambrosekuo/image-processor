#!/usr/bin/env python3
"""
Test runner script for sprite-processor.

This script provides an easy way to run all tests with different configurations.
"""
import argparse
import subprocess
import sys
from pathlib import Path


def run_tests(test_type="all", verbose=True, coverage=False, parallel=False):
    """
    Run tests with the specified configuration.

    Args:
        test_type: Type of tests to run ('all', 'unit', 'integration', 'api', 'core', 'video', 'pipeline', 'cli')
        verbose: Whether to run tests in verbose mode
        coverage: Whether to run with coverage reporting
        parallel: Whether to run tests in parallel
    """
    # Base pytest command
    cmd = ["python", "-m", "pytest"]

    # Add test directory
    cmd.append("tests/")

    # Add verbosity
    if verbose:
        cmd.append("-v")

    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=sprite_processor", "--cov-report=html", "--cov-report=term"])

    # Add parallel execution if requested
    if parallel:
        cmd.extend(["-n", "auto"])

    # Filter tests by type
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "api":
        cmd.append("tests/test_api.py")
    elif test_type == "core":
        cmd.append("tests/test_core.py")
    elif test_type == "video":
        cmd.append("tests/test_video.py")
    elif test_type == "pipeline":
        cmd.append("tests/test_pipeline.py")
    elif test_type == "cli":
        cmd.append("tests/test_cli.py")
    elif test_type == "legacy":
        cmd.append("tests/test_remove.py")
    elif test_type != "all":
        print(f"Unknown test type: {test_type}")
        return False

    # Run the tests
    print(f"Running tests: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Run sprite-processor tests")
    parser.add_argument(
        "--type",
        choices=["all", "unit", "integration", "api", "core", "video", "pipeline", "cli", "legacy"],
        default="all",
        help="Type of tests to run",
    )
    parser.add_argument(
        "--no-verbose", action="store_true", help="Run tests without verbose output"
    )
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage reporting")
    parser.add_argument(
        "--parallel", action="store_true", help="Run tests in parallel (requires pytest-xdist)"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Run only quick tests (exclude slow tests)"
    )

    args = parser.parse_args()

    # Add quick test filter if requested
    if args.quick:
        # This would be handled by pytest markers
        pass

    success = run_tests(
        test_type=args.type,
        verbose=not args.no_verbose,
        coverage=args.coverage,
        parallel=args.parallel,
    )

    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
