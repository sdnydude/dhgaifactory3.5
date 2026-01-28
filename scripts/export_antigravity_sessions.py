#!/usr/bin/env python3
"""
Export Antigravity conversations via local LanguageServerService API.

This script connects to the local Antigravity language server and exports
all conversations to JSON format for ingestion into CR database.

Usage (on Mac where Antigravity is running):
    python3 export_antigravity_sessions.py --output sessions.json

Auto-detection:
    - Finds Antigravity process PID
    - Extracts CSRF token from process args
    - Determines port via lsof
"""

import argparse
import json
import subprocess
import sys
import requests
from pathlib import Path


def find_antigravity_process():
    """Find the Antigravity process and extract CSRF token and port."""
    try:
        # Find Antigravity process
        result = subprocess.run(
            ["pgrep", "-f", "antigravity"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("ERROR: Antigravity process not found. Is the app running?")
            sys.exit(1)
        
        pid = result.stdout.strip().split('\n')[0]
        print(f"Found Antigravity PID: {pid}")
        
        # Get process args to find CSRF token
        result = subprocess.run(
            ["ps", "-p", pid, "-o", "args="],
            capture_output=True,
            text=True
        )
        args = result.stdout.strip()
        
        # Extract CSRF token from --csrf_token argument
        csrf_token = None
        if "--csrf_token" in args:
            parts = args.split("--csrf_token")
            if len(parts) > 1:
                token_part = parts[1].strip().split()[0]
                csrf_token = token_part.strip("= ")
        
        if not csrf_token:
            print("ERROR: Could not extract CSRF token from process args")
            print(f"Process args: {args[:200]}...")
            sys.exit(1)
        
        print(f"Found CSRF token: {csrf_token[:10]}...")
        
        # Find port via lsof
        result = subprocess.run(
            ["lsof", "-p", pid, "-i", "-P", "-n"],
            capture_output=True,
            text=True
        )
        
        port = None
        for line in result.stdout.split('\n'):
            if "LISTEN" in line and "localhost" in line:
                # Extract port from line like "localhost:58575 (LISTEN)"
                parts = line.split(":")
                if len(parts) > 1:
                    port_part = parts[-1].split()[0]
                    if port_part.isdigit():
                        port = int(port_part)
                        break
        
        if not port:
            # Try alternative parsing
            for line in result.stdout.split('\n'):
                if "LISTEN" in line:
                    import re
                    match = re.search(r':(\d+)\s+\(LISTEN\)', line)
                    if match:
                        port = int(match.group(1))
                        break
        
        if not port:
            print("ERROR: Could not determine port from lsof")
            print("Try: lsof -p {pid} -i -P -n")
            sys.exit(1)
        
        print(f"Found port: {port}")
        
        return pid, csrf_token, port
        
    except Exception as e:
        print(f"ERROR finding Antigravity process: {e}")
        sys.exit(1)


def call_api(port, csrf_token, method, params=None):
    """Call the LanguageServerService API."""
    url = f"http://localhost:{port}/exa.language_server_pb.LanguageServerService/{method}"
    
    headers = {
        "Content-Type": "application/json",
        "Connect-Protocol-Version": "1",
        "X-Codeium-Csrf-Token": csrf_token
    }
    
    data = params or {}
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        print(f"ERROR: API call failed - {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return None
    
    return response.json()


def get_all_trajectories(port, csrf_token):
    """Get list of all conversation trajectories."""
    result = call_api(port, csrf_token, "GetAllCascadeTrajectories")
    if not result:
        return []
    
    trajectories = result.get("trajectories", result.get("cascades", []))
    print(f"Found {len(trajectories)} conversations")
    return trajectories


def get_trajectory_steps(port, csrf_token, cascade_id, start_index=0, end_index=1000):
    """Get all messages for a specific conversation."""
    result = call_api(port, csrf_token, "GetCascadeTrajectorySteps", {
        "cascadeId": cascade_id,
        "startIndex": start_index,
        "endIndex": end_index
    })
    if not result:
        return []
    
    return result.get("steps", result.get("messages", []))


def export_sessions(port, csrf_token, output_path):
    """Export all sessions to JSON format compatible with ingest script."""
    trajectories = get_all_trajectories(port, csrf_token)
    
    sessions = []
    for i, traj in enumerate(trajectories):
        cascade_id = traj.get("id", traj.get("cascadeId"))
        title = traj.get("title", traj.get("name", f"Session {i+1}"))
        
        print(f"  [{i+1}/{len(trajectories)}] Exporting: {title[:50]}...")
        
        steps = get_trajectory_steps(port, csrf_token, cascade_id)
        
        messages = []
        for step in steps:
            # Map to expected format
            role = step.get("role", "unknown")
            content = step.get("content", step.get("text", ""))
            
            # Normalize role names
            if role.lower() in ["user", "human"]:
                role = "user"
            elif role.lower() in ["assistant", "model", "ai"]:
                role = "assistant"
            
            messages.append({
                "role": role,
                "content": content
            })
        
        sessions.append({
            "session_id": cascade_id,
            "title": title,
            "messages": messages
        })
    
    # Write output
    output_path = Path(output_path)
    with open(output_path, 'w') as f:
        json.dump(sessions, f, indent=2)
    
    print(f"\nExported {len(sessions)} sessions ({sum(len(s['messages']) for s in sessions)} messages)")
    print(f"Output: {output_path}")
    
    return sessions


def main():
    parser = argparse.ArgumentParser(description="Export Antigravity conversations")
    parser.add_argument("--output", "-o", default="antigravity_sessions_export.json",
                        help="Output JSON file path")
    parser.add_argument("--port", type=int, help="Override port detection")
    parser.add_argument("--token", help="Override CSRF token detection")
    args = parser.parse_args()
    
    print("=== Antigravity Session Exporter ===\n")
    
    if args.port and args.token:
        pid, csrf_token, port = None, args.token, args.port
    else:
        pid, csrf_token, port = find_antigravity_process()
    
    print(f"\nExporting conversations...")
    export_sessions(port, csrf_token, args.output)


if __name__ == "__main__":
    main()
