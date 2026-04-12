# TranspoBot — Projet GLSi L3 ESP/UCAD

Assistant intelligent de gestion de transport urbain au Sénégal.

## Démarrage rapide

### 1. Base de données
```bash
mysql -u root -p < schema.sql
```

### 2. Configuration
```bash
cp .env.example .env
# Éditez .env et renseignez :
#   ANTHROPIC_API_KEY=sk-ant-...
#   DB_PASSWORD=votre_mot_de_passe  (si nécessaire)
```

### 3. Installation et lancement
```bash
pip install -r requirements.txt
python app.py
```

### 4. Ouvrir l'interface
```
http://localhost:8000
```

---

## Déploiement Railway

1. Créer un projet sur [railway.app](https://railway.app)
2. Ajouter un service **MySQL** et noter les variables de connexion
3. Déployer le repo Git (branch `master`)
4. Dans les variables d'environnement Railway, ajouter :
   - `ANTHROPIC_API_KEY`
   - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
5. Dans le terminal Railway, exécuter : `mysql < schema.sql`
6. L'URL publique est disponible dans l'onglet **Settings → Domains**

---

## Technologies

- **Backend** : FastAPI (Python 3.10+)
- **Base de données** : MySQL 8
- **LLM** : Anthropic Claude (`claude-sonnet-4-5`)
- **Frontend** : HTML/CSS/JS vanilla — interface single-page

## Structure

```
transpobot/
├── app.py           # API FastAPI + intégration Claude
├── schema.sql       # Schéma + données enrichies (contexte sénégalais)
├── requirements.txt
├── .env.example
├── README.md
└── static/
    └── index.html   # Interface web complète
```

## Livrables

- Lien plateforme déployée (Railway/Render)
- Lien interface de chat
- Rapport PDF (MCD, MLD, architecture, tests)
- Présentation PowerPoint (démo)
