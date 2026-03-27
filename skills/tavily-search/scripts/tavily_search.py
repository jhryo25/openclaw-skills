#!/usr/bin/env python3
"""
Tavily Search API Client
Usage: python tavily_search.py <query> [--max-results N] [--search-depth basic|advanced]
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

def get_api_key():
    """Get API key from .env.tavily file or environment variable."""
    # Try to load from .env.tavily in workspace
    env_path = Path('/Users/huangd/.openclaw/workspace/.env.tavily')
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith('TAVILY_API_KEY='):
                    return line.strip().split('=', 1)[1]
    
    # Fallback to environment variable
    return os.environ.get('TAVILY_API_KEY')

def search(query, max_results=5, search_depth="basic"):
    """Perform Tavily search."""
    api_key = get_api_key()
    if not api_key:
        print("Error: TAVILY_API_KEY not found in .env.tavily or environment", file=sys.stderr)
        sys.exit(1)
    
    url = "https://api.tavily.com/search"
    
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
        "include_answer": True,
        "include_raw_content": False
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"HTTP Error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Tavily Search')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--max-results', type=int, default=5, help='Maximum results (default: 5)')
    parser.add_argument('--search-depth', choices=['basic', 'advanced'], default='basic',
                        help='Search depth (default: basic)')
    parser.add_argument('--json', action='store_true', help='Output raw JSON')
    
    args = parser.parse_args()
    
    result = search(args.query, args.max_results, args.search_depth)
    
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Pretty print results
        if 'answer' in result and result['answer']:
            print(f"\n📌 AI Answer:\n{result['answer']}\n")
        
        print(f"🔍 Search Results ({len(result.get('results', []))} found):\n")
        
        for i, r in enumerate(result.get('results', []), 1):
            print(f"{i}. {r.get('title', 'No title')}")
            print(f"   URL: {r.get('url', 'N/A')}")
            print(f"   Content: {r.get('content', 'No content')[:200]}...")
            print()

if __name__ == '__main__':
    main()
