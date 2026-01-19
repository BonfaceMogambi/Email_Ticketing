import streamlit as st
import time
import hashlib
import mysql.connector
from mysql.connector import Error  # ADD THIS IMPORT
from database.connection import get_db_connection

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
        _create_default_users(cursor)
        
        conn.commit()
        
        # FIX: Safe check for user session state
        user = st.session_state.get('user')
        if user and user.get("role", "").lower() == "admin":
            placeholder = st.empty()
            placeholder.success("✅ Database initialized successfully.")
            time.sleep(5)
            placeholder.empty()
        
    except Error as e:  # Now this will work
        st.error(f"Error initializing database: {e}")
    finally:
        cursor.close()
        conn.close()

def _create_default_users(cursor):
    """Create default users in the system"""
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