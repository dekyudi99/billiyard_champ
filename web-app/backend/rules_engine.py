import sqlite3
import json

TROPHY_DEFINITIONS = {
    'M_SERIES': {
        1: {'points': 1500, 'image': 'trofi_m_championship.png', 'title': 'Juara 1 M World Championship', 'field': 'trofi_m_1st'},
        2: {'points': 1000, 'image': 'runner_up_m_championship.png', 'title': 'Runner-up M World Championship', 'field': 'trofi_m_2nd'},
        3: {'points': 750, 'image': '3rd_place_m_championship.png', 'title': 'Peringkat 3 M World Championship', 'field': 'trofi_m_3rd'},
        4: {'points': 500, 'image': '4rd_place_championship.png', 'title': 'Peringkat 4 M World Championship', 'field': 'trofi_m_4th'}
    },
    'MSL': {
        1: {'points': 1250, 'image': 'trofi_msl.png', 'title': 'Juara 1 MSL Championship', 'field': 'trofi_msl_1st'},
        2: {'points': 750, 'image': 'runner_up_msl.png', 'title': 'Runner-up MSL Championship', 'field': 'trofi_msl_2nd'},
        3: {'points': 500, 'image': 'msl_3rd_medal.png', 'title': 'Peringkat 3 MSL Championship', 'field': 'trofi_msl_3rd'}
    },
    'MPL': {
        1: {'points': 1000, 'image': 'trofi_mpl.png', 'title': 'Juara 1 MPL Regional', 'field': 'trofi_mpl_1st'},
        2: {'points': 500, 'image': 'runner_up_mpl.png', 'title': 'Runner-up MPL Regional', 'field': 'trofi_mpl_2nd'}
    }
}

def recalculate_all_time_standings(conn):
    """
    Recalculates all points, trophies, and rankings for teams and regions based on
    all completed tournaments in the database.
    Strictly: ONLY teams that won trophies receive points in Base Team & Base Region!
    """
    c = conn.cursor()
    
    # 1. Reset trophies history table
    c.execute("DELETE FROM trophies_history")
    
    # 2. Reset team data structure
    c.execute("SELECT id, region_id FROM teams")
    teams = {}
    for row in c.fetchall():
        teams[row['id']] = {
            'points': 0,
            'region': row['region_id'],
            'trofi_m_1st': 0,
            'trofi_m_2nd': 0,
            'trofi_m_3rd': 0,
            'trofi_m_4th': 0,
            'trofi_msl_1st': 0,
            'trofi_msl_2nd': 0,
            'trofi_msl_3rd': 0,
            'trofi_mpl_1st': 0,
            'trofi_mpl_2nd': 0,
            'trophies_detail': []
        }
    
    # 3. Iterate through all completed tournaments
    c.execute("SELECT id, name, type, season, region_id, winner_id, runner_up_id, third_place_id, fourth_place_id FROM tournaments WHERE status='COMPLETED' ORDER BY season ASC, type ASC")
    tournaments = c.fetchall()
    
    region_m_points = {r: 0 for r in ['MEA', 'PEL', 'ID', 'SEA', 'PH', 'MY', 'AM']}
    region_msl_points = {r: 0 for r in ['MEA', 'PEL', 'ID', 'SEA', 'PH', 'MY', 'AM']}
    
    for t in tournaments:
        t_id = t['id']
        t_name = t['name']
        t_type = t['type']
        season = t['season']
        
        placements = [
            (1, t['winner_id']),
            (2, t['runner_up_id']),
            (3, t['third_place_id']),
            (4, t['fourth_place_id'])
        ]
        
        if t_type in TROPHY_DEFINITIONS:
            for place, team_id in placements:
                if team_id and place in TROPHY_DEFINITIONS[t_type]:
                    t_info = TROPHY_DEFINITIONS[t_type][place]
                    pts = t_info['points']
                    img = t_info['image']
                    title = f"{t_info['title']} ({t_name})"
                    
                    if team_id in teams:
                        teams[team_id]['points'] += pts
                        teams[team_id][t_info['field']] += 1
                        teams[team_id]['trophies_detail'].append({
                            'season': season,
                            'tournament_id': t_id,
                            'tournament_name': t_name,
                            'tournament_type': t_type,
                            'placement': place,
                            'points': pts,
                            'image': img,
                            'title': title
                        })
                        
                        reg = teams[team_id]['region']
                        if t_type == 'M_SERIES':
                            region_m_points[reg] = region_m_points.get(reg, 0) + pts
                        elif t_type == 'MSL':
                            region_msl_points[reg] = region_msl_points.get(reg, 0) + pts
                            
                        # Insert into trophies_history table
                        c.execute("""
                            INSERT INTO trophies_history (season, tournament_id, tournament_name, tournament_type, placement, team_id, region_id, points, trophy_image, trophy_title)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (season, t_id, t_name, t_type, place, team_id, reg, pts, img, title))

    # 4. Update Teams Table
    # Sort teams by points, then M_1st, MSL_1st, MPL_1st
    sorted_teams = sorted(teams.items(), key=lambda x: (x[1]['points'], x[1]['trofi_m_1st'], x[1]['trofi_msl_1st'], x[1]['trofi_mpl_1st']), reverse=True)
    for rank, (tid, data) in enumerate(sorted_teams, 1):
        c.execute("""
            UPDATE teams 
            SET points = ?, rank = ?,
                trofi_m_1st = ?, trofi_m_2nd = ?, trofi_m_3rd = ?, trofi_m_4th = ?,
                trofi_msl_1st = ?, trofi_msl_2nd = ?, trofi_msl_3rd = ?,
                trofi_mpl_1st = ?, trofi_mpl_2nd = ?,
                trophies_detail = ?
            WHERE id = ?
        """, (
            data['points'], rank,
            data['trofi_m_1st'], data['trofi_m_2nd'], data['trofi_m_3rd'], data['trofi_m_4th'],
            data['trofi_msl_1st'], data['trofi_msl_2nd'], data['trofi_msl_3rd'],
            data['trofi_mpl_1st'], data['trofi_mpl_2nd'],
            json.dumps(data['trophies_detail']), tid
        ))

    # 5. Update Regions Table
    c.execute("SELECT id, comp_points FROM regions")
    reg_rows = c.fetchall()
    reg_totals = []
    for r in reg_rows:
        rid = r['id']
        m_pts = region_m_points.get(rid, 0)
        msl_pts = region_msl_points.get(rid, 0)
        c_pts = r['comp_points']
        tot = m_pts + msl_pts + c_pts
        reg_totals.append((rid, m_pts, msl_pts, c_pts, tot))
        
    sorted_regs = sorted(reg_totals, key=lambda x: x[4], reverse=True)
    for rank, (rid, m_pts, msl_pts, c_pts, tot) in enumerate(sorted_regs, 1):
        c.execute("""
            UPDATE regions
            SET m_points = ?, msl_points = ?, total_points = ?, rank = ?
            WHERE id = ?
        """, (m_pts, msl_pts, tot, rank, rid))

    conn.commit()


def update_road_to_world_slots(conn, current_season=4):
    """
    Evaluates Season qualification slots for M-Championship (M4) and MSL Championship (MSL S4).
    Rules:
    - M Championship (16 slots):
      1. Slots 1-14: Champions (#1) and Runner-ups (#2) of all 7 MPL regions (AM, ID, MEA, MY, PEL, PH, SEA).
      2. Slot 15: Ditentukan oleh Juara 1 M-Championship sebelumnya (Reward Juara 1 M3: T1 dari PEL -> PEL #3: DRX).
      3. Slot 16: Juara 1 dari MSL Championship Season 4 (MSL #1).
    - MSL Championship (8 slots):
      1. 7 slot dasar dari peringkat 3 liga regional MPL.
         Khusus region Juara 1 M-Championship (PEL), karena #3 sudah promosi ke M4, mengirim Peringkat 4 (IHC).
      2. Slot ke-8 (Slot Ekstra MSL):
         DITENTUKAN OLEH PERINGKAT 2 (RUNNER-UP) M-CHAMPIONSHIP SEBELUMNYA!
         Di M3 Runner-up adalah IHC yang KEBETULAN SAMA-SAMA DARI REGION PEL.
         Karena Juara 1 & 2 M3 sama-sama dari PEL, slot PEL jadi melimpah dan mengirim Peringkat 5 (DK / Dplus KIA)!
    """
    c = conn.cursor()
    
    # Get Defending Champions info
    c.execute("SELECT key, value FROM system_settings")
    settings = {row['key']: row['value'] for row in c.fetchall()}
    
    m_1st_region = settings.get('defending_m_champ_1st_region', 'PEL')
    m_2nd_region = settings.get('defending_m_champ_2nd_region', 'PEL')
    
    # Hanya hapus slot milik season yang sedang dihitung (riwayat season lain tetap aman)
    c.execute("DELETE FROM qualification_slots WHERE target_tournament IN (?, ?)",
              (f"M{current_season}", f"MSL_S{current_season}"))
    
    regions = ['AM', 'ID', 'MEA', 'MY', 'PEL', 'PH', 'SEA']
    mpl_results = {}
    for r in regions:
        c.execute("""
            SELECT id, status, winner_id, runner_up_id, third_place_id, fourth_place_id 
            FROM tournaments 
            WHERE type='MPL' AND region_id=? AND season=?
        """, (r, current_season))
        row = c.fetchone()
        if row:
            mpl_results[r] = {
                'status': row['status'],
                '1st': row['winner_id'],
                '2nd': row['runner_up_id'],
                '3rd': row['third_place_id'],
                '4th': row['fourth_place_id']
            }
        else:
            mpl_results[r] = {'status': 'UPCOMING', '1st': None, '2nd': None, '3rd': None, '4th': None}

    # Fetch MSL S4 Winner if completed
    c.execute("SELECT winner_id, status FROM tournaments WHERE type='MSL' AND season=?", (current_season,))
    msl_row = c.fetchone()
    msl_winner = msl_row['winner_id'] if msl_row and msl_row['status'] == 'COMPLETED' else None

    # 1. Populate M4 Slots (16 Slots)
    m4_slots = []
    for r in regions:
        w1 = mpl_results[r]['1st']
        w2 = mpl_results[r]['2nd']
        m4_slots.append({
            'slot_code': f"{r}_#1",
            'region_id': r,
            'team_id': w1,
            'description': f"Juara 1 MPL {r} Season {current_season}",
            'status': 'CONFIRMED' if w1 else 'PENDING'
        })
        m4_slots.append({
            'slot_code': f"{r}_#2",
            'region_id': r,
            'team_id': w2,
            'description': f"Runner-up MPL {r} Season {current_season}",
            'status': 'CONFIRMED' if w2 else 'PENDING'
        })
        
    # Slot 15: Defending World Champion 1st Place Region's 3rd place
    defending_m_3rd = mpl_results.get(m_1st_region, {}).get('3rd')
    m4_slots.append({
        'slot_code': f"{m_1st_region}_#3 (JUARA_1_M{current_season-1}_REWARD)",
        'region_id': m_1st_region,
        'team_id': defending_m_3rd,
        'description': f"Peringkat 3 Region Juara 1 Dunia M{current_season-1} ({m_1st_region})",
        'status': 'CONFIRMED' if defending_m_3rd else 'PENDING'
    })
    
    # Slot 16: MSL Champion
    m4_slots.append({
        'slot_code': "MSL_#1",
        'region_id': 'GLOBAL',
        'team_id': msl_winner,
        'description': f"Juara 1 MSL Championship Season {current_season}",
        'status': 'CONFIRMED' if msl_winner else 'PENDING'
    })

    for idx, s in enumerate(m4_slots, 1):
        c.execute("""
            INSERT INTO qualification_slots (target_tournament, slot_number, slot_code, region_id, team_id, description, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (f"M{current_season}", idx, s['slot_code'], s['region_id'], s['team_id'], s['description'], s['status']))

    # 2. Populate MSL S4 Slots (8 Slots)
    msl_slots = []
    for r in regions:
        if r == m_1st_region:
            team_4th = mpl_results[r]['4th']
            msl_slots.append({
                'slot_code': f"{r}_#4 (PENGGANTI_M4)",
                'region_id': r,
                'team_id': team_4th,
                'description': f"Peringkat 4 MPL {r} (Pengganti kuota #3 yang promosi ke M{current_season})",
                'status': 'CONFIRMED' if team_4th else 'PENDING'
            })
        else:
            team_3rd = mpl_results[r]['3rd']
            msl_slots.append({
                'slot_code': f"{r}_#3",
                'region_id': r,
                'team_id': team_3rd,
                'description': f"Peringkat 3 MPL {r} Season {current_season}",
                'status': 'CONFIRMED' if team_3rd else 'PENDING'
            })
            
    # Slot 8: Determined by Runner-up (2nd Place) of previous M-Championship!
    extra_team = None
    extra_desc = ""
    extra_code = ""
    
    if m_1st_region == m_2nd_region:
        # Juara 1 & 2 dari region sama: slot melimpah -> Peringkat 5 region tsb.
        # Peringkat 5 tidak tersimpan di data turnamen, jadi ditentukan lewat pengaturan 'msl_extra_team'.
        extra_team = settings.get('msl_extra_team') or None
        extra_desc = f"Slot Ekstra Peringkat 2 M{current_season-1}: Peringkat 5 Region {m_2nd_region} (Slot Melimpah karena Juara 1 & 2 M{current_season-1} dari Region Sama)"
        extra_code = f"{m_2nd_region}_#5 (JUARA_2_M{current_season-1}_REWARD)"
    else:
        extra_team = mpl_results.get(m_2nd_region, {}).get('4th')
        extra_desc = f"Slot Ekstra Peringkat 2 M{current_season-1}: Peringkat 4 Region {m_2nd_region}"
        extra_code = f"{m_2nd_region}_#4 (JUARA_2_M{current_season-1}_REWARD)"

    msl_slots.append({
        'slot_code': extra_code,
        'region_id': m_2nd_region,
        'team_id': extra_team,
        'description': extra_desc,
        'status': 'CONFIRMED' if extra_team else 'PENDING'
    })

    for idx, s in enumerate(msl_slots, 1):
        c.execute("""
            INSERT INTO qualification_slots (target_tournament, slot_number, slot_code, region_id, team_id, description, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (f"MSL_S{current_season}", idx, s['slot_code'], s['region_id'], s['team_id'], s['description'], s['status']))

    conn.commit()


def get_season_workflow_status(conn, season_num):
    """
    Checks the exact sequence of tournaments for a given season:
    Phase 1: MPL (all 7 must be completed)
    Phase 2: MSL (only after all 7 MPLs are completed)
    Phase 3: M-Championship (only after MSL and all MPLs are completed)
    Guarantees no tournament is held twice in 1 season.
    """
    c = conn.cursor()
    
    # 1. Check all 7 MPLs
    c.execute("SELECT id, region_id, status, winner_id FROM tournaments WHERE type='MPL' AND season=?", (season_num,))
    mpl_tourneys = [dict(row) for row in c.fetchall()]
    mpl_completed = len([t for t in mpl_tourneys if t['status'] == 'COMPLETED'])
    all_mpl_done = (len(mpl_tourneys) == 7 and mpl_completed == 7)
    
    # 2. Check MSL
    c.execute("SELECT id, status, winner_id FROM tournaments WHERE type='MSL' AND season=?", (season_num,))
    msl_tourney = c.fetchone()
    msl_exists = msl_tourney is not None
    msl_done = msl_tourney['status'] == 'COMPLETED' if msl_tourney else False
    
    # 3. Check M-Series
    c.execute("SELECT id, status, winner_id FROM tournaments WHERE type='M_SERIES' AND season=?", (season_num,))
    m_tourney = c.fetchone()
    m_exists = m_tourney is not None
    m_done = m_tourney['status'] == 'COMPLETED' if m_tourney else False
    
    # Current Phase Calculation
    current_phase = 1
    if all_mpl_done:
        if msl_done:
            if m_done:
                current_phase = 4 # Season Completed!
            else:
                current_phase = 3 # Ready for M-Championship
        else:
            current_phase = 2 # Ready for MSL
            
    return {
        'season': season_num,
        'current_phase': current_phase,
        'phase_name': ['MPL Regional Leagues', 'MSL Championship', 'M World Championship', 'Season Completed'][current_phase-1],
        'all_mpl_done': all_mpl_done,
        'mpl_completed_count': mpl_completed,
        'total_mpl_required': 7,
        'mpl_tournaments': mpl_tourneys,
        'msl_exists': msl_exists,
        'msl_done': msl_done,
        'msl_tournament': dict(msl_tourney) if msl_tourney else None,
        'm_exists': m_exists,
        'm_done': m_done,
        'm_tournament': dict(m_tourney) if m_tourney else None,
        'can_start_msl': all_mpl_done and not msl_done,
        'can_start_m': all_mpl_done and msl_done and not m_done,
        'can_start_next_season': all_mpl_done and msl_done and m_done
    }
