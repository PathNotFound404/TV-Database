-- SQL script to create a normalized TV shows MySQL database
-- Database: tv_shows_db
-- Notes:
-- 1) This schema uses `shows` (main), `genres` and `show_genres` (many-to-many),
--    `countries` and `show_countries` (many-to-many because origin_country can have multiple codes),
--    and `popularity_history` to track popularity over time.
-- 2) We include a staging table `raw_shows` to import the CSV as-is (genre arrays and origin arrays
--    will remain as strings) and example transforms using JSON_TABLE (MySQL 8+). If your MySQL
--    version is older than 8.0, see the Python preprocessing example at the bottom.

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS `tv_shows_db` CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
USE `tv_shows_db`;

-- Main shows table (use TMDB id as the PK)
CREATE TABLE IF NOT EXISTS `shows` (
  `id` INT NOT NULL COMMENT 'TMDB id from CSV',
  `adult` TINYINT(1) DEFAULT 0,
  `backdrop_path` VARCHAR(255),
  `original_name` VARCHAR(255),
  `name` VARCHAR(255),
  `overview` TEXT,
  `original_language` VARCHAR(10),
  `poster_path` VARCHAR(255),
  `first_air_date` DATE,
  `vote_average` DECIMAL(5,3),
  `vote_count` INT,
  `popularity` DECIMAL(12,4),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Countries table (normalized)
CREATE TABLE IF NOT EXISTS `countries` (
  `country_code` VARCHAR(8) NOT NULL,
  `country_name` VARCHAR(255),
  PRIMARY KEY (`country_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Many-to-many: shows <-> countries
CREATE TABLE IF NOT EXISTS `show_countries` (
  `show_id` INT NOT NULL,
  `country_code` VARCHAR(8) NOT NULL,
  PRIMARY KEY (`show_id`,`country_code`),
  CONSTRAINT `fk_show_countries_show` FOREIGN KEY (`show_id`) REFERENCES `shows`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_show_countries_country` FOREIGN KEY (`country_code`) REFERENCES `countries`(`country_code`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Genres master table (genre ids from CSV are kept as-is). You can populate `name` if you have a mapping.
CREATE TABLE IF NOT EXISTS `genres` (
  `genre_id` INT NOT NULL,
  `name` VARCHAR(100),
  PRIMARY KEY (`genre_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Many-to-many: shows <-> genres
CREATE TABLE IF NOT EXISTS `show_genres` (
  `show_id` INT NOT NULL,
  `genre_id` INT NOT NULL,
  PRIMARY KEY (`show_id`,`genre_id`),
  CONSTRAINT `fk_show_genres_show` FOREIGN KEY (`show_id`) REFERENCES `shows`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_show_genres_genre` FOREIGN KEY (`genre_id`) REFERENCES `genres`(`genre_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Popularity history table (captures popularity metric over time)
CREATE TABLE IF NOT EXISTS `popularity_history` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `show_id` INT NOT NULL,
  `popularity` DECIMAL(12,4) NOT NULL,
  `vote_average` DECIMAL(6,3) DEFAULT NULL,
  `vote_count` INT DEFAULT NULL,
  `source` VARCHAR(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  INDEX (`show_id`),
  CONSTRAINT `fk_pop_history_show` FOREIGN KEY (`show_id`) REFERENCES `shows`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
