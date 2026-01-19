from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class User:
    id: Optional[int]
    email: str
    password_hash: str
    name: str
    role: str = "Staff"
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

@dataclass
class Ticket:
    id: Optional[int]
    message_id: str
    subject: str
    sender_email: str
    sender_name: str
    body: str
    assigned_to: Optional[str] = None
    status: str = "open"
    priority: str = "medium"
    sentiment_score: float = 0.0
    urgency_level: str = "normal"
    created_at: Optional[datetime] = None
    assigned_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    admin_notes: Optional[str] = None
    ai_insights: Optional[str] = None

@dataclass
class Analytics:
    id: Optional[int]
    metric_name: str
    metric_value: float
    recorded_at: Optional[datetime] = None
    period: Optional[str] = None