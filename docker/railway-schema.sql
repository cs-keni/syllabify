-- Syllabify schema for Railway MySQL (fresh database setup)
-- Run this once against your Railway MySQL database.
-- Get connection details from Railway dashboard → your MySQL service → Connect.

-- 1. Users (auth)
CREATE TABLE IF NOT EXISTS Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    security_setup_done BOOLEAN DEFAULT FALSE
);

-- 2. Security answers (password recovery)
CREATE TABLE IF NOT EXISTS UserSecurityAnswers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    question_text VARCHAR(500) NOT NULL,
    answer_hash VARCHAR(255) NOT NULL,
    FOREIGN KEY(user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- 3. Terms (semesters/quarters)
CREATE TABLE IF NOT EXISTS Terms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    term_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES Users(id) ON DELETE CASCADE,
    INDEX idx_user_active (user_id, is_active),
    INDEX idx_user_dates (user_id, start_date, end_date)
);

-- 4. Courses (belong to a Term)
CREATE TABLE IF NOT EXISTS Courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_name VARCHAR(255) NOT NULL,
    term_id INT NOT NULL,
    study_hours_per_week INT NULL,
    FOREIGN KEY (term_id) REFERENCES Terms(id) ON DELETE CASCADE
);

-- 5. Assignments (belong to a Course)
CREATE TABLE IF NOT EXISTS Assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_name VARCHAR(255) NOT NULL,
    work_load INT NOT NULL,
    notes VARCHAR(2048),
    start_date DATETIME NOT NULL,
    due_date DATETIME NOT NULL,
    assignment_type VARCHAR(50) NULL,
    course_id INT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES Courses(id) ON DELETE CASCADE
);

-- 6. Meetings (class times, belong to a Course)
CREATE TABLE IF NOT EXISTS Meetings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    day_of_week VARCHAR(2) NULL,
    start_time_str VARCHAR(5) NULL,
    end_time_str VARCHAR(5) NULL,
    location VARCHAR(255) NULL,
    meeting_type VARCHAR(50) NULL,
    start_time DATETIME NULL,
    end_time DATETIME NULL,
    FOREIGN KEY (course_id) REFERENCES Courses(id) ON DELETE CASCADE
);
