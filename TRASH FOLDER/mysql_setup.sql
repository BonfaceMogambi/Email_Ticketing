-- Create database
CREATE DATABASE IF NOT EXISTS sacco_tickets;
USE sacco_tickets;

-- Create tickets table
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    assigned_at DATETIME,
    resolved_at DATETIME,
    resolved_by VARCHAR(255),
    resolution_notes TEXT,
    admin_notes TEXT,
    INDEX idx_status (status),
    INDEX idx_assigned_to (assigned_to),
    INDEX idx_priority (priority),
    INDEX idx_created_at (created_at)
);

-- Create staff table
CREATE TABLE IF NOT EXISTS staff (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    role VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_email (email),
    INDEX idx_role (role)
);

-- Insert default staff
INSERT IGNORE INTO staff (email, name, role) VALUES 
('bmogambi@co-opbank.co.ke', 'B. Mogambi', 'IT Staff'),
('llesiit@co-opbank.co.ke', 'L. Lesiit', 'IT Staff'),
('bnyakundi@co-opbank.co.ke', 'B. Nyakundi', 'IT Staff'),
('eotieno@co-opbank.co.ke', 'E. Otieno', 'Admin');