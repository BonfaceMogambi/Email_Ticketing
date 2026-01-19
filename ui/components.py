import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

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
        """Return a compact sentiment gauge chart"""
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