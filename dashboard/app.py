"""
CMMS Dashboard - Computerized Maintenance Management System
Author: Wassim BELAID
Run: streamlit run dashboard/app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import uuid
from app.database.db import (
    init_database, get_equipment, get_work_orders,
    get_maintenance_history, get_spare_parts, get_technicians,
    get_maintenance_plans, compute_kpis, execute
)

st.set_page_config(page_title="CMMS - SIBEA Plant", page_icon="🏭", layout="wide")
st.markdown("""<style>
.kpi-card{background:#111827;border-radius:12px;padding:18px;border:1px solid #1f2937;text-align:center;margin:4px 0;}
.wo-emergency{background:#1a0000;border-left:5px solid #ff0000;padding:10px 14px;border-radius:0 8px 8px 0;margin:4px 0;}
.wo-high{background:#1a0d00;border-left:5px solid #ff6600;padding:10px 14px;border-radius:0 8px 8px 0;margin:4px 0;}
.wo-medium{background:#0d1a00;border-left:5px solid #cccc00;padding:10px 14px;border-radius:0 8px 8px 0;margin:4px 0;}
.wo-low{background:#001a1a;border-left:5px solid #2196F3;padding:10px 14px;border-radius:0 8px 8px 0;margin:4px 0;}
.wo-planned{background:#100020;border-left:5px solid #9C27B0;padding:10px 14px;border-radius:0 8px 8px 0;margin:4px 0;}
</style>""", unsafe_allow_html=True)

if "db_init" not in st.session_state:
    init_database()
    st.session_state.db_init = True

# SIDEBAR
with st.sidebar:
    st.markdown("## 🏭 CMMS")
    st.caption("SIBEA Industrial Plant")
    st.divider()
    page = st.selectbox("Navigation", [
        "🏠 Dashboard", "🔧 Equipment", "📝 Work Orders",
        "📅 PM Plans", "🔩 Spare Parts", "👷 Technicians",
        "📊 KPI Reports", "📚 History"
    ])
    st.divider()
    kpis = compute_kpis()
    st.markdown(f"""**Today**
- Open WOs: **{kpis["open_wo"]}**
- Overdue: **{kpis["overdue_wo"]}** {"🔴" if kpis["overdue_wo"] > 0 else "✅"}
- Low Stock: **{kpis["low_stock_parts"]}** {"⚠️" if kpis["low_stock_parts"] > 0 else "✅"}
- MTBF: **{kpis["mtbf_hours"]:.0f}h**""")

priority_css = {"emergency":"wo-emergency","high":"wo-high","medium":"wo-medium","low":"wo-low","planned":"wo-planned"}
priority_icons = {"emergency":"🔴","high":"🟠","medium":"🟡","low":"🔵","planned":"🟣"}
type_icons = {"corrective":"🔧","preventive":"📅","predictive":"🤖","inspection":"🔍"}

# DASHBOARD PAGE
if page == "🏠 Dashboard":
    st.markdown("## 🏭 CMMS Dashboard — SIBEA Industrial Plant")
    st.caption(f"{datetime.now().strftime('%A %d %B %Y %H:%M')}")
    kpis = compute_kpis()

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    for col,label,value,color in [
        (c1,"Open Work Orders",kpis["open_wo"],"#2196F3"),
        (c2,"Overdue",kpis["overdue_wo"],"#ff3333" if kpis["overdue_wo"]>0 else "#00cc66"),
        (c3,"MTBF",f"{kpis['mtbf_hours']:.0f}h","#00cc66"),
        (c4,"MTTR",f"{kpis['mttr_hours']:.1f}h","#FF9800"),
        (c5,"Total Cost",f"€{kpis['total_cost_eur']:,.0f}","#9C27B0"),
        (c6,"Low Stock",kpis["low_stock_parts"],"#ff8c00" if kpis["low_stock_parts"]>0 else "#00cc66"),
    ]:
        col.markdown(f'''<div class="kpi-card"><p style="color:#aaa;font-size:11px">{label.upper()}</p><h2 style="color:{color};margin:8px 0">{value}</h2></div>''', unsafe_allow_html=True)

    st.divider()
    col_l, col_r = st.columns([2,1])

    with col_l:
        st.subheader("🏭 Equipment Health")
        equipment = get_equipment()
        if equipment:
            eq_df = pd.DataFrame(equipment)
            colors_map = {"critical":"#ff3333","high":"#ff8c00","medium":"#ffcc00","low":"#00cc66"}
            fig_eq = go.Figure()
            for _, row in eq_df.iterrows():
                h = row.get("health_pct", 100)
                c = "#ff3333" if h < 40 else ("#ff8c00" if h < 70 else "#00cc66")
                fig_eq.add_trace(go.Bar(x=[row["name"]], y=[h], marker_color=c, text=[f"{h:.0f}%"], textposition="auto", showlegend=False))
            fig_eq.add_hline(y=70, line_dash="dash", line_color="orange", annotation_text="Warning")
            fig_eq.add_hline(y=40, line_dash="dash", line_color="red", annotation_text="Critical")
            fig_eq.update_layout(template="plotly_dark", height=280, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(range=[0,110],title="Health (%)"))
            st.plotly_chart(fig_eq, use_container_width=True)

        st.subheader("📝 Open Work Orders")
        wos = get_work_orders()
        open_wos = [w for w in wos if w["status"] not in ("completed","cancelled")]
        for wo in open_wos[:8]:
            css = priority_css.get(wo["priority"],"wo-low")
            icon = priority_icons.get(wo["priority"],"⚪")
            ticon = type_icons.get(wo["wo_type"],"🔧")
            overdue = " ⚠️ OVERDUE" if wo.get("is_overdue") else ""
            st.markdown(f'''<div class="{css}"><b>{icon} {wo["id"]}</b>{overdue} — {ticon} {wo["title"]}<br><small style="color:#aaa">🏭 {wo["equipment_name"]} | 📅 {wo.get("scheduled_date","—")} | 👤 {wo.get("assigned_to","—")} | ⏱️ {wo.get("estimated_hours",0)}h | 💶 €{wo.get("estimated_cost_eur",0):.0f}</small></div>''', unsafe_allow_html=True)

    with col_r:
        st.subheader("📊 WO Distribution")
        all_wos = get_work_orders()
        if all_wos:
            by_p = pd.DataFrame(all_wos).groupby("priority").size().reset_index(name="count")
            fig_pie = px.pie(by_p, values="count", names="priority", hole=0.4,
                color_discrete_map={"emergency":"#ff3333","high":"#ff8c00","medium":"#ffcc00","low":"#2196F3","planned":"#9C27B0"})
            fig_pie.update_layout(template="plotly_dark", height=240, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("🔧 Maintenance Mix")
        mix = go.Figure(go.Bar(
            x=[kpis["preventive_pct"],kpis["predictive_pct"],kpis["corrective_pct"]],
            y=["Preventive","Predictive","Corrective"], orientation="h",
            marker_color=["#00cc66","#2196F3","#ff3333"],
            text=[f"{v:.0f}%" for v in [kpis["preventive_pct"],kpis["predictive_pct"],kpis["corrective_pct"]]],
            textposition="auto"))
        mix.update_layout(template="plotly_dark", height=180, margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(range=[0,100]))
        st.plotly_chart(mix, use_container_width=True)

        st.markdown(f'''<div class="kpi-card"><p style="color:#aaa;font-size:11px">COST SUMMARY</p>
            <p style="color:#ff3333">Corrective: €{kpis["corrective_cost_eur"]:,.0f}</p>
            <p style="color:#00cc66">Preventive: €{kpis["preventive_cost_eur"]:,.0f}</p>
            <p style="color:#00cc66;font-weight:bold">Savings: €{kpis["savings_vs_reactive"]:,.0f}</p>
            <p style="color:#aaa;font-size:11px">Inventory: €{kpis["inventory_value_eur"]:,.0f}</p></div>''', unsafe_allow_html=True)

        st.subheader("📅 Upcoming PM")
        plans = get_maintenance_plans()
        for p in sorted([x for x in plans if x.get("next_due")], key=lambda x: x["next_due"])[:5]:
            days = (datetime.strptime(p["next_due"],"%Y-%m-%d") - datetime.now()).days
            c = "#ff3333" if days<0 else ("#ff8c00" if days<14 else "#00cc66")
            st.markdown(f"<small style='color:{c}'>📅 {p['next_due']} — {p['plan_name'][:35]}</small>", unsafe_allow_html=True)

# EQUIPMENT PAGE
elif page == "🔧 Equipment":
    st.markdown("## 🔧 Equipment Registry")
    equipment = get_equipment()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total",len(equipment))
    c2.metric("Critical",len([e for e in equipment if e["criticality"]=="critical"]))
    c3.metric("Degraded",len([e for e in equipment if e["status"]=="degraded"]))
    c4.metric("Avg Health",f"{np.mean([e.get('health_pct',100) for e in equipment]):.1f}%")
    st.divider()
    for eq in equipment:
        h = eq.get("health_pct",100)
        hc = "#ff3333" if h<40 else ("#ff8c00" if h<70 else "#00cc66")
        cc = {"critical":"#ff3333","high":"#ff8c00","medium":"#ffcc00","low":"#00cc66"}.get(eq["criticality"],"#aaa")
        with st.expander(f"**{eq['id']}** — {eq['name']} | {eq['zone']} | Health: {h:.0f}% | {eq['criticality'].upper()}"):
            a,b,c = st.columns(3)
            with a:
                st.markdown(f"**Type:** {eq['equipment_type']}\n\n**Manufacturer:** {eq.get('manufacturer','—')}\n\n**Model:** {eq.get('model','—')}\n\n**Serial:** {eq.get('serial_number','—')}")
            with b:
                st.markdown(f"**Power:** {eq.get('nominal_power_kw',0)} kW\n\n**Speed:** {eq.get('nominal_speed_rpm',0)} RPM\n\n**Voltage:** {eq.get('nominal_voltage_v',0)} V\n\n**PM Interval:** {eq.get('maintenance_interval_hours',0)}h")
            with c:
                st.markdown(f"**Criticality:** <span style='color:{cc}'>{eq['criticality'].upper()}</span>\n\n**Health:** <span style='color:{hc}'>{h:.0f}%</span>\n\n**Run Hours:** {eq.get('current_run_hours',0):.0f}h\n\n**Last PM:** {eq.get('last_maintenance_date','—')}", unsafe_allow_html=True)
            hist = get_maintenance_history(eq["id"], limit=5)
            if hist:
                st.dataframe(pd.DataFrame(hist)[["performed_at","maintenance_type","performed_by","duration_hours","cost_eur"]], use_container_width=True, hide_index=True)

# WORK ORDERS PAGE
elif page == "📝 Work Orders":
    st.markdown("## 📝 Work Orders")
    tab_open, tab_all, tab_new = st.tabs(["📂 Open","📋 All","➕ New"])

    with tab_open:
        wos = get_work_orders()
        open_wos = [w for w in wos if w["status"] not in ("completed","cancelled")]
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Open",len(open_wos))
        m2.metric("Emergency",len([w for w in open_wos if w["priority"]=="emergency"]))
        m3.metric("Overdue",len([w for w in open_wos if w.get("is_overdue")]))
        m4.metric("Est. Cost",f"€{sum(w.get('estimated_cost_eur',0) for w in open_wos):,.0f}")
        st.divider()
        for wo in open_wos:
            css = priority_css.get(wo["priority"],"wo-low")
            icon = priority_icons.get(wo["priority"],"⚪")
            ticon = type_icons.get(wo["wo_type"],"🔧")
            od = " ⚠️ OVERDUE" if wo.get("is_overdue") else ""
            st.markdown(f'''<div class="{css}"><b>{icon} [{wo["priority"].upper()}] {wo["id"]}</b>{od} — {ticon} {wo["title"]}<br>
            <small style="color:#aaa">🏭 {wo["equipment_name"]} | 📅 {wo.get("scheduled_date","—")} | 👤 {wo.get("assigned_to","—")} | ⏱️ {wo.get("estimated_hours",0)}h | 💶 €{wo.get("estimated_cost_eur",0):.0f}</small><br>
            <small style="color:#666">{str(wo.get("description",""))[:120]}</small></div>''', unsafe_allow_html=True)

    with tab_all:
        all_wos = get_work_orders()
        if all_wos:
            df = pd.DataFrame(all_wos)
            cols = ["id","equipment_name","title","wo_type","priority","status","scheduled_date","assigned_to","estimated_cost_eur"]
            st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True, height=400)
            col_c1,col_c2 = st.columns(2)
            with col_c1:
                by_s = df.groupby("status").size().reset_index(name="count")
                fig_s = px.pie(by_s, values="count", names="status", hole=0.4, title="By Status")
                fig_s.update_layout(template="plotly_dark", height=260, margin=dict(l=0,r=0,t=30,b=0))
                st.plotly_chart(fig_s, use_container_width=True)
            with col_c2:
                by_t = df.groupby("wo_type").size().reset_index(name="count")
                fig_t = px.bar(by_t, x="wo_type", y="count", title="By Type", color="wo_type",
                    color_discrete_map={"corrective":"#ff3333","preventive":"#00cc66","predictive":"#2196F3","inspection":"#FF9800"})
                fig_t.update_layout(template="plotly_dark", height=260, margin=dict(l=0,r=0,t=30,b=0), showlegend=False)
                st.plotly_chart(fig_t, use_container_width=True)

    with tab_new:
        st.subheader("Create New Work Order")
        equipment = get_equipment()
        techs = get_technicians()
        with st.form("new_wo"):
            n1,n2 = st.columns(2)
            with n1:
                wo_eq = st.selectbox("Equipment*", [f"{e['id']} — {e['name']}" for e in equipment])
                wo_title = st.text_input("Title*")
                wo_type = st.selectbox("Type*", ["corrective","preventive","predictive","inspection"])
                wo_priority = st.selectbox("Priority*", ["emergency","high","medium","low","planned"])
            with n2:
                wo_assigned = st.selectbox("Assign To", [t["name"] for t in techs])
                wo_scheduled = st.date_input("Scheduled", datetime.now()+timedelta(days=3))
                wo_hours = st.number_input("Est. Hours", 0.5, 48.0, 2.0, 0.5)
                wo_cost = st.number_input("Est. Cost (€)", 0.0, 50000.0, 200.0, 50.0)
            wo_desc = st.text_area("Description*")
            if st.form_submit_button("✅ Create Work Order", use_container_width=True, type="primary"):
                if wo_title and wo_desc:
                    wo_id = f"WO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
                    eq_id = wo_eq.split(" — ")[0]
                    execute("""INSERT INTO work_orders (id,equipment_id,title,description,wo_type,priority,status,scheduled_date,assigned_to,estimated_hours,estimated_cost_eur) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (wo_id,eq_id,wo_title,wo_desc,wo_type,wo_priority,"open",str(wo_scheduled),wo_assigned,wo_hours,wo_cost))
                    st.success(f"✅ {wo_id} created!")

# PM PLANS PAGE
elif page == "📅 PM Plans":
    st.markdown("## 📅 Preventive Maintenance Plans")
    plans = get_maintenance_plans()
    if plans:
        tab_l, tab_c = st.tabs(["📋 List","📅 Calendar"])
        with tab_l:
            for plan in sorted(plans, key=lambda x: x.get("next_due") or "9999"):
                if plan.get("next_due"):
                    days = (datetime.strptime(plan["next_due"],"%Y-%m-%d") - datetime.now()).days
                    color = "#ff3333" if days<0 else ("#ff8c00" if days<14 else "#00cc66")
                    urgency = "🔴 OVERDUE" if days<0 else (f"🟡 {days}d" if days<30 else f"🟢 {days}d")
                else:
                    color,urgency = "#aaa","📅"
                with st.expander(f"{urgency} — **{plan['plan_name']}** | {plan['equipment_name']}"):
                    a,b = st.columns(2)
                    with a:
                        st.markdown(f"- **Type:** {plan['plan_type']}\n- **Interval:** {plan.get('interval_hours','—')}h\n- **Duration:** {plan.get('estimated_duration_hours',0)}h\n- **Cost:** €{plan.get('estimated_cost_eur',0):.0f}\n- **Next due:** <span style='color:{color}'>{plan.get('next_due','—')}</span>", unsafe_allow_html=True)
                    with b:
                        st.markdown(f"- **Skills:** {plan.get('required_skills','—')}\n- **Tools:** {plan.get('required_tools','—')}\n- **Parts:** {plan.get('spare_parts_needed','—')}\n- **Safety:** {plan.get('safety_precautions','—')}")
                    if plan.get("procedure"):
                        st.code(plan["procedure"])
        with tab_c:
            gantt = [{"Task":p["plan_name"][:35],"Start":datetime.strptime(p["next_due"],"%Y-%m-%d"),"Finish":datetime.strptime(p["next_due"],"%Y-%m-%d")+timedelta(hours=p.get("estimated_duration_hours",2)),"Type":p["plan_type"]} for p in plans if p.get("next_due")]
            if gantt:
                gdf = pd.DataFrame(gantt)
                fig_g = px.timeline(gdf, x_start="Start", x_end="Finish", y="Task", color="Type",
                    color_discrete_map={"preventive":"#00cc66","corrective":"#ff3333","inspection":"#2196F3"}, title="Maintenance Calendar")
                fig_g.update_yaxes(autorange="reversed")
                fig_g.add_vline(x=datetime.now(), line_dash="dash", line_color="white", annotation_text="Today")
                fig_g.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=30,b=0))
                st.plotly_chart(fig_g, use_container_width=True)

# SPARE PARTS PAGE
elif page == "🔩 Spare Parts":
    st.markdown("## 🔩 Spare Parts Inventory")
    parts = get_spare_parts()
    if parts:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Part Numbers",len(parts))
        low = [p for p in parts if p["stock_quantity"]<=p["reorder_point"]]
        c2.metric("Low Stock",len(low))
        c3.metric("Inventory Value",f"€{sum(p['stock_quantity']*p['unit_cost_eur'] for p in parts):,.0f}")
        c4.metric("Categories",len(set(p["category"] for p in parts)))
        st.divider()
        tab_a, tab_b = st.tabs(["📦 All Parts","⚠️ Low Stock"])
        with tab_a:
            cat_f = st.selectbox("Category",["All"]+sorted(set(p["category"] for p in parts)))
            fp = parts if cat_f=="All" else [p for p in parts if p["category"]==cat_f]
            for part in fp:
                s = part["stock_quantity"]; r = part["reorder_point"]; m = part["max_stock"]
                icon = "🔴" if s<=part["min_stock"] else ("🟡" if s<=r else "🟢")
                with st.expander(f"{icon} **{part['id']}** — {part['name']} | {s:.0f} {part['unit']} | €{part['unit_cost_eur']:.2f}"):
                    a,b,c = st.columns(3)
                    with a: st.markdown(f"**Part#:** {part.get('part_number','—')}\n\n**Manufacturer:** {part.get('manufacturer','—')}\n\n**Category:** {part['category']}")
                    with b: st.markdown(f"**Stock:** {s:.0f} | Min: {part['min_stock']:.0f} | Max: {m:.0f}\n\n**Reorder at:** {r:.0f} {part['unit']}\n\n**Total value:** €{s*part['unit_cost_eur']:.2f}")
                    with c: st.markdown(f"**Location:** {part.get('location','—')}\n\n**Supplier:** {part.get('supplier','—')}\n\n**Lead time:** {part.get('lead_time_days',14)} days")
                    st.progress(min(1.0,s/max(m,1)), text=f"{s:.0f}/{m:.0f} {part['unit']}")
        with tab_b:
            if low:
                for part in low:
                    qty = part["max_stock"]-part["stock_quantity"]
                    color = "#ff3333" if part["stock_quantity"]<=part["min_stock"] else "#ff8c00"
                    st.markdown(f'''<div style="background:#1a0d00;border-left:4px solid {color};padding:10px;border-radius:0 6px 6px 0;margin:3px 0"><b style="color:{color}">{part["id"]}</b> — {part["name"]}<br><small>Stock: <b>{part["stock_quantity"]:.0f}</b> | Order: <b>{qty:.0f} {part["unit"]}</b> | Supplier: {part.get("supplier","—")} | Lead: {part.get("lead_time_days",14)}d | Value: €{qty*part["unit_cost_eur"]:.0f}</small></div>''', unsafe_allow_html=True)
            else:
                st.success("✅ All parts adequately stocked")

# TECHNICIANS PAGE
elif page == "👷 Technicians":
    st.markdown("## 👷 Technician Management")
    techs = get_technicians()
    wos = get_work_orders()
    c1,c2,c3 = st.columns(3)
    c1.metric("Total",len(techs))
    c2.metric("Available",len([t for t in techs if t.get("available",1)]))
    c3.metric("Total Workload",f"{sum(t.get('current_workload_hours',0) for t in techs):.0f}h")
    for tech in techs:
        twos = [w for w in wos if w.get("assigned_to")==tech["name"] and w["status"] not in ("completed","cancelled")]
        load = tech.get("current_workload_hours",0)
        lc = "#ff3333" if load>8 else ("#ff8c00" if load>5 else "#00cc66")
        with st.expander(f"**{tech['name']}** — {tech.get('specialization','—')} | Workload: {load}h | {len(twos)} WOs"):
            a,b = st.columns(2)
            with a: st.markdown(f"**Specialization:** {tech.get('specialization','—')}\n\n**Certifications:** {tech.get('certifications','—')}\n\n**Phone:** {tech.get('phone','—')}\n\n**Email:** {tech.get('email','—')}")
            with b:
                st.markdown(f"**Workload:** <span style='color:{lc}'>{load}h</span>", unsafe_allow_html=True)
                st.progress(min(1.0,load/10),text=f"{load}h / 10h")
                for wo in twos[:3]: st.markdown(f"- `{wo['id']}` {wo['title'][:40]}")

# KPI REPORTS PAGE
elif page == "📊 KPI Reports":
    st.markdown("## 📊 KPI Reports & Analytics")
    kpis = compute_kpis()
    k1,k2,k3,k4 = st.columns(4)
    for col,label,value in [(k1,"MTBF",f"{kpis['mtbf_hours']:.0f}h"),(k2,"MTTR",f"{kpis['mttr_hours']:.1f}h"),
        (k3,"Preventive %",f"{kpis['preventive_pct']:.0f}%"),(k4,"Total Cost",f"€{kpis['total_cost_eur']:,.0f}")]:
        col.markdown(f'''<div class="kpi-card"><p style="color:#aaa;font-size:11px">{label}</p><h2 style="color:#2196F3">{value}</h2></div>''', unsafe_allow_html=True)
    st.divider()
    hist = get_maintenance_history(limit=200)
    if hist:
        hdf = pd.DataFrame(hist)
        hdf["performed_at"] = pd.to_datetime(hdf["performed_at"])
        hdf["month"] = hdf["performed_at"].dt.to_period("M").astype(str)
        r1,r2 = st.columns(2)
        with r1:
            mc = hdf.groupby(["month","maintenance_type"])["cost_eur"].sum().reset_index()
            fig_c = px.bar(mc, x="month", y="cost_eur", color="maintenance_type",
                color_discrete_map={"corrective":"#ff3333","preventive":"#00cc66","inspection":"#2196F3","predictive":"#FF9800"},
                title="Monthly Cost by Type (€)")
            fig_c.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=30,b=0))
            st.plotly_chart(fig_c, use_container_width=True)
        with r2:
            bt = hdf.groupby("maintenance_type")["duration_hours"].mean().reset_index()
            fig_d = px.bar(bt, x="maintenance_type", y="duration_hours", color="maintenance_type",
                title="Avg Duration by Type (h)", color_discrete_map={"corrective":"#ff3333","preventive":"#00cc66","inspection":"#2196F3"})
            fig_d.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=30,b=0), showlegend=False)
            st.plotly_chart(fig_d, use_container_width=True)
        hv = hdf.dropna(subset=["vibration_before","vibration_after"]).copy()
        if not hv.empty:
            fig_v = go.Figure()
            fig_v.add_trace(go.Scatter(x=hv["performed_at"], y=hv["vibration_before"], mode="markers", name="Before", marker=dict(color="#ff3333",size=8)))
            fig_v.add_trace(go.Scatter(x=hv["performed_at"], y=hv["vibration_after"], mode="markers", name="After", marker=dict(color="#00cc66",size=8)))
            fig_v.add_hline(y=4.5, line_dash="dash", line_color="orange", annotation_text="ISO Zone C")
            fig_v.update_layout(template="plotly_dark", height=280, margin=dict(l=0,r=0,t=10,b=0), title="Vibration Before/After Maintenance", yaxis_title="mm/s")
            st.plotly_chart(fig_v, use_container_width=True)
        st.markdown(f"""**Savings vs reactive maintenance: €{kpis["savings_vs_reactive"]:,.0f}** | **Inventory value: €{kpis["inventory_value_eur"]:,.0f}**""")

# HISTORY PAGE
elif page == "📚 History":
    st.markdown("## 📚 Maintenance History")
    equipment = get_equipment()
    eq_sel = st.selectbox("Equipment",["All"]+[f"{e['id']} — {e['name']}" for e in equipment])
    eq_id = None if eq_sel=="All" else eq_sel.split(" — ")[0]
    hist = get_maintenance_history(eq_id, limit=100)
    if hist:
        hdf = pd.DataFrame(hist)
        cols = ["performed_at","equipment_name","maintenance_type","performed_by","duration_hours","cost_eur","condition_before","condition_after","vibration_before","vibration_after"]
        st.dataframe(hdf[[c for c in cols if c in hdf.columns]], use_container_width=True, hide_index=True, height=400)
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Records",len(hist))
        c2.metric("Total Cost",f"€{sum(h.get('cost_eur',0) for h in hist):,.0f}")
        c3.metric("Total Hours",f"{sum(h.get('duration_hours',0) for h in hist):.0f}h")
        c4.metric("Avg Cost",f"€{sum(h.get('cost_eur',0) for h in hist)/max(len(hist),1):.0f}")
