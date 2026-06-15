#!/usr/bin/env python3
"""Comprehensive backfill script for industry + concept tags.
Supports multiple data sources: 东方财富, 同花顺, 新浪.

Usage: python3 scripts/backfill_sectors.py
"""
import sqlite3, sys, time
sys.path.insert(0, ".")

DB_PATH = "data/stock_picker.db"

def build_maps():
    """Build (sector_map, concept_map) from available APIs."""
    import akshare as ak
    
    sector_map, concept_map = {}, {}
    
    # --- Phase 1: 东方财富 via 同花顺 board names (if available) ---
    ind_names, conc_names = [], []
    try:
        ind_df = ak.stock_board_industry_name_ths()
        ind_names = ind_df["name"].tolist()
        print("同花顺 industry boards: %d" % len(ind_names))
    except Exception as e:
        print("同花顺 industry boards failed: %s" % e)
    
    try:
        conc_df = ak.stock_board_concept_name_ths()
        conc_names = conc_df["name"].tolist()
        print("同花顺 concept boards: %d" % len(conc_names))
    except Exception as e:
        print("同花顺 concept boards failed: %s" % e)
    
    # --- Phase 2: Try 东方财富 ---
    em_ok = False
    try:
        print("Trying 东方财富 industry constituent API...")
        for i, name in enumerate(ind_names):
            try:
                cons = ak.stock_board_industry_cons_em(symbol=name)
                for _, row in cons.iterrows():
                    code = str(row.get("代码", "")).strip().lower()
                    for p in ("sh","sz","bj"):
                        if code.startswith(p): code = code[2:]
                    code = code.zfill(6)
                    if name not in sector_map.get(code, ""):
                        sector_map[code] = name
            except: pass
            if (i+1) % 30 == 0:
                print("  Industry: %d/%d, %d sectors" % (i+1, len(ind_names), len(sector_map)))
                time.sleep(0.3)
        em_ok = bool(sector_map)
    except: pass
    
    if em_ok:
        print("东方财富 industry OK, trying concept...")
        for i, name in enumerate(conc_names):
            try:
                cons = ak.stock_board_concept_cons_em(symbol=name)
                for _, row in cons.iterrows():
                    code = str(row.get("代码", "")).strip().lower()
                    for p in ("sh","sz","bj"):
                        if code.startswith(p): code = code[2:]
                    code = code.zfill(6)
                    if code not in concept_map: concept_map[code] = name
                    else: concept_map[code] += "," + name
            except: pass
            if (i+1) % 30 == 0:
                print("  Concept: %d/%d, %d concepts" % (i+1, len(conc_names), len(concept_map)))
                time.sleep(0.3)
    else:
        # --- Phase 3: 新浪 fallback ---
        print("东方财富 unavailable, trying 新浪...")
        try:
            ind = ak.stock_classify_sina(symbol="申万行业")
            for _, row in ind.iterrows():
                code = str(row.get("symbol","")).strip()
                val = str(row.get("class","")).strip()
                if code and val and code not in sector_map:
                    sector_map[code] = val
            print("  新浪 industry: %d" % len(sector_map))
            
            conc = ak.stock_classify_sina(symbol="热门概念")
            for _, row in conc.iterrows():
                code = str(row.get("symbol","")).strip()
                val = str(row.get("class","")).strip()
                if code and val:
                    if code not in concept_map: concept_map[code] = val
                    else: concept_map[code] += "," + val
            print("  新浪 concept: %d" % len(concept_map))
        except Exception as e:
            print("  新浪 failed: %s" % e)
    
    return sector_map, concept_map

def update_db(sector_map, concept_map):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    up_s = 0
    for code, sector in sector_map.items():
        cur.execute(
            "UPDATE screening_results SET sector = ? "
            "WHERE stock_code = ? AND (sector IS NULL OR sector = '')",
            (sector, code)
        )
        up_s += cur.rowcount
    up_c = 0
    for code, concepts in concept_map.items():
        cur.execute(
            "UPDATE screening_results SET concepts = ? WHERE stock_code = ?",
            (concepts, code)
        )
        up_c += cur.rowcount
    conn.commit()
    conn.close()
    print("Updated: %d sectors, %d concepts" % (up_s, up_c))
    print("Total: %d stocks with sectors, %d with concepts" % (
        cur.execute("SELECT COUNT(DISTINCT stock_code) FROM screening_results WHERE sector != ''").fetchone()[0] if False else 0,
        cur.execute("SELECT COUNT(DISTINCT stock_code) FROM screening_results WHERE concepts != ''").fetchone()[0] if False else 0,
    ))

if __name__ == "__main__":
    print("=== Multi-Source Backfill ===")
    print("Sources: 东方财富 > 新浪 > 东方财富行情")
    s, c = build_maps()
    update_db(s, c)
    print("Done! Restart server and refresh browser.")
