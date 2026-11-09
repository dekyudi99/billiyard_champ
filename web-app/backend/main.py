from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import os
import json

from database import get_connection, init_db
from rules_engine import recalculate_all_time_standings, update_road_to_world_slots, get_season_workflow_status
from seed_data import run_seed

app = FastAPI(title="Billiard Championship World System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGOS_DIR = os.path.join(os.path.dirname(BASE_DIR), "logos")
TROFI_DIR = os.path.join(os.path.dirname(BASE_DIR), "trofi")
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

# Serve logos
if os.path.exists(LOGOS_DIR):
    app.mount("/static/logos", StaticFiles(directory=LOGOS_DIR), name="logos")

# Serve trophy images
if os.path.exists(TROFI_DIR):
    app.mount("/static/trofi", StaticFiles(directory=TROFI_DIR), name="trofi")

@app.on_event("startup")
def startup_event():
    init_db()
    run_seed()

# --- API Endpoints ---

@app.get("/api/stats")
def get_stats():
    conn = get_connection()
    c = conn.cursor()
    teams_cnt = c.execute("SELECT count(*) FROM teams").fetchone()[0]
    tourneys_cnt = c.execute("SELECT count(*) FROM tournaments").fetchone()[0]
    completed_cnt = c.execute("SELECT count(*) FROM tournaments WHERE status='COMPLETED'").fetchone()[0]
    pending_cnt = c.execute("SELECT count(*) FROM tournaments WHERE status != 'COMPLETED'").fetchone()[0]
    trophies_cnt = c.execute("SELECT count(*) FROM trophies_history").fetchone()[0]
    
    # Check max season
    c.execute("SELECT MAX(season) FROM tournaments")
    max_s = c.fetchone()[0] or 4
    
    conn.close()
    return {
        "teams_count": teams_cnt,
        "tournaments_count": tourneys_cnt,
        "completed_tournaments": completed_cnt,
        "pending_tournaments": pending_cnt,
        "trophies_awarded": trophies_cnt,
        "active_season": max_s
    }

@app.get("/api/teams")
def get_teams(region: Optional[str] = None):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT t.id, t.name, t.region_id, t.points, t.rank, t.logo, 
               t.trofi_m_1st, t.trofi_m_2nd, t.trofi_m_3rd, t.trofi_m_4th,
               t.trofi_msl_1st, t.trofi_msl_2nd, t.trofi_msl_3rd,
               t.trofi_mpl_1st, t.trofi_mpl_2nd,
               t.trophies_detail,
               r.name as region_name
        FROM teams t
        LEFT JOIN regions r ON t.region_id = r.id
    """
    params = []
    if region:
        query += " WHERE t.region_id = ?"
        params.append(region)
    query += " ORDER BY t.rank ASC, t.points DESC"
    
    c.execute(query, params)
    rows = c.fetchall()
    teams = []
    for row in rows:
        d = dict(row)
        try:
            d['trophies_detail'] = json.loads(d['trophies_detail']) if d['trophies_detail'] else []
        except:
            d['trophies_detail'] = []
        teams.append(d)
        
    conn.close()
    return teams

@app.get("/api/regions")
def get_regions():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM regions ORDER BY rank ASC, total_points DESC")
    regions = [dict(row) for row in c.fetchall()]
    conn.close()
    return regions

@app.get("/api/tournaments")
def get_tournaments(type: Optional[str] = None, season: Optional[int] = None, region: Optional[str] = None):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT t.*, 
               w.name as winner_name, w.logo as winner_logo,
               ru.name as runner_up_name, ru.logo as runner_up_logo
        FROM tournaments t
        LEFT JOIN teams w ON t.winner_id = w.id
        LEFT JOIN teams ru ON t.runner_up_id = ru.id
        WHERE 1=1
    """
    params = []
    if type:
        query += " AND t.type = ?"
        params.append(type)
    if season:
        query += " AND t.season = ?"
        params.append(season)
    if region:
        query += " AND t.region_id = ?"
        params.append(region)
        
    query += " ORDER BY t.season DESC, t.phase ASC, t.id ASC"
    c.execute(query, params)
    tourneys = [dict(row) for row in c.fetchall()]
    conn.close()
    return tourneys

@app.get("/api/tournaments/{tournament_id}")
def get_tournament_details(tournament_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT t.*, 
               w.name as winner_name, w.logo as winner_logo,
               ru.name as runner_up_name, ru.logo as runner_up_logo,
               tp.name as third_place_name, tp.logo as third_place_logo,
               fp.name as fourth_place_name, fp.logo as fourth_place_logo
        FROM tournaments t
        LEFT JOIN teams w ON t.winner_id = w.id
        LEFT JOIN teams ru ON t.runner_up_id = ru.id
        LEFT JOIN teams tp ON t.third_place_id = tp.id
        LEFT JOIN teams fp ON t.fourth_place_id = fp.id
        WHERE t.id = ?
    """, (tournament_id,))
    t = c.fetchone()
    if not t:
        conn.close()
        raise HTTPException(status_code=404, detail="Tournament not found")
        
    t_dict = dict(t)
    
    # Matches
    c.execute("""
        SELECT m.*, 
               t1.name as team1_name, t1.logo as team1_logo,
               t2.name as team2_name, t2.logo as team2_logo,
               w.name as winner_name
        FROM matches m
        LEFT JOIN teams t1 ON m.team1_id = t1.id
        LEFT JOIN teams t2 ON m.team2_id = t2.id
        LEFT JOIN teams w ON m.winner_id = w.id
        WHERE m.tournament_id = ?
        ORDER BY m.match_order ASC, m.id ASC
    """, (tournament_id,))
    t_dict['matches'] = [dict(row) for row in c.fetchall()]
    conn.close()
    return t_dict

class MatchUpdateRequest(BaseModel):
    team1_id: Optional[str] = None
    team2_id: Optional[str] = None
    score1: Optional[int] = None
    score2: Optional[int] = None
    winner_id: Optional[str] = None
    loser_id: Optional[str] = None
    status: Optional[str] = "COMPLETED"

@app.post("/api/matches/{match_id}/update")
def update_match_score(match_id: int, req: MatchUpdateRequest):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM matches WHERE id=?", (match_id,))
    match_row = c.fetchone()
    if not match_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Match not found")
        
    t1_id = req.team1_id if req.team1_id is not None else match_row['team1_id']
    t2_id = req.team2_id if req.team2_id is not None else match_row['team2_id']
    
    # Auto-determine winner if scores are provided and winner_id not explicit
    winner_id = req.winner_id
    loser_id = req.loser_id
    if req.score1 is not None and req.score2 is not None:
        if not winner_id:
            if req.score1 > req.score2:
                winner_id = t1_id
                loser_id = t2_id
            elif req.score2 > req.score1:
                winner_id = t2_id
                loser_id = t1_id
                
    c.execute("""
        UPDATE matches
        SET team1_id = ?,
            team2_id = ?,
            score1 = ?,
            score2 = ?,
            winner_id = ?,
            loser_id = ?,
            status = ?
        WHERE id = ?
    """, (t1_id, t2_id, req.score1, req.score2, winner_id, loser_id, req.status, match_id))
    
    conn.commit()
    conn.close()
    return {"message": "Skor pertandingan berhasil diperbarui!", "match_id": match_id, "winner_id": winner_id}

class TournamentFinishRequest(BaseModel):
    winner_id: str
    runner_up_id: str
    third_place_id: Optional[str] = None
    fourth_place_id: Optional[str] = None

@app.post("/api/tournaments/{tournament_id}/finish")
def finish_tournament(tournament_id: str, req: TournamentFinishRequest):
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("SELECT season, type, region_id FROM tournaments WHERE id=?", (tournament_id,))
    t_row = c.fetchone()
    if not t_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Tournament not found")
    t_season = t_row['season']

    # --- Validasi hasil akhir ---
    placements = [req.winner_id, req.runner_up_id, req.third_place_id, req.fourth_place_id]
    required = 2
    if t_row['type'] == 'MPL':
        required = 4          # peringkat 3 & 4 menentukan slot MSL
    elif t_row['type'] == 'M_SERIES':
        required = 4          # 4 trofi: juara 1-4
    elif t_row['type'] == 'MSL':
        required = 3          # trofi sampai peringkat 3
    given = [p for p in placements if p]
    if any(not p for p in placements[:required]):
        conn.close()
        raise HTTPException(status_code=400, detail=f"Turnamen {t_row['type']} wajib mengisi peringkat 1 sampai {required}.")
    if len(set(given)) != len(given):
        conn.close()
        raise HTTPException(status_code=400, detail="Satu tim tidak boleh menempati lebih dari satu peringkat.")
    for team_id in given:
        c.execute("SELECT region_id FROM teams WHERE id=?", (team_id,))
        team_row = c.fetchone()
        if not team_row:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Tim '{team_id}' tidak ditemukan.")
        if t_row['type'] == 'MPL' and t_row['region_id'] and team_row['region_id'] != t_row['region_id']:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Tim '{team_id}' bukan dari region {t_row['region_id']}.")
    
    c.execute("""
        UPDATE tournaments
        SET status = 'COMPLETED',
            winner_id = ?,
            runner_up_id = ?,
            third_place_id = ?,
            fourth_place_id = ?
        WHERE id = ?
    """, (req.winner_id, req.runner_up_id, req.third_place_id, req.fourth_place_id, tournament_id))
    
    conn.commit()
    
    # Automatically recalculate all-time standings & qualification slots!
    recalculate_all_time_standings(conn)
    update_road_to_world_slots(conn, current_season=t_season)
    
    conn.close()
    return {"message": "Tournament updated successfully and all standings recalculated automatically!"}

@app.get("/api/trophies/history")
def get_trophies_history(season: Optional[int] = None, team_id: Optional[str] = None):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT th.*, t.name as team_name, t.logo as team_logo
        FROM trophies_history th
        LEFT JOIN teams t ON th.team_id = t.id
        WHERE 1=1
    """
    params = []
    if season:
        query += " AND th.season = ?"
        params.append(season)
    if team_id:
        query += " AND th.team_id = ?"
        params.append(team_id)
        
    query += " ORDER BY th.season DESC, th.points DESC, th.id ASC"
    c.execute(query, params)
    history = [dict(row) for row in c.fetchall()]
    conn.close()
    return history

@app.get("/api/road-to-world")
def get_road_to_world(season: Optional[int] = None):
    conn = get_connection()
    c = conn.cursor()

    # Default: season terbaru yang ada di database
    if season is None:
        c.execute("SELECT MAX(season) FROM tournaments")
        season = c.fetchone()[0] or 4
    m_target = f"M{season}"
    msl_target = f"MSL_S{season}"

    c.execute("""
        SELECT qs.*, t.name as team_name, t.logo as team_logo, r.name as region_name
        FROM qualification_slots qs
        LEFT JOIN teams t ON qs.team_id = t.id
        LEFT JOIN regions r ON qs.region_id = r.id
        WHERE qs.target_tournament = ?
        ORDER BY qs.slot_number ASC
    """, (m_target,))
    m_slots = [dict(row) for row in c.fetchall()]

    c.execute("""
        SELECT qs.*, t.name as team_name, t.logo as team_logo, r.name as region_name
        FROM qualification_slots qs
        LEFT JOIN teams t ON qs.team_id = t.id
        LEFT JOIN regions r ON qs.region_id = r.id
        WHERE qs.target_tournament = ?
        ORDER BY qs.slot_number ASC
    """, (msl_target,))
    msl_slots = [dict(row) for row in c.fetchall()]

    c.execute("SELECT key, value FROM system_settings")
    settings = {row['key']: row['value'] for row in c.fetchall()}

    conn.close()
    return {
        "season": season,
        "m_championship": {
            "name": f"Road to M{season} World Championship",
            "total_slots": 16,
            "slots": m_slots
        },
        "msl_championship": {
            "name": f"Road to MSL Championship Season {season}",
            "total_slots": 8,
            "slots": msl_slots
        },
        "settings": settings
    }

class SettingsRequest(BaseModel):
    msl_extra_team: Optional[str] = None

@app.post("/api/settings")
def update_settings(req: SettingsRequest):
    """Menentukan tim slot ekstra MSL (Peringkat 5 region juara) lalu menghitung ulang slot season terbaru."""
    conn = get_connection()
    c = conn.cursor()
    if req.msl_extra_team is not None:
        if req.msl_extra_team:
            c.execute("SELECT 1 FROM teams WHERE id=?", (req.msl_extra_team,))
            if not c.fetchone():
                conn.close()
                raise HTTPException(status_code=400, detail="Tim tidak ditemukan")
        c.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('msl_extra_team', ?)", (req.msl_extra_team,))
    conn.commit()
    c.execute("SELECT MAX(season) FROM tournaments")
    latest = c.fetchone()[0] or 4
    update_road_to_world_slots(conn, current_season=latest)
    conn.close()
    return {"message": "Pengaturan disimpan dan slot kualifikasi diperbarui!"}

@app.get("/api/season-workflow/{season_num}")
def get_season_workflow(season_num: int):
    conn = get_connection()
    status = get_season_workflow_status(conn, season_num)
    conn.close()
    return status

# --- Season Workflow Actions ---

@app.post("/api/season/{season_num}/create-msl")
def create_msl_tournament(season_num: int):
    """
    Creates the MSL Championship for season_num.
    Strict rule: All 7 MPL tournaments must be completed first!
    """
    conn = get_connection()
    c = conn.cursor()
    
    wf = get_season_workflow_status(conn, season_num)
    if not wf['all_mpl_done']:
        conn.close()
        raise HTTPException(status_code=400, detail="Semua 7 liga regional MPL harus selesai terlebih dahulu sebelum MSL dapat dimulai!")
        
    msl_id = f"MSL CHAMPIONSHIP S{season_num}"
    c.execute("SELECT id FROM tournaments WHERE id=?", (msl_id,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail=f"{msl_id} sudah ada dalam database!")
        
    # Create tournament
    c.execute("""
        INSERT INTO tournaments (id, name, type, region_id, season, phase, status)
        VALUES (?, ?, 'MSL', 'GLOBAL', ?, 2, 'ONGOING')
    """, (msl_id, msl_id, season_num))
    
    # Pull the 8 qualified teams from qualification_slots
    c.execute("SELECT team_id FROM qualification_slots WHERE target_tournament=? ORDER BY slot_number ASC", (f"MSL_S{season_num}",))
    q_teams = [row['team_id'] for row in c.fetchall() if row['team_id']]

    if len(q_teams) < 8:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Baru {len(q_teams)}/8 slot MSL S{season_num} terisi. Lengkapi dulu slot yang masih kosong "
                   f"(mis. tim slot ekstra Peringkat 5 di tab Road to World)."
        )

    # Create tournament
    c.execute("""
        INSERT INTO tournaments (id, name, type, region_id, season, phase, status)
        VALUES (?, ?, 'MSL', 'GLOBAL', ?, 2, 'ONGOING')
    """, (msl_id, msl_id, season_num))
    
    # Create initial playoff matches
    if len(q_teams) >= 8:
        matches = [
            (msl_id, "PLAYOFF", "Match 1", "UPPER", 1, q_teams[0], q_teams[1], None, None, None, None, "PENDING"),
            (msl_id, "PLAYOFF", "Match 2", "UPPER", 2, q_teams[2], q_teams[3], None, None, None, None, "PENDING"),
            (msl_id, "PLAYOFF", "Match 3", "UPPER", 3, q_teams[4], q_teams[5], None, None, None, None, "PENDING"),
            (msl_id, "PLAYOFF", "Match 4", "UPPER", 4, q_teams[6], q_teams[7], None, None, None, None, "PENDING"),
            (msl_id, "PLAYOFF", "Match 5", "UPPER", 5, "Winner M1", "Winner M2", None, None, None, None, "PENDING"),
            (msl_id, "PLAYOFF", "Match 6", "UPPER", 6, "Winner M3", "Winner M4", None, None, None, None, "PENDING"),
            (msl_id, "PLAYOFF", "Upper Final", "UPPER", 7, "Winner M5", "Winner M6", None, None, None, None, "PENDING"),
            (msl_id, "PLAYOFF", "Grand Final", "FINAL", 8, "Winner Upper Final", "Winner Lower Final", None, None, None, None, "PENDING"),
        ]
        for m in matches:
            c.execute("""
                INSERT INTO matches (tournament_id, stage, round_name, bracket_type, match_order, team1_id, team2_id, score1, score2, winner_id, loser_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, m)
            
    conn.commit()
    conn.close()
    return {"message": f"Turnamen {msl_id} berhasil dibuat dan 8 tim teratas otomatis masuk bagan!"}

@app.post("/api/season/{season_num}/create-m-championship")
def create_m_championship_tournament(season_num: int):
    """
    Creates the M World Championship for season_num.
    Strict rule: All 7 MPLs and MSL must be completed first!
    """
    conn = get_connection()
    c = conn.cursor()
    
    wf = get_season_workflow_status(conn, season_num)
    if not wf['all_mpl_done']:
        conn.close()
        raise HTTPException(status_code=400, detail="Semua 7 liga MPL harus selesai terlebih dahulu!")
    if not wf['msl_done']:
        conn.close()
        raise HTTPException(status_code=400, detail="Turnamen MSL Championship harus selesai terlebih dahulu untuk menentukan slot MSL #1!")
        
    m_id = f"M{season_num}"
    c.execute("SELECT id FROM tournaments WHERE id=?", (m_id,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail=f"{m_id} sudah ada dalam database!")
        
    c.execute("""
        INSERT INTO tournaments (id, name, type, region_id, season, phase, status)
        VALUES (?, ?, 'M_SERIES', 'GLOBAL', ?, 3, 'ONGOING')
    """, (m_id, f"M{season_num} World Championship", season_num))
    
    conn.commit()
    conn.close()
    return {"message": f"Turnamen M{season_num} World Championship berhasil dibuat dan siap dimainkan!"}

@app.post("/api/season/start-new")
def start_new_season():
    """
    Starts a completely new season (e.g. Season 5).
    Rules:
    - Previous season must be completely finished (MPL, MSL, and M-Championship all COMPLETED).
    - Checks previous M-Championship winner and runner-up:
      - Winner's region becomes the new defending_m_champ_1st_region.
      - Runner-up's region becomes the new defending_m_champ_2nd_region.
    - Creates the 7 MPL tournaments for the new season!
    """
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("SELECT MAX(season) FROM tournaments")
    curr_season = c.fetchone()[0] or 4
    
    wf = get_season_workflow_status(conn, curr_season)
    if not wf['can_start_next_season']:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Season {curr_season} belum tuntas seluruhnya! Pastikan semua MPL, MSL, dan M-Championship telah selesai.")
        
    new_season = curr_season + 1
    
    # Previous M winner & runner up
    c.execute("SELECT winner_id, runner_up_id FROM tournaments WHERE type='M_SERIES' AND season=?", (curr_season,))
    m_last = c.fetchone()
    if m_last:
        w_id, ru_id = m_last['winner_id'], m_last['runner_up_id']
        c.execute("SELECT region_id FROM teams WHERE id=?", (w_id,))
        w_reg = c.fetchone()['region_id']
        c.execute("SELECT region_id FROM teams WHERE id=?", (ru_id,))
        ru_reg = c.fetchone()['region_id']
        
        c.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('defending_m_champ_1st_region', ?)", (w_reg,))
        c.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('defending_m_champ_2nd_region', ?)", (ru_reg,))
        
    # Create the 7 MPL tournaments for new season
    regions = ['AM', 'ID', 'MEA', 'MY', 'PEL', 'PH', 'SEA']
    for r in regions:
        t_id = f"MPL {r} S{new_season}"
        c.execute("""
            INSERT INTO tournaments (id, name, type, region_id, season, phase, status)
            VALUES (?, ?, 'MPL', ?, ?, 1, 'ONGOING')
        """, (t_id, t_id, r, new_season))
        
    conn.commit()
    conn.close()
    return {"message": f"Season {new_season} resmi dimulai! 7 liga regional MPL baru telah dibuat."}

# Simulation helpers
@app.post("/api/simulate/sea-s4")
def simulate_sea_s4(winner_id: str = "YG", runner_up_id: str = "CFU", third_place_id: str = "PRX", fourth_place_id: str = "VPE"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE tournaments
        SET status = 'COMPLETED',
            winner_id = ?,
            runner_up_id = ?,
            third_place_id = ?,
            fourth_place_id = ?
        WHERE id = 'MPL SEA S4'
    """, (winner_id, runner_up_id, third_place_id, fourth_place_id))
    
    conn.commit()
    recalculate_all_time_standings(conn)
    update_road_to_world_slots(conn, current_season=4)
    conn.close()
    return {"message": f"MPL SEA S4 selesai: Juara={winner_id}, Runner-up={runner_up_id}, Peringkat 3={third_place_id}. Slot kualifikasi otomatis terisi dan Base Team/Region ter-update!"}

@app.post("/api/reset-sea-s4")
def reset_sea_s4():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE tournaments
        SET status = 'ONGOING',
            winner_id = NULL,
            runner_up_id = NULL,
            third_place_id = NULL,
            fourth_place_id = NULL
        WHERE id = 'MPL SEA S4'
    """)
    conn.commit()
    recalculate_all_time_standings(conn)
    update_road_to_world_slots(conn, current_season=4)
    conn.close()
    return {"message": "MPL SEA S4 dikembalikan ke status belum selesai."}

# Serve frontend
@app.get("/")
def serve_frontend_index():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Frontend index.html not found"}

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
