-- ============================================================================
-- AI-Based Smart Study Planner - Sample MySQL Seed Data
-- Demo Login: aarav.sharma@college.edu / StudySmart123!
-- ============================================================================

USE smart_study_planner;

INSERT INTO Students (
  full_name, email, password_hash, department, year_of_study,
  daily_study_goal_hours, preferred_study_time
) VALUES (
  'Aarav Sharma',
  'aarav.sharma@college.edu',
  'pbkdf2:sha256:1000000$wAe6FLZiddFtspvp$f11553ba2d9e4a396aee93f8d3a21659f924639be62a0d251b5e76cbdca798c9',
  'Computer Science & Engineering',
  '3rd Year',
  4.0,
  'evening'
);

SET @sid = LAST_INSERT_ID();

INSERT INTO Subjects (student_id, subject_name, subject_code, difficulty_level, priority, color_tag, target_hours_per_week) VALUES
(@sid, 'Data Structures & Algorithms', 'CS301', 5, 'High', '#6d28d9', 8.0),
(@sid, 'Database Management Systems', 'CS304', 3, 'High', '#06b6d4', 6.0),
(@sid, 'Operating Systems', 'CS302', 4, 'Medium', '#0b1437', 5.0),
(@sid, 'Linear Algebra', 'MA204', 4, 'Medium', '#059669', 5.0);

SET @sub_cs301 = (SELECT subject_id FROM Subjects WHERE student_id = @sid AND subject_code = 'CS301' LIMIT 1);
SET @sub_cs304 = (SELECT subject_id FROM Subjects WHERE student_id = @sid AND subject_code = 'CS304' LIMIT 1);
SET @sub_cs302 = (SELECT subject_id FROM Subjects WHERE student_id = @sid AND subject_code = 'CS302' LIMIT 1);
SET @sub_ma204 = (SELECT subject_id FROM Subjects WHERE student_id = @sid AND subject_code = 'MA204' LIMIT 1);

INSERT INTO Exams (student_id, subject_id, exam_title, exam_date, exam_time, syllabus_notes, preparedness_score) VALUES
(@sid, @sub_cs301, 'Midterm Exam', DATE_ADD(CURDATE(), INTERVAL 5 DAY), '09:00', 'Trees, Graphs, and Dynamic Programming', 45),
(@sid, @sub_ma204, 'Linear Algebra Midterm', DATE_ADD(CURDATE(), INTERVAL 9 DAY), '11:00', 'Vector Spaces & Eigenvalues', 60),
(@sid, @sub_cs304, 'DBMS Quiz & Lab Exam', DATE_ADD(CURDATE(), INTERVAL 11 DAY), '14:00', 'Normalization, SQL Joins, and B+ Trees', 72),
(@sid, @sub_cs302, 'OS Unit Test', DATE_ADD(CURDATE(), INTERVAL 16 DAY), '10:30', 'CPU Scheduling & Deadlocks', 65);

INSERT INTO Topics (subject_id, student_id, chapter_name, topic_name, estimated_hours, status, understanding_rating, weakness_level, last_studied_at, next_revision_date, revision_count) VALUES
(@sub_cs301, @sid, 'Chapter 1: Trees', 'Binary Search Trees & AVL Rotations', 2.0, 'completed', 5, 'strong', DATE_SUB(CURDATE(), INTERVAL 3 DAY), DATE_ADD(CURDATE(), INTERVAL 3 DAY), 1),
(@sub_cs301, @sid, 'Chapter 2: Graphs', 'Dijkstra & Shortest Paths', 2.5, 'in_progress', 2, 'weak', DATE_SUB(CURDATE(), INTERVAL 2 DAY), CURDATE(), 0),
(@sub_cs301, @sid, 'Chapter 3: Dynamic Programming', '0/1 Knapsack & Memoization', 3.0, 'pending', 1, 'weak', DATE_SUB(CURDATE(), INTERVAL 6 DAY), CURDATE(), 0),
(@sub_cs304, @sid, 'Chapter 1: Relational Design', 'ER Diagrams & Keys', 1.5, 'completed', 5, 'strong', DATE_SUB(CURDATE(), INTERVAL 4 DAY), DATE_ADD(CURDATE(), INTERVAL 5 DAY), 1),
(@sub_cs304, @sid, 'Chapter 2: Normalization', '1NF to BCNF Decomposition', 2.0, 'completed', 3, 'average', DATE_SUB(CURDATE(), INTERVAL 1 DAY), DATE_ADD(CURDATE(), INTERVAL 1 DAY), 0),
(@sub_cs302, @sid, 'Chapter 1: Processes', 'CPU Scheduling Algorithms', 2.0, 'completed', 4, 'strong', DATE_SUB(CURDATE(), INTERVAL 5 DAY), DATE_ADD(CURDATE(), INTERVAL 4 DAY), 1),
(@sub_cs302, @sid, 'Chapter 2: Synchronization', 'Deadlock Prevention & Bankers Algorithm', 2.5, 'in_progress', 2, 'weak', DATE_SUB(CURDATE(), INTERVAL 2 DAY), CURDATE(), 0),
(@sub_ma204, @sid, 'Chapter 2: Eigenvalues', 'Eigenvalues & Diagonalization', 2.5, 'pending', 2, 'weak', DATE_SUB(CURDATE(), INTERVAL 3 DAY), CURDATE(), 0);

SET @t_dp = (SELECT topic_id FROM Topics WHERE student_id = @sid AND topic_name = '0/1 Knapsack & Memoization' LIMIT 1);
SET @t_graph = (SELECT topic_id FROM Topics WHERE student_id = @sid AND topic_name = 'Dijkstra & Shortest Paths' LIMIT 1);
SET @t_trees = (SELECT topic_id FROM Topics WHERE student_id = @sid AND topic_name = 'Binary Search Trees & AVL Rotations' LIMIT 1);

INSERT INTO Quiz_Results (student_id, subject_id, topic_id, quiz_title, score, max_score, percentage, difficulty_feedback) VALUES
(@sid, @sub_cs301, @t_trees, 'Trees Practice Quiz', 9.0, 10.0, 90.0, 'Easy'),
(@sid, @sub_cs301, @t_graph, 'Graph Traversal Check', 4.5, 10.0, 45.0, 'Hard'),
(@sid, @sub_cs301, @t_dp, 'DP Diagnostic Quiz', 3.5, 10.0, 35.0, 'Hard');

INSERT INTO Study_Progress (student_id, subject_id, topic_id, study_date, hours_studied, topics_completed_count, focus_rating, notes) VALUES
(@sid, @sub_cs301, @t_trees, DATE_SUB(CURDATE(), INTERVAL 4 DAY), 2.0, 1, 5, 'Completed AVL rotations practice'),
(@sid, @sub_cs302, NULL, DATE_SUB(CURDATE(), INTERVAL 3 DAY), 2.5, 1, 4, 'Solved Round Robin Gantt charts'),
(@sid, @sub_cs304, NULL, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 2.0, 1, 5, 'Designed college schema diagrams'),
(@sid, @sub_cs301, @t_graph, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 2.5, 0, 3, 'Reviewed Dijkstra priority queue'),
(@sid, @sub_cs301, @t_dp, CURDATE(), 1.5, 0, 4, 'Started DP recurrence practice');

INSERT INTO Study_Schedules (student_id, subject_id, topic_id, study_date, start_time, end_time, duration_hours, session_type, priority_score, is_ai_generated, status, notes) VALUES
(@sid, @sub_cs301, @t_dp, CURDATE(), '18:00', '19:30', 1.5, 'exam_prep', 92.0, 1, 'scheduled', 'Exam in 5d · High priority · Weak topic'),
(@sid, @sub_cs301, @t_graph, DATE_ADD(CURDATE(), INTERVAL 1 DAY), '18:00', '19:30', 1.5, 'revision', 84.0, 1, 'scheduled', 'Exam in 5d · Weak topic boost');

INSERT INTO Reminders (student_id, subject_id, topic_id, reminder_type, title, message, due_date, priority, is_auto_generated) VALUES
(@sid, @sub_cs301, NULL, 'exam', 'Exam Alert: Data Structures & Algorithms (Midterm Exam)', 'Exam in 5 days. Focus on Trees, Graphs, and Dynamic Programming.', DATE_ADD(CURDATE(), INTERVAL 5 DAY), 'high', 1),
(@sid, @sub_cs301, @t_dp, 'revision', 'Revision Due: 0/1 Knapsack & Memoization', 'Weak topic flagged for immediate active-recall review.', CURDATE(), 'high', 1);

