-- List top 20 shows by popularity (basic select)
SELECT id, name, first_air_date, popularity
FROM shows
ORDER BY popularity DESC
LIMIT 20;