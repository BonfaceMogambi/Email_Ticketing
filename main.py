import streamlit as st
import time
import threading
import os
import sys
from config import Config
from database.setup import init_db, reset_db
from auth.authentication import AuthSystem
from ui.pages import (
    show_login_section, 
    show_main_application
)
from email_processing.fetcher import EmailFetcher
from config import EmailConfig

# Initialize session state
def init_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "debug" not in st.session_state:
        st.session_state.debug = Config.DEBUG
    if "app_initialized" not in st.session_state:
        st.session_state.app_initialized = False

# Background email fetching thread
def start_background_fetcher():
    """Start background email fetching thread"""
    def fetch_emails_periodically():
        while True:
            try:
                if st.session_state.get('debug', False):
                    print("🔧 Debug: Background email fetch running...")
                    
                config = EmailConfig()
                fetcher = EmailFetcher(config)
                emails = fetcher.fetch_emails()
                fetcher.disconnect()
                
                if emails:
                    from tickets.manager import TicketManager
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

def main():
    # Page configuration
    st.set_page_config(
        page_title="Sacco Ticket System",
        page_icon="🎫",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Load custom CSS
    try:
        with open('static/style.css') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("CSS file not found. Application will run without custom styling.")
    
    # Initialize session state
    init_session_state()
    
    # Initialize database only once per session
    if not st.session_state.get('app_initialized', False):
        init_db()
        st.session_state.app_initialized = True
    
    # Debug panel (only show if debug mode is enabled)
    if st.session_state.get('debug', False):
        with st.sidebar.expander("🔧 Debug Panel"):
            st.write("Session State:", st.session_state)
            if st.button("Clear Session"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
    
    # Enhanced Login Section
    if not st.session_state.authenticated:
        show_login_section()
        return
    
    # Main application after authentication
    show_main_application()

# Initialize background fetcher on startup
if __name__ == "__main__":
    # Start background email fetching
    start_background_fetcher()
    
    # Run the main app
    main()