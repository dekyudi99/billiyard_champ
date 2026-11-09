import sqlite3
import zipfile
import re
import xml.etree.ElementTree as ET
import os

from database import get_connection
from rules_engine import recalculate_all_time_standings, update_road_to_world_slots
from seed_data import get_shared_strings, read_sheet, ROOT_EXCEL_DIR

BASE_DIR = os.path.join(ROOT_EXCEL_DIR, "M Championship")

FILES = {
    'M1': os.path.join(BASE_DIR, "M1 BILLIYARD-T1.xlsx"),
    'M2': os.path.join(BASE_DIR, "M2 BILLIYARD-TLPH.xlsx"),
    'M3': os.path.join(BASE_DIR, "M3 BILLIYARD-T1.xlsx"),
}

# Round pool mapping for Swiss Stage 33 matches
def get_swiss_pool_info(m_num):
    if 1 <= m_num <= 8:
        return ("Round 1", "Pool 0-0 (BO1)")
    elif 9 <= m_num <= 12:
        return ("Round 2 (High)", "Pool 1-0 (BO1)")
    elif 13 <= m_num <= 16:
        return ("Round 2 (Low)", "Pool 0-1 (BO1)")
    elif 17 <= m_num <= 18:
        return ("Round 3 (High)", "Pool 2-0 (BO3)")
    elif 19 <= m_num <= 22:
        return ("Round 3 (Mid)", "Pool 1-1 (BO1)")
    elif 23 <= m_num <= 24:
        return ("Round 3 (Low)", "Pool 0-2 (BO3)")
    elif 25 <= m_num <= 27:
        return ("Round 4 (High)", "Pool 2-1 (BO3)")
    elif 28 <= m_num <= 30:
        return ("Round 4 (Low)", "Pool 1-2 (BO3)")
    elif 31 <= m_num <= 33:
        return ("Round 5 (Decider)", "Pool 2-2 (BO3)")
    return ("Swiss Stage", "Swiss")

def parse_swiss_stage(file_path):
    with zipfile.ZipFile(file_path) as z:
        ss = get_shared_strings(z)
        wb_tree = ET.fromstring(z.read('xl/workbook.xml'))
        sheets = {s.attrib['name']: s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'] 
                  for s in wb_tree.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet')}
        rels_tree = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        rels = {r.attrib['Id']: r.attrib['Target'] 
                for r in rels_tree.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship')}
        
        target = 'xl/' + rels[sheets['Swiss Stage']]
        grid = read_sheet(z, target, ss)
        
        match_cells = {}
        for pos, val in grid.items():
            if isinstance(val, str) and re.match(r'^Match\s*\d+', val):
                m_num = int(re.search(r'\d+', val).group())
                # Handle typo in row 32 where Match 8 is labeled Match 1
                row_idx = int(''.join(filter(str.isdigit, pos)))
                if row_idx >= 32 and m_num == 1:
                    m_num = 8
                match_cells[m_num] = pos

        matches = []
        for m_num in sorted(match_cells.keys()):
            pos = match_cells[m_num]
            col = ''.join(filter(str.isalpha, pos))
            row = int(''.join(filter(str.isdigit, pos)))
            score_col = chr(ord(col) + 1)
            
            t1 = grid.get(f"{col}{row+1}", "").strip()
            s1_val = grid.get(f"{score_col}{row+1}", "")
            t2 = grid.get(f"{col}{row+2}", "").strip()
            s2_val = grid.get(f"{score_col}{row+2}", "")
            
            s1 = int(s1_val) if s1_val != "" and s1_val.isdigit() else 0
            s2 = int(s2_val) if s2_val != "" and s2_val.isdigit() else 0
            
            winner = t1 if s1 > s2 else (t2 if s2 > s1 else None)
            loser = t2 if s1 > s2 else (t1 if s2 > s1 else None)
            
            round_name, bracket_type = get_swiss_pool_info(m_num)
            
            matches.append({
                'match_order': m_num,
                'round_name': round_name,
                'bracket_type': bracket_type,
                'team1_id': t1,
                'team2_id': t2,
                'score1': s1,
                'score2': s2,
                'winner_id': winner,
                'loser_id': loser,
                'status': 'COMPLETED'
            })
            
        return matches

def run_import():
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Fix M3 Podium (Peringkat 4 = AE, bukan RORA!)
    print("Fixing M3 podium: 4th place = AE (Alter Ego)...")
    c.execute("""
        UPDATE tournaments
        SET fourth_place_id = 'AE'
        WHERE id = 'M3'
    """)
    
    # Also check M2 podium: 4th place = AG (All Gamers)
    c.execute("""
        UPDATE tournaments
        SET fourth_place_id = 'AG'
        WHERE id = 'M2'
    """)
    
    # 2. Insert Swiss Stage matches for M1, M2, M3
    for m_id, file_path in FILES.items():
        print(f"Parsing Swiss Stage for {m_id} from {file_path}...")
        swiss_matches = parse_swiss_stage(file_path)
        print(f"Found {len(swiss_matches)} Swiss Stage matches for {m_id}.")
        
        # Remove existing Swiss matches for this tournament if any
        c.execute("DELETE FROM matches WHERE tournament_id=? AND stage='SWISS'", (m_id,))
        
        for m in swiss_matches:
            c.execute("""
                INSERT INTO matches (tournament_id, stage, round_name, bracket_type, match_order, 
                                    team1_id, team2_id, score1, score2, winner_id, loser_id, status)
                VALUES (?, 'SWISS', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (m_id, m['round_name'], m['bracket_type'], m['match_order'],
                  m['team1_id'], m['team2_id'], m['score1'], m['score2'], 
                  m['winner_id'], m['loser_id'], m['status']))
                  
    conn.commit()
    
    # 3. Recalculate standings, trophies, and points
    print("Recalculating all-time standings with correct M3 4th place for AE...")
    recalculate_all_time_standings(conn)
    update_road_to_world_slots(conn, current_season=4)
    
    conn.close()
    print("Import and recalculation successfully completed!")

if __name__ == "__main__":
    run_import()

