import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "billiard_championship.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Regions Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS regions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        m_points INTEGER DEFAULT 0,
        msl_points INTEGER DEFAULT 0,
        comp_points INTEGER DEFAULT 0,
        total_points INTEGER DEFAULT 0,
        rank INTEGER DEFAULT 0
    )''')
    
    # Teams Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS teams (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        region_id TEXT NOT NULL,
        points INTEGER DEFAULT 0,
        rank INTEGER DEFAULT 0,
        logo TEXT,
        trofi_m_1st INTEGER DEFAULT 0,
        trofi_m_2nd INTEGER DEFAULT 0,
        trofi_m_3rd INTEGER DEFAULT 0,
        trofi_m_4th INTEGER DEFAULT 0,
        trofi_msl_1st INTEGER DEFAULT 0,
        trofi_msl_2nd INTEGER DEFAULT 0,
        trofi_msl_3rd INTEGER DEFAULT 0,
        trofi_mpl_1st INTEGER DEFAULT 0,
        trofi_mpl_2nd INTEGER DEFAULT 0,
        trophies_detail TEXT DEFAULT '[]',
        FOREIGN KEY (region_id) REFERENCES regions(id)
    )''')
    
    # Add columns if teams table already existed without them
    c.execute("PRAGMA table_info(teams)")
    existing_cols = [row['name'] for row in c.fetchall()]
    for col in ['trofi_m_1st', 'trofi_m_2nd', 'trofi_m_3rd', 'trofi_m_4th', 'trofi_msl_1st', 'trofi_msl_2nd', 'trofi_msl_3rd', 'trofi_mpl_1st', 'trofi_mpl_2nd', 'trophies_detail']:
        if col not in existing_cols:
            col_type = "TEXT DEFAULT '[]'" if col == 'trophies_detail' else "INTEGER DEFAULT 0"
            c.execute(f"ALTER TABLE teams ADD COLUMN {col} {col_type}")
    
    # Seasons Table (Manages workflow & sequence)
    c.execute('''
    CREATE TABLE IF NOT EXISTS seasons (
        season_number INTEGER PRIMARY KEY,
        current_phase INTEGER DEFAULT 1,
        status TEXT DEFAULT 'ONGOING',
        m_winner_id TEXT,
        m_runner_up_id TEXT,
        msl_winner_id TEXT
    )''')

    # Tournaments Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS tournaments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        region_id TEXT,
        season INTEGER NOT NULL,
        phase INTEGER DEFAULT 1,
        status TEXT DEFAULT 'COMPLETED',
        winner_id TEXT,
        runner_up_id TEXT,
        third_place_id TEXT,
        fourth_place_id TEXT,
        FOREIGN KEY (region_id) REFERENCES regions(id),
        FOREIGN KEY (winner_id) REFERENCES teams(id)
    )''')
    
    c.execute("PRAGMA table_info(tournaments)")
    t_cols = [row['name'] for row in c.fetchall()]
    if 'phase' not in t_cols:
        c.execute("ALTER TABLE tournaments ADD COLUMN phase INTEGER DEFAULT 1")
    
    # Matches Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id TEXT NOT NULL,
        stage TEXT NOT NULL,
        round_name TEXT NOT NULL,
        bracket_type TEXT,
        match_order INTEGER DEFAULT 0,
        team1_id TEXT,
        team2_id TEXT,
        score1 INTEGER,
        score2 INTEGER,
        winner_id TEXT,
        loser_id TEXT,
        status TEXT DEFAULT 'COMPLETED',
        FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
    )''')

    # Trophies History Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS trophies_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        season INTEGER NOT NULL,
        tournament_id TEXT NOT NULL,
        tournament_name TEXT NOT NULL,
        tournament_type TEXT NOT NULL,
        placement INTEGER NOT NULL,
        team_id TEXT NOT NULL,
        region_id TEXT NOT NULL,
        points INTEGER NOT NULL,
        trophy_image TEXT NOT NULL,
        trophy_title TEXT NOT NULL,
        FOREIGN KEY (team_id) REFERENCES teams(id)
    )''')

    # Qualification Slots Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS qualification_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_tournament TEXT NOT NULL,
        slot_number INTEGER NOT NULL,
        slot_code TEXT NOT NULL,
        region_id TEXT,
        team_id TEXT,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'PENDING',
        FOREIGN KEY (team_id) REFERENCES teams(id)
    )''')

    # System Settings Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database schema successfully upgraded and verified!")
