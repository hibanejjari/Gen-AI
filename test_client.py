#!/usr/bin/env python3
"""
Test client for LLM Council.

Usage:
    python test_client.py "What is an API?"
    python test_client.py --health
    python test_client.py --status
"""

import argparse
import requests
import json
import sys
from typing import Optional

# Default orchestrator URL
DEFAULT_URL = "http://localhost:8080"


def print_header(text: str):
    """Print a formatted header."""
    width = 60
    print()
    print("=" * width)
    print(f" {text}")
    print("=" * width)


def print_json(data: dict, indent: int = 2):
    """Print formatted JSON."""
    print(json.dumps(data, indent=indent, default=str))


def check_health(base_url: str) -> bool:
    """Check system health."""
    print_header("SYSTEM HEALTH CHECK")
    
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        data = response.json()
        
        print(f"\nOrchestrator Status: {data.get('status', 'unknown')}")
        print(f"Can Process Queries: {'Yes' if data.get('can_process') else 'No'}")
        print(f"Healthy Nodes: {data.get('healthy_nodes', 0)}/{data.get('min_required', 2)} required")
        
        print("\nCouncil Nodes:")
        for node in data.get('council_nodes', []):
            status = "✓" if node.get('healthy') else "✗"
            error = f" ({node.get('error')})" if node.get('error') else ""
            print(f"  {status} {node.get('id')}: {node.get('url')}{error}")
        
        chairman = data.get('chairman')
        if chairman:
            status = "✓" if chairman.get('healthy') else "✗"
            error = f" ({chairman.get('error')})" if chairman.get('error') else ""
            print(f"\nChairman:")
            print(f"  {status} {chairman.get('id')}: {chairman.get('url')}{error}")
        
        return data.get('can_process', False)
        
    except requests.ConnectionError:
        print(f"\n✗ Cannot connect to orchestrator at {base_url}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def get_status(base_url: str):
    """Get detailed council status."""
    print_header("COUNCIL STATUS")
    
    try:
        response = requests.get(f"{base_url}/council/status", timeout=10)
        print_json(response.json())
    except Exception as e:
        print(f"Error: {e}")


def submit_query(base_url: str, question: str) -> Optional[dict]:
    """Submit a question to the council."""
    print_header("SUBMITTING QUERY TO LLM COUNCIL")
    
    print(f"\nQuestion: {question}")
    print("\nProcessing... (this may take a few minutes)")
    
    try:
        response = requests.post(
            f"{base_url}/query",
            json={"question": question},
            timeout=600  # 10 minute timeout for full workflow
        )
        
        if response.status_code != 200:
            print(f"\n✗ Error: HTTP {response.status_code}")
            print(response.text)
            return None
        
        data = response.json()
        
        # Print results
        print_header("STAGE 1: OPINIONS")
        opinions = data.get('opinions', {})
        for node_id, opinion in opinions.items():
            print(f"\n[{opinion.get('node_name', node_id)}] ({opinion.get('model', 'unknown')}):")
            print(f"{opinion.get('answer', 'No answer')[:500]}...")
            print(f"(Generation time: {opinion.get('generation_time_ms', 0):.0f}ms)")
        
        print_header("STAGE 2: REVIEWS")
        reviews = data.get('reviews', {})
        for node_id, review in reviews.items():
            print(f"\n[{node_id}] Review:")
            review_data = review.get('review', {})
            if 'scores' in review_data:
                print(f"  Scores: {json.dumps(review_data.get('scores', {}))}")
            if 'ranking' in review_data:
                print(f"  Ranking: {' > '.join(review_data.get('ranking', []))}")
        
        print_header("STAGE 3: FINAL ANSWER")
        print(f"\n{data.get('final_answer', 'No final answer')}")
        
        print_header("TIMING")
        timing = data.get('timing', {})
        print(f"  Stage 1 (Opinions):  {timing.get('stage_1_ms', 0):,.0f}ms")
        print(f"  Stage 2 (Reviews):   {timing.get('stage_2_ms', 0):,.0f}ms")
        print(f"  Stage 3 (Synthesis): {timing.get('stage_3_ms', 0):,.0f}ms")
        print(f"  Total:               {timing.get('total_ms', 0):,.0f}ms")
        
        print(f"\nNodes used: {', '.join(data.get('nodes_used', []))}")
        
        return data
        
    except requests.Timeout:
        print("\n✗ Request timed out. The council is taking too long.")
        return None
    except requests.ConnectionError:
        print(f"\n✗ Cannot connect to orchestrator at {base_url}")
        return None
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="LLM Council Test Client")
    parser.add_argument("question", nargs="?", help="Question to ask the council")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Orchestrator URL (default: {DEFAULT_URL})")
    parser.add_argument("--health", action="store_true", help="Check system health")
    parser.add_argument("--status", action="store_true", help="Get detailed council status")
    
    args = parser.parse_args()
    
    if args.health:
        check_health(args.url)
    elif args.status:
        get_status(args.url)
    elif args.question:
        # First check health
        if not check_health(args.url):
            print("\n⚠️  System is not ready. Please check the services.")
            sys.exit(1)
        
        # Submit query
        result = submit_query(args.url, args.question)
        if result is None:
            sys.exit(1)
    else:
        # Interactive mode
        print("LLM Council Test Client")
        print(f"Connected to: {args.url}")
        print()
        
        if not check_health(args.url):
            print("\n⚠️  System is not ready. Please check the services.")
            sys.exit(1)
        
        print("\nEnter a question (or 'quit' to exit):")
        while True:
            try:
                question = input("\n> ").strip()
                if question.lower() in ('quit', 'exit', 'q'):
                    break
                if question:
                    submit_query(args.url, question)
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break


if __name__ == "__main__":
    main()
