# 🏭 CMMS — Computerized Maintenance Management System

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red)](https://streamlit.io)
[![SQLite](https://img.shields.io/badge/Database-SQLite-green)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> Enterprise-grade **Computerized Maintenance Management System** for industrial plant operations. Manages equipment registry, work orders, maintenance history, spare parts inventory, KPI tracking and regulatory compliance.

Based on real maintenance management experience at **SIBEA Industrial Plant (Béjaia, Algeria)** — demonstrates both field expertise and engineering management skills.

---

## 🏭 Industrial Context

A CMMS is the operational backbone of any industrial maintenance department:
- **ISO 55000** — Asset management standard
- **ISO 15663** — Life-cycle costing for petroleum industry
- **EN 13460** — Maintenance documentation
- **OSHA / SUVA** — Safety compliance

In Switzerland, CMMS tools like SAP PM, IBM Maximo and Infor EAM are used by major industrials. This project demonstrates you understand both sides: **field maintenance + management systems**.

---

## 🎯 Features

### Equipment Management
- Complete equipment registry with technical specs
- Equipment hierarchy (Plant → Zone → System → Equipment)
- Criticality classification (Critical / High / Medium / Low)
- Technical documentation links
- QR code generation for field use

### Work Order Management
- Automated WO generation from sensor alerts / ML predictions
- Priority-based scheduling (Emergency → High → Medium → Low → Planned)
- WO lifecycle: Open → Assigned → In Progress → On Hold → Completed
- Technician assignment and workload balancing
- Spare parts reservation per WO
- Labor and material cost tracking

### Maintenance Planning
- Preventive maintenance schedules (time-based, usage-based)
- Maintenance calendar with Gantt view
- Resource planning (technicians, tools, spare parts)
- Shutdown planning coordination

### Spare Parts & Inventory
- Real-time stock levels with min/max management
- Automatic reorder point alerts
- Supplier database with lead times
- ABC analysis for stock optimization
- Cost tracking per equipment

### KPI Dashboard
- OEE (Overall Equipment Effectiveness)
- MTBF / MTTR per equipment and fleet
- Maintenance cost analysis (planned vs corrective)
- Technician productivity
- Compliance rate (PM completed on time)

### Reporting
- Monthly maintenance reports
- Cost center analysis
- Regulatory compliance reports (safety, environment)
- Export to CSV/PDF

---

## 📁 Project Structure

```
cmms-maintenance-system/
├── app/
│   ├── models/
│   │   ├── equipment.py       # Equipment, EquipmentType, Criticality
│   │   ├── work_order.py      # WorkOrder, WOStatus, WOPriority
│   │   ├── maintenance.py     # MaintenancePlan, MaintenanceRecord
│   │   ├── spare_parts.py     # SparePart, StockMovement, Supplier
│   │   └── kpi.py             # KPICalculator, OEE, MTBF, MTTR
│   ├── services/
│   │   ├── wo_service.py      # Work order business logic
│   │   ├── planning_service.py # PM scheduling
│   │   ├── inventory_service.py # Spare parts management
│   │   └── report_service.py  # Report generation
│   └── database/
│       └── db.py              # SQLite database manager
├── dashboard/
│   └── app.py                 # Main Streamlit application
├── database/
│   └── schema.sql             # Database schema
├── tests/
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start

```bash
git clone https://github.com/wassimbelaid05-EIE/cmms-maintenance-system.git
cd cmms-maintenance-system
pip install -r requirements.txt
streamlit run dashboard/app.py
```

---

## 📊 Database Schema

```sql
Equipment ──────────── WorkOrders
    │                       │
    ├── MaintenancePlans     ├── LaborRecords
    ├── MaintenanceHistory   ├── MaterialRecords
    └── SpareParts ─────────└── SparePartReservations
```

---

## 🏭 Equipment Registry (SIBEA Plant)

| ID | Equipment | Zone | Criticality | PM Interval |
|----|-----------|------|-------------|-------------|
| E001 | Compressor A | Zone A | Critical | 2000h |
| E002 | Pump B | Zone B | High | 3000h |
| E003 | Motor C | Zone C | High | 4000h |
| E004 | Conveyor D | Zone D | Medium | 2500h |
| E005 | Compressor E | Zone A | Critical | 2000h |
| E006 | Pump F | Zone B | High | 3000h |
| E007 | Heat Exchanger | Zone C | Medium | 6000h |
| E008 | Fan H | Zone E | Low | 5000h |

---

## 💼 Why CMMS Skills Matter in Switzerland

Swiss industrial companies require engineers who understand:
- **SAP PM** module (Plant Maintenance)
- **Maintenance KPIs** (MTBF, MTTR, OEE)
- **ISO 55000** asset management
- **Cost optimization** through predictive maintenance

This project demonstrates you can bridge the gap between field maintenance and management information systems — a rare and valuable skill combination.

---

## 👤 Author

**Wassim BELAID**
MSc Electrical Engineering — HES-SO Lausanne, Switzerland
Former maintenance engineer at SIBEA Industrial Plant
[GitHub](https://github.com/wassimbelaid05-EIE)
