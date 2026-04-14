"""
CMMS Database Manager
SQLite-based persistence layer for all CMMS data.

Author: Wassim BELAID
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import json
import random


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "cmms.db")


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """Create all tables and seed with realistic data."""
    conn = get_connection()
    c = conn.cursor()

    # ── EQUIPMENT TABLE ───────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS equipment (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        equipment_type TEXT NOT NULL,
        manufacturer TEXT,
        model TEXT,
        serial_number TEXT,
        zone TEXT NOT NULL,
        location TEXT,
        criticality TEXT NOT NULL,
        installation_date TEXT,
        nominal_power_kw REAL,
        nominal_speed_rpm REAL,
        nominal_voltage_v REAL,
        nominal_current_a REAL,
        maintenance_interval_hours REAL,
        current_run_hours REAL DEFAULT 0,
        total_run_hours REAL DEFAULT 0,
        health_pct REAL DEFAULT 100,
        status TEXT DEFAULT 'operational',
        last_maintenance_date TEXT,
        next_maintenance_date TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── WORK ORDERS TABLE ─────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS work_orders (
        id TEXT PRIMARY KEY,
        equipment_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        wo_type TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        scheduled_date TEXT,
        started_at TEXT,
        completed_at TEXT,
        due_date TEXT,
        assigned_to TEXT,
        created_by TEXT DEFAULT 'System',
        estimated_hours REAL DEFAULT 2,
        actual_hours REAL DEFAULT 0,
        estimated_cost_eur REAL DEFAULT 0,
        actual_cost_eur REAL DEFAULT 0,
        fault_type TEXT DEFAULT 'none',
        risk_score REAL DEFAULT 0,
        resolution TEXT,
        failure_cause TEXT,
        corrective_actions TEXT,
        spare_parts_used TEXT,
        is_overdue INTEGER DEFAULT 0,
        FOREIGN KEY (equipment_id) REFERENCES equipment(id)
    )""")

    # ── MAINTENANCE PLANS TABLE ───────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS maintenance_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_id TEXT NOT NULL,
        plan_name TEXT NOT NULL,
        plan_type TEXT NOT NULL,
        description TEXT,
        interval_hours REAL,
        interval_days INTEGER,
        estimated_duration_hours REAL DEFAULT 2,
        estimated_cost_eur REAL DEFAULT 200,
        required_skills TEXT,
        required_tools TEXT,
        spare_parts_needed TEXT,
        safety_precautions TEXT,
        procedure TEXT,
        last_performed TEXT,
        next_due TEXT,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (equipment_id) REFERENCES equipment(id)
    )""")

    # ── MAINTENANCE HISTORY TABLE ─────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS maintenance_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_id TEXT NOT NULL,
        work_order_id TEXT,
        maintenance_type TEXT NOT NULL,
        performed_at TEXT NOT NULL,
        performed_by TEXT NOT NULL,
        duration_hours REAL,
        cost_eur REAL DEFAULT 0,
        description TEXT,
        actions_taken TEXT,
        parts_replaced TEXT,
        condition_before TEXT,
        condition_after TEXT,
        vibration_before REAL,
        vibration_after REAL,
        temperature_before REAL,
        temperature_after REAL,
        hours_at_maintenance REAL,
        next_maintenance_due TEXT,
        FOREIGN KEY (equipment_id) REFERENCES equipment(id)
    )""")

    # ── SPARE PARTS TABLE ─────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS spare_parts (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        part_number TEXT,
        manufacturer TEXT,
        category TEXT,
        unit TEXT DEFAULT 'piece',
        stock_quantity REAL DEFAULT 0,
        min_stock REAL DEFAULT 1,
        max_stock REAL DEFAULT 10,
        reorder_point REAL DEFAULT 2,
        unit_cost_eur REAL DEFAULT 0,
        location TEXT,
        supplier TEXT,
        lead_time_days INTEGER DEFAULT 14,
        compatible_equipment TEXT,
        last_updated TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── STOCK MOVEMENTS TABLE ─────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        part_id TEXT NOT NULL,
        movement_type TEXT NOT NULL,
        quantity REAL NOT NULL,
        work_order_id TEXT,
        equipment_id TEXT,
        performed_by TEXT,
        unit_cost_eur REAL DEFAULT 0,
        notes TEXT,
        performed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (part_id) REFERENCES spare_parts(id)
    )""")

    # ── TECHNICIANS TABLE ─────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS technicians (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        specialization TEXT,
        certifications TEXT,
        available INTEGER DEFAULT 1,
        current_workload_hours REAL DEFAULT 0,
        phone TEXT,
        email TEXT
    )""")

    # ── KPI SNAPSHOTS TABLE ───────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS kpi_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
        equipment_id TEXT,
        oee REAL,
        availability REAL,
        performance REAL,
        quality REAL,
        mtbf_hours REAL,
        mttr_hours REAL,
        planned_maintenance_pct REAL,
        total_cost_eur REAL,
        corrective_cost_eur REAL,
        preventive_cost_eur REAL
    )""")

    conn.commit()

    # ── SEED DATA ─────────────────────────────────────────────────────────────
    _seed_equipment(c)
    _seed_technicians(c)
    _seed_spare_parts(c)
    _seed_maintenance_plans(c)
    _seed_maintenance_history(c)
    _seed_work_orders(c)
    _seed_stock_movements(c)

    conn.commit()
    conn.close()


def _seed_equipment(c):
    if c.execute("SELECT COUNT(*) FROM equipment").fetchone()[0] > 0:
        return

    equipment_data = [
        ("E001", "Compressor A",    "Centrifugal Compressor", "Atlas Copco", "GA75",   "SN-2019-001", "Zone A", "Building 1, Row A", "critical", "2019-03-15", 75,   2980, 400, 145, 2000, 1243, 5800,  78,  "operational",  "2024-10-15", "2025-04-15", "Primary air compressor"),
        ("E002", "Pump B",          "Centrifugal Pump",       "Grundfos",    "NB80",   "SN-2020-002", "Zone B", "Building 2, Row B", "high",     "2020-06-20", 45,   1480, 400, 92,  3000, 823,  3800,  85,  "operational",  "2024-12-01", "2025-06-01", "Process water pump"),
        ("E003", "Motor C",         "Induction Motor",        "ABB",         "M3BP",   "SN-2021-003", "Zone C", "Building 3, Row A", "high",     "2021-01-10", 30,   1470, 400, 62,  4000, 512,  2200,  92,  "operational",  "2025-01-20", "2025-07-20", "Conveyor drive motor"),
        ("E004", "Conveyor D",      "Belt Conveyor",          "Rexnord",     "FlatTop", "SN-2018-004", "Zone D", "Building 4, Row C", "medium",   "2018-09-05", 22,   960,  400, 48,  2500, 1876, 8200,  62,  "degraded",     "2024-09-01", "2025-01-15", "Main production conveyor"),
        ("E005", "Compressor E",    "Screw Compressor",       "Kaeser",      "SK19",   "SN-2022-005", "Zone A", "Building 1, Row B", "critical", "2022-04-01", 90,   2960, 400, 175, 2000, 298,  1200,  95,  "operational",  "2024-11-10", "2025-05-10", "Backup compressor"),
        ("E006", "Pump F",          "Gear Pump",              "Viking",      "K124",   "SN-2021-006", "Zone B", "Building 2, Row A", "high",     "2021-07-14", 55,   990,  400, 110, 3000, 634,  2800,  80,  "operational",  "2024-10-30", "2025-04-30", "Chemical transfer pump"),
        ("E007", "Heat Exchanger",  "Shell & Tube HEX",       "Alfa Laval",  "TL10",   "SN-2019-007", "Zone C", "Building 3, Row B", "medium",   "2019-11-22", 15,   0,    0,   0,   6000, 956,  4200,  88,  "operational",  "2024-08-15", "2025-08-15", "Process heat exchanger"),
        ("E008", "Fan H",           "Centrifugal Fan",        "Flakt Woods", "AXCBF",  "SN-2020-008", "Zone E", "Roof, Unit 1",      "low",      "2020-02-28", 11,   1480, 400, 23,  5000, 912,  4000,  75,  "degraded",     "2024-07-20", "2025-01-20", "Ventilation fan"),
    ]

    for eq in equipment_data:
        try:
            c.execute("""INSERT OR IGNORE INTO equipment VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""", eq)
        except Exception:
            pass


def _seed_technicians(c):
    if c.execute("SELECT COUNT(*) FROM technicians").fetchone()[0] > 0:
        return

    techs = [
        ("T001", "Ahmed Belkacem",   "Electrical",  "IEC 60079, HV Permit", 1, 6,  "+213 555 001", "a.belkacem@sibea.dz"),
        ("T002", "Karim Mansouri",   "Mechanical",  "ISO 18001, Vibration", 1, 4,  "+213 555 002", "k.mansouri@sibea.dz"),
        ("T003", "Yacine Boudjedra", "Instrumentation", "ATEX, ISA",        1, 8,  "+213 555 003", "y.boudjedra@sibea.dz"),
        ("T004", "Mohamed Cherif",   "Mechanical",  "Hydraulics, Welding",  1, 2,  "+213 555 004", "m.cherif@sibea.dz"),
        ("T005", "Farid Oussedik",   "Electrical",  "VFD, PLC, SCADA",     1, 5,  "+213 555 005", "f.oussedik@sibea.dz"),
        ("T006", "Salim Rahmani",    "General",     "Rigging, Safety",      1, 3,  "+213 555 006", "s.rahmani@sibea.dz"),
    ]
    for t in techs:
        c.execute("INSERT OR IGNORE INTO technicians VALUES (?,?,?,?,?,?,?,?)", t)


def _seed_spare_parts(c):
    if c.execute("SELECT COUNT(*) FROM spare_parts").fetchone()[0] > 0:
        return

    parts = [
        ("SP001", "SKF 6205-2RS Bearing",     "Deep groove ball bearing 25×52×15mm", "6205-2RS",   "SKF",         "bearing",    "piece", 8,  2, 20, 4,  45.50,  "Store A, Shelf 1", "SKF Algeria", 14, "E001,E002,E003,E008"),
        ("SP002", "SKF 6308-2RS Bearing",     "Deep groove ball bearing 40×90×23mm", "6308-2RS",   "SKF",         "bearing",    "piece", 4,  1, 10, 2,  89.00,  "Store A, Shelf 1", "SKF Algeria", 14, "E001,E005"),
        ("SP003", "Shaft Seal 50×80×10",      "Radial shaft seal PTFE lip",          "TC50X80X10", "Freudenberg", "seal",       "piece", 6,  2, 15, 3,  12.80,  "Store A, Shelf 2", "Local Supply", 7,  "E002,E006"),
        ("SP004", "O-Ring Set NBR 70",        "Standard O-ring set 50 pieces",       "ORB-50",     "Parker",      "seal",       "set",   5,  1, 10, 2,  28.50,  "Store A, Shelf 2", "Parker Algeria", 21,"E001,E002,E005,E006"),
        ("SP005", "V-Belt B78",               "Classical V-belt B section",          "B78",        "Gates",       "belt",       "piece", 12, 3, 20, 5,  18.00,  "Store B, Shelf 1", "Local Supply", 3,  "E003,E004,E008"),
        ("SP006", "Coupling Insert GR38",     "Elastomeric coupling element",        "GR38-98",    "Rexnord",     "coupling",   "piece", 4,  1, 8,  2,  67.50,  "Store B, Shelf 2", "Rexnord EU",  28, "E001,E002,E005"),
        ("SP007", "Oil Filter C1040",         "Hydraulic oil filter element",        "C1040",      "Parker",      "filter",     "piece", 10, 3, 20, 4,  23.40,  "Store B, Shelf 3", "Parker Algeria", 14,"E001,E005"),
        ("SP008", "Air Filter AF-75",         "Compressor air intake filter",        "AF-75",      "Atlas Copco", "filter",     "piece", 6,  2, 12, 3,  145.00, "Store C, Shelf 1", "Atlas Copco",  21, "E001,E005"),
        ("SP009", "Temperature Sensor PT100", "RTD PT100 class A 1/3 DIN",          "PT100-3W",   "Endress+H",   "instrument", "piece", 5,  2, 10, 3,  78.00,  "Store C, Shelf 2", "E+H Algeria",  14, "E001,E002,E003"),
        ("SP010", "Pressure Gauge 0-16bar",   "SS Bourdon tube pressure gauge",      "PG-16",      "Wika",        "instrument", "piece", 8,  2, 15, 3,  42.00,  "Store C, Shelf 2", "Wika Algeria", 14, "E001,E002,E005,E006"),
        ("SP011", "Vibration Sensor ICP",     "Accelerometer 100mV/g top exit",     "PCB-608",    "PCB",         "instrument", "piece", 3,  1, 6,  2,  285.00, "Store C, Shelf 3", "PCB Europe",   30, "E001,E002,E003,E004"),
        ("SP012", "Impeller D=200mm SS316",   "Centrifugal pump impeller stainless", "IMP-200",    "Grundfos",    "rotating",   "piece", 2,  1, 4,  1,  890.00, "Store D, Shelf 1", "Grundfos EU",  45, "E002,E006"),
        ("SP013", "Bearing Grease EP2",       "NLGI grade 2 extreme pressure grease","EP2-400g",   "Klüber",      "lubricant",  "kg",    25, 5, 50, 8,  8.50,   "Store D, Shelf 2", "Local Supply", 7,  "E001,E002,E003,E004,E005,E006,E008"),
        ("SP014", "Hydraulic Oil ISO46",      "Antiwear hydraulic oil ISO VG 46",    "AW46-20L",   "Total",       "lubricant",  "liter", 80, 20, 200,30, 3.20,   "Oil Store",        "Total DZ",     7,  "E001,E005"),
        ("SP015", "Contactor 75kW LC1D",      "Schneider 3P contactor 150A 380V",   "LC1D150",    "Schneider",   "electrical", "piece", 2,  1, 4,  1,  245.00, "Electrical Store", "Schneider DZ", 21, "E001,E005"),
        ("SP016", "Circuit Breaker 100A",     "Schneider NSX 100A 3P motor protect", "NSX100F",   "Schneider",   "electrical", "piece", 3,  1, 6,  2,  189.00, "Electrical Store", "Schneider DZ", 14, "E001,E002,E003"),
        ("SP017", "Belt Conveyor PVC 500mm",  "PVC conveyor belt B=500mm T=8mm",    "PVC-500",    "Siegling",    "conveyor",   "meter", 15, 5, 30, 6,  45.00,  "Store D, Shelf 3", "Siegling EU",  35, "E004"),
        ("SP018", "Carbon Brush 12.5×32mm",   "Carbon brush for slip ring motors",   "CB-1232",    "Schunk",      "electrical", "piece", 20, 4, 40, 6,  18.50,  "Electrical Store", "Schunk EU",    21, "E003,E008"),
        ("SP019", "Coupling Flange DN80",     "Pipe flange PN16 DN80 SS304",        "FL-80-16",   "Local",       "piping",     "piece", 4,  1, 8,  2,  35.00,  "Piping Store",     "Local Supply", 7,  "E002,E006"),
        ("SP020", "Gasket Set DN80 EPDM",     "Full face gasket DN80 EPDM 3mm",     "GK-80-EP",   "Klinger",     "piping",     "set",   10, 2, 20, 3,  12.50,  "Piping Store",     "Klinger EU",   21, "E002,E006"),
    ]

    for p in parts:
        c.execute("INSERT OR IGNORE INTO spare_parts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", p)


def _seed_maintenance_plans(c):
    if c.execute("SELECT COUNT(*) FROM maintenance_plans").fetchone()[0] > 0:
        return

    plans = [
        ("E001", "Compressor A — Weekly Inspection",   "preventive", "Weekly visual inspection, oil level, belt tension, filter check", 168,  7,   1.5,  50,   "Mechanical", "Inspection kit", "SP007,SP013",         "Lockout/Tagout required", "1. Check oil level\n2. Inspect belt tension\n3. Check filter ΔP\n4. Listen for unusual noise", "2025-03-25", "2025-04-01"),
        ("E001", "Compressor A — Monthly PM",          "preventive", "Monthly oil analysis, belt replacement if needed, full inspection", 720, 30,   4.0,  250,  "Mechanical", "Torque wrench, oil sampler", "SP005,SP007,SP013", "Lockout/Tagout, PPE required", "1. Drain oil sample\n2. Check all belts\n3. Clean cooler fins\n4. Check safety valves", "2025-03-01", "2025-04-01"),
        ("E001", "Compressor A — Annual Overhaul",     "preventive", "Full overhaul: bearings, seals, coupling, valve maintenance", 8760, 365,  16.0, 2500, "Mechanical,Electrical", "Full tool kit, crane", "SP001,SP002,SP003,SP004,SP006,SP008", "Hot work permit, confined space", "1. Full disassembly\n2. Inspect all internals\n3. Replace bearings\n4. Replace seals\n5. Dynamic balancing", "2024-04-01", "2025-04-01"),
        ("E002", "Pump B — Quarterly PM",              "preventive", "Seal check, bearing lubrication, impeller inspection",          2160, 90,   3.0,  180,  "Mechanical", "Standard tool kit", "SP003,SP013",         "Lockout/Tagout, drain pump", "1. Check shaft seal for leaks\n2. Grease bearings\n3. Check coupling alignment\n4. Measure vibration", "2024-12-01", "2025-03-01"),
        ("E002", "Pump B — Annual Inspection",         "preventive", "Full pump inspection, impeller wear check, clearance measurement", 8760, 365, 8.0, 1200, "Mechanical", "Dial gauge, feeler gauge", "SP003,SP012,SP013",  "Lockout/Tagout", "1. Disassemble pump\n2. Measure impeller wear\n3. Check wear rings\n4. Replace shaft seal", "2024-06-20", "2025-06-20"),
        ("E003", "Motor C — 6-Month PM",               "preventive", "Winding resistance, insulation resistance, bearing check",       4380, 180,  4.0,  300,  "Electrical,Mechanical", "Megohmmeter, vibration analyzer", "SP013,SP018", "Lockout/Tagout, arc flash PPE", "1. Megger test windings\n2. Check bearing play\n3. Clean cooling fins\n4. Tighten all terminals", "2025-01-20", "2025-07-20"),
        ("E004", "Conveyor D — Weekly Inspection",     "preventive", "Belt tension, roller condition, drive chain lubrication",        168,  7,   1.0,  40,   "Mechanical", "Belt tension gauge", "SP013",               "Guarding check required", "1. Check belt tension\n2. Inspect all rollers\n3. Lubricate drive chain\n4. Check belt alignment", "2025-03-25", "2025-04-01"),
        ("E004", "Conveyor D — Belt Replacement",      "corrective", "Replace worn belt — trigger when wear > 50%",                    2500, 0,    8.0,  800,  "Mechanical", "Belt tensioner, crane", "SP017",              "Full shutdown required", "1. Remove old belt\n2. Install new belt\n3. Set tension\n4. Run-in procedure", None, None),
        ("E005", "Compressor E — Monthly PM",          "preventive", "Monthly PM same as E001",                                        720,  30,   4.0,  250,  "Mechanical", "Standard kit", "SP007,SP013",           "Lockout/Tagout", "Same procedure as E001 monthly PM", "2025-03-10", "2025-04-10"),
        ("E008", "Fan H — Quarterly Balance Check",    "preventive", "Dynamic balance check, bearing inspection, belt check",          2190, 90,   3.0,  200,  "Mechanical", "Balance analyzer", "SP005,SP013",         "Work at height permit", "1. Measure vibration\n2. Dynamic balance if needed\n3. Check belt\n4. Grease bearings", "2025-01-20", "2025-04-20"),
    ]

    for p in plans:
        c.execute("""INSERT OR IGNORE INTO maintenance_plans 
            (equipment_id, plan_name, plan_type, description, interval_hours, interval_days, 
             estimated_duration_hours, estimated_cost_eur, required_skills, required_tools, 
             spare_parts_needed, safety_precautions, procedure, last_performed, next_due)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", p)


def _seed_maintenance_history(c):
    if c.execute("SELECT COUNT(*) FROM maintenance_history").fetchone()[0] > 0:
        return

    techs = ["Ahmed Belkacem", "Karim Mansouri", "Yacine Boudjedra", "Mohamed Cherif", "Farid Oussedik"]
    equipment = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008"]
    types = ["preventive", "preventive", "preventive", "corrective", "inspection"]

    random.seed(42)
    for i in range(48):
        eq = equipment[i % len(equipment)]
        mtype = random.choice(types)
        days_ago = random.randint(10, 365)
        performed_at = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M")
        cost = random.uniform(80, 2500) if mtype == "corrective" else random.uniform(50, 400)
        duration = random.uniform(1, 12) if mtype == "corrective" else random.uniform(0.5, 4)
        vib_before = random.uniform(1.5, 8.0)
        vib_after = vib_before * random.uniform(0.3, 0.9)
        temp_before = random.uniform(55, 95)
        temp_after = temp_before * random.uniform(0.7, 0.95)

        c.execute("""INSERT INTO maintenance_history 
            (equipment_id, maintenance_type, performed_at, performed_by, duration_hours, cost_eur,
             description, actions_taken, condition_before, condition_after,
             vibration_before, vibration_after, temperature_before, temperature_after,
             hours_at_maintenance)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            eq, mtype, performed_at, random.choice(techs),
            round(duration, 1), round(cost, 2),
            f"{'Scheduled PM' if mtype=='preventive' else 'Corrective maintenance'} on {eq}",
            "Inspection, lubrication, parts replacement as needed",
            "Degraded" if mtype == "corrective" else "Routine",
            "Good",
            round(vib_before, 2), round(vib_after, 2),
            round(temp_before, 1), round(temp_after, 1),
            round(random.uniform(100, 2000), 0)
        ))


def _seed_work_orders(c):
    if c.execute("SELECT COUNT(*) FROM work_orders").fetchone()[0] > 0:
        return

    wo_data = [
        # (id, eq_id, title, description, wo_type, priority, status, created_at, scheduled_date, started_at, completed_at, due_date, assigned_to, created_by, est_h, act_h, est_cost, act_cost, fault, risk, resolution, cause, parts, overdue)
        ("WO-2025-001","E004","Bearing replacement — Conveyor D","High vibration kurtosis>8. Replace SKF 6308-2RS.","corrective","emergency","in_progress","2025-03-28","2025-03-30",None,"2025-03-31","2025-03-31","Karim Mansouri","System",6,0,850,0,"bearing_fault",85,None,"Fatigue failure","SP002,SP013",1),
        ("WO-2025-002","E001","Monthly PM — Compressor A","Scheduled monthly PM: oil change, filter, belt.","preventive","medium","open","2025-04-01","2025-04-01",None,None,"2025-04-01","Ahmed Belkacem","Planner",4,0,250,0,"none",0,None,None,"SP007,SP013",0),
        ("WO-2025-003","E008","Imbalance correction — Fan H","AI detected imbalance. Schedule dynamic balancing.","predictive","high","open","2025-04-03","2025-04-03",None,None,"2025-04-05","Mohamed Cherif","ML System",3,0,350,0,"imbalance",72,None,None,"SP005",0),
        ("WO-2025-004","E002","Shaft seal replacement — Pump B","Visible oil leak on mechanical seal.","corrective","high","assigned","2025-03-29","2025-03-31",None,None,"2025-04-01","Yacine Boudjedra","Operator",4,0,420,0,"none",45,None,"Wear","SP003,SP004",0),
        ("WO-2025-005","E003","Insulation resistance test — Motor C","6-month electrical inspection. Megger test.","preventive","low","open","2025-04-10","2025-04-10",None,None,"2025-04-12","Farid Oussedik","Planner",3,0,200,0,"none",0,None,None,"",0),
        ("WO-2025-006","E006","Cavitation investigation — Pump F","AI detected cavitation. Check inlet pressure.","predictive","high","open","2025-04-02","2025-04-02",None,None,"2025-04-04","Karim Mansouri","ML System",5,0,580,0,"cavitation",68,None,None,"SP019,SP020",0),
        ("WO-2025-007","E001","Air filter replacement — Compressor A","Filter delta-P > 0.6 bar. Replace air filter.","preventive","medium","completed","2025-03-15","2025-03-15","2025-03-15","2025-03-15","2025-03-15","Salim Rahmani","Planner",1,1,145,145,"none",0,"Filter replaced OK",None,"SP008",0),
        ("WO-2025-008","E005","Annual overhaul — Compressor E","Annual overhaul: bearings, seals, valves.","preventive","planned","open","2025-06-15","2025-06-15",None,None,"2025-06-20","Ahmed Belkacem","Planner",16,0,3500,0,"none",0,None,None,"SP001,SP002,SP003",0),
        ("WO-2025-009","E004","Conveyor belt inspection","Belt wear marks at joints. Measure thickness.","inspection","medium","completed","2025-03-20","2025-03-20","2025-03-20","2025-03-20","2025-03-20","Mohamed Cherif","Operator",2,2,100,95,"none",0,"Belt OK 6mm remaining",None,"",0),
        ("WO-2025-010","E007","Heat exchanger cleaning","Fouling detected. Clean tube bundle.","preventive","low","open","2025-04-20","2025-04-20",None,None,"2025-04-22","Salim Rahmani","Planner",6,0,400,0,"fouling",35,None,None,"",0),
    ]

    for wo in wo_data:
        c.execute("""INSERT OR IGNORE INTO work_orders 
            (id, equipment_id, title, description, wo_type, priority, status,
             created_at, scheduled_date, started_at, completed_at, due_date,
             assigned_to, created_by, estimated_hours, actual_hours,
             estimated_cost_eur, actual_cost_eur, fault_type, risk_score,
             resolution, failure_cause, spare_parts_used, is_overdue)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", wo)


def _seed_stock_movements(c):
    if c.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] > 0:
        return

    random.seed(99)
    parts = ["SP001", "SP002", "SP003", "SP005", "SP007", "SP008", "SP013", "SP014"]
    techs = ["Ahmed Belkacem", "Karim Mansouri", "Mohamed Cherif"]
    for i in range(30):
        part = random.choice(parts)
        days_ago = random.randint(1, 180)
        c.execute("""INSERT INTO stock_movements (part_id, movement_type, quantity, performed_by, notes, performed_at)
            VALUES (?,?,?,?,?,?)""", (
            part,
            random.choice(["out", "out", "in"]),
            round(random.uniform(1, 5), 0),
            random.choice(techs),
            f"Used for maintenance WO-2025-00{random.randint(1,9)}",
            (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M"),
        ))


# ── Query helpers ─────────────────────────────────────────────────────────────

def query(sql: str, params=()) -> List[Dict]:
    conn = get_connection()
    result = [dict(row) for row in conn.execute(sql, params).fetchall()]
    conn.close()
    return result


def execute(sql: str, params=()):
    conn = get_connection()
    conn.execute(sql, params)
    conn.commit()
    conn.close()


def get_equipment() -> List[Dict]:
    return query("SELECT * FROM equipment ORDER BY criticality DESC, id")


def get_work_orders(status=None, equipment_id=None) -> List[Dict]:
    sql = "SELECT wo.*, eq.name as equipment_name, eq.zone FROM work_orders wo JOIN equipment eq ON wo.equipment_id = eq.id"
    conditions = []
    params = []
    if status:
        conditions.append("wo.status = ?")
        params.append(status)
    if equipment_id:
        conditions.append("wo.equipment_id = ?")
        params.append(equipment_id)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY CASE wo.priority WHEN 'emergency' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5 END, wo.scheduled_date"
    return query(sql, params)


def get_maintenance_history(equipment_id=None, limit=50) -> List[Dict]:
    sql = "SELECT mh.*, eq.name as equipment_name FROM maintenance_history mh JOIN equipment eq ON mh.equipment_id = eq.id"
    params = []
    if equipment_id:
        sql += " WHERE mh.equipment_id = ?"
        params.append(equipment_id)
    sql += f" ORDER BY mh.performed_at DESC LIMIT {limit}"
    return query(sql, params)


def get_spare_parts(low_stock_only=False) -> List[Dict]:
    sql = "SELECT * FROM spare_parts"
    if low_stock_only:
        sql += " WHERE stock_quantity <= reorder_point"
    sql += " ORDER BY category, name"
    return query(sql)


def get_technicians() -> List[Dict]:
    return query("SELECT * FROM technicians ORDER BY name")


def get_maintenance_plans(equipment_id=None) -> List[Dict]:
    sql = "SELECT mp.*, eq.name as equipment_name FROM maintenance_plans mp JOIN equipment eq ON mp.equipment_id = eq.id"
    if equipment_id:
        sql += f" WHERE mp.equipment_id = '{equipment_id}'"
    sql += " ORDER BY mp.next_due"
    return query(sql)


def compute_kpis() -> Dict:
    wos = query("SELECT * FROM work_orders")
    hist = query("SELECT * FROM maintenance_history")
    parts = query("SELECT * FROM spare_parts")

    total_wo = len(wos)
    completed = [w for w in wos if w["status"] == "completed"]
    open_wo = [w for w in wos if w["status"] not in ("completed", "cancelled")]
    overdue = [w for w in open_wo if w.get("is_overdue")]

    corrective = [w for w in wos if w["wo_type"] == "corrective"]
    preventive = [w for w in wos if w["wo_type"] == "preventive"]
    predictive = [w for w in wos if w["wo_type"] == "predictive"]

    total_cost = sum(w.get("actual_cost_eur", 0) or w.get("estimated_cost_eur", 0) for w in completed)
    corr_cost  = sum(w.get("actual_cost_eur", 0) or w.get("estimated_cost_eur", 0) for w in corrective if w["status"] == "completed")
    prev_cost  = sum(w.get("actual_cost_eur", 0) or w.get("estimated_cost_eur", 0) for w in preventive if w["status"] == "completed")

    mttr_vals = [h["duration_hours"] for h in hist if h.get("duration_hours")]
    mttr = round(sum(mttr_vals) / len(mttr_vals), 2) if mttr_vals else 0

    n_failures = len([h for h in hist if h["maintenance_type"] == "corrective"])
    total_hours = query("SELECT SUM(total_run_hours) as s FROM equipment")[0].get("s") or 8760
    mtbf = round(total_hours / max(n_failures, 1), 1)

    low_stock = len([p for p in parts if p["stock_quantity"] <= p["reorder_point"]])
    inv_value = sum(p["stock_quantity"] * p["unit_cost_eur"] for p in parts)

    return {
        "total_wo": total_wo,
        "open_wo": len(open_wo),
        "overdue_wo": len(overdue),
        "completed_wo": len(completed),
        "corrective_pct": round(len(corrective) / max(total_wo, 1) * 100, 1),
        "preventive_pct": round(len(preventive) / max(total_wo, 1) * 100, 1),
        "predictive_pct": round(len(predictive) / max(total_wo, 1) * 100, 1),
        "total_cost_eur": round(total_cost, 0),
        "corrective_cost_eur": round(corr_cost, 0),
        "preventive_cost_eur": round(prev_cost, 0),
        "mtbf_hours": mtbf,
        "mttr_hours": mttr,
        "low_stock_parts": low_stock,
        "inventory_value_eur": round(inv_value, 0),
        "savings_vs_reactive": round(corr_cost * 3 - total_cost, 0),
    }
