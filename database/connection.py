import mysql.connector
from mysql.connector import Error
import streamlit as st
from config import Config

def get_db_connection():
    """Create and return a MySQL database connection"""
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
        )
        if Config.DEBUG:
            st.success("🔧 Debug: Database connection established")
        return conn
    except Error as e:
        st.error(f"Database connection error: {e}")
        return None