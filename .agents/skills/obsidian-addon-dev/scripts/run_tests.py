#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Helper script to run all Obsidian Addon Suite unit tests cleanly."""
import os
import sys
import unittest

def main():
    workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    tests_dir = os.path.join(workspace_dir, "tests")
    print(f"Running unit tests from: {tests_dir}")

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=tests_dir)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == "__main__":
    main()
