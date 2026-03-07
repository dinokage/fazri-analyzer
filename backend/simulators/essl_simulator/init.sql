-- eSSL Card Reader Database Schema
-- Simulates the database structure from eSSL X990/K90 series card readers

CREATE DATABASE IF NOT EXISTS essl_db;
USE essl_db;

-- Main access logs table (matches eSSL schema)
CREATE TABLE IF NOT EXISTS AccessLogs (
    LogID INT AUTO_INCREMENT PRIMARY KEY,
    UserID VARCHAR(50) NOT NULL,
    CardNo VARCHAR(50),
    AccessTime DATETIME NOT NULL,
    DoorID VARCHAR(50) NOT NULL,
    EventType VARCHAR(50) DEFAULT 'IN',
    DeviceID VARCHAR(50),
    VerifyMode VARCHAR(50) DEFAULT 'CARD',
    INDEX idx_user_id (UserID),
    INDEX idx_access_time (AccessTime),
    INDEX idx_door_id (DoorID),
    INDEX idx_card_no (CardNo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- User master table (optional - for reference)
CREATE TABLE IF NOT EXISTS Users (
    UserID VARCHAR(50) PRIMARY KEY,
    Name VARCHAR(100),
    CardNo VARCHAR(50) UNIQUE,
    Department VARCHAR(100),
    Role VARCHAR(50),
    Active BOOLEAN DEFAULT TRUE,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Doors/Entry Points master table
CREATE TABLE IF NOT EXISTS Doors (
    DoorID VARCHAR(50) PRIMARY KEY,
    DoorName VARCHAR(100),
    Location VARCHAR(100),
    BuildingName VARCHAR(100),
    Active BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert sample doors/entry points
INSERT INTO Doors (DoorID, DoorName, Location, BuildingName) VALUES
('MAIN_ENTRANCE', 'Main Entrance Gate', 'North Campus', 'Admin Block'),
('LIBRARY_ENTRY', 'Library Main Door', 'Central Campus', 'Library Building'),
('LAB_BLOCK_A', 'Lab Block A Entry', 'East Campus', 'Engineering Block A'),
('LAB_BLOCK_B', 'Lab Block B Entry', 'East Campus', 'Engineering Block B'),
('CAFETERIA_ENTRY', 'Cafeteria Entrance', 'Central Campus', 'Student Center'),
('HOSTEL_GATE_1', 'Hostel Gate 1', 'West Campus', 'Student Hostel'),
('HOSTEL_GATE_2', 'Hostel Gate 2', 'West Campus', 'Student Hostel'),
('ADMIN_OFFICE', 'Admin Office Entry', 'North Campus', 'Admin Block'),
('SPORTS_COMPLEX', 'Sports Complex Gate', 'South Campus', 'Sports Facility'),
('RESEARCH_LAB', 'Research Lab Entry', 'East Campus', 'Research Center');

-- Note: Users and AccessLogs will be populated by the data generator script
