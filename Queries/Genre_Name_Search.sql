-- Search shows by genre name
SELECT s.id, s.name, s.first_air_date, s.popularity, s.vote_average, s.vote_count
FROM shows s
JOIN show_genres sg ON s.id = sg.show_id
JOIN genres g ON sg.genre_id = g.genre_id
WHERE g.name = %s
ORDER BY s.popularity DESC