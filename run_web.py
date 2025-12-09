#!/usr/bin/env python3
"""
Run the Fantasy Analyzer web application.

Usage:
    python run_web.py [--host HOST] [--port PORT] [--debug]

Examples:
    python run_web.py                    # Run on http://localhost:5000
    python run_web.py --port 8080        # Run on http://localhost:8080
    python run_web.py --host 0.0.0.0     # Run on all interfaces
"""

import argparse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from analyzer.web.app import app, run_app


def main():
    parser = argparse.ArgumentParser(description='Run Fantasy Analyzer Web App')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')
    parser.add_argument('--no-debug', action='store_true',
                        help='Disable debug mode')

    args = parser.parse_args()

    debug = True if args.debug else (False if args.no_debug else True)

    print(f"""
╔═══════════════════════════════════════════════════════════╗
║         Fantasy Analyzer - MLB Best Ball                  ║
║                  Web Application                          ║
╠═══════════════════════════════════════════════════════════╣
║  Open in browser: http://{args.host}:{args.port:<24}║
╚═══════════════════════════════════════════════════════════╝
    """)

    run_app(host=args.host, port=args.port, debug=debug)


if __name__ == '__main__':
    main()
