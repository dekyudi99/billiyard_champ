import sqlite3
import json
import os
import zipfile
import xml.etree.ElementTree as ET
from database import get_connection, init_db
from rules_engine import recalculate_all_time_standings, update_road_to_world_slots

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_EXCEL_DIR = os.environ.get(
    "EXCEL_DIR",
    os.path.normpath(os.path.join(_HERE, "..", "..", "Billiard Championship"))
)
SEED_JSON = os.path.join(_HERE, "initial_seed.json")

# Kode tim di Excel yang berbeda dengan ID tim di database
TEAM_ALIASES = {"HB": "HBSE"}

def get_shared_strings(z):
    shared_strings = []
    if 'xl/sharedStrings.xml' in z.namelist():
        tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in tree.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
            t_nodes = si.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
            shared_strings.append("".join([t.text for t in t_nodes if t.text]))
    return shared_strings

def read_sheet(z, sheet_path, shared_strings):
    tree = ET.fromstring(z.read(sheet_path))
    rows = tree.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheetData/{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row')
    grid = {}
    for row in rows:
        for c in row.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
            ref = c.attrib.get('r')
            t = c.attrib.get('t')
            v_el = c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            val = v_el.text if v_el is not None else ""
            if t == 's' and val != '':
                val = shared_strings[int(val)]
            if val != "":
                grid[ref] = val
    return grid

def run_seed():
    init_db()
    conn = get_connection()
    c = conn.cursor()
    
    # Check if already seeded with matches
    c.execute("SELECT count(*) as cnt FROM matches")
    if c.fetchone()['cnt'] > 100:
        print("Database already has full historical data. Skipping re-seed.")
        conn.close()
        return

    print("Seeding full historical data into SQLite database...")

    # Load initial seed json for teams and regions
    with open(SEED_JSON, 'r') as f:
        data = json.load(f)

    # 1. Insert Regions
    for r in data['regions']:
        c.execute("""
            INSERT OR REPLACE INTO regions (id, name, m_points, msl_points, comp_points, total_points, rank)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (r['id'], r['name'], r['m_points'], r['msl_points'], r['comp_points'], r['total_points'], 0))

    # 2. Insert Teams
    for t in data['teams']:
        c.execute("""
            INSERT OR REPLACE INTO teams (id, name, region_id, points, rank, logo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (t['id'], t['name'], t['region'], t['points'], t['rank'], t['logo']))

    # 3. Insert System Settings
    settings = [
        ('defending_m_champ_1st_region', 'PEL'), # M3 Juara 1: T1 (PEL)
        ('defending_m_champ_2nd_region', 'PEL'), # M3 Juara 2: IHC (PEL) -> Juara 1 & 2 dari PEL, slot melimpah!
        ('defending_msl_champ_region', 'MEA'),
        ('msl_extra_slot_rule', 'defending_m_champ_region'),
        ('msl_extra_team', 'DK'),
        ('current_season', '4')
    ]
    for k, v in settings:
        c.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (k, v))

    # 4. Insert Tournaments
    mpl_podiums = {
        "MPL AM S1": ("TL", "C9", "A7", "FAZE"),
        "MPL AM S2": ("TL", "C9", "A7", "FAZE"),
        "MPL AM S3": ("A7", "TL", "C9", "FAZE"),
        "MPL AM S4": ("TL", "FUR", "C9", "A7"),
        
        "MPL ID S1": ("AE", "ONIC", "EVOS", "RRQ"),
        "MPL ID S2": ("AE", "ONIC", "EVOS", "RRQ"),
        "MPL ID S3": ("AE", "ONIC", "EVOS", "RRQ"),
        "MPL ID S4": ("EVOS", "RRQ", "ONIC", "AE"),
        
        "MPL MEA S1": ("VIT", "RORA", "FNC", "G2"),
        "MPL MEA S2": ("RORA", "VIT", "FNC", "G2"),
        "MPL MEA S3": ("VIT", "FLCN", "FNC", "RORA"),
        "MPL MEA S4": ("VIT", "FNC", "FLCN", "G2"),
        
        "MPL MY S1": ("AG", "SRG", "HB", "TDK"),
        "MPL MY S2": ("AG", "SRG", "HB", "TDK"),
        "MPL MY S3": ("HBSE", "SRG", "AG", "TDK"),
        "MPL MY S4": ("APG", "SRG", "HBSE", "NV"),
        
        "MPL PEL S1": ("T1", "WBG", "IHC", "DRX"),
        "MPL PEL S2": ("WBG", "T1", "IHC", "DRX"),
        "MPL PEL S3": ("T1", "IHC", "WBG", "DRX"),
        "MPL PEL S4": ("WBG", "T1", "DRX", "IHC"),
        
        "MPL PH S1": ("ROPH", "TLPH", "APBR", "ONPH"),
        "MPL PH S2": ("TLPH", "ROPH", "APBR", "ONPH"),
        "MPL PH S3": ("ROPH", "TLPH", "APBR", "ONPH"),
        "MPL PH S4": ("TLPH", "ROPH", "FLCP", "BOOM"),
        
        "MPL SEA S1": ("YG", "CFU", "PRX", "VPE"),
        "MPL SEA S2": ("CFU", "YG", "PRX", "VPE"),
        "MPL SEA S3": ("YG", "CFU", "PRX", "VPE"),
        "MPL SEA S4": (None, None, None, None) # Currently unplayed!
    }

    msl_podiums = {
        "MSL CHAMPIONSHIP S1": ("FNC", "PRX", "G2", "APBR"),
        "MSL CHAMPIONSHIP S2": ("G2", "PRX", "APBR", "FNC"),
        "MSL CHAMPIONSHIP S3": ("RORA", "RRQ", "C9", "AG")
    }

    m_podiums = {
        "M1": ("T1", "VIT", "AE", "YG"),
        "M2": ("TLPH", "AE", "CFU", "CG"),
        "M3": ("T1", "IHC", "ROPH", "RORA")
    }

    # Tournaments table insertion
    for tid, podium in mpl_podiums.items():
        parts = tid.split()
        region = parts[1]
        season = int(parts[2][1:])
        status = 'ONGOING' if tid == 'MPL SEA S4' else 'COMPLETED'
        c.execute("""
            INSERT OR REPLACE INTO tournaments (id, name, type, region_id, season, status, winner_id, runner_up_id, third_place_id, fourth_place_id)
            VALUES (?, ?, 'MPL', ?, ?, ?, ?, ?, ?, ?)
        """, (tid, tid, region, season, status, podium[0], podium[1], podium[2], podium[3]))

    for tid, podium in msl_podiums.items():
        season = int(tid.split('S')[-1])
        c.execute("""
            INSERT OR REPLACE INTO tournaments (id, name, type, region_id, season, status, winner_id, runner_up_id, third_place_id, fourth_place_id)
            VALUES (?, ?, 'MSL', 'GLOBAL', ?, 'COMPLETED', ?, ?, ?, ?)
        """, (tid, tid, season, podium[0], podium[1], podium[2], podium[3]))

    for tid, podium in m_podiums.items():
        m_num = int(tid[1])
        c.execute("""
            INSERT OR REPLACE INTO tournaments (id, name, type, region_id, season, status, winner_id, runner_up_id, third_place_id, fourth_place_id)
            VALUES (?, ?, 'M_SERIES', 'GLOBAL', ?, 'COMPLETED', ?, ?, ?, ?)
        """, (tid, f"{tid} World Championship", m_num, podium[0], podium[1], podium[2], podium[3]))

    # 5. Extract & Insert All Historical Matches
    c.execute("DELETE FROM matches")
    
    # MPL matches
    mpl_dir = os.path.join(ROOT_EXCEL_DIR, "MPL")
    for region in sorted(os.listdir(mpl_dir)):
        reg_path = os.path.join(mpl_dir, region)
        if not os.path.isdir(reg_path): continue
        for f in sorted(os.listdir(reg_path)):
            if not f.endswith('.xlsx'): continue
            fpath = os.path.join(reg_path, f)
            t_id = f.replace('.xlsx', '').split('-')[0].strip()
            season = int(t_id.split('S')[-1]) if 'S' in t_id else 1
            
            with zipfile.ZipFile(fpath, 'r') as z:
                ss = get_shared_strings(z)
                wb = ET.fromstring(z.read('xl/workbook.xml'))
                rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
                rel_map = {rel.attrib['Id']: rel.attrib['Target'] for rel in rels.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship')}
                sheet = wb.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet')
                target = 'xl/' + rel_map[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
                grid = read_sheet(z, target, ss)
                
                if season == 4 and t_id != "MPL PH S4":
                    if t_id == "MPL SEA S4":
                        m_defs = [
                            ("Qualified 1", "QUALIFIED", "QUALIFIER", 1, "VPE", "FL", None, None, None, None, "PENDING"),
                            ("Qualified 2", "QUALIFIED", "QUALIFIER", 2, "PRX", "ESB", None, None, None, None, "PENDING"),
                            ("Match 1", "PLAYOFF", "UPPER", 3, "YG", "Winner Q1", None, None, None, None, "PENDING"),
                            ("Match 2", "PLAYOFF", "UPPER", 4, "CFU", "Winner Q2", None, None, None, None, "PENDING"),
                            ("Final Upper", "PLAYOFF", "UPPER", 5, "Winner M1", "Winner M2", None, None, None, None, "PENDING"),
                            ("Match 4", "PLAYOFF", "LOWER", 6, "Loser M1", "Loser M2", None, None, None, None, "PENDING"),
                            ("Final Lower", "PLAYOFF", "LOWER", 7, "Loser F-Upper", "Winner M4", None, None, None, None, "PENDING"),
                            ("Grand Final", "PLAYOFF", "FINAL", 8, "Winner F-Upper", "Winner F-Lower", None, None, None, None, "PENDING"),
                        ]
                    else:
                        def get_m(rname, st, br, ord_num, t1_c, t2_c, s1_c, s2_c):
                            t1 = grid.get(t1_c)
                            t2 = grid.get(t2_c)
                            s1 = int(grid[s1_c]) if grid.get(s1_c, '').isdigit() else None
                            s2 = int(grid[s2_c]) if grid.get(s2_c, '').isdigit() else None
                            w = t1 if s1 is not None and s2 is not None and s1 > s2 else (t2 if s2 is not None and s1 is not None and s2 > s1 else None)
                            l = t2 if w == t1 else t1
                            return (rname, st, br, ord_num, t1, t2, s1, s2, w, l, 'COMPLETED')
                        
                        m_defs = [
                            get_m("Qualified 1", "QUALIFIED", "QUALIFIER", 1, "B5", "B6", "C5", "C6"),
                            get_m("Qualified 2", "QUALIFIED", "QUALIFIER", 2, "B9", "B10", "C9", "C10"),
                            get_m("Match 1", "PLAYOFF", "UPPER", 3, "E5", "E6", "F5", "F6"),
                            get_m("Match 2", "PLAYOFF", "UPPER", 4, "E9", "E10", "F9", "F10"),
                            get_m("Final Upper", "PLAYOFF", "UPPER", 5, "H7", "H8", "I7", "I8"),
                            get_m("Match 4", "PLAYOFF", "LOWER", 6, "E15", "E16", "F15", "F16"),
                            get_m("Final Lower", "PLAYOFF", "LOWER", 7, "N16", "N17", "O16", "O17"),
                            get_m("Grand Final", "PLAYOFF", "FINAL", 8, "N7", "N8", "O7", "O8"),
                        ]
                    for m in m_defs:
                        c.execute("""
                            INSERT INTO matches (tournament_id, stage, round_name, bracket_type, match_order, team1_id, team2_id, score1, score2, winner_id, loser_id, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (t_id, m[1], m[0], m[2], m[3], m[4], m[5], m[6], m[7], m[8], m[9], m[10]))
                elif t_id == "MPL PH S4":
                    m_defs = [
                        ("Qualified 1", "QUALIFIED", "QUALIFIER", 1, grid.get("C5"), grid.get("C7"), 0, 2, "BOOM", "APBR", "COMPLETED"),
                        ("Match 1", "PLAYOFF", "UPPER", 2, grid.get("H5"), grid.get("H7"), 2, 0, "ROPH", "BOOM", "COMPLETED"),
                        ("Qualified 2", "QUALIFIED", "QUALIFIER", 3, grid.get("C13"), grid.get("C15"), 1, 2, "FLCP", "ONPH", "COMPLETED"),
                        ("Match 2", "PLAYOFF", "UPPER", 4, grid.get("H13"), grid.get("H15"), 2, 0, "TLPH", "FLCP", "COMPLETED"),
                        ("Final Upper", "PLAYOFF", "UPPER", 5, grid.get("M9"), grid.get("M11"), 1, 2, "TLPH", "ROPH", "COMPLETED"),
                        ("Match 4", "PLAYOFF", "LOWER", 6, grid.get("H22"), grid.get("H24"), 0, 2, "FLCP", "BOOM", "COMPLETED"),
                        ("Final Lower", "PLAYOFF", "LOWER", 7, grid.get("R22"), grid.get("R24"), 2, 1, "ROPH", "FLCP", "COMPLETED"),
                        ("Grand Final", "PLAYOFF", "FINAL", 8, grid.get("R9"), grid.get("R11"), 2, 0, "TLPH", "ROPH", "COMPLETED"),
                    ]
                    for m in m_defs:
                        c.execute("""
                            INSERT INTO matches (tournament_id, stage, round_name, bracket_type, match_order, team1_id, team2_id, score1, score2, winner_id, loser_id, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (t_id, m[1], m[0], m[2], m[3], m[4], m[5], m[6], m[7], m[8], m[9], m[10]))
                else:
                    def get_m_s1(rname, st, br, ord_num, t1_c, t2_c, s1_c, s2_c):
                        t1 = grid.get(t1_c)
                        t2 = grid.get(t2_c)
                        s1 = int(grid[s1_c]) if grid.get(s1_c, '').isdigit() else None
                        s2 = int(grid[s2_c]) if grid.get(s2_c, '').isdigit() else None
                        w = t1 if s1 is not None and s2 is not None and s1 > s2 else (t2 if s2 is not None and s1 is not None and s2 > s1 else None)
                        l = t2 if w == t1 else t1
                        return (rname, st, br, ord_num, t1, t2, s1, s2, w, l, 'COMPLETED')
                    
                    m_defs = [
                        get_m_s1("Match 1", "PLAYOFF", "UPPER", 1, "B5", "B6", "C5", "C6"),
                        get_m_s1("Match 2", "PLAYOFF", "UPPER", 2, "B9", "B10", "C9", "C10"),
                        get_m_s1("Final Upper", "PLAYOFF", "UPPER", 3, "E7", "E8", "F7", "F8"),
                        get_m_s1("Match 4", "PLAYOFF", "LOWER", 4, "B15", "B16", "C15", "C16"),
                        get_m_s1("Final Lower", "PLAYOFF", "LOWER", 5, "K16", "K17", "L16", "L17"),
                        get_m_s1("Grand Final", "PLAYOFF", "FINAL", 6, "K7", "K8", "L7", "L8"),
                    ]
                    for m in m_defs:
                        c.execute("""
                            INSERT INTO matches (tournament_id, stage, round_name, bracket_type, match_order, team1_id, team2_id, score1, score2, winner_id, loser_id, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (t_id, m[1], m[0], m[2], m[3], m[4], m[5], m[6], m[7], m[8], m[9], m[10]))

    # MSL matches
    msl_dir = os.path.join(ROOT_EXCEL_DIR, "MSL Championship")
    for f in sorted(os.listdir(msl_dir)):
        if f.endswith('.xlsx'):
            t_id = f.replace('.xlsx', '').split('-')[0].strip()
            fpath = os.path.join(msl_dir, f)
            with zipfile.ZipFile(fpath, 'r') as z:
                ss = get_shared_strings(z)
                wb = ET.fromstring(z.read('xl/workbook.xml'))
                rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
                rel_map = {rel.attrib['Id']: rel.attrib['Target'] for rel in rels.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship')}
                for sheet in wb.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet'):
                    if sheet.attrib.get('name') == 'Playoff':
                        target = 'xl/' + rel_map[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
                        grid = read_sheet(z, target, ss)
                        
                        def get_msl_m(rname, br, ord_num, t1_c, t2_c, s1_c, s2_c):
                            t1 = grid.get(t1_c)
                            t2 = grid.get(t2_c)
                            s1 = int(grid[s1_c]) if grid.get(s1_c, '').isdigit() else None
                            s2 = int(grid[s2_c]) if grid.get(s2_c, '').isdigit() else None
                            w = t1 if s1 is not None and s2 is not None and s1 > s2 else (t2 if s2 is not None and s1 is not None and s2 > s1 else None)
                            l = t2 if w == t1 else t1
                            return (rname, "PLAYOFF", br, ord_num, t1, t2, s1, s2, w, l, 'COMPLETED')
                        
                        msl_m = [
                            get_msl_m("Match 1", "UPPER", 1, "B6", "B7", "C6", "C7"),
                            get_msl_m("Match 2", "UPPER", 2, "B10", "B11", "C10", "C11"),
                            get_msl_m("Match 3", "UPPER", 3, "B14", "B15", "C14", "C15"),
                            get_msl_m("Match 4", "UPPER", 4, "B18", "B19", "C18", "C19"),
                            get_msl_m("Match 5", "UPPER", 5, "E9", "E10", "F9", "F10"),
                            get_msl_m("Match 6", "UPPER", 6, "E14", "E15", "F14", "F15"),
                            get_msl_m("Upper Final", "UPPER", 7, "H12", "H13", "I12", "I13"),
                            get_msl_m("Match 7", "LOWER", 8, "B25", "B26", "C25", "C26"),
                            get_msl_m("Match 8", "LOWER", 9, "B30", "B31", "C30", "C31"),
                            get_msl_m("Match 9", "LOWER", 10, "E25", "E26", "F25", "F26"),
                            get_msl_m("Match 10", "LOWER", 11, "E30", "E31", "F30", "F31"),
                            get_msl_m("Lower Semifinal", "LOWER", 12, "H27", "H28", "I27", "I28"),
                            get_msl_m("Lower Final", "LOWER", 13, "P27", "P28", "Q27", "Q28"),
                            get_msl_m("Grand Final", "FINAL", 14, "P12", "P13", "Q12", "Q13"),
                        ]
                        for m in msl_m:
                            if m[4] and m[5]:
                                c.execute("""
                                    INSERT INTO matches (tournament_id, stage, round_name, bracket_type, match_order, team1_id, team2_id, score1, score2, winner_id, loser_id, status)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (t_id, m[1], m[0], m[2], m[3], m[4], m[5], m[6], m[7], m[8], m[9], m[10]))

    # M-Series Playoff matches
    m_dir = os.path.join(ROOT_EXCEL_DIR, "M Championship")
    for f in sorted(os.listdir(m_dir)):
        if f.endswith('.xlsx'):
            t_id = f.replace('.xlsx', '').split('-')[0].strip()
            m_num = int(t_id[1]) if len(t_id) > 1 and t_id[1].isdigit() else 1
            tourney_id = f"M{m_num}"
            fpath = os.path.join(m_dir, f)
            with zipfile.ZipFile(fpath, 'r') as z:
                ss = get_shared_strings(z)
                wb = ET.fromstring(z.read('xl/workbook.xml'))
                rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
                rel_map = {rel.attrib['Id']: rel.attrib['Target'] for rel in rels.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship')}
                for sheet in wb.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet'):
                    if sheet.attrib.get('name') == 'Playoff':
                        target = 'xl/' + rel_map[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
                        grid = read_sheet(z, target, ss)
                        
                        def get_m_playoff(rname, br, ord_num, t1_c, t2_c, s1_c, s2_c):
                            t1 = grid.get(t1_c)
                            t2 = grid.get(t2_c)
                            s1 = int(grid[s1_c]) if grid.get(s1_c, '').isdigit() else None
                            s2 = int(grid[s2_c]) if grid.get(s2_c, '').isdigit() else None
                            w = t1 if s1 is not None and s2 is not None and s1 > s2 else (t2 if s2 is not None and s1 is not None and s2 > s1 else None)
                            l = t2 if w == t1 else t1
                            return (rname, "PLAYOFF", br, ord_num, t1, t2, s1, s2, w, l, 'COMPLETED')
                        
                        m_playoff = [
                            get_m_playoff("Match 1", "UPPER", 1, "B6", "B7", "C6", "C7"),
                            get_m_playoff("Match 2", "UPPER", 2, "B10", "B11", "C10", "C11"),
                            get_m_playoff("Match 3", "UPPER", 3, "B14", "B15", "C14", "C15"),
                            get_m_playoff("Match 4", "UPPER", 4, "B18", "B19", "C18", "C19"),
                            get_m_playoff("Match 5", "UPPER", 5, "E9", "E10", "F9", "F10"),
                            get_m_playoff("Match 6", "UPPER", 6, "E14", "E15", "F14", "F15"),
                            get_m_playoff("Upper Final", "UPPER", 7, "H12", "H13", "I12", "I13"),
                            get_m_playoff("Match 7", "LOWER", 8, "B25", "B26", "C25", "C26"),
                            get_m_playoff("Match 8", "LOWER", 9, "B30", "B31", "C30", "C31"),
                            get_m_playoff("Match 9", "LOWER", 10, "E25", "E26", "F25", "F26"),
                            get_m_playoff("Match 10", "LOWER", 11, "E30", "E31", "F30", "F31"),
                            get_m_playoff("Lower Semifinal", "LOWER", 12, "H27", "H28", "I27", "I28"),
                            get_m_playoff("Lower Final", "LOWER", 13, "P27", "P28", "Q27", "Q28"),
                            get_m_playoff("Grand Final", "FINAL", 14, "P12", "P13", "Q12", "Q13"),
                        ]
                        for m in m_playoff:
                            if m[4] and m[5]:
                                c.execute("""
                                    INSERT INTO matches (tournament_id, stage, round_name, bracket_type, match_order, team1_id, team2_id, score1, score2, winner_id, loser_id, status)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (tourney_id, m[1], m[0], m[2], m[3], m[4], m[5], m[6], m[7], m[8], m[9], m[10]))

    # Normalisasi kode tim Excel -> ID tim database
    for old, new in TEAM_ALIASES.items():
        for col in ("team1_id", "team2_id", "winner_id", "loser_id"):
            c.execute(f"UPDATE matches SET {col}=? WHERE {col}=?", (new, old))
        for col in ("winner_id", "runner_up_id", "third_place_id", "fourth_place_id"):
            c.execute(f"UPDATE tournaments SET {col}=? WHERE {col}=?", (new, old))

    conn.commit()
    conn.close()

    # Import Swiss Stage M1-M3 + koreksi peringkat 3/4 sesuai Excel (juga menghitung ulang standing & slot)
    from import_swiss_and_fix_m import run_import
    run_import()

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT count(*) FROM matches")
    matches_count = c.fetchone()[0]
    conn.close()
    print(f"Seed completed! Inserted {matches_count} matches into database.")

if __name__ == "__main__":
    run_seed()
