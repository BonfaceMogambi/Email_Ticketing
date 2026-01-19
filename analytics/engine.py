import streamlit as st
from database.connection import get_db_connection

class AnalyticsEngine:
    @staticmethod
    def get_dashboard_metrics(conn):
        """Get comprehensive dashboard metrics"""
        cursor = conn.cursor()
        
        metrics = {}
        
        try:
            if st.session_state.get('debug', False):
                st.info("🔧 Debug: Fetching dashboard metrics...")
                
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
            
            if st.session_state.get('debug', False):
                st.success(f"🔧 Debug: Retrieved {len(metrics)} metric groups")
                
        except Exception as e:
            st.error(f"Analytics error: {e}")
        finally:
            cursor.close()
        
        return metrics