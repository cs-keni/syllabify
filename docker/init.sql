CREATE TABLE IF NOT EXISTS Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    security_setup_done BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS UserSecurityAnswers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    question_text VARCHAR(500) NOT NULL,
    answer_hash VARCHAR(255) NOT NULL,
    FOREIGN KEY(user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- Terms table for semester/quarter management
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

-- Courses belong to a Term
CREATE TABLE IF NOT EXISTS Courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_name VARCHAR(255) NOT NULL,
    term_id INT NOT NULL,
    CONSTRAINT fk_courses_term
        FOREIGN KEY (term_id)
        REFERENCES Terms(id)
        ON DELETE CASCADE
);

-- Assignments belong to a Course
CREATE TABLE IF NOT EXISTS Assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_name VARCHAR(255) NOT NULL,
    work_load INT NOT NULL,
    notes VARCHAR(2048),
    start_date DATETIME NOT NULL,
    due_date DATETIME NOT NULL,
--    schedule_id INT NOT NULL,
    course_id INT NOT NULL,
--    CONSTRAINT fk_assignments_schedule
--        FOREIGN KEY (schedule_id)
--        REFERENCES Schedules(id)
--        ON DELETE CASCADE,
    CONSTRAINT fk_assignments_course
        FOREIGN KEY (course_id)
        REFERENCES Courses(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS StudyTimes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    notes VARCHAR(2048),
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    schedule_id INT NOT NULL,
    CONSTRAINT fk_study_times_schedule
        FOREIGN KEY (schedule_id)
        REFERENCES Schedules(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_name VARCHAR(255) NOT NULL,
    schedule_id INT NOT NULL,
    CONSTRAINT fk_courses_schedule
        FOREIGN KEY (schedule_id)
        REFERENCES Schedules(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Meetings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    CONSTRAINT fk_meetings_course
        FOREIGN KEY (course_id)
        REFERENCES Courses(id)
        ON DELETE CASCADE
);
