#!/bin/bash
cd /home/hailo/claude-root/Projects/ApexAurum
./venv/bin/python sandbox/simple_browser_test.py
echo "Exit code: $?" > /tmp/browser_exit_code.txt
