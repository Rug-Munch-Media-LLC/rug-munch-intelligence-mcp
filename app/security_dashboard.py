"""Stub security_dashboard - security alert aggregation"""
from typing import Dict, Any, List, Optional

class SecurityDashboard:
    """Security dashboard for monitoring alerts."""
    
    def __init__(self):
        self.alerts: List[Dict[str, Any]] = []
    
    def add_alert(self, alert: Dict[str, Any]) -> None:
        self.alerts.append(alert)
    
    def get_alerts(self, status: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        return self.alerts[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_alerts": len(self.alerts),
            "by_status": {"all": len(self.alerts)},
            "by_type": {},
        }


def create_alert_from_detection(detection: Dict[str, Any]) -> Dict[str, Any]:
    """Create an alert from a detection."""
    return {
        "id": f"alert_{detection.get('hash', 'unknown')}",
        "detection": detection,
        "status": "pending",
        "created_at": "2026-05-12T00:00:00Z",
    }

def get_dashboard() -> SecurityDashboard:
    """Get the global dashboard instance."""
    return SecurityDashboard()
