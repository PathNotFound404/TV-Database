-- Count number of shows per genre (genres without shows will show 0)
SELECT g.genre_id, g.name, COUNT(sg.show_id) AS show_count
FROM genres g
LEFT JOIN show_genres sg ON g.genre_id = sg.genre_id
GROUP BY g.genre_id, g.name
ORDER BY show_count DESC
