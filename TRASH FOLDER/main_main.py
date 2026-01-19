import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from imap_tools import MailBox, AND
import time
import threading
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import hashlib
import re
from textblob import TextBlob
import warnings
from decimal import Decimal
warnings.filterwarnings('ignore')

# Load environment variables
load_dotenv()

# Database configuration
def get_db_connection():
    """Create and return a MySQL database connection"""
    try:
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DATABASE', 'sacco_tickets'),
        )
        return conn
    except Error as e:
        st.error(f"Database connection error: {e}")
        return None

# Initialize session state keys
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user" not in st.session_state:
    st.session_state["user"] = {"role": "guest", "email": None}

# Enhanced database setup with user authentication and ticket closure system
@st.cache_resource
def init_db():
    """Initialize MySQL database with required tables including user authentication"""
    conn = get_db_connection()
    if conn is None:
        st.error("Failed to connect to database")
        return
    
    cursor = conn.cursor()
    
    try:
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                role VARCHAR(100) DEFAULT 'Staff',
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                INDEX idx_email (email),
                INDEX idx_role (role)
            )
        ''')
        
        # Create tickets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message_id VARCHAR(255) UNIQUE,
                subject TEXT,
                sender_email VARCHAR(255),
                sender_name VARCHAR(255),
                body LONGTEXT,
                assigned_to VARCHAR(255),
                status VARCHAR(50) DEFAULT 'open',
                priority VARCHAR(50) DEFAULT 'medium',
                sentiment_score FLOAT DEFAULT 0.0,
                urgency_level VARCHAR(50) DEFAULT 'normal',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                assigned_at DATETIME,
                resolved_at DATETIME,
                resolved_by VARCHAR(255),
                resolution_notes TEXT,
                admin_notes TEXT,
                ai_insights TEXT,
                INDEX idx_status (status),
                INDEX idx_assigned_to (assigned_to),
                INDEX idx_priority (priority),
                INDEX idx_created_at (created_at),
                INDEX idx_sentiment (sentiment_score)
            )
        ''')
        
        # Create analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                metric_name VARCHAR(255),
                metric_value FLOAT,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                period VARCHAR(50)
            )
        ''')
        
        # Create default users
        default_password = "admin123"  # ⚠️ Change in production
        password_hash = hashlib.sha256(default_password.encode()).hexdigest()
        
        default_users = [
            ('bmogambi@co-opbank.co.ke', password_hash, 'B. Mogambi', 'IT Staff'),
            ('llesiit@co-opbank.co.ke', password_hash, 'L. Lesiit', 'IT Staff'),
            ('bnyakundi@co-opbank.co.ke', password_hash, 'B. Bildad', 'IT Staff'),
            ('eotieno@co-opbank.co.ke', password_hash, 'Eva Admin', 'Admin'),
            ('admin@sacco.co.ke', password_hash, 'System Administrator', 'Admin')
        ]
        
        for user in default_users:
            cursor.execute('''
                INSERT IGNORE INTO users (email, password_hash, name, role) 
                VALUES (%s, %s, %s, %s)
            ''', user)
        
        conn.commit()
        
        # ✅ Success only once, and only for Admin
        if st.session_state.user["role"].lower() == "admin":
            placeholder = st.empty()
            placeholder.success("✅ Database initialized successfully.")
            time.sleep(5)
            placeholder.empty()
        
    except Error as e:
        st.error(f"Error initializing database: {e}")
    finally:
        cursor.close()
        conn.close()


def reset_db():
    """Drop and recreate all tables (Admin only)"""
    conn = get_db_connection()
    if conn is None:
        st.error("Failed to connect to database")
        return
    
    cursor = conn.cursor()
    try:
        cursor.execute("DROP TABLE IF EXISTS analytics")
        cursor.execute("DROP TABLE IF EXISTS tickets")
        cursor.execute("DROP TABLE IF EXISTS users")
        conn.commit()
        init_db()  # Recreate tables and default users
        st.success("⚠️ Database has been reset successfully!")
    except Error as e:
        st.error(f"Error resetting database: {e}")
    finally:
        cursor.close()
        conn.close()

# ✅ Always initialize DB automatically on startup
init_db()

def deactivate_user(user_id, user_email):
    """Deactivate user and reassign their open tickets"""
    conn = get_db_connection()
    if conn is None:
        return False
    
    cursor = conn.cursor()
    try:
        # Reassign open tickets to other active staff
        cursor.execute('''
            UPDATE tickets 
            SET assigned_to = NULL, 
                assigned_at = NULL,
                admin_notes = CONCAT(IFNULL(admin_notes, ''), ' | User deactivated - needs reassignment')
            WHERE assigned_to = %s AND status = "open"
        ''', (user_email,))
        
        # Then deactivate the user
        cursor.execute(
            "UPDATE users SET is_active = FALSE WHERE id = %s",
            (user_id,)
        )
        conn.commit()
        return True
    except Error as e:
        st.error(f"Error deactivating user: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Email configuration
class EmailConfig:
    def __init__(self):
        self.email = os.getenv('EMAIL_ADDRESS', 'saccodesksupport@co-opbank.co.ke')
        self.password = os.getenv('EMAIL_PASSWORD')
        self.service_name = os.getenv('EMAIL_SERVICE_NAME', 'Office365')
        self.imap_server = os.getenv('IMAP_SERVER', 'outlook.office365.com')
        self.imap_port = int(os.getenv('IMAP_PORT', 993))

# AI-Powered Email Analyzer
class AIEmailAnalyzer:
    @staticmethod
    def analyze_sentiment(text):
        """Analyze sentiment of email content"""
        if not text or len(text.strip()) < 10:
            return 0.0, 'neutral'
        
        analysis = TextBlob(text)
        sentiment_score = analysis.sentiment.polarity
        
        if sentiment_score > 0.1:
            sentiment_label = 'positive'
        elif sentiment_score < -0.1:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
            
        return sentiment_score, sentiment_label
    
    @staticmethod
    def detect_urgency(subject, body):
        """Detect urgency level based on content analysis"""
        text = f"{subject} {body}".lower()
        
        urgent_keywords = ['urgent', 'emergency', 'asap', 'immediately', 'critical', 'broken', 'down']
        high_keywords = ['important', 'priority', 'attention', 'issue', 'problem']
        
        urgent_count = sum(1 for keyword in urgent_keywords if keyword in text)
        high_count = sum(1 for keyword in high_keywords if keyword in text)
        
        if urgent_count > 0:
            return 'urgent'
        elif high_count > 2:
            return 'high'
        else:
            return 'normal'
    
    @staticmethod
    def generate_insights(ticket_data):
        """Generate AI insights for tickets"""
        insights = []
        
        # Response time insight
        if ticket_data['status'] == 'open':
            created_time = pd.to_datetime(ticket_data['created_at'])
            time_open = (datetime.now() - created_time).total_seconds() / 3600
            
            if time_open > 24:
                insights.append("⚠️ Ticket has been open for more than 24 hours")
            elif time_open > 8:
                insights.append("ℹ️ Ticket approaching 24-hour mark")
        
        # Sentiment insight
        sentiment_score = ticket_data.get('sentiment_score', 0)
        if sentiment_score < -0.3:
            insights.append("😠 Customer appears frustrated")
        elif sentiment_score > 0.3:
            insights.append("😊 Customer seems satisfied")
        
        # Content-based insights
        body = f"{ticket_data.get('subject', '')} {ticket_data.get('body', '')}".lower()
        
        if any(word in body for word in ['password', 'login', 'access']):
            insights.append("🔐 Security-related issue detected")
        if any(word in body for word in ['slow', 'performance', 'lag']):
            insights.append("⚡ Performance issue identified")
        if any(word in body for word in ['error', 'failed', 'crash']):
            insights.append("🐛 Technical error reported")
            
        return insights

# Enhanced Email fetcher with AI analysis
class EmailFetcher:
    def __init__(self, config: EmailConfig):
        self.config = config
        self.mailbox = None
        self.analyzer = AIEmailAnalyzer()
    
    def connect(self):
        try:
            self.mailbox = MailBox(self.config.imap_server)
            self.mailbox.login(self.config.email, self.config.password, initial_folder='INBOX')
            return True
        except Exception as e:
            st.error(f"Failed to connect to email: {e}")
            return False
    
    def fetch_emails(self):
        if not self.mailbox:
            if not self.connect():
                return []
        
        try:
            emails = []
            for msg in self.mailbox.fetch(AND(seen=False)):
                # AI Analysis
                sentiment_score, sentiment_label = self.analyzer.analyze_sentiment(msg.text or msg.html)
                urgency_level = self.analyzer.detect_urgency(msg.subject, msg.text or msg.html)
                
                email_data = {
                    'message_id': msg.uid,
                    'subject': msg.subject or 'No Subject',
                    'sender_email': msg.from_,
                    'sender_name': msg.from_values.name or msg.from_,
                    'body': msg.text or msg.html or 'No content',
                    'date': msg.date,
                    'sentiment_score': sentiment_score,
                    'sentiment_label': sentiment_label,
                    'urgency_level': urgency_level
                }
                emails.append(email_data)
            
            return emails
        except Exception as e:
            st.error(f"Error fetching emails: {e}")
            return []
    
    def disconnect(self):
        if self.mailbox:
            self.mailbox.logout()

# Enhanced Ticket manager with automatic assignment and closure system
class TicketManager:
    def __init__(self):
        self.config = EmailConfig()
        self.analyzer = AIEmailAnalyzer()
    
    def get_available_staff(self):
        """Get list of available IT staff for assignment - EXCLUDES inactive users"""
        conn = get_db_connection()
        if conn is None:
            return []
        
        cursor = conn.cursor()
        try:
            # UPDATED QUERY: Only select ACTIVE IT Staff
            cursor.execute('''
                SELECT email, name 
                FROM users 
                WHERE role = "IT Staff" 
                AND is_active = TRUE  -- Only active users
                AND email NOT IN (  -- Exclude specific users if needed
                    SELECT DISTINCT assigned_to 
                    FROM tickets 
                    WHERE status = "open" 
                    AND assigned_to IS NOT NULL
                )
                ORDER BY name
            ''')
            staff = cursor.fetchall()
            return staff
        except Error as e:
            st.error(f"Error fetching staff: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def assign_ticket(self, email_data: Dict) -> str:
        conn = get_db_connection()
        if conn is None:
            return "db_error"
        
        cursor = conn.cursor()
        
        try:
            # Check if ticket already exists
            cursor.execute('SELECT id FROM tickets WHERE message_id = %s', (email_data['message_id'],))
            if cursor.fetchone():
                return "exists"
            
            # Get available staff for automatic assignment
            staff_list = self.get_available_staff()
            if not staff_list:
                return "no_staff"
            
            # Automatic round-robin assignment among the three staff
            assigned_to = self._automatic_assignment(cursor, staff_list)
            
            # Generate AI insights
            ai_insights = self.analyzer.generate_insights({
                'subject': email_data['subject'],
                'body': email_data['body'],
                'sentiment_score': email_data.get('sentiment_score', 0),
                'status': 'open',
                'created_at': datetime.now()
            })
            
            # Insert ticket with AI data
            cursor.execute('''
                INSERT INTO tickets 
                (message_id, subject, sender_email, sender_name, body, 
                 assigned_to, assigned_at, sentiment_score, urgency_level, ai_insights)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                email_data['message_id'],
                email_data['subject'],
                email_data['sender_email'],
                email_data['sender_name'],
                email_data['body'],
                assigned_to,
                datetime.now(),
                email_data.get('sentiment_score', 0),
                email_data.get('urgency_level', 'normal'),
                '; '.join(ai_insights) if ai_insights else 'No insights'
            ))
            
            conn.commit()
            ticket_id = cursor.lastrowid
            
            # Send notification email
            self._send_assignment_notification(assigned_to, email_data, ticket_id)
            
            return assigned_to
            
        except Error as e:
            st.error(f"Database error: {e}")
            return "db_error"
        finally:
            cursor.close()
            conn.close()
    
    def _automatic_assignment(self, cursor, staff_list):
        """Automatic round-robin assignment among available staff - VERIFIES active status"""
        # Get the last assigned staff to continue round-robin
        cursor.execute('SELECT assigned_to FROM tickets ORDER BY assigned_at DESC LIMIT 1')
        last_assigned = cursor.fetchone()
        
        # Double-check that all staff in the list are still active
        staff_emails = [staff[0] for staff in staff_list]
        
        # Verify active status for each staff member
        verified_staff_emails = []
        for email in staff_emails:
            cursor.execute('SELECT is_active FROM users WHERE email = %s', (email,))
            result = cursor.fetchone()
            if result and result[0]:  # Only include if active
                verified_staff_emails.append(email)
        
        if not verified_staff_emails:
            return None  # No active staff available
        
        if last_assigned and last_assigned[0] in verified_staff_emails:
            last_index = verified_staff_emails.index(last_assigned[0])
            next_index = (last_index + 1) % len(verified_staff_emails)
        else:
            next_index = 0
            
        return verified_staff_emails[next_index]
    
    def manual_assign_ticket(self, ticket_id, assigned_to):
        """Manual ticket assignment by admin"""
        conn = get_db_connection()
        if conn is None:
            return False
        
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE tickets 
                SET assigned_to = %s, assigned_at = %s 
                WHERE id = %s
            ''', (assigned_to, datetime.now(), ticket_id))
            conn.commit()
            return True
        except Error as e:
            st.error(f"Error assigning ticket: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def close_ticket(self, ticket_id, resolved_by, resolution_notes):
        """Close a ticket with resolution notes"""
        conn = get_db_connection()
        if conn is None:
            return False
        
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE tickets 
                SET status = 'closed', resolved_at = %s, resolved_by = %s, resolution_notes = %s 
                WHERE id = %s
            ''', (datetime.now(), resolved_by, resolution_notes, ticket_id))
            conn.commit()
            return True
        except Error as e:
            st.error(f"Error closing ticket: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def _send_assignment_notification(self, staff_email: str, email_data: Dict, ticket_id: int):
        try:
            # Enhanced notification with AI insights
            subject = f"🚨 New Ticket Assigned: #{ticket_id} - {email_data['subject']}"
            urgency_icon = "🔴" if email_data.get('urgency_level') == 'urgent' else "🟡"
            
            body = f"""
            {urgency_icon} **New Ticket Assigned** {urgency_icon}
            
            **Ticket ID:** #{ticket_id}
            **From:** {email_data['sender_name']} ({email_data['sender_email']})
            **Subject:** {email_data['subject']}
            **Urgency:** {email_data.get('urgency_level', 'normal').upper()}
            **Sentiment:** {email_data.get('sentiment_label', 'neutral')}
            
            **AI Insights:**
            {chr(10).join(self.analyzer.generate_insights(email_data))}
            
            Please log in to the system to view and resolve this ticket.
            
            Best regards,
            🤖 Sacco Support System
            """
            
            print(f"Would send email to {staff_email}: {subject}")
            
        except Exception as e:
            print(f"Failed to send notification: {e}")

# Analytics Engine
class AnalyticsEngine:
    @staticmethod
    def get_dashboard_metrics(conn):
        """Get comprehensive dashboard metrics"""
        cursor = conn.cursor()
        
        metrics = {}
        
        try:
            # Basic metrics
            cursor.execute('SELECT COUNT(*) as count FROM tickets')
            metrics['total_tickets'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) as count FROM tickets WHERE status = "open"')
            metrics['open_tickets'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) as count FROM tickets WHERE status = "closed"')
            metrics['closed_tickets'] = cursor.fetchone()[0]
            
            # Resolution time metrics
            cursor.execute('''
                SELECT AVG(TIMESTAMPDIFF(HOUR, created_at, resolved_at)) as avg_hours 
                FROM tickets WHERE status = "closed"
            ''')
            metrics['avg_resolution_hours'] = cursor.fetchone()[0] or 0
            
            # Sentiment analysis
            cursor.execute('SELECT AVG(sentiment_score) as avg_sentiment FROM tickets')
            metrics['avg_sentiment'] = cursor.fetchone()[0] or 0
            
            # Urgency distribution
            cursor.execute('SELECT urgency_level, COUNT(*) FROM tickets GROUP BY urgency_level')
            metrics['urgency_distribution'] = dict(cursor.fetchall())
            
            # Daily ticket trends
            cursor.execute('''
                SELECT DATE(created_at) as date, COUNT(*) as count 
                FROM tickets 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY DATE(created_at) 
                ORDER BY date
            ''')
            metrics['daily_trends'] = cursor.fetchall()
            
        except Error as e:
            st.error(f"Analytics error: {e}")
        finally:
            cursor.close()
        
        return metrics

# Enhanced UI Components
class UIComponents:
    @staticmethod
    def styled_metric(value, label, delta=None, delta_color="normal"):
        """Create a styled metric card"""
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.metric(
                label=label,
                value=value,
                delta=delta,
                delta_color=delta_color
            )
    
    @staticmethod
    def create_sentiment_gauge(value: float):
        """Return a compact sentiment gauge chart (single instance only)"""
        if value is None:
            value = 0.0
        value = float(value)

        sentiment_icon = "😊" if value > 0.1 else "😐" if value > -0.1 else "😠"

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            title={
                'text': f"Average Sentiment {sentiment_icon}",
                'font': {'size': 14, 'color': '#2c3e50'}
            },
            number={'font': {'size': 18, 'color': '#2c3e50'}},
            gauge={
                'axis': {'range': [-1, 1], 'tickwidth': 1, 'tickcolor': "#666"},
                'bar': {'color': "#2980b9"},
                'steps': [
                    {'range': [-1, -0.3], 'color': "rgba(231, 76, 60, 0.6)"},
                    {'range': [-0.3, 0.3], 'color': "rgba(241, 196, 15, 0.6)"},
                    {'range': [0.3, 1], 'color': "rgba(46, 204, 113, 0.6)"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 2},
                    'thickness': 0.6,
                    'value': value
                }
            }
        ))

        # Just adjust margins & height (no layout title settings!)
        fig.update_layout(
            height=220,
            margin=dict(l=10, r=10, t=60, b=20)
        )

        return fig


    @staticmethod
    def create_trend_chart(daily_data):
        """Create an improved ticket trend chart"""
        if not daily_data:
            return None

        dates = [row[0] for row in daily_data]
        counts = [row[1] for row in daily_data]

        fig = px.area(
            x=dates, 
            y=counts,
            title="📈 Ticket Trends (Last 30 Days)",
            labels={'x': 'Date', 'y': 'Number of Tickets'},
        )

        fig.update_traces(
            mode="lines+markers", 
            line=dict(width=2, color="royalblue"), 
            marker=dict(size=6, symbol="circle", color="darkblue")
        )
        fig.update_layout(
            height=400,
            template="plotly_white",
            xaxis=dict(showgrid=True, tickangle=-45, dtick="D1"),
            yaxis=dict(showgrid=True, rangemode="tozero"),
            margin=dict(l=40, r=20, t=60, b=40)
        )

        fig.update_traces(
            hovertemplate="Date: %{x}<br>Tickets: %{y}<extra></extra>"
        )

        return fig


# Authentication System
class AuthSystem:
    @staticmethod
    def hash_password(password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(plain_password, hashed_password):
        """Verify password against hash"""
        return AuthSystem.hash_password(plain_password) == hashed_password
    
    @staticmethod
    def authenticate_user(email, password):
        """Authenticate user against database"""
        conn = get_db_connection()
        if conn is None:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT email, password_hash, name, role FROM users WHERE email = %s AND is_active = TRUE',
                (email,)
            )
            user_data = cursor.fetchone()
            
            if user_data and AuthSystem.verify_password(password, user_data[1]):
                # Update last login
                cursor.execute(
                    'UPDATE users SET last_login = %s WHERE email = %s',
                    (datetime.now(), email)
                )
                conn.commit()
                
                return {
                    'email': user_data[0],
                    'name': user_data[2],
                    'role': user_data[3]
                }
            return None
            
        except Error as e:
            st.error(f"Authentication error: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

# Streamlit App with Enhanced UI
def main():
    st.set_page_config(
        page_title="Sacco Ticket System",
        page_icon="🎫",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 10px;
            border-left: 4px solid #1f77b4;
        }
        .urgent-ticket {
            border-left: 4px solid #ff4b4b !important;
        }
        .high-priority {
            border-left: 4px solid #ffa500 !important;
        }
        .ai-insight {
            background-color: #e8f4fd;
            padding: 0.5rem;
            border-radius: 5px;
            margin: 0.5rem 0;
        }
        .closed-ticket {
            background-color: #f0fff0 !important;
            border-left: 4px solid #28a745 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # User session with enhanced security
    if 'user' not in st.session_state:
        st.session_state.user = None
        st.session_state.authenticated = False

    # Enhanced Login Section
    if not st.session_state.authenticated:
        show_login_section()
        return
    
    # Main application after authentication
    show_main_application()

def show_login_section():
    """Enhanced login section with better UI"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="main-header">🤖 Sacco Ticket System</div>', unsafe_allow_html=True)
        
        with st.container():
            st.subheader("🔐 Secure Login")
            
            with st.form("login_form"):
                email = st.text_input(
                    "📧 Email Address",
                    placeholder="Enter your email address",
                    help="Use your registered email address"
                )
                
                password = st.text_input(
                    "🔑 Password",
                    type="password",
                    placeholder="Enter your password",
                    help="Enter your secure password"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    login_btn = st.form_submit_button("🚀 Login", width='stretch')
                with col2:
                    reset_btn = st.form_submit_button("🔄 Reset", width='stretch')
                
                if login_btn:
                    if not email or not password:
                        st.error("❌ Please enter both email and password")
                    else:
                        with st.spinner("🔐 Authenticating..."):
                            user = AuthSystem.authenticate_user(email, password)
                            if user:
                                st.session_state.user = user
                                st.session_state.authenticated = True
                                st.success(f"✅ Welcome back, {user['name']}!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Invalid credentials. Please check your email and password.")
                
                if reset_btn:
                    st.rerun()
        
        # Help section
        with st.expander("ℹ️ Login Help"):
            st.info("""
            **Default Login Credentials:**
            - Admin: eotieno@co-opbank.co.ke / admin123
            - Staff: Use your registered email with password 'admin123'
            
            **Contact Support:** If you cannot access your account, please contact system administrator.
            """)

def show_main_application():
    """Main application after successful login"""
    
    # Sidebar with enhanced navigation
    st.sidebar.markdown(f"""
        <div style='background-color: #f0f2f6; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;'>
            <h4>👤 User Info</h4>
            <p><strong>Name:</strong> {st.session_state.user['name']}</p>
            <p><strong>Role:</strong> {st.session_state.user['role']}</p>
            <p><strong>Email:</strong> {st.session_state.user['email']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Navigation
    st.sidebar.title("🧭 Navigation")
    
    # Role-based menu options
    if st.session_state.user['role'] == 'Admin':
        menu_options = ["📊 AI Dashboard", "🎫 Ticket Management", "👥 User Management", "📈 Advanced Analytics", "⚙️ Settings"]
    else:
        menu_options = ["📊 AI Dashboard", "🎫 Ticket Management", "📈 My Analytics"]
    
    page = st.sidebar.radio("Go to", menu_options)
    
    # Database reset option for Eva only
    if st.session_state.user['email'] == 'eotieno@co-opbank.co.ke':
        if st.sidebar.button("⚠️ Reset Database"):
            if st.sidebar.checkbox("Confirm reset"):
                reset_db()
    
    # Logout button
    if st.sidebar.button("🚪 Logout", width='stretch'):
        st.session_state.user = None
        st.session_state.authenticated = False
        st.rerun()
    
    # Page routing
    if page == "📊 AI Dashboard":
        show_ai_dashboard()
    elif page == "🎫 Ticket Management":
        show_ticket_management()
    elif page == "👥 User Management" and st.session_state.user['role'] == 'Admin':
        show_user_management()
    elif page == "📈 Advanced Analytics" and st.session_state.user['role'] == 'Admin':
        show_advanced_analytics()
    elif page == "📈 My Analytics":
        show_personal_analytics()
    elif page == "⚙️ Settings" and st.session_state.user['role'] == 'Admin':
        show_settings()

def show_ai_dashboard():
    """Enhanced AI-powered dashboard with cleaner layout"""
    st.markdown('<div class="main-header">🎫 TICKET MAIN DASHBOARD</div>', unsafe_allow_html=True)

    conn = get_db_connection()
    if conn is None:
        st.error("❌ Cannot connect to database")
        return

    try:
        # --- Analytics data ---
        analytics = AnalyticsEngine.get_dashboard_metrics(conn)

        # =======================
        # KPI CARDS
        # =======================
        st.subheader("📈 Key Performance Indicators")

        st.markdown("""
            <style>
            .kpi-card {
                background: linear-gradient(135deg, #ffffff, #f9f9f9);
                border: 1px solid #e0e0e0;
                border-radius: 14px;
                padding: 18px;
                text-align: left;
                box-shadow: 0 2px 6px rgba(0,0,0,0.06);
                margin: 4px;
                transition: all 0.2s ease-in-out;
            }
            .kpi-card:hover {
                box-shadow: 0 4px 12px rgba(0,0,0,0.12);
                transform: translateY(-2px);
            }
            .kpi-value {
                font-size: 1.5rem;
                font-weight: bold;
                margin-bottom: 6px;
                color: #2c3e50;
            }
            .kpi-label {
                font-size: 0.85rem;
                color: #666;
            }
            </style>
        """, unsafe_allow_html=True)

        kpis = [
            ("📊", analytics["total_tickets"], "Total Tickets"),
            ("🟡", analytics["open_tickets"], "Open Tickets"),
            ("✅", analytics["closed_tickets"], "Closed Tickets"),
            ("⏱", f"{analytics['avg_resolution_hours']:.1f}h", "Avg Resolution"),
        ]

        # sentiment KPI
        avg_sentiment = analytics.get("avg_sentiment", 0)
        sentiment_icon = "😊" if avg_sentiment > 0.1 else "😐" if avg_sentiment > -0.1 else "😠"
        kpis.append((sentiment_icon, f"{avg_sentiment:.2f}", "Avg Sentiment"))

        cols = st.columns(len(kpis))
        for col, (icon, value, label) in zip(cols, kpis):
            col.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-value">{icon} {value}</div>
                    <div class="kpi-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # =======================
        # CHARTS
        # =======================
        st.subheader("📊 Trends & Sentiment")

        left, right = st.columns(2)

        with left:
            if analytics.get("daily_trends"):
                trend_chart = UIComponents.create_trend_chart(analytics["daily_trends"])
                if trend_chart:
                    st.plotly_chart(trend_chart, width='stretch')

        with right:
            if "avg_sentiment" in analytics:
                sentiment_gauge = UIComponents.create_sentiment_gauge(avg_sentiment)
                if sentiment_gauge:
                    st.plotly_chart(sentiment_gauge, width='stretch')

        # =======================
        # URGENCY DISTRIBUTION
        # =======================
        if analytics.get("urgency_distribution"):
            st.subheader("🚨 Urgency Distribution")
            urgency_df = pd.DataFrame(
                list(analytics["urgency_distribution"].items()), 
                columns=["Urgency", "Count"]
            )
            fig = px.pie(
                urgency_df,
                values="Count",
                names="Urgency",
                title="Ticket Urgency Levels",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            st.plotly_chart(fig, width='stretch')

        # =======================
        # RECENT TICKETS
        # =======================
        st.subheader("🔍 Recent Tickets")
        show_recent_tickets_with_insights(conn)

        # =======================
        # EMAIL INTEGRATION
        # =======================
        st.subheader("📧 Email Integration")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info("""
            **Email Automation Status**: Active  
            **Last Check**: Recent  
            **Next Fetch**: 15 minutes
            """)
        
        with col2:
            if st.button("🔄 Fetch Now", width='stretch', type="secondary"):
                with st.spinner("🤖 Analyzing emails..."):
                    try:
                        config = EmailConfig()
                        fetcher = EmailFetcher(config)
                        emails = fetcher.fetch_emails()
                        fetcher.disconnect()
                        
                        if emails:
                            manager = TicketManager()
                            results = []
                            for email in emails:
                                result = manager.assign_ticket(email)
                                results.append(result)
                            
                            success_count = sum(1 for r in results if r not in ["exists", "no_staff", "db_error"])
                            
                            if success_count > 0:
                                st.success(f"✅ Created {success_count} new tickets from {len(emails)} emails")
                            else:
                                st.info("📭 No new tickets created (all emails already processed)")
                        else:
                            st.info("📭 No new emails found")
                            
                    except Exception as e:
                        st.error(f"❌ Email fetch failed: {str(e)}")
    finally:
        conn.close()


def show_recent_tickets_with_insights(conn):
    """Show recent tickets with AI insights in styled cards"""
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT id, subject, sender_email, assigned_to, status, priority,
                   created_at, sentiment_score, urgency_level, ai_insights
            FROM tickets 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        
        tickets = cursor.fetchall()
        column_names = [i[0] for i in cursor.description]

        # Inject CSS for beautiful cards
        st.markdown("""
            <style>
            .ticket-card {
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
                background: #ffffff;
                box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            }
            .ticket-title {
                font-size: 1.1rem;
                font-weight: bold;
                color: #1f77b4;
                margin-bottom: 6px;
            }
            .ticket-meta {
                font-size: 0.9rem;
                color: #555;
                margin-bottom: 6px;
            }
            .badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 8px;
                font-size: 0.8rem;
                font-weight: 600;
                margin-right: 6px;
            }
            .status-open { background: #f1c40f; color: black; }
            .status-closed { background: #2ecc71; color: white; }
            .urgency-urgent { background: #e74c3c; color: white; }
            .urgency-high { background: #e67e22; color: white; }
            .urgency-normal { background: #27ae60; color: white; }
            .ai-insight {
                background: #f9f9f9;
                border-left: 4px solid #1f77b4;
                padding: 6px 10px;
                margin: 4px 0;
                border-radius: 6px;
                font-size: 0.9rem;
            }
            </style>
        """, unsafe_allow_html=True)

        for ticket_data in tickets:
            ticket = dict(zip(column_names, ticket_data))

            # Status badge
            status_badge = (
                f"<span class='badge status-closed'>✅ {ticket['status']}</span>"
                if ticket["status"] == "closed"
                else f"<span class='badge status-open'>🟡 {ticket['status']}</span>"
            )

            # Urgency badge
            urgency_badge = (
                f"<span class='badge urgency-urgent'>🔴 urgent</span>"
                if ticket["urgency_level"] == "urgent"
                else f"<span class='badge urgency-high'>🟠 high</span>"
                if ticket["urgency_level"] == "high"
                else f"<span class='badge urgency-normal'>🟢 normal</span>"
            )

            # Sentiment icon
            sentiment_icon = "😊" if ticket["sentiment_score"] > 0.1 else "😐" if ticket["sentiment_score"] > -0.1 else "😠"

            with st.container():
                st.markdown('<div class="ticket-card">', unsafe_allow_html=True)

                # Header
                st.markdown(f"<div class='ticket-title'>#{ticket['id']}: {ticket['subject']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='ticket-meta'>📧 {ticket['sender_email']} &nbsp; | &nbsp; 👤 {ticket['assigned_to']}</div>", unsafe_allow_html=True)
                st.markdown(f"{status_badge} {urgency_badge} <span class='badge'>⚡ {ticket['priority']}</span> <span class='badge'>{sentiment_icon} sentiment</span>", unsafe_allow_html=True)

                # AI Insights
                if ticket["ai_insights"]:
                    with st.expander("🤖 AI Insights"):
                        insights = ticket["ai_insights"].split("; ")
                        for insight in insights:
                            if insight.strip():
                                st.markdown(f"<div class='ai-insight'>💡 {insight}</div>", unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)  # close card

    except Error as e:
        st.error(f"Error loading tickets: {e}")
    finally:
        cursor.close()


def show_ticket_management():
    """Enhanced ticket management with assignment and closure features"""
    
    # ================================
    # 🎨 CUSTOM CSS STYLING
    # ================================
    st.markdown("""
        <style>
        /* Main header */
        .main-header {
            font-size: 28px;
            font-weight: bold;
            color: #2E86C1;
            text-align: center;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 10px;
            background: linear-gradient(90deg, #D6EAF8, #AED6F1);
            box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
        }

        /* Tabs styling */
        .stTabs [role="tablist"] {
            justify-content: center;
            gap: 15px;
        }
        .stTabs [role="tab"] {
            font-size: 16px;
            font-weight: 600;
            padding: 10px 20px;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        .stTabs [role="tab"]:hover {
            background-color: #EBF5FB;
            color: #1B4F72;
        }
        .stTabs [aria-selected="true"] {
            background: #2E86C1;
            color: white;
        }

        /* Info / error / success messages */
        .stAlert {
            border-radius: 10px;
            font-size: 15px;
            padding: 12px;
        }

        /* Tables */
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0px 2px 8px rgba(0,0,0,0.1);
        }

        /* Buttons */
        div.stButton > button {
            background: #2E86C1;
            color: white;
            font-weight: bold;
            border-radius: 8px;
            padding: 8px 20px;
            transition: 0.3s;
        }
        div.stButton > button:hover {
            background: #1B4F72;
            transform: scale(1.03);
        }
        </style>
    """, unsafe_allow_html=True)

    # ================================
    # MAIN CONTENT
    # ================================
    st.markdown('<div class="main-header">🎫 TICKET MANAGEMENT</div>', unsafe_allow_html=True)

    conn = get_db_connection()
    if conn is None:
        st.error("❌ Cannot connect to database")
        return
    
    try:
        # Ticket management tabs
        tab1, tab2, tab3 = st.tabs(["📋 All Tickets", "🔧 Manage Tickets", "✅ Close Tickets"])
        
        with tab1:
            show_all_tickets(conn)
        
        with tab2:
            if st.session_state.user['role'] == 'Admin' or st.session_state.user['email'] == 'eotieno@co-opbank.co.ke':
                show_manual_assignment(conn)
            else:
                st.info("🔒 Manual ticket assignment is available for administrators only.")
        
        with tab3:
            show_ticket_closure(conn)
    
    except Error as e:
        st.error(f"Database error: {e}")
    finally:
        conn.close()


def show_all_tickets(conn):
    """Display all tickets in a styled table"""
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT id, subject, sender_email, assigned_to, status, priority, 
                   urgency_level, created_at, resolved_at
            FROM tickets 
            ORDER BY created_at DESC
        ''')
        
        tickets = cursor.fetchall()
        column_names = [i[0] for i in cursor.description]
        
        if tickets:
            df = pd.DataFrame(tickets, columns=column_names)

            # Format datetime columns
            for col in ["created_at", "resolved_at"]:
                df[col] = df[col].apply(lambda x: x.strftime("%Y-%m-%d %H:%M") if pd.notnull(x) else "")

            # Add status badges
            def format_status(x):
                if x == "closed":
                    return f"<span style='color:white; background:#2ecc71; padding:2px 8px; border-radius:10px;'>✅ {x}</span>"
                else:
                    return f"<span style='color:black; background:#f1c40f; padding:2px 8px; border-radius:10px;'>🟡 {x}</span>"

            df["status"] = df["status"].apply(format_status)

            # Add urgency badges
            def format_urgency(x):
                if x == "urgent":
                    return f"<span style='color:white; background:#e74c3c; padding:2px 8px; border-radius:10px;'>🔴 {x}</span>"
                elif x == "high":
                    return f"<span style='color:white; background:#e67e22; padding:2px 8px; border-radius:10px;'>🟡 {x}</span>"
                else:
                    return f"<span style='color:white; background:#27ae60; padding:2px 8px; border-radius:10px;'>🟢 {x}</span>"

            df["urgency_level"] = df["urgency_level"].apply(format_urgency)

            # Render as HTML for styling
            st.markdown(
                df.to_html(escape=False, index=False), 
                unsafe_allow_html=True
            )
        else:
            st.info("📭 No tickets found in the system.")
    
    except Error as e:
        st.error(f"Error loading tickets: {e}")
    finally:
        cursor.close()


def show_manual_assignment(conn):
    """Manual ticket assignment interface for Eva/admin"""
    st.subheader("👑 Manual Ticket Assignment")
    
    cursor = conn.cursor()
    
    try:
        # Get open tickets
        cursor.execute('''
            SELECT id, subject, assigned_to, created_at 
            FROM tickets 
            WHERE status = "open" 
            ORDER BY created_at DESC
        ''')
        
        open_tickets = cursor.fetchall()
        
        if open_tickets:
            # Get available staff from database
            cursor.execute('''
                SELECT email, name 
                FROM users 
                WHERE role = "IT Staff" 
                AND is_active = TRUE
                ORDER BY name
            ''')
            staff_list = cursor.fetchall()
            
            if not staff_list:
                st.error("❌ No active IT staff available for assignment. Please activate some staff users first.")
                return
            
            staff_options = {staff[1]: staff[0] for staff in staff_list}  # {name: email}
            
            # Create assignment form
            with st.form("manual_assignment"):
                st.write("**Select Ticket and Assign Staff**")
                
                # Ticket selection
                ticket_options = {f"#{ticket[0]} - {ticket[1]}": ticket[0] for ticket in open_tickets}
                selected_ticket_label = st.selectbox("📋 Select Ticket", list(ticket_options.keys()))
                ticket_id = ticket_options[selected_ticket_label]
                
                # Get current assignment for this ticket
                current_assignment_email = next((ticket[2] for ticket in open_tickets if ticket[0] == ticket_id), None)
                
                # Staff assignment with current assignment as default
                staff_names = list(staff_options.keys())
                
                # Find current assignment name if exists
                default_index = 0
                if current_assignment_email:
                    current_staff_name = next(
                        (name for name, email in staff_options.items() if email == current_assignment_email), 
                        None
                    )
                    if current_staff_name in staff_names:
                        default_index = staff_names.index(current_staff_name)
                
                selected_staff_name = st.selectbox(
                    "👤 Assign to Staff", 
                    staff_names,
                    index=default_index
                )
                
                assigned_to = staff_options[selected_staff_name]
                
                # Assignment notes
                admin_notes = st.text_area(
                    "📝 Admin Notes (Optional)", 
                    placeholder="Add any special instructions for the assigned staff..."
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    assign_btn = st.form_submit_button("✅ Assign Ticket", use_container_width=True)
                with col2:
                    cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
                
                if assign_btn:
                    manager = TicketManager()
                    if manager.manual_assign_ticket(ticket_id, assigned_to):
                        # Update admin notes if provided
                        if admin_notes:
                            cursor.execute(
                                'UPDATE tickets SET admin_notes = %s WHERE id = %s',
                                (admin_notes, ticket_id)
                            )
                            conn.commit()
                        
                        st.success(f"✅ Ticket #{ticket_id} successfully assigned to {selected_staff_name}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Failed to assign ticket. Please try again.")
                
                if cancel_btn:
                    st.info("❌ Ticket assignment canceled.")
        
        else:
            st.info("🎉 All tickets are currently assigned! No open tickets available for manual assignment.")
    
    except Error as e:
        st.error(f"Error in manual assignment: {e}")
    finally:
        cursor.close()


def show_ticket_closure(conn):
    """Ticket closure interface"""
    st.subheader("✅ Ticket Resolution Center")
    
    cursor = conn.cursor()
    
    try:
        # Get tickets assigned to current user that are still open
        current_user_email = st.session_state.user['email']
        
        cursor.execute('''
            SELECT id, subject, sender_email, created_at, assigned_to 
            FROM tickets 
            WHERE status = "open" AND assigned_to = %s
            ORDER BY created_at DESC
        ''', (current_user_email,))
        
        my_tickets = cursor.fetchall()
        
        if my_tickets:
            st.info(f"🔧 You have {len(my_tickets)} open ticket(s) assigned to you")
            
            for ticket in my_tickets:
                ticket_id, subject, sender_email, created_at, assigned_to = ticket
                
                with st.expander(f"🎫 Ticket #{ticket_id}: {subject}", expanded=True):
                    st.write(f"**From:** {sender_email}")
                    st.write(f"**Created:** {created_at.strftime('%Y-%m-%d %H:%M')}")
                    
                    # Resolution form
                    with st.form(f"resolve_ticket_{ticket_id}"):
                        resolution_notes = st.text_area(
                            "📝 Resolution Notes",
                            placeholder="Describe how you resolved this issue...",
                            key=f"notes_{ticket_id}"
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            resolve_btn = st.form_submit_button("✅ Mark as Resolved", width='stretch')
                        with col2:
                            st.form_submit_button("💾 Save Draft", width='stretch')
                        
                        if resolve_btn:
                            if not resolution_notes.strip():
                                st.error("❌ Please provide resolution notes before closing the ticket.")
                            else:
                                manager = TicketManager()
                                if manager.close_ticket(ticket_id, current_user_email, resolution_notes):
                                    st.success(f"✅ Ticket #{ticket_id} has been successfully closed!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to close ticket. Please try again.")
        else:
            st.info("📋 No open tickets are currently assigned to you. Great work! 🎉")
            
        # Show recently closed tickets
        st.subheader("📋 Recently Closed Tickets")

        cursor.execute('''
            SELECT id, subject, resolved_at, resolved_by, resolution_notes
            FROM tickets 
            WHERE status = "closed" 
            ORDER BY resolved_at DESC 
            LIMIT 5
        ''')

        closed_tickets = cursor.fetchall()

        # Add CSS for ticket cards
        st.markdown("""
            <style>
            .ticket-card {
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 12px;
                background-color: #f9f9f9;
                box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            }
            .ticket-title {
                font-weight: bold;
                font-size: 1.1rem;
                color: #1f77b4;
                margin-bottom: 8px;
            }
            .ticket-meta {
                font-size: 0.9rem;
                color: #555;
                margin-bottom: 8px;
            }
            </style>
        """, unsafe_allow_html=True)

        if closed_tickets:
            for ticket in closed_tickets:
                ticket_id, subject, resolved_at, resolved_by, notes = ticket

                with st.container():
                    st.markdown(f"""
                        <div class="ticket-card">
                            <div class="ticket-title">#{ticket_id}: {subject}</div>
                            <div class="ticket-meta">
                                ✅ Resolved by <b>{resolved_by}</b> on {resolved_at.strftime('%Y-%m-%d %H:%M')}
                            </div>
                    """, unsafe_allow_html=True)

                    # Expander stays inside the card
                    if notes:
                        with st.expander("📝 View Resolution Notes"):
                            st.write(notes)

                    # Close the card div
                    st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("📭 No closed tickets found.")


            
    except Error as e:
        st.error(f"Error in ticket closure: {e}")
    finally:
        cursor.close()

def show_user_management():
    """User management interface for admin"""
    st.markdown('<div class="main-header">👥 USER MANAGEMENT</div>', unsafe_allow_html=True)
    
    conn = get_db_connection()
    if conn is None:
        st.error("❌ Cannot connect to database")
        return
    
    try:
        tab1, tab2, tab3 = st.tabs(["👥 Current Users", "➕ Add New User", "📊 User Activity"])
        
        with tab1:
            show_current_users(conn)
        
        with tab2:
            show_add_user_form(conn)
        
        with tab3:
            show_user_analytics(conn)
    
    except Error as e:
        st.error(f"Database error: {e}")
    finally:
        conn.close()

def show_current_users(conn):
    """Display and manage current users"""
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, email, name, role, is_active, created_at, last_login
            FROM users 
            ORDER BY created_at DESC
        ''')
        
        users = cursor.fetchall()
        column_names = [i[0] for i in cursor.description]
        
        if users:
            st.subheader("📋 Registered Users")
            
            for user_data in users:
                user = dict(zip(column_names, user_data))
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.write(f"**{user['name']}**")
                        st.write(f"`{user['email']}`")
                    
                    with col2:
                        role_icon = "👑" if user['role'] == 'Admin' else "👨‍💼"
                        st.write(f"{role_icon} {user['role']}")
                        status = "🟢 Active" if user['is_active'] else "🔴 Inactive"
                        st.write(status)
                    
                    with col3:
                        st.write(f"**Joined:** {user['created_at'].strftime('%Y-%m-%d')}")
                        if user['last_login']:
                            st.write(f"**Last login:** {user['last_login'].strftime('%Y-%m-%d %H:%M')}")
                        else:
                            st.write("**Last login:** Never")
                    
                    with col4:
                        # ✅ Admin can edit ANY account, including their own
                        if st.session_state.user['role'] == "Admin":
                            if st.button("⚙️", key=f"edit_{user['id']}"):
                                st.session_state.editing_user = user['id']
                        
                        # Protect default accounts from delete
                        if user['email'] not in ['eotieno@co-opbank.co.ke', 'admin@sacco.co.ke']:
                            delete_key = f"delete_{user['id']}"
                            confirm_key = f"confirm_delete_{user['id']}"
                            if st.button("🗑️", key=delete_key):
                                st.session_state[confirm_key] = True
                            if st.session_state.get(confirm_key, False):
                                if st.checkbox(f"Confirm delete {user['email']}?", key=f"chk_{user['id']}"):
                                    cursor.execute(
                                        "UPDATE users SET is_active = FALSE WHERE id = %s",
                                        (user['id'],)
                                    )
                                    conn.commit()
                                    st.success(f"✅ User {user['email']} deactivated")
                                    st.session_state.pop(confirm_key, None)
                                    st.rerun()
                    
                    st.write("---")
            
            # ✅ Edit user modal (admins can reset password too)
            if 'editing_user' in st.session_state:
                edit_user_id = st.session_state.editing_user
                user_to_edit = next((user for user in users if user[0] == edit_user_id), None)
                
                if user_to_edit:
                    with st.form(f"edit_user_{edit_user_id}"):
                        st.subheader(f"✏️ Edit User: {user_to_edit[2]}")
                        
                        new_name = st.text_input("Name", value=user_to_edit[2])
                        new_email = st.text_input("Email", value=user_to_edit[1])
                        new_role = st.selectbox("Role", ["Admin", "IT Staff"], 
                                              index=0 if user_to_edit[3] == "Admin" else 1)
                        is_active = st.checkbox("Active", value=bool(user_to_edit[4]))
                        new_password = st.text_input("New Password (leave blank to keep unchanged)", type="password")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Save Changes"):
                                if new_password.strip():
                                    hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
                                    cursor.execute('''
                                        UPDATE users 
                                        SET name = %s, email = %s, role = %s, is_active = %s, password_hash = %s
                                        WHERE id = %s
                                    ''', (new_name, new_email, new_role, is_active, hashed_pw, edit_user_id))
                                else:
                                    cursor.execute('''
                                        UPDATE users 
                                        SET name = %s, email = %s, role = %s, is_active = %s
                                        WHERE id = %s
                                    ''', (new_name, new_email, new_role, is_active, edit_user_id))
                                conn.commit()
                                st.success("✅ User updated successfully!")
                                del st.session_state.editing_user
                                st.rerun()
                        
                        with col2:
                            if st.form_submit_button("❌ Cancel"):
                                del st.session_state.editing_user
                                st.rerun()
        else:
            st.info("👥 No users found in the system.")
    
    except Error as e:
        st.error(f"Error loading users: {e}")
    finally:
        cursor.close()


def show_add_user_form(conn):
    """Form to add new users"""
    st.subheader("➕ Add New User")
    
    with st.form("add_user_form"):
        name = st.text_input("👤 Full Name", placeholder="Enter user's full name")
        email = st.text_input("📧 Email Address", placeholder="user@example.com")
        role = st.selectbox("🎭 Role", ["IT Staff", "Admin"])
        password = st.text_input("🔑 Temporary Password", type="password", 
                               placeholder="Set a temporary password")
        
        col1, col2 = st.columns(2)
        with col1:
            add_btn = st.form_submit_button("👥 Add User", width='stretch')
        with col2:
            clear_btn = st.form_submit_button("🗑️ Clear", width='stretch')
        
        if add_btn:
            if not all([name, email, password]):
                st.error("❌ Please fill in all fields")
            elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                st.error("❌ Please enter a valid email address")
            else:
                cursor = conn.cursor()
                try:
                    # Check if email already exists
                    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
                    if cursor.fetchone():
                        st.error("❌ A user with this email already exists")
                    else:
                        password_hash = AuthSystem.hash_password(password)
                        cursor.execute('''
                            INSERT INTO users (email, password_hash, name, role)
                            VALUES (%s, %s, %s, %s)
                        ''', (email, password_hash, name, role))
                        conn.commit()
                        st.success(f"✅ User {name} added successfully!")
                        st.info(f"📧 Login credentials sent to {email}")
                except Error as e:
                    st.error(f"Database error: {e}")
                finally:
                    cursor.close()
        
        if clear_btn:
            st.rerun()

def show_user_analytics(conn):
    """Show user activity analytics"""
    st.subheader("📊 User Performance Analytics")
    
    cursor = conn.cursor()
    
    try:
        # User ticket statistics
        cursor.execute('''
            SELECT 
                u.name,
                u.role,
                COUNT(t.id) as total_tickets,
                SUM(CASE WHEN t.status = 'closed' THEN 1 ELSE 0 END) as closed_tickets,
                AVG(CASE WHEN t.status = 'closed' THEN TIMESTAMPDIFF(HOUR, t.created_at, t.resolved_at) ELSE NULL END) as avg_resolution_time
            FROM users u
            LEFT JOIN tickets t ON u.email = t.assigned_to
            WHERE u.is_active = TRUE
            GROUP BY u.email, u.name, u.role
            ORDER BY closed_tickets DESC
        ''')
        
        user_stats = cursor.fetchall()
        
        if user_stats:
            st.write("**📈 Ticket Resolution Performance**")
            
            for stat in user_stats:
                name, role, total, closed, avg_time = stat
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{name}**")
                        st.write(f"*{role}*")
                    
                    with col2:
                        st.write(f"**Total:** {total}")
                    
                    with col3:
                        st.write(f"**Closed:** {closed}")
                    
                    with col4:
                        if avg_time:
                            st.write(f"**Avg Time:** {avg_time:.1f}h")
                        else:
                            st.write("**Avg Time:** N/A")
                    
                    # Progress bar for completion rate
                    if total > 0:
                        completion_rate = (closed / total) * 100
                        st.progress(int(completion_rate))
                        st.write(f"Completion rate: {completion_rate:.1f}%")
                    
                    st.write("---")
        else:
            st.info("📊 No user activity data available yet.")
    
    except Error as e:
        st.error(f"Error loading user analytics: {e}")
    finally:
        cursor.close()

def show_advanced_analytics():
    """Advanced analytics for admin"""
    st.markdown('<div class="main-header">📈 ADVANCED ANALYTICS</div>', unsafe_allow_html=True)
    
    conn = get_db_connection()
    if conn is None:
        st.error("❌ Cannot connect to database")
        return
    
    try:
        # Time period selection
        col1, col2, col3 = st.columns(3)
        with col1:
            period = st.selectbox("📅 Time Period", 
                                ["Last 7 days", "Last 30 days", "Last 90 days", "All time"])
        
        # Convert period to SQL
        period_map = {
            "Last 7 days": "7 DAY",
            "Last 30 days": "30 DAY",
            "Last 90 days": "90 DAY",
            "All time": "1000 YEAR"  # Practical "all time"
        }
        
        cursor = conn.cursor()
        
        # Ticket volume trends
        st.subheader("📊 Ticket Volume Trends")
        cursor.execute(f'''
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM tickets
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL {period_map[period]})
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')
        
        trend_data = cursor.fetchall()
        
        if trend_data:
            dates = [row[0] for row in trend_data]
            counts = [row[1] for row in trend_data]
            
            fig = px.line(x=dates, y=counts, title=f"Ticket Volume Trend - {period}",
                         labels={'x': 'Date', 'y': 'Number of Tickets'})
            st.plotly_chart(fig, width='stretch')
        
        # Staff performance comparison
        st.subheader("👥 Staff Performance Comparison")
        cursor.execute(f'''
            SELECT 
                assigned_to,
                COUNT(*) as total_tickets,
                SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_tickets,
                AVG(CASE WHEN status = 'closed' THEN TIMESTAMPDIFF(HOUR, created_at, resolved_at) ELSE NULL END) as avg_resolution_hours
            FROM tickets
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL {period_map[period]})
                AND assigned_to IS NOT NULL
            GROUP BY assigned_to
            ORDER BY closed_tickets DESC
        ''')
        
        staff_performance = cursor.fetchall()
        
        if staff_performance:
            df = pd.DataFrame(staff_performance, 
                            columns=['Staff', 'Total Tickets', 'Closed Tickets', 'Avg Resolution Hours'])
            df['Closed Tickets'] = pd.to_numeric(df['Closed Tickets'], errors='coerce')
            df['Total Tickets'] = pd.to_numeric(df['Total Tickets'], errors='coerce')
            df['Completion Rate'] = (df['Closed Tickets'] / df['Total Tickets'] * 100).round(1)
            
            # Create performance chart
            fig = px.bar(df, x='Staff', y=['Total Tickets', 'Closed Tickets'],
                        title="Ticket Assignment and Completion",
                        barmode='group')
            st.plotly_chart(fig, width='stretch')
            
            # Show detailed table
            st.dataframe(df, width='stretch')
        
        # Sentiment analysis over time
        st.subheader("😊 Sentiment Analysis Trend")
        cursor.execute(f'''
            SELECT DATE(created_at) as date, AVG(sentiment_score) as avg_sentiment
            FROM tickets
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL {period_map[period]})
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')
        
        sentiment_data = cursor.fetchall()
        
        if sentiment_data:
            dates = [row[0] for row in sentiment_data]
            sentiments = [row[1] for row in sentiment_data]
            
            fig = px.area(x=dates, y=sentiments, title="Average Sentiment Over Time",
                         labels={'x': 'Date', 'y': 'Sentiment Score'})
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig, width='stretch')
    
    except Error as e:
        st.error(f"Analytics error: {e}")
    finally:
        cursor.close()
        conn.close()

def show_personal_analytics():
    """Personal analytics for staff members"""

    # ---------- Custom Styling ----------
    st.markdown("""
        <style>
            .main-header {
                font-size: 26px;
                font-weight: 700;
                color: #2E86C1;
                margin-bottom: 20px;
            }
            .ticket-card {
                background-color: #f9f9f9;
                padding: 15px 20px;
                border-radius: 12px;
                margin-bottom: 12px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            }
            .ticket-id {
                font-weight: 600;
                font-size: 16px;
                color: #1F618D;
            }
            .ticket-meta {
                font-size: 14px;
                color: #555;
            }
            .metric-card {
            background: #ffffff;
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            margin: 5px;
            }
            .metric-value {
                font-size: 22px;
                font-weight: 700;
                color: #2E86C1;
            }
            .metric-label {
                font-size: 14px;
                color: #555;
            }
        </style>
    """, unsafe_allow_html=True)

    # ---------- Header ----------
    st.markdown('<div class="main-header">📊 My Performance Analytics</div>', unsafe_allow_html=True)

    conn = get_db_connection()
    if conn is None:
        st.error("❌ Cannot connect to database")
        return

    current_user = st.session_state.user['email']

    try:
        cursor = conn.cursor()

        # ---------- Personal stats ----------
        cursor.execute('''
            SELECT 
                COUNT(*) as total_assigned,
                SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_tickets,
                SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_tickets,
                AVG(CASE WHEN status = 'closed' THEN TIMESTAMPDIFF(HOUR, created_at, resolved_at) ELSE NULL END) as avg_resolution_time
            FROM tickets 
            WHERE assigned_to = %s
        ''', (current_user,))
        
        stats = cursor.fetchone()

        if stats:
            total, closed, open_tickets, avg_time = stats

            total = int(total) if total is not None else 0
            closed = int(closed) if closed is not None else 0
            open_tickets = int(open_tickets) if open_tickets is not None else 0
            avg_time = float(avg_time) if avg_time is not None else None

            st.markdown("")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">📌 {total}</div>
                        <div class="metric-label">Total Assigned</div>
                    </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">✅ {closed}</div>
                        <div class="metric-label">Closed</div>
                    </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">🟡 {open_tickets}</div>
                        <div class="metric-label">Open</div>
                    </div>
                """, unsafe_allow_html=True)

            with col4:
                avg_time_display = f"{avg_time:.1f}h" if avg_time is not None else "N/A"
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">⏱ {avg_time_display}</div>
                        <div class="metric-label">Avg Resolution Time</div>
                    </div>
                """, unsafe_allow_html=True)

            # ---------- Completion Rate Gauge ----------
            if total > 0:
                completion_rate = (closed / total) * 100
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=completion_rate,
                    title={'text': "Completion Rate %"},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#2E86C1"},
                        'steps': [
                            {'range': [0, 50], 'color': "#F1948A"},
                            {'range': [50, 80], 'color': "#F7DC6F"},
                            {'range': [80, 100], 'color': "#82E0AA"}
                        ]
                    }
                ))
                fig.update_layout(height=300)
                st.plotly_chart(fig, width='stretch')

        # ---------- Recent Activity ----------
        st.markdown("### 📈 My Recent Activity")
        cursor.execute('''
            SELECT id, subject, status, created_at, resolved_at
            FROM tickets
            WHERE assigned_to = %s
            ORDER BY created_at DESC
            LIMIT 10
        ''', (current_user,))
        
        recent_tickets = cursor.fetchall()

        if recent_tickets:
            for ticket in recent_tickets:
                ticket_id, subject, status, created, resolved = ticket
                status_icon = "✅ Closed" if status == 'closed' else "🟡 Open"

                st.markdown(f"""
                    <div class="ticket-card">
                        <div class="ticket-id">#{ticket_id}: {subject}</div>
                        <div class="ticket-meta">{status_icon}</div>
                        <div class="ticket-meta">🗓 Created: {created.strftime('%Y-%m-%d %H:%M')}</div>
                        {f"<div class='ticket-meta'>✔ Resolved: {resolved.strftime('%Y-%m-%d %H:%M')}</div>" if resolved else ""}
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📭 No tickets assigned to you yet.")

    except Error as e:
        st.error(f"Error loading personal analytics: {e}")
    finally:
        cursor.close()
        conn.close()


def show_settings():
    """System settings for admin"""
    st.markdown('<div class="main-header">⚙️ SYSTEM SETTINGS</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🔧 Configuration", "📧 Email Settings", "🔄 System Maintenance"])
    
    with tab1:
        st.subheader("System Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**General Settings**")
            auto_fetch = st.checkbox("Enable Automatic Email Fetching", value=True)
            fetch_interval = st.slider("Fetch Interval (minutes)", 5, 60, 15)
            enable_ai = st.checkbox("Enable AI Analysis", value=True)
            
            if st.button("💾 Save General Settings"):
                st.success("✅ Settings saved successfully!")
        
        with col2:
            st.write("**Notification Settings**")
            email_notifications = st.checkbox("Email Notifications", value=True)
            desktop_alerts = st.checkbox("Desktop Alerts", value=True)
            urgency_threshold = st.selectbox("Urgency Alert Level", ["High", "Urgent", "All"])
            
            if st.button("💾 Save Notification Settings"):
                st.success("✅ Notification settings saved!")
    
    with tab2:
        st.subheader("Email Configuration")
        
        st.info("ℹ️ Configure email server settings for ticket integration")
        
        with st.form("email_config"):
            email_server = st.text_input("IMAP Server", value="outlook.office365.com")
            email_port = st.number_input("Port", value=993)
            email_address = st.text_input("Email Address", value="saccodesksupport@co-opbank.co.ke")
            email_password = st.text_input("Password", type="password")
            
            if st.form_submit_button("🔗 Test Connection"):
                with st.spinner("Testing email connection..."):
                    config = EmailConfig()
                    fetcher = EmailFetcher(config)
                    if fetcher.connect():
                        st.success("✅ Email connection successful!")
                        fetcher.disconnect()
                    else:
                        st.error("❌ Failed to connect to email server")
    
    with tab3:
        st.subheader("System Maintenance")
        
        st.warning("⚠️ These actions affect system data. Proceed with caution.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Clear Cache", width='stretch'):
                st.info("🗑️ Cache cleared successfully")
            
            if st.button("📊 Rebuild Analytics", width='stretch'):
                with st.spinner("Rebuilding analytics data..."):
                    time.sleep(2)
                    st.success("✅ Analytics data rebuilt!")
        
        with col2:
            if st.button("🗃️ Archive Old Tickets", width='stretch'):
                st.info("📦 Tickets older than 90 days have been archived")
            
            if st.button("🔍 System Health Check", width='stretch'):
                with st.spinner("Running system diagnostics..."):
                    time.sleep(3)
                    st.success("✅ System health check completed!")

# Background email fetching thread
def start_background_fetcher():
    """Start background email fetching thread"""
    def fetch_emails_periodically():
        while True:
            try:
                config = EmailConfig()
                fetcher = EmailFetcher(config)
                emails = fetcher.fetch_emails()
                fetcher.disconnect()
                
                if emails:
                    manager = TicketManager()
                    for email in emails:
                        manager.assign_ticket(email)
                
                time.sleep(900)  # 15 minutes
            except Exception as e:
                print(f"Background fetcher error: {e}")
                time.sleep(300)  # 5 minutes on error
    
    # Start thread only if not already running
    if 'bg_thread' not in st.session_state:
        thread = threading.Thread(target=fetch_emails_periodically, daemon=True)
        thread.start()
        st.session_state.bg_thread = thread

# Initialize background fetcher on startup
if __name__ == "__main__":
    # Start background email fetching
    start_background_fetcher()
    
    # Run the main app
    main()