from textblob import TextBlob
from datetime import datetime
import pandas as pd

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