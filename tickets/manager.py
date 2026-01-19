import streamlit as st
from datetime import datetime
from database.connection import get_db_connection
from config import EmailConfig
from email_processing.analyzer import AIEmailAnalyzer
from email_processing.fetcher import EmailFetcher

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
            cursor.execute('''
                SELECT email, name 
                FROM users 
                WHERE role = "IT Staff" 
                AND is_active = TRUE
                AND email NOT IN (
                    SELECT DISTINCT assigned_to 
                    FROM tickets 
                    WHERE status = "open" 
                    AND assigned_to IS NOT NULL
                )
                ORDER BY name
            ''')
            staff = cursor.fetchall()
            
            if st.session_state.get('debug', False):
                st.info(f"🔧 Debug: Found {len(staff)} available staff members")
                
            return staff
        except Exception as e:
            st.error(f"Error fetching staff: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def assign_ticket(self, email_data: dict) -> str:
        conn = get_db_connection()
        if conn is None:
            return "db_error"
        
        cursor = conn.cursor()
        
        try:
            # Check if ticket already exists
            cursor.execute('SELECT id FROM tickets WHERE message_id = %s', (email_data['message_id'],))
            if cursor.fetchone():
                if st.session_state.get('debug', False):
                    st.info(f"🔧 Debug: Ticket with message_id {email_data['message_id']} already exists")
                return "exists"
            
            # Get available staff for automatic assignment
            staff_list = self.get_available_staff()
            if not staff_list:
                st.warning("🔧 Debug: No available staff for assignment")
                return "no_staff"
            
            # Automatic round-robin assignment
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
            
            if st.session_state.get('debug', False):
                st.success(f"🔧 Debug: Created ticket #{ticket_id} assigned to {assigned_to}")
            
            # Send notification email
            self._send_assignment_notification(assigned_to, email_data, ticket_id)
            
            return assigned_to
            
        except Exception as e:
            st.error(f"Database error: {e}")
            return "db_error"
        finally:
            cursor.close()
            conn.close()
    
    def _automatic_assignment(self, cursor, staff_list):
        """Automatic round-robin assignment among available staff"""
        cursor.execute('SELECT assigned_to FROM tickets ORDER BY assigned_at DESC LIMIT 1')
        last_assigned = cursor.fetchone()
        
        staff_emails = [staff[0] for staff in staff_list]
        
        # Verify active status for each staff member
        verified_staff_emails = []
        for email in staff_emails:
            cursor.execute('SELECT is_active FROM users WHERE email = %s', (email,))
            result = cursor.fetchone()
            if result and result[0]:
                verified_staff_emails.append(email)
        
        if not verified_staff_emails:
            return None
        
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
            
            if st.session_state.get('debug', False):
                st.success(f"🔧 Debug: Manually assigned ticket #{ticket_id} to {assigned_to}")
                
            return True
        except Exception as e:
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
            
            if st.session_state.get('debug', False):
                st.success(f"🔧 Debug: Closed ticket #{ticket_id}")
                
            return True
        except Exception as e:
            st.error(f"Error closing ticket: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def _send_assignment_notification(self, staff_email: str, email_data: dict, ticket_id: int):
        try:
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
            
            if st.session_state.get('debug', False):
                st.info(f"🔧 Debug: Would send email to {staff_email}: {subject}")
            
        except Exception as e:
            st.error(f"Failed to send notification: {e}")