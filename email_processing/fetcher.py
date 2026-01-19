import streamlit as st
from imap_tools import MailBox, AND
from config import EmailConfig
from email_processing.analyzer import AIEmailAnalyzer

class EmailFetcher:
    def __init__(self, config: EmailConfig):
        self.config = config
        self.mailbox = None
        self.analyzer = AIEmailAnalyzer()
    
    def connect(self):
        try:
            if st.session_state.get('debug', False):
                st.info("🔧 Debug: Connecting to email server...")
                
            self.mailbox = MailBox(self.config.imap_server)
            self.mailbox.login(self.config.email, self.config.password, initial_folder='INBOX')
            
            if st.session_state.get('debug', False):
                st.success("🔧 Debug: Email connection successful")
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
            
            if st.session_state.get('debug', False):
                st.info(f"🔧 Debug: Fetched {len(emails)} new emails")
                
            return emails
        except Exception as e:
            st.error(f"Error fetching emails: {e}")
            return []
    
    def disconnect(self):
        if self.mailbox:
            self.mailbox.logout()
            if st.session_state.get('debug', False):
                st.info("🔧 Debug: Disconnected from email server")