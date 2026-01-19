import hashlib
import streamlit as st
from datetime import datetime
from database.connection import get_db_connection

class AuthSystem:
    @staticmethod
    def hash_password(password):
        """Hash password using SHA-256"""
        if st.session_state.get('debug', False):
            st.info(f"🔧 Debug: Hashing password (length: {len(password)})")
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
        
        cursor = None
        try:
            cursor = conn.cursor()
            if st.session_state.get('debug', False):
                st.info(f"🔧 Debug: Authenticating user: {email}")
                
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
                
                user_info = {
                    'email': user_data[0],
                    'name': user_data[2],
                    'role': user_data[3]
                }
                
                if st.session_state.get('debug', False):
                    st.success(f"🔧 Debug: User authenticated successfully: {user_info}")
                    
                return user_info
            return None
            
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            conn.close()