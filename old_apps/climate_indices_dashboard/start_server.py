#!/usr/bin/env python3
"""
Simple HTTP server to view the climate indices dashboard.
Run this script and open your browser to http://localhost:8080
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 8080

# Change to the script directory
os.chdir(Path(__file__).parent)

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow local file access
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def log_message(self, format, *args):
        # Custom logging format
        print(f"[Server] {args[0]}")

def main():
    Handler = MyHTTPRequestHandler

    print("=" * 80)
    print("CLIMATE INDICES DASHBOARD - LOCAL SERVER")
    print("=" * 80)
    print(f"\nStarting server on port {PORT}...")
    print(f"Server directory: {os.getcwd()}")

    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            url = f"http://localhost:{PORT}/index.html"
            print(f"\n✓ Server started successfully!")
            print(f"\n{'=' * 80}")
            print(f"Open your browser to: {url}")
            print(f"{'=' * 80}")
            print("\nPress Ctrl+C to stop the server\n")

            # Try to open browser automatically
            try:
                webbrowser.open(url)
                print("✓ Browser opened automatically\n")
            except:
                print("⚠ Could not open browser automatically")
                print(f"  Please open {url} manually\n")

            # Serve forever
            httpd.serve_forever()

    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("Server stopped by user")
        print("=" * 80)
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"\n✗ Error: Port {PORT} is already in use")
            print(f"  Either close the other application or change the PORT in this script")
        else:
            print(f"\n✗ Error starting server: {e}")

if __name__ == "__main__":
    main()
