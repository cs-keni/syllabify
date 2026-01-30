CREATE TABLE IF NOT EXISTS Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sched_name VARCHAR(255) NOT NULL,
    owner_id INT NOT NULL,
    FOREIGN KEY(owner_id) REFERENCES Users(id)
);

CREATE TABLE IF NOT EXISTS Assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_name VARCHAR(255) NOT NULL,
    work_load INT NOT NULL,
    notes VARCHAR(2048),
    schedule_id INT NOT NULL,
    FOREIGN KEY(schedule_id) REFERENCES Schedules(id)
);
