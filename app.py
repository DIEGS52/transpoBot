"""
TranspoBot — Backend FastAPI
Projet GLSi L3 — ESP/UCAD
"""

import os
import re
import json
import urllib.parse
from openai import OpenAI
from decimal import Decimal
from datetime import date, datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# ── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="TranspoBot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# ── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es TranspoBot, assistant intelligent de gestion de transport urbain au Sénégal.
Tu réponds aux questions en français de façon naturelle et concise, puis tu fournis la requête SQL correspondante.

Tables disponibles :
- vehicules(id, immatriculation, type[bus/minibus/taxi], capacite, statut[actif/maintenance/hors_service], kilometrage, date_acquisition)
- chauffeurs(id, nom, prenom, telephone, numero_permis, categorie_permis, disponibilite, vehicule_id, date_embauche)
- lignes(id, code, nom, origine, destination, distance_km, duree_minutes)
- tarifs(id, ligne_id, type_client[normal/etudiant/senior], prix)
- trajets(id, ligne_id, chauffeur_id, vehicule_id, date_heure_depart, date_heure_arrivee, statut[planifie/en_cours/termine/annule], nb_passagers, recette)
- incidents(id, trajet_id, type[panne/accident/retard/autre], description, gravite[faible/moyen/grave], date_incident, resolu)

RÈGLES STRICTES :
1. Génère UNIQUEMENT des requêtes SELECT (jamais INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE)
2. Réponds TOUJOURS en JSON avec ce format exact : {"sql":"SELECT ...","explication":"..."}
3. Le champ "explication" doit être une phrase courte et naturelle qui répond directement à la question (ex: "Il y a 1 véhicule en maintenance : le bus DK-9012-EF."). Pas de description technique de la requête.
4. Si la question ne peut pas être répondue avec SQL : {"sql":null,"explication":"..."}
5. Limite toujours les résultats avec LIMIT 50 maximum
6. Les montants sont en FCFA (Francs CFA)"""


# ── DB helpers ───────────────────────────────────────────────────────────────
def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        p = urllib.parse.urlparse(database_url)
        return mysql.connector.connect(
            host=p.hostname,
            port=p.port or 3306,
            user=p.username,
            password=p.password,
            database=p.path.lstrip("/"),
            charset="utf8mb4",
            use_pure=True,
        )
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "transpobot"),
        charset="utf8mb4",
        use_pure=True,
    )


def execute_query(sql: str, params=None):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def execute_write(sql: str, params=None) -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


def serialize(data):
    result = []
    for row in data:
        new_row = {}
        for k, v in row.items():
            if isinstance(v, Decimal):
                new_row[k] = float(v)
            elif isinstance(v, (date, datetime)):
                new_row[k] = v.isoformat()
            elif isinstance(v, timedelta):
                new_row[k] = str(v)
            elif isinstance(v, bytes):
                new_row[k] = v.decode("utf-8", errors="replace")
            else:
                new_row[k] = v
        result.append(new_row)
    return result


def is_safe_sql(sql: str) -> bool:
    if not sql:
        return False
    forbidden = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
        "CREATE", "TRUNCATE", "--", ";--", "EXEC", "EXECUTE",
        "GRANT", "REVOKE",
    ]
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith("SELECT"):
        return False
    for word in forbidden:
        if word in sql_upper:
            return False
    return True


def ask_claude(question: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=600,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": question},
        ],
    )
    text = response.choices[0].message.content
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {"sql": None, "explication": text}


# ── Pydantic models ──────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str


class VehiculeCreate(BaseModel):
    immatriculation: str
    type: str
    capacite: int
    statut: Optional[str] = "actif"
    kilometrage: Optional[int] = 0
    date_acquisition: Optional[str] = None


class VehiculeUpdate(BaseModel):
    immatriculation: Optional[str] = None
    type: Optional[str] = None
    capacite: Optional[int] = None
    statut: Optional[str] = None
    kilometrage: Optional[int] = None
    date_acquisition: Optional[str] = None


class ChauffeurCreate(BaseModel):
    nom: str
    prenom: str
    telephone: Optional[str] = None
    numero_permis: str
    categorie_permis: Optional[str] = None
    disponibilite: Optional[bool] = True
    vehicule_id: Optional[int] = None
    date_embauche: Optional[str] = None


class ChauffeurUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    telephone: Optional[str] = None
    categorie_permis: Optional[str] = None
    disponibilite: Optional[bool] = None
    vehicule_id: Optional[int] = None
    date_embauche: Optional[str] = None


class TrajetCreate(BaseModel):
    ligne_id: int
    chauffeur_id: int
    vehicule_id: int
    date_heure_depart: str
    statut: Optional[str] = "planifie"
    nb_passagers: Optional[int] = 0
    recette: Optional[float] = 0


class IncidentCreate(BaseModel):
    trajet_id: int
    type: str
    description: Optional[str] = None
    gravite: Optional[str] = "faible"
    date_incident: str


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    try:
        conn = get_connection()
        conn.close()
        return {"status": "ok", "database": "connected", "app": "TranspoBot", "version": "1.0.0"}
    except Exception as e:
        return {"status": "error", "database": str(e)}


@app.get("/api/stats")
def get_stats():
    try:
        revenus_mois = serialize(execute_query("""
            SELECT
                DATE_FORMAT(date_heure_depart, '%Y-%m')  AS mois,
                DATE_FORMAT(date_heure_depart, '%b %Y')  AS mois_label,
                COALESCE(SUM(recette), 0)                AS total,
                COUNT(*)                                 AS nb_trajets
            FROM trajets
            WHERE statut = 'termine'
              AND date_heure_depart >= DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 3 MONTH), '%Y-%m-01')
            GROUP BY DATE_FORMAT(date_heure_depart, '%Y-%m'), DATE_FORMAT(date_heure_depart, '%b %Y')
            ORDER BY mois ASC
        """))

        statuts = serialize(execute_query(
            "SELECT statut, COUNT(*) AS n FROM trajets GROUP BY statut"
        ))

        kpi_total_vehicules      = execute_query("SELECT COUNT(*) AS n FROM vehicules")[0]["n"]
        kpi_total_chauffeurs     = execute_query("SELECT COUNT(*) AS n FROM chauffeurs")[0]["n"]
        kpi_total_trajets        = execute_query("SELECT COUNT(*) AS n FROM trajets")[0]["n"]
        kpi_recette              = execute_query(
            "SELECT COALESCE(SUM(recette), 0) AS total FROM trajets WHERE statut='termine'"
        )[0]["total"]
        kpi_incidents_non_resolus = execute_query(
            "SELECT COUNT(*) AS n FROM incidents WHERE resolu = FALSE"
        )[0]["n"]

        top_chauffeurs = serialize(execute_query("""
            SELECT c.nom, c.prenom,
                   COALESCE(SUM(t.recette), 0) AS total_recette,
                   COUNT(t.id) AS nb_trajets
            FROM chauffeurs c
            LEFT JOIN trajets t ON c.id = t.chauffeur_id AND t.statut = 'termine'
            GROUP BY c.id, c.nom, c.prenom
            ORDER BY total_recette DESC
            LIMIT 3
        """))

        recette_mois_courant = execute_query("""
            SELECT COALESCE(SUM(recette), 0) AS total
            FROM trajets
            WHERE statut = 'termine'
              AND DATE_FORMAT(date_heure_depart, '%Y-%m') = DATE_FORMAT(NOW(), '%Y-%m')
        """)[0]["total"]

        recette_mois_precedent = execute_query("""
            SELECT COALESCE(SUM(recette), 0) AS total
            FROM trajets
            WHERE statut = 'termine'
              AND DATE_FORMAT(date_heure_depart, '%Y-%m') = DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%Y-%m')
        """)[0]["total"]

        return {
            "revenus_mois": revenus_mois,
            "statuts": statuts,
            "top_chauffeurs": top_chauffeurs,
            "kpi": {
                "total_vehicules":        kpi_total_vehicules,
                "total_chauffeurs":       kpi_total_chauffeurs,
                "total_trajets":          kpi_total_trajets,
                "recette_totale":         float(kpi_recette) if kpi_recette else 0,
                "incidents_non_resolus":  kpi_incidents_non_resolus,
                "recette_mois_courant":   float(recette_mois_courant) if recette_mois_courant else 0,
                "recette_mois_precedent": float(recette_mois_precedent) if recette_mois_precedent else 0,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Véhicules ────────────────────────────────────────────────────────────────

@app.get("/api/vehicules")
def list_vehicules():
    try:
        return serialize(execute_query("SELECT * FROM vehicules ORDER BY id"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vehicules", status_code=201)
def create_vehicule(v: VehiculeCreate):
    try:
        lid = execute_write(
            """INSERT INTO vehicules (immatriculation, type, capacite, statut, kilometrage, date_acquisition)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (v.immatriculation, v.type, v.capacite, v.statut, v.kilometrage, v.date_acquisition),
        )
        return serialize(execute_query("SELECT * FROM vehicules WHERE id = %s", (lid,)))[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/vehicules/{vid}")
def update_vehicule(vid: int, v: VehiculeUpdate):
    try:
        fields = {k: val for k, val in v.model_dump().items() if val is not None}
        if not fields:
            raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        execute_write(f"UPDATE vehicules SET {set_clause} WHERE id = %s", [*fields.values(), vid])
        rows = execute_query("SELECT * FROM vehicules WHERE id = %s", (vid,))
        if not rows:
            raise HTTPException(status_code=404, detail="Véhicule non trouvé")
        return serialize(rows)[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/vehicules/{vid}")
def delete_vehicule(vid: int):
    try:
        if not execute_query("SELECT id FROM vehicules WHERE id = %s", (vid,)):
            raise HTTPException(status_code=404, detail="Véhicule non trouvé")
        execute_write("DELETE FROM vehicules WHERE id = %s", (vid,))
        return {"message": "Véhicule supprimé"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Chauffeurs ───────────────────────────────────────────────────────────────

@app.get("/api/chauffeurs")
def list_chauffeurs():
    try:
        return serialize(execute_query("""
            SELECT c.*, v.immatriculation AS vehicule_immat
            FROM chauffeurs c
            LEFT JOIN vehicules v ON c.vehicule_id = v.id
            ORDER BY c.id
        """))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chauffeurs", status_code=201)
def create_chauffeur(c: ChauffeurCreate):
    try:
        lid = execute_write(
            """INSERT INTO chauffeurs (nom, prenom, telephone, numero_permis, categorie_permis,
                                       disponibilite, vehicule_id, date_embauche)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (c.nom, c.prenom, c.telephone, c.numero_permis, c.categorie_permis,
             c.disponibilite, c.vehicule_id, c.date_embauche),
        )
        return serialize(execute_query("SELECT * FROM chauffeurs WHERE id = %s", (lid,)))[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/chauffeurs/{cid}")
def update_chauffeur(cid: int, c: ChauffeurUpdate):
    try:
        fields = {k: val for k, val in c.model_dump().items() if val is not None}
        if not fields:
            raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        execute_write(f"UPDATE chauffeurs SET {set_clause} WHERE id = %s", [*fields.values(), cid])
        rows = execute_query("SELECT * FROM chauffeurs WHERE id = %s", (cid,))
        if not rows:
            raise HTTPException(status_code=404, detail="Chauffeur non trouvé")
        return serialize(rows)[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/chauffeurs/{cid}")
def delete_chauffeur(cid: int):
    try:
        if not execute_query("SELECT id FROM chauffeurs WHERE id = %s", (cid,)):
            raise HTTPException(status_code=404, detail="Chauffeur non trouvé")
        execute_write("DELETE FROM chauffeurs WHERE id = %s", (cid,))
        return {"message": "Chauffeur supprimé"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Lignes ───────────────────────────────────────────────────────────────────

@app.get("/api/lignes")
def list_lignes():
    try:
        return serialize(execute_query("SELECT * FROM lignes ORDER BY code"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Trajets ──────────────────────────────────────────────────────────────────

@app.get("/api/trajets/recent")
def recent_trajets():
    try:
        return serialize(execute_query("""
            SELECT t.*,
                   l.code AS ligne_code, l.nom AS ligne_nom,
                   c.nom AS chauffeur_nom, c.prenom AS chauffeur_prenom,
                   v.immatriculation
            FROM trajets t
            JOIN lignes     l ON t.ligne_id     = l.id
            JOIN chauffeurs c ON t.chauffeur_id = c.id
            JOIN vehicules  v ON t.vehicule_id  = v.id
            ORDER BY t.date_heure_depart DESC
            LIMIT 10
        """))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trajets", status_code=201)
def create_trajet(t: TrajetCreate):
    try:
        lid = execute_write(
            """INSERT INTO trajets (ligne_id, chauffeur_id, vehicule_id, date_heure_depart,
                                    statut, nb_passagers, recette)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (t.ligne_id, t.chauffeur_id, t.vehicule_id, t.date_heure_depart,
             t.statut, t.nb_passagers, t.recette),
        )
        return serialize(execute_query("SELECT * FROM trajets WHERE id = %s", (lid,)))[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Incidents ────────────────────────────────────────────────────────────────

@app.get("/api/incidents")
def list_incidents():
    try:
        return serialize(execute_query("""
            SELECT i.*,
                   t.date_heure_depart,
                   l.code AS ligne_code, l.nom AS ligne_nom
            FROM incidents i
            JOIN trajets t ON i.trajet_id = t.id
            JOIN lignes  l ON t.ligne_id  = l.id
            ORDER BY i.date_incident DESC
        """))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/incidents", status_code=201)
def create_incident(i: IncidentCreate):
    try:
        lid = execute_write(
            """INSERT INTO incidents (trajet_id, type, description, gravite, date_incident)
               VALUES (%s, %s, %s, %s, %s)""",
            (i.trajet_id, i.type, i.description, i.gravite, i.date_incident),
        )
        return serialize(execute_query("SELECT * FROM incidents WHERE id = %s", (lid,)))[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/api/incidents/{iid}/resoudre")
def resoudre_incident(iid: int):
    try:
        if not execute_query("SELECT id FROM incidents WHERE id = %s", (iid,)):
            raise HTTPException(status_code=404, detail="Incident non trouvé")
        execute_write("UPDATE incidents SET resolu = TRUE WHERE id = %s", (iid,))
        return {"message": "Incident marqué comme résolu"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Chat ─────────────────────────────────────────────────────────────────────

@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        result      = ask_claude(req.message)
        sql         = result.get("sql")
        explication = result.get("explication", "")

        if sql and is_safe_sql(sql):
            try:
                rows = execute_query(sql)
                data = serialize(rows)
                return {
                    "reponse":     explication,
                    "sql":         sql,
                    "resultats":   data,
                    "nb_resultats": len(data),
                }
            except Exception as db_err:
                return {
                    "reponse":     explication,
                    "sql":         sql,
                    "resultats":   [],
                    "nb_resultats": 0,
                    "erreur":      f"Erreur SQL : {db_err}",
                }

        return {
            "reponse":     explication or "Je ne peux répondre qu'à des questions de consultation (SELECT).",
            "sql":         None,
            "resultats":   [],
            "nb_resultats": 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Static (must be last) ────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
