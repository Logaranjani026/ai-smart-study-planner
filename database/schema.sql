-- ============================================================================
-- AI-Based Smart Study Planner - MySQL 8.0 Database Schema
-- 8 Core Tables:
--   1. Students
--   2. Subjects
--   3. Topics
--   4. Study_Schedules
--   5. Study_Progress
--   6. Exams
--   7. Reminders
--   8. Quiz_Results
-- ============================================================================

CREATE DATABASE IF NOT EXISTS smart_study_planner
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE smart_study_planner;

-- 1. Students Table
CREATE TABLE IF NOT EXISTS Students (
  student_id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(160) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  department VARCHAR(120) NOT NULL,
  year_of_study VARCHAR(40) NOT NULL,
  daily_study_goal_hours DOUBLE NOT NULL DEFAULT 4.0,
  preferred_study_time ENUM('morning', 'afternoon', 'evening') NOT NULL DEFAULT 'evening',
  reset_token VARCHAR(120) NULL,
  reset_token_expiry DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_students_email (email)
) ENGINE=InnoDB;

-- 2. Subjects Table
CREATE TABLE IF NOT EXISTS Subjects (
  subject_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  subject_name VARCHAR(140) NOT NULL,
  subject_code VARCHAR(30) NULL,
  difficulty_level INT NOT NULL DEFAULT 3,
  priority ENUM('High', 'Medium', 'Low') NOT NULL DEFAULT 'Medium',
  color_tag VARCHAR(20) NOT NULL DEFAULT '#6d28d9',
  target_hours_per_week DOUBLE NOT NULL DEFAULT 6.0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_subjects_student FOREIGN KEY (student_id)
    REFERENCES Students(student_id) ON DELETE CASCADE,
  INDEX idx_subjects_student (student_id)
) ENGINE=InnoDB;

-- 3. Topics Table
CREATE TABLE IF NOT EXISTS Topics (
  topic_id INT AUTO_INCREMENT PRIMARY KEY,
  subject_id INT NOT NULL,
  student_id INT NOT NULL,
  chapter_name VARCHAR(140) NOT NULL,
  topic_name VARCHAR(180) NOT NULL,
  estimated_hours DOUBLE NOT NULL DEFAULT 2.0,
  status ENUM('pending', 'in_progress', 'completed') NOT NULL DEFAULT 'pending',
  understanding_rating INT NOT NULL DEFAULT 3,
  weakness_level ENUM('weak', 'average', 'strong') NOT NULL DEFAULT 'average',
  last_studied_at DATE NULL,
  next_revision_date DATE NULL,
  revision_count INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_topics_subject FOREIGN KEY (subject_id)
    REFERENCES Subjects(subject_id) ON DELETE CASCADE,
  CONSTRAINT fk_topics_student FOREIGN KEY (student_id)
    REFERENCES Students(student_id) ON DELETE CASCADE,
  INDEX idx_topics_subject (subject_id),
  INDEX idx_topics_student (student_id)
) ENGINE=InnoDB;

-- 4. Exams Table
CREATE TABLE IF NOT EXISTS Exams (
  exam_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  subject_id INT NOT NULL,
  exam_title VARCHAR(140) NOT NULL,
  exam_date DATE NOT NULL,
  exam_time VARCHAR(15) NULL DEFAULT '09:00',
  syllabus_notes VARCHAR(255) NULL,
  preparedness_score INT NOT NULL DEFAULT 50,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_exams_student FOREIGN KEY (student_id)
    REFERENCES Students(student_id) ON DELETE CASCADE,
  CONSTRAINT fk_exams_subject FOREIGN KEY (subject_id)
    REFERENCES Subjects(subject_id) ON DELETE CASCADE,
  INDEX idx_exams_student_date (student_id, exam_date)
) ENGINE=InnoDB;

-- 5. Study_Schedules Table
CREATE TABLE IF NOT EXISTS Study_Schedules (
  schedule_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  subject_id INT NOT NULL,
  topic_id INT NULL,
  study_date DATE NOT NULL,
  start_time VARCHAR(10) NOT NULL,
  end_time VARCHAR(10) NOT NULL,
  duration_hours DOUBLE NOT NULL DEFAULT 1.0,
  session_type ENUM('learning', 'revision', 'practice', 'exam_prep') NOT NULL DEFAULT 'learning',
  priority_score DOUBLE NOT NULL DEFAULT 50.0,
  is_ai_generated TINYINT(1) NOT NULL DEFAULT 1,
  status ENUM('scheduled', 'completed', 'missed', 'rescheduled') NOT NULL DEFAULT 'scheduled',
  notes VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_schedules_student FOREIGN KEY (student_id)
    REFERENCES Students(student_id) ON DELETE CASCADE,
  CONSTRAINT fk_schedules_subject FOREIGN KEY (subject_id)
    REFERENCES Subjects(subject_id) ON DELETE CASCADE,
  CONSTRAINT fk_schedules_topic FOREIGN KEY (topic_id)
    REFERENCES Topics(topic_id) ON DELETE SET NULL,
  INDEX idx_schedules_student_date (student_id, study_date)
) ENGINE=InnoDB;

-- 6. Study_Progress Table
CREATE TABLE IF NOT EXISTS Study_Progress (
  progress_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  subject_id INT NOT NULL,
  topic_id INT NULL,
  study_date DATE NOT NULL,
  hours_studied DOUBLE NOT NULL DEFAULT 1.0,
  topics_completed_count INT NOT NULL DEFAULT 0,
  focus_rating INT NOT NULL DEFAULT 4,
  notes VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_progress_student FOREIGN KEY (student_id)
    REFERENCES Students(student_id) ON DELETE CASCADE,
  CONSTRAINT fk_progress_subject FOREIGN KEY (subject_id)
    REFERENCES Subjects(subject_id) ON DELETE CASCADE,
  CONSTRAINT fk_progress_topic FOREIGN KEY (topic_id)
    REFERENCES Topics(topic_id) ON DELETE SET NULL,
  INDEX idx_progress_student_date (student_id, study_date)
) ENGINE=InnoDB;

-- 7. Reminders Table
CREATE TABLE IF NOT EXISTS Reminders (
  reminder_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  subject_id INT NULL,
  topic_id INT NULL,
  exam_id INT NULL,
  reminder_type ENUM('exam', 'daily_study', 'pending_topic', 'revision', 'custom') NOT NULL DEFAULT 'custom',
  title VARCHAR(180) NOT NULL,
  message VARCHAR(350) NOT NULL,
  due_date DATE NOT NULL,
  priority ENUM('high', 'medium', 'low') NOT NULL DEFAULT 'medium',
  is_read TINYINT(1) NOT NULL DEFAULT 0,
  is_completed TINYINT(1) NOT NULL DEFAULT 0,
  is_auto_generated TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_reminders_student FOREIGN KEY (student_id)
    REFERENCES Students(student_id) ON DELETE CASCADE,
  CONSTRAINT fk_reminders_subject FOREIGN KEY (subject_id)
    REFERENCES Subjects(subject_id) ON DELETE SET NULL,
  CONSTRAINT fk_reminders_topic FOREIGN KEY (topic_id)
    REFERENCES Topics(topic_id) ON DELETE SET NULL,
  CONSTRAINT fk_reminders_exam FOREIGN KEY (exam_id)
    REFERENCES Exams(exam_id) ON DELETE SET NULL,
  INDEX idx_reminders_student_due (student_id, due_date)
) ENGINE=InnoDB;

-- 8. Quiz_Results Table
CREATE TABLE IF NOT EXISTS Quiz_Results (
  quiz_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  subject_id INT NOT NULL,
  topic_id INT NOT NULL,
  quiz_title VARCHAR(160) NOT NULL,
  score DOUBLE NOT NULL,
  max_score DOUBLE NOT NULL DEFAULT 10.0,
  percentage DOUBLE NOT NULL,
  difficulty_feedback VARCHAR(40) NULL DEFAULT 'Medium',
  taken_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_quiz_student FOREIGN KEY (student_id)
    REFERENCES Students(student_id) ON DELETE CASCADE,
  CONSTRAINT fk_quiz_subject FOREIGN KEY (subject_id)
    REFERENCES Subjects(subject_id) ON DELETE CASCADE,
  CONSTRAINT fk_quiz_topic FOREIGN KEY (topic_id)
    REFERENCES Topics(topic_id) ON DELETE CASCADE,
  INDEX idx_quiz_student_topic (student_id, topic_id)
) ENGINE=InnoDB;

