-- Search shows by (partial) name (case-insensitive)
SELECT id, name, overview, popularity
FROM shows
WHERE name LIKE CONCAT('%%', %s, '%%');