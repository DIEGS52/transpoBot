-- ============================================================
--  TranspoBot — Base de données MySQL
--  Projet GLSi L3 — ESP/UCAD
-- ============================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

CREATE DATABASE IF NOT EXISTS transpobot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE transpobot;

-- Véhicules
CREATE TABLE IF NOT EXISTS vehicules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    immatriculation VARCHAR(20) NOT NULL UNIQUE,
    type ENUM('bus','minibus','taxi') NOT NULL,
    capacite INT NOT NULL,
    statut ENUM('actif','maintenance','hors_service') DEFAULT 'actif',
    kilometrage INT DEFAULT 0,
    date_acquisition DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chauffeurs
CREATE TABLE IF NOT EXISTS chauffeurs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    telephone VARCHAR(20),
    numero_permis VARCHAR(30) UNIQUE NOT NULL,
    categorie_permis VARCHAR(5),
    disponibilite BOOLEAN DEFAULT TRUE,
    vehicule_id INT,
    date_embauche DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicule_id) REFERENCES vehicules(id)
);

-- Lignes
CREATE TABLE IF NOT EXISTS lignes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    nom VARCHAR(100),
    origine VARCHAR(100) NOT NULL,
    destination VARCHAR(100) NOT NULL,
    distance_km DECIMAL(6,2),
    duree_minutes INT
);

-- Tarifs
CREATE TABLE IF NOT EXISTS tarifs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ligne_id INT NOT NULL,
    type_client ENUM('normal','etudiant','senior') DEFAULT 'normal',
    prix DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (ligne_id) REFERENCES lignes(id)
);

-- Trajets
CREATE TABLE IF NOT EXISTS trajets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ligne_id INT NOT NULL,
    chauffeur_id INT NOT NULL,
    vehicule_id INT NOT NULL,
    date_heure_depart DATETIME NOT NULL,
    date_heure_arrivee DATETIME,
    statut ENUM('planifie','en_cours','termine','annule') DEFAULT 'planifie',
    nb_passagers INT DEFAULT 0,
    recette DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ligne_id) REFERENCES lignes(id),
    FOREIGN KEY (chauffeur_id) REFERENCES chauffeurs(id),
    FOREIGN KEY (vehicule_id) REFERENCES vehicules(id)
);

-- Incidents
CREATE TABLE IF NOT EXISTS incidents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trajet_id INT NOT NULL,
    type ENUM('panne','accident','retard','autre') NOT NULL,
    description TEXT,
    gravite ENUM('faible','moyen','grave') DEFAULT 'faible',
    date_incident DATETIME NOT NULL,
    resolu BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trajet_id) REFERENCES trajets(id)
);

-- ============================================================
--  Données enrichies — Contexte sénégalais
-- ============================================================

-- 8 véhicules
INSERT INTO vehicules (immatriculation, type, capacite, statut, kilometrage, date_acquisition) VALUES
('DK-1234-AB', 'bus',     60, 'actif',        45000,  '2021-03-15'),
('DK-5678-CD', 'minibus', 25, 'actif',        32000,  '2022-06-01'),
('DK-9012-EF', 'bus',     60, 'maintenance',  78000,  '2019-11-20'),
('DK-3456-GH', 'taxi',     5, 'actif',       120000,  '2020-01-10'),
('DK-7890-IJ', 'minibus', 25, 'actif',        15000,  '2023-09-05'),
('DK-2345-KL', 'bus',     60, 'actif',        55000,  '2021-07-22'),
('DK-6789-MN', 'minibus', 30, 'actif',        28000,  '2022-11-14'),
('DK-0123-OP', 'taxi',     4, 'hors_service', 150000, '2018-05-30');

-- 6 chauffeurs avec noms sénégalais
INSERT INTO chauffeurs (nom, prenom, telephone, numero_permis, categorie_permis, disponibilite, vehicule_id, date_embauche) VALUES
('DIOP',  'Mamadou', '+221771234567', 'P-2019-001', 'D', TRUE, 1, '2019-04-01'),
('FALL',  'Ibrahima','+221772345678', 'P-2020-002', 'D', TRUE, 2, '2020-07-15'),
('NDIAYE','Fatou',   '+221773456789', 'P-2021-003', 'B', TRUE, 4, '2021-02-01'),
('SECK',  'Ousmane', '+221774567890', 'P-2022-004', 'D', TRUE, 5, '2022-10-20'),
('BA',    'Aminata', '+221775678901', 'P-2023-005', 'D', TRUE, 6, '2023-01-10'),
('MBAYE', 'Cheikh',  '+221776789012', 'P-2023-006', 'D', TRUE, 7, '2023-03-15');

-- 5 lignes
INSERT INTO lignes (code, nom, origine, destination, distance_km, duree_minutes) VALUES
('L1', 'Dakar-Thiès',    'Dakar',        'Thiès',    70.5,  90),
('L2', 'Dakar-Mbour',    'Dakar',        'Mbour',    82.0, 120),
('L3', 'Plateau-Pikine', 'Plateau',      'Pikine',   15.0,  45),
('L4', 'Dakar-AIBD',    'Centre-ville', 'AIBD',     45.0,  60),
('L5', 'Dakar-Rufisque', 'Dakar',        'Rufisque', 25.0,  40);

-- Tarifs pour chaque ligne et type de client
INSERT INTO tarifs (ligne_id, type_client, prix) VALUES
(1,'normal',2500),(1,'etudiant',1500),(1,'senior',1800),
(2,'normal',3000),(2,'etudiant',1800),(2,'senior',2200),
(3,'normal',500), (3,'etudiant',300), (3,'senior',400),
(4,'normal',5000),(4,'etudiant',3000),(4,'senior',4000),
(5,'normal',1500),(5,'etudiant',900), (5,'senior',1200);

-- 40 trajets — janvier, février, mars 2026
-- Recettes : bus (50-60 pass × tarif ligne), minibus (20-25 pass), taxi (3-5 pass)
INSERT INTO trajets (ligne_id, chauffeur_id, vehicule_id, date_heure_depart, date_heure_arrivee, statut, nb_passagers, recette) VALUES
-- ---- Janvier 2026 (12 trajets) ----
(1,1,1,'2026-01-05 06:00:00','2026-01-05 07:30:00','termine',55,137500),
(2,2,2,'2026-01-06 07:00:00','2026-01-06 09:00:00','termine',22, 66000),
(3,4,5,'2026-01-07 07:30:00','2026-01-07 08:15:00','termine',24, 12000),
(4,3,4,'2026-01-08 08:00:00','2026-01-08 09:00:00','termine', 4, 20000),
(1,5,6,'2026-01-10 06:00:00','2026-01-10 07:30:00','termine',58,145000),
(5,6,7,'2026-01-12 06:30:00','2026-01-12 07:10:00','termine',20, 30000),
(2,1,1,'2026-01-13 07:00:00','2026-01-13 09:00:00','termine',52,156000),
(3,2,2,'2026-01-15 07:30:00','2026-01-15 08:15:00','termine',23, 11500),
(4,6,7,'2026-01-17 08:00:00','2026-01-17 09:00:00','termine',21,105000),
(1,4,5,'2026-01-20 06:00:00','2026-01-20 07:30:00','termine',20, 50000),
(5,3,4,'2026-01-22 06:30:00','2026-01-22 07:10:00','termine', 4,  6000),
(2,5,6,'2026-01-25 07:00:00','2026-01-25 09:00:00','termine',55,165000),
-- ---- Février 2026 (14 trajets) ----
(1,1,1,'2026-02-02 06:00:00','2026-02-02 07:30:00','termine',56,140000),
(3,4,5,'2026-02-04 07:30:00','2026-02-04 08:15:00','termine',25, 12500),
(4,2,2,'2026-02-05 08:00:00','2026-02-05 09:00:00','termine',22,110000),
(2,6,7,'2026-02-06 07:00:00','2026-02-06 09:00:00','termine',22, 66000),
(5,5,6,'2026-02-08 06:30:00','2026-02-08 07:10:00','termine',50, 75000),
(1,3,4,'2026-02-10 06:00:00','2026-02-10 07:30:00','termine', 4, 10000),
(2,1,1,'2026-02-12 07:00:00','2026-02-12 09:00:00','termine',57,171000),
(3,6,7,'2026-02-14 07:30:00','2026-02-14 08:15:00','termine',24, 12000),
(4,4,5,'2026-02-15 08:00:00',NULL,'annule',0,0),
(5,2,2,'2026-02-17 06:30:00','2026-02-17 07:10:00','termine',20, 30000),
(1,5,6,'2026-02-19 06:00:00','2026-02-19 07:30:00','termine',54,135000),
(2,3,4,'2026-02-20 07:00:00','2026-02-20 09:00:00','termine', 5, 15000),
(3,1,1,'2026-02-22 07:30:00','2026-02-22 08:15:00','termine',55, 27500),
(4,6,7,'2026-02-24 08:00:00','2026-02-24 09:00:00','termine',22,110000),
-- ---- Mars 2026 (14 trajets) ----
(1,1,1,'2026-03-01 06:00:00','2026-03-01 07:30:00','termine',55,137500),
(2,2,2,'2026-03-01 07:00:00','2026-03-01 09:00:00','termine',22, 66000),
(3,4,5,'2026-03-03 07:30:00','2026-03-03 08:15:00','termine',24, 12000),
(4,3,4,'2026-03-05 08:00:00','2026-03-05 09:00:00','termine', 4, 20000),
(5,5,6,'2026-03-07 06:30:00','2026-03-07 07:10:00','termine',50, 75000),
(1,6,7,'2026-03-08 06:00:00','2026-03-08 07:30:00','termine',22, 55000),
(2,1,1,'2026-03-10 07:00:00','2026-03-10 09:00:00','termine',58,174000),
(3,2,2,'2026-03-12 07:30:00','2026-03-12 08:15:00','termine',23, 11500),
(4,6,7,'2026-03-14 08:00:00','2026-03-14 09:00:00','termine',21,105000),
(5,4,5,'2026-03-16 06:30:00',NULL,'annule',0,0),
(1,5,6,'2026-03-18 06:00:00','2026-03-18 07:30:00','termine',56,140000),
(2,3,4,'2026-03-20 07:00:00','2026-03-20 09:00:00','termine', 5, 15000),
(3,1,1,'2026-03-22 07:30:00',NULL,'en_cours',45,0),
(4,2,2,'2026-03-25 08:00:00',NULL,'planifie',0,0);

-- 10 incidents variés avec gravités différentes
INSERT INTO incidents (trajet_id, type, description, gravite, date_incident, resolu) VALUES
(2, 'retard',   'Embouteillage sur la route de Mbour',           'faible', '2026-01-06 07:45:00', TRUE),
(5, 'panne',    'Panne moteur — arrêt 1h pour réparation',       'moyen',  '2026-01-10 06:35:00', TRUE),
(9, 'retard',   'Trafic dense à Hann — retard 30 min',           'faible', '2026-01-17 08:25:00', TRUE),
(12,'accident', 'Accrochage léger sur l\'autoroute à péage',     'faible', '2026-01-25 07:30:00', TRUE),
(17,'panne',    'Crevaison pneu arrière gauche',                 'grave',  '2026-02-08 06:45:00', TRUE),
(20,'retard',   'Manifestation bloquant la route de Pikine',     'faible', '2026-02-14 07:50:00', TRUE),
(21,'panne',    'Panne électrique — trajet annulé',              'grave',  '2026-02-15 08:05:00', FALSE),
(27,'retard',   'Embouteillage au rond-point de Thiès',          'faible', '2026-03-01 06:40:00', FALSE),
(33,'accident', 'Collision avec moto-taxi à Mbour',              'grave',  '2026-03-10 07:25:00', FALSE),
(37,'autre',    'Passager malade — arrêt d\'urgence requis',     'moyen',  '2026-03-18 06:50:00', FALSE);
