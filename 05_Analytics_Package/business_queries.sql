
-- Q1: Monthly Trends
SELECT d.year, d.month, SUM(f.loan_days), SUM(f.download_count), SUM(f.duration_hours)
FROM library_usage_fact f JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month ORDER BY d.year, d.month;

-- Q2: Department Ranking
SELECT s.department, COUNT(*), SUM(f.download_count), SUM(f.loan_days)
FROM library_usage_fact f JOIN dim_student s ON f.student_key = s.student_key
WHERE s.department IS NOT NULL GROUP BY s.department ORDER BY COUNT(*) DESC;

-- (add Q3-Q10 similarly — or copy from cells above)
