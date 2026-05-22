"""
RMI TUI Dashboard - Terminal User Interface
===========================================

Interactive CLI dashboard for RMI platform.
Features:
- System status display
- Menu-driven navigation
- Quick commands for common actions
- Live backend status monitoring
"""

import sys
import os
import subprocess
import time
import json
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# Terminal colors
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[0;37m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


# ─── UI UTILITIES ──────────────────────────────────────────────────

def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')


def print_header(title: str):
    """Print centered header."""
    width = 60
    print(f"\n{Colors.BLUE}{'=' * width}{Colors.RESET}")
    print(f"{Colors.BLUE}║{Colors.RESET}{Colors.BOLD}{title.center(width - 2)}{Colors.RESET}{Colors.BLUE}║{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * width}{Colors.RESET}\n")


def print_box(title: str, content: str, color=Colors.WHITE):
    """Print content in a box."""
    lines = content.split('\n')
    max_len = max(len(l) for l in lines) if lines else 0
    width = max_len + 4
    
    print(f"\n{color}┌{'─' * width}┐{Colors.RESET}")
    print(f"{color}│{Colors.RESET} {Colors.BOLD}{title.center(width - 2)}{Colors.RESET} {color}│{Colors.RESET}")
    print(f"{color}├{'─' * width}┤{Colors.RESET}")
    for line in lines:
        print(f"{color}│{Colors.RESET} {line.ljust(width - 2)} {color}│{Colors.RESET}")
    print(f"{color}└{'─' * width}┘{Colors.RESET}\n")


# ─── STATUS MONITOR ────────────────────────────────────────────────

def get_backend_status(url: str = "http://127.0.0.1:8010") -> Dict[str, Any]:
    """Get backend health status."""
    try:
        response = requests.get(f"{url}/health", timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {"error": "Backend not reachable"}


def get_redis_status() -> Dict[str, Any]:
    """Get Redis connection status."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=2)
        if r.ping():
            info = r.info()
            return {
                "connected": True,
                "version": info.get("redis_version", "unknown"),
                "memory_used": info.get("used_memory_human", "unknown"),
                "connections": info.get("connected_clients", 0),
            }
    except Exception:
        pass
    return {"error": "Redis not reachable"}


# ─── DASHBOARD UI ──────────────────────────────────────────────────

class Dashboard:
    """Interactive TUI Dashboard."""
    
    def __init__(self):
        self.running = True
        self.current_view = "main"
    
    def display_main(self):
        """Display main menu."""
        clear_screen()
        
        # Header
        print(f"{Colors.CYAN}{Colors.BOLD}")
        print("╔════════════════════════════════════════════════════════════╗")
        print("║  RMI INTELLIGENCE PLATFORM           v2.0.0                ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print(f"{Colors.RESET}")
        
        # Status
        backend = get_backend_status()
        redis = get_redis_status()
        
        backend_status = f"{Colors.GREEN}● Online{Colors.RESET}" if backend.get("status") == "ok" else f"{Colors.RED}● Offline{Colors.RESET}"
        redis_status = f"{Colors.GREEN}● Connected{Colors.RESET}" if redis.get("connected") else f"{Colors.RED}● Disconnected{Colors.RESET}"
        
        print(f"{Colors.YELLOW}System Status:{Colors.RESET}")
        print(f"  Backend: {backend_status} | Redis: {redis_status}")
        
        if backend.get("status") == "ok":
            print(f"  Service: {backend.get('service', 'unknown')}")
            print(f"  Version: {backend.get('version', 'unknown')}")
            print(f"  Timestamp: {backend.get('timestamp', 'N/A')}")
        
        print(f"\n{Colors.YELLOW}Available Ports:{Colors.RESET}")
        print("  8010 - Main Backend API")
        print("  6379 - Redis Server")
        print("  22 - SSH (if enabled)")
        
        # Features
        print(f"\n{Colors.YELLOW}Built-in Features:{Colors.RESET}")
        features = [
            ("[1] Server Control", "Start/stop/restart backend server"),
            ("[2] Auth System", "User authentication & OAuth management"),
            ("[3] Security Intel", "Threat intel & contract scanning"),
            ("[4] x402 Micropayments", "Micropayment enforcement & tools"),
            ("[5] Chat Interface", "Direct chat with RMI assistant"),
            ("[6] Dashboard TUI", "Interactive terminal dashboard"),
            ("[7] Network Status", "Check all service connectivity"),
            ("[0] Quit", "Exit to shell"),
        ]
        
        for key, (name, desc) in enumerate(features):
            print(f"  {Colors.GREEN}{key}{Colors.RESET}. {Colors.CYAN}{name:<20}{Colors.RESET} - {desc}")
        
        print(f"\n{Colors.PURPLE}Use 'help' for more information{Colors.RESET}\n")
    
    def display_server_control(self):
        """Display server control menu."""
        print_header("Server Control")
        
        pid = self._get_backend_pid()
        status = "Running" if pid else "Stopped"
        
        print(f"  Backend Status: {Colors.GREEN if pid else Colors.RED}{status}{Colors.RESET}")
        if pid:
            print(f"  PID: {pid}")
        
        print("\n  Actions:")
        print(f"    {Colors.GREEN}1{Colors.RESET}. Start Backend")
        print(f"    {Colors.GREEN}2{Colors.RESET}. Stop Backend")
        print(f"    {Colors.GREEN}3{Colors.RESET}. Restart Backend")
        print(f"    {Colors.GREEN}0{Colors.RESET}. Back")
        
        choice = input("\n  Select: ").strip()
        
        if choice == "1":
            self._start_backend()
        elif choice == "2":
            self._stop_backend()
        elif choice == "3":
            self._restart_backend()
    
    def _get_backend_pid(self) -> Optional[int]:
        """Get backend process ID."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "uvicorn main:app"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout.strip():
                return int(result.stdout.strip())
        except Exception:
            pass
        return None
    
    def _start_backend(self):
        """Start backend server."""
        print("\n{Colors.YELLOW}Starting backend...{Colors.RESET}")
        try:
            subprocess.Popen(
                ["python3", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8010"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(3)
            print(f"{Colors.GREEN}Backend started!{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}Error starting backend: {e}{Colors.RESET}")
    
    def _stop_backend(self):
        """Stop backend server."""
        pid = self._get_backend_pid()
        if pid:
            try:
                os.kill(pid, 15)
                print(f"{Colors.GREEN}Backend stopped (PID: {pid}){Colors.RESET}")
            except Exception as e:
                print(f"{Colors.RED}Error stopping backend: {e}{Colors.RESET}")
    
    def _restart_backend(self):
        """Restart backend server."""
        self._stop_backend()
        time.sleep(1)
        self._start_backend()
    
    def display_auth_system(self):
        """Display auth system info."""
        print_header("Authentication System")
        
        print(f"  {Colors.CYAN}OAuth Providers:{Colors.RESET}")
        print("    • Email + Password")
        print("    • Google")
        print("    • Telegram")
        print("    • GitHub")
        print("    • Wallet Signature (EIP-4361)")
        
        print(f"\n  {Colors.CYAN}Features:{Colors.RESET}")
        print("    • Session management (JWT)")
        print("    • Rate limiting per user")
        print("    • x402 micropayment enforcement")
        
        print(f"\n  {Colors.CYAN}Endpoints:{Colors.RESET}")
        print("    POST /api/v1/auth/register   - Register new user")
        print("    POST /api/v1/auth/login      - Login user")
        print("    GET  /api/v1/auth/status     - Get current session")
        
        input(f"\n{Colors.PURPLE}Press Enter to return...{Colors.RESET}")
    
    def display_security_intel(self):
        """Display security intel info."""
        print_header("Security Intelligence")
        
        print(f"  {Colors.CYAN}Modules:{Colors.RESET}")
        print("    • Slither - Static analysis")
        print("    • Mythril - Symbolic execution")
        print("    • OFAC Sanctions - Blocklist")
        print("    • Threat Intel - Risk scoring")
        
        print(f"\n  {Colors.CYAN}Contract Scanning:{Colors.RESET}")
        print("    • Reentrancy detection")
        print("    • Integer overflow/underflow")
        print("    • Unchecked calls")
        print("    • DAO patterns")
        
        input(f"\n{Colors.PURPLE}Press Enter to return...{Colors.RESET}")
    
    def display_x402_menu(self):
        """Display x402 micropayments info."""
        print_header("x402 Micropayments")
        
        print(f"  {Colors.CYAN}Features:{Colors.RESET}")
        print("    • Micropayment enforcement")
        print("    • Rate-based pricing")
        print("    • Forensic analysis")
        print("    • Redis-backed tracking")
        
        print(f"\n  {Colors.CYAN}Endpoints:{Colors.RESET}")
        print("    GET  /api/v1/x402/tools      - Available tools catalog")
        print("    GET  /api/v1/x402/status     - Payment status")
        print("    POST /api/v1/x402/enforce    - Enforce micropayment")
        
        input(f"\n{Colors.PURPLE}Press Enter to return...{Colors.RESET}")
    
    def display_chat(self):
        """Launch chat interface."""
        print_header("Chat Interface")
        print("\n{Colors.YELLOW}Direct chat with RMI assistant{Colors.RESET}")
        print("\n{Colors.RED}Note:{Colors.RESET} This launches the system shell")
        
        input(f"\n{Colors.PURPLE}Press Enter to return...{Colors.RESET}")
    
    def display_network_status(self):
        """Display network connectivity status."""
        print_header("Network Status")
        
        tests = [
            ("Local Backend", "http://127.0.0.1:8010", "/health"),
            ("Redis", "localhost", None),
            ("Ethereum RPC", "https://ethereum-rpc.publicnode.com", None),
            ("Base RPC", "https://base-rpc.publicnode.com", None),
        ]
        
        for name, url, path in tests:
            try:
                full_url = f"{url}{path}" if path else url
                response = requests.get(full_url, timeout=3)
                status = f"{Colors.GREEN}✓ OK{Colors.RESET} ({response.status_code})"
            except Exception as e:
                status = f"{Colors.RED}✗ Failed{Colors.RESET}"
            
            print(f"  {name:<20} {status}")
        
        print()
        input(f"{Colors.PURPLE}Press Enter to return...{Colors.RESET}")
    
    def run(self):
        """Main dashboard loop."""
        while self.running:
            self.display_main()
            
            choice = input("Select an option: ").strip().lower()
            
            if choice == "0":
                self.running = False
            elif choice == "1":
                self.display_server_control()
            elif choice == "2":
                self.display_auth_system()
            elif choice == "3":
                self.display_security_intel()
            elif choice == "4":
                self.display_x402_menu()
            elif choice == "5":
                self.display_chat()
            elif choice == "6":
                print("{TUI already running}")
            elif choice == "7":
                self.display_network_status()
            elif choice in ["help", "?"]:
                print(f"{Colors.YELLOW}Commands:{Colors.RESET}")
                print("  help  - Show this help")
                print("  clear - Clear screen")
                print("  quit  - Exit dashboard")
            elif choice == "clear":
                clear_screen()
            elif choice in ["quit", "exit"]:
                self.running = False
            else:
                print(f"{Colors.RED}Invalid option{Colors.RESET}")


# ─── SINGLETON LAUNCHER ────────────────────────────────────────────

def launch_dashboard():
    """Launch the interactive dashboard."""
    try:
        dashboard = Dashboard()
        dashboard.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"{Colors.RED}Dashboard error: {e}{Colors.RESET}")


# ─── CLI ENTRY POINT ───────────────────────────────────────────────

if __name__ == "__main__":
    launch_dashboard()
