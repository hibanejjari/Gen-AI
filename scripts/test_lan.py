#!/usr/bin/env python3
"""
LAN Testing Script for LLM Council.

This script helps verify network connectivity between machines
before demo day.

Usage:
    python scripts/test_lan.py --discover              # Find council nodes on LAN
    python scripts/test_lan.py --test-all              # Test all configured nodes
    python scripts/test_lan.py --test 192.168.1.101    # Test specific IP
    python scripts/test_lan.py --scan 192.168.1.0/24   # Scan subnet
"""

import argparse
import socket
import requests
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional

# Common ports to check
COUNCIL_PORT = 5001
CHAIRMAN_PORT = 9000
ORCHESTRATOR_PORT = 8080


def get_local_ip() -> str:
    """Get this machine's local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def check_port(ip: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False


def check_council_service(ip: str, port: int, timeout: float = 5.0) -> Tuple[bool, str, Optional[dict]]:
    """
    Check if a council service is running at the given address.
    
    Returns:
        Tuple of (is_healthy, service_type, health_data)
    """
    url = f"http://{ip}:{port}/health"
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            # Determine service type from response
            if 'chairman_id' in data:
                service_type = "chairman"
            elif 'node_id' in data:
                service_type = "council"
            elif 'orchestrator_version' in data:
                service_type = "orchestrator"
            else:
                service_type = "unknown"
            return True, service_type, data
        return False, "error", None
    except requests.Timeout:
        return False, "timeout", None
    except requests.ConnectionError:
        return False, "connection_error", None
    except Exception as e:
        return False, f"error: {e}", None


def ping_host(ip: str) -> bool:
    """Ping a host to check if it's reachable."""
    try:
        # Works on both Windows and Unix
        param = "-n" if sys.platform == "win32" else "-c"
        result = subprocess.run(
            ["ping", param, "1", "-W", "1", ip],
            capture_output=True,
            timeout=3
        )
        return result.returncode == 0
    except:
        return False


def scan_subnet(subnet: str, port: int = COUNCIL_PORT) -> List[str]:
    """
    Scan a subnet for hosts with the specified port open.
    
    Args:
        subnet: Subnet in CIDR notation (e.g., "192.168.1.0/24")
        port: Port to check
    
    Returns:
        List of IPs with the port open
    """
    import ipaddress
    
    network = ipaddress.ip_network(subnet, strict=False)
    found = []
    
    print(f"Scanning {subnet} for port {port}...")
    print("This may take a minute...")
    
    def check_host(ip):
        ip_str = str(ip)
        if check_port(ip_str, port, timeout=1.0):
            return ip_str
        return None
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(check_host, ip): ip for ip in network.hosts()}
        for future in as_completed(futures):
            result = future.result()
            if result:
                print(f"  Found: {result}:{port}")
                found.append(result)
    
    return found


def discover_nodes() -> dict:
    """Discover LLM Council nodes on the local network."""
    local_ip = get_local_ip()
    subnet = ".".join(local_ip.split(".")[:3]) + ".0/24"
    
    print(f"\nLocal IP: {local_ip}")
    print(f"Scanning subnet: {subnet}")
    print()
    
    results = {
        "orchestrators": [],
        "council_nodes": [],
        "chairmen": [],
        "unknown": []
    }
    
    # Scan for common ports
    ports_to_check = [ORCHESTRATOR_PORT, COUNCIL_PORT, CHAIRMAN_PORT]
    
    for port in ports_to_check:
        found_ips = scan_subnet(subnet, port)
        for ip in found_ips:
            healthy, service_type, data = check_council_service(ip, port)
            if healthy:
                entry = {
                    "ip": ip,
                    "port": port,
                    "url": f"http://{ip}:{port}",
                    "data": data
                }
                if service_type == "orchestrator":
                    results["orchestrators"].append(entry)
                elif service_type == "council":
                    results["council_nodes"].append(entry)
                elif service_type == "chairman":
                    results["chairmen"].append(entry)
                else:
                    results["unknown"].append(entry)
    
    return results


def test_node(ip: str, port: int = COUNCIL_PORT) -> bool:
    """Test connectivity to a specific node."""
    print(f"\nTesting {ip}:{port}...")
    
    # Step 1: Ping
    print(f"  1. Ping: ", end="")
    if ping_host(ip):
        print("✓ Host is reachable")
    else:
        print("✗ Host not responding to ping (may be blocked)")
    
    # Step 2: Port check
    print(f"  2. Port {port}: ", end="")
    if check_port(ip, port):
        print("✓ Port is open")
    else:
        print("✗ Port is closed or blocked")
        return False
    
    # Step 3: HTTP health check
    print(f"  3. Health check: ", end="")
    healthy, service_type, data = check_council_service(ip, port)
    if healthy:
        print(f"✓ Service is healthy ({service_type})")
        if data:
            if 'model' in data:
                print(f"     Model: {data.get('model')}")
            if 'ollama_status' in data:
                print(f"     Ollama: {data.get('ollama_status')}")
        return True
    else:
        print(f"✗ Service error: {service_type}")
        return False


def test_all_config(config_path: str = "config.yaml"):
    """Test all nodes in config file."""
    import yaml
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Config file not found: {config_path}")
        return
    
    print(f"\nTesting nodes from {config_path}...")
    
    # Test council nodes
    print("\n" + "="*50)
    print("COUNCIL NODES")
    print("="*50)
    
    for node in config.get('council_nodes', []):
        url = node.get('url', '')
        # Parse URL to get IP and port
        parts = url.replace('http://', '').replace('https://', '').split(':')
        ip = parts[0]
        port = int(parts[1]) if len(parts) > 1 else COUNCIL_PORT
        test_node(ip, port)
    
    # Test chairman
    chairman = config.get('chairman', {})
    if chairman:
        print("\n" + "="*50)
        print("CHAIRMAN")
        print("="*50)
        
        url = chairman.get('url', '')
        parts = url.replace('http://', '').replace('https://', '').split(':')
        ip = parts[0]
        port = int(parts[1]) if len(parts) > 1 else CHAIRMAN_PORT
        test_node(ip, port)


def print_network_info():
    """Print useful network information."""
    local_ip = get_local_ip()
    hostname = socket.gethostname()
    
    print("\n" + "="*50)
    print("NETWORK INFORMATION")
    print("="*50)
    print(f"  Hostname:  {hostname}")
    print(f"  Local IP:  {local_ip}")
    print(f"  Subnet:    {'.'.join(local_ip.split('.')[:3])}.0/24")
    print()
    print("  Expected URLs for this machine:")
    print(f"    Council Node: http://{local_ip}:5001")
    print(f"    Chairman:     http://{local_ip}:9000")
    print(f"    Orchestrator: http://{local_ip}:8080")


def main():
    parser = argparse.ArgumentParser(description="LAN Testing for LLM Council")
    parser.add_argument("--discover", action="store_true", help="Discover nodes on LAN")
    parser.add_argument("--test", metavar="IP", help="Test specific IP address")
    parser.add_argument("--port", type=int, default=COUNCIL_PORT, help="Port to test")
    parser.add_argument("--test-all", action="store_true", help="Test all configured nodes")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--scan", metavar="SUBNET", help="Scan subnet (e.g., 192.168.1.0/24)")
    parser.add_argument("--info", action="store_true", help="Show network info")
    
    args = parser.parse_args()
    
    if args.info or len(sys.argv) == 1:
        print_network_info()
    
    if args.discover:
        results = discover_nodes()
        print("\n" + "="*50)
        print("DISCOVERY RESULTS")
        print("="*50)
        
        print(f"\nOrchestrators ({len(results['orchestrators'])}):")
        for node in results['orchestrators']:
            print(f"  - {node['url']}")
        
        print(f"\nCouncil Nodes ({len(results['council_nodes'])}):")
        for node in results['council_nodes']:
            data = node.get('data', {})
            print(f"  - {node['url']} ({data.get('model', 'unknown')})")
        
        print(f"\nChairmen ({len(results['chairmen'])}):")
        for node in results['chairmen']:
            print(f"  - {node['url']}")
    
    if args.test:
        test_node(args.test, args.port)
    
    if args.test_all:
        test_all_config(args.config)
    
    if args.scan:
        found = scan_subnet(args.scan, args.port)
        print(f"\nFound {len(found)} hosts with port {args.port} open")


if __name__ == "__main__":
    main()
