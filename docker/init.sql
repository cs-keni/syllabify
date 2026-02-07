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

CREATE TABLE IF NOT EXISTS Schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sched_name VARCHAR(255) NOT NULL,
    owner_id INT NOT NULL,
    CONSTRAINT fk_schedules_user
        FOREIGN KEY (owner_id)
        REFERENCES Users(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_name VARCHAR(255) NOT NULL,
    work_load INT NOT NULL,
    notes VARCHAR(2048),
    start_date DATETIME NOT NULL,
    due_date DATETIME NOT NULL,
    schedule_id INT NOT NULL,
    CONSTRAINT fk_assignments_schedule
        FOREIGN KEY (schedule_id)
        REFERENCES Schedules(id)
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
