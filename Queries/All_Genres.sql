-- Get genres for a single show (join through show_genres -> genres)
SELECT s.id AS show_id, s.name AS show_name, g.genre_id, g.name AS genre_name
FROM shows s
JOIN show_genres sg ON s.id = sg.show_id
JOIN genres g ON sg.genre_id = g.genre_id
WHERE s.id = %s;