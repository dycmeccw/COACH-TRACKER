import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="Coach Tracker", page_icon="🚆", layout="wide")

# --- DATABASE SETUP ---
conn = sqlite3.connect("coaches.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS coaches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coach_no TEXT,
    coach_type TEXT,
    date_in TEXT,
    current_shop TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coach_no TEXT,
    shop_in TEXT,
    shop_out TEXT,
    work_done TEXT,
    time_in TEXT,
    time_out TEXT
)
""")
conn.commit()

# --- MAIN TITLE ---
st.title("🚆 Railway Workshop Coach Tracker")
st.markdown("Easily manage and monitor coaches across workshops.")
st.divider()

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Dashboard", "➕ Add Coach", "🔄 Update Movement", "📋 Coach Details", "📑 Reports"]
)

# ================================
# DASHBOARD
# ================================
with tab1:
    st.subheader("📊 Live Status of Coaches")

    # KPI metrics
    c.execute("SELECT COUNT(*) FROM coaches")
    total_coaches = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM movements")
    total_movements = c.fetchone()[0]

    c.execute("SELECT DISTINCT current_shop FROM coaches")
    total_shops = len(c.fetchall())

    col1, col2, col3 = st.columns(3)
    col1.metric("🚆 Total Coaches", total_coaches)
    col2.metric("🔄 Total Movements", total_movements)
    col3.metric("🏭 Active Shops", total_shops)

    st.divider()

    # Coaches table
    c.execute("SELECT * FROM coaches")
    data = c.fetchall()
    if data:
        df = pd.DataFrame(data, columns=["ID", "Coach No", "Type", "Date In", "Current Shop"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No coaches available yet. Add some in ➕ Add Coach tab.")

    st.divider()

    # Coaches by Type
    c.execute("SELECT coach_type, COUNT(*) FROM coaches GROUP BY coach_type")
    data = c.fetchall()
    if data:
        df = pd.DataFrame(data, columns=["Coach Type", "Count"])
        fig = px.bar(df, x="Coach Type", y="Count", color="Coach Type",
                     text="Count", title="Coaches by Type",
                     color_discrete_sequence=px.colors.qualitative.Vivid)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    # Movements per Coach
    c.execute("SELECT coach_no, COUNT(*) FROM movements GROUP BY coach_no")
    report = c.fetchall()
    if report:
        df = pd.DataFrame(report, columns=["Coach No", "Movements"])
        fig = px.line(df, x="Coach No", y="Movements", markers=True,
                      title="Movements per Coach",
                      color_discrete_sequence=["#FF4B4B"])
        st.plotly_chart(fig, use_container_width=True)

# ================================
# ADD COACH
# ================================
with tab2:
    st.subheader("➕ Enter New Coach")
    coach_no = st.text_input("Coach Number")
    coach_type = st.selectbox("Type", ["AC", "Sleeper", "General"])
    date_in = st.date_input("Date In")
    shop = st.text_input("Initial Shop")

    if st.button("Add Coach"):
        if coach_no and shop:
            c.execute("INSERT INTO coaches (coach_no, coach_type, date_in, current_shop) VALUES (?,?,?,?)",
                      (coach_no, coach_type, str(date_in), shop))
            conn.commit()
            st.success(f"✅ Coach {coach_no} added!")
        else:
            st.warning("Please fill in all details.")

# ================================
# UPDATE MOVEMENT
# ================================
with tab3:
    st.subheader("🔄 Update Coach Movement")

    c.execute("SELECT coach_no FROM coaches")
    coach_list = [row[0] for row in c.fetchall()]

    if coach_list:
        coach_no = st.selectbox("Select Coach", coach_list)
        shop_out = st.text_input("Shop Out")
        shop_in = st.text_input("Shop In (Next Shop)")
        work_done = st.text_area("Work Done")

        if st.button("Update Movement"):
            if shop_in and shop_out:
                time_in = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                time_out = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                c.execute("INSERT INTO movements (coach_no, shop_in, shop_out, work_done, time_in, time_out) VALUES (?,?,?,?,?,?)",
                          (coach_no, shop_in, shop_out, work_done, time_in, time_out))
                c.execute("UPDATE coaches SET current_shop=? WHERE coach_no=?", (shop_in, coach_no))
                conn.commit()

                st.success(f"✅ Movement updated for Coach {coach_no}")
            else:
                st.warning("Please fill in both shop fields.")
    else:
        st.info("No coaches available. Please add a coach first.")

# ================================
# COACH DETAILS
# ================================
with tab4:
    st.subheader("📋 Coach History")
    coach_no = st.text_input("Enter Coach Number")

    if st.button("Get Details"):
        c.execute("SELECT * FROM movements WHERE coach_no=?", (coach_no,))
        data = c.fetchall()

        if data:
            df = pd.DataFrame(data, columns=[
                "ID", "Coach No", "Shop In", "Shop Out", "Work Done", "Time In", "Time Out"
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No movement found for this coach!")

# ================================
# REPORTS (with filters + export)
# ================================
with tab5:
    st.subheader("📑 Workshop Reports")

    # --- Filters ---
    st.markdown("### 🔍 Filters")
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("Start Date", value=datetime(2025, 1, 1))
    with col2:
        end_date = st.date_input("End Date", value=datetime.today())
    with col3:
        coach_type_filter = st.selectbox("Coach Type", ["All", "AC", "Sleeper", "General"])

    # Build query
    query = "SELECT * FROM coaches WHERE date_in BETWEEN ? AND ?"
    params = [str(start_date), str(end_date)]

    if coach_type_filter != "All":
        query += " AND coach_type=?"
        params.append(coach_type_filter)

    c.execute(query, params)
    data = c.fetchall()

    if data:
        df = pd.DataFrame(data, columns=["ID", "Coach No", "Type", "Date In", "Current Shop"])
        st.dataframe(df, use_container_width=True)

        # Summary for chart
        summary = df["Type"].value_counts().reset_index()
        summary.columns = ["Coach Type", "Count"]

        # Plotly bar chart
        fig = px.bar(
            summary,
            x="Coach Type",
            y="Count",
            labels={"Coach Type": "Coach Type", "Count": "Count"},
            title="Coaches by Type (Filtered)",
            color="Coach Type",
            text="Count",
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

        # --- Export Buttons ---
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name="coaches_report.csv",
            mime="text/csv",
        )

        # Excel export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Report")
        excel_data = output.getvalue()

        st.download_button(
            label="⬇️ Download Excel",
            data=excel_data,
            file_name="coaches_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    else:
        st.info("⚠️ No coaches found for given filters.")
