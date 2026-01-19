import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class for environment variables"""
    
    # Database
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'sacco_tickets')
    
    # Email
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'saccodesksupport@co-opbank.co.ke')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    EMAIL_SERVICE_NAME = os.getenv('EMAIL_SERVICE_NAME', 'Office365')
    IMAP_SERVER = os.getenv('IMAP_SERVER', 'outlook.office365.com')
    IMAP_PORT = int(os.getenv('IMAP_PORT', 993))
    
    # App
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

class EmailConfig:
    def __init__(self):
        self.email = Config.EMAIL_ADDRESS
        self.password = Config.EMAIL_PASSWORD
        self.service_name = Config.EMAIL_SERVICE_NAME
        self.imap_server = Config.IMAP_SERVER
        self.imap_port = Config.IMAP_PORT