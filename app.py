import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta, date
from psycopg2 import extras

# --- 1. DATABASE CONNECTION (SUPABASE) ---
def get_connection():
    # 'FATAL: Tenant or user not found' mane user format-e vul ache.
    # Pooler-er khetre user hobe: [Project_Ref].[User]
    # Apnar Project Ref: icegtuwpbogvgikyygjf
    
    # FORMAT: project_ref.postgres
    user = "icegtuwpbogvgikyygjf.postgres" 
    password = "Win%401234"
    host = "aws-0-ap-southeast-1.pooler.supabase.com"
    port = "6543"
    dbname = "postgres"
    
    conn_str = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"
    return psycopg2.connect(conn_str)

# --- 2. LOGIC: DATE GENERATOR (21st to 20th) ---
def get_roster_dates(target_month, target_year):
    if target_month == 1:
        start_date = date(target_year - 1, 12, 21)
    else:
        start_date = date(target_year, target_month - 1, 21)
    end_date = date(target_year, target_month, 20)
    delta = end_date - start_date
    return [start_date + timedelta(days=i) for i in range(delta.days + 1)]

# --- 3. APP CONFIG ---
st.set_page_config(page_title="CX Agent Roster Tool", layout="wide")
st.sidebar.title("Roster Management")
auth_mode = st.sidebar.radio("Authorization", ["Admin Portal", "Agent Portal"])

# ---------------- ADMIN PORTAL ----------------
if auth_mode == "Admin Portal":
    page = st.sidebar.selectbox("Navigate", ["1. Agent Details", "2. Create Roster", "3. Review & Publish", "4. Update & Swap Requests", "5. Reports"])

    # PAGE 1: AGENT DETAILS
    if page == "1. Agent Details":
        st.header("👤 Agent Management")
        with st.form("add_agent"):
            col1, col2, col3 = st.columns(3)
            name = col1.text_input("Agent Name")
            emp_id = col2.text_input("Employee ID")
            channel = col3.selectbox("Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
            if st.form_submit_button("Save Agent"):
                conn = get_connection()
                cur = conn.cursor()
                try:
                    cur.execute("INSERT INTO agents (emp_id, name, channel) VALUES (%s, %s, %s)", (emp_id, name, channel))
                    conn.commit()
                    st.success(f"Agent {name} added successfully!")
                except Exception as e: st.error(f"Error: {e}")
                finally: conn.close()

    # PAGE 2: CREATE ROSTER
    elif page == "2. Create Roster":
        st.header("📅 Monthly Roster Creation")
        col1, col2 = st.columns(2)
        sel_channel = col1.selectbox("Select Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
        
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        sel_month_name = col2.selectbox("Select Cycle Month (Ends 20th)", months, index=datetime.now().month-1)
        sel_month = months.index(sel_month_name) + 1
        
        dates = get_roster_dates(sel_month, datetime.now().year)
        date_cols = [d.strftime("%Y-%m-%d") for d in dates]
        
        conn = get_connection()
        agents_df = pd.read_sql(f"SELECT emp_id, name FROM agents WHERE channel='{sel_channel}'", conn)
        conn.close()

        if not agents_df.empty:
            for d_col in date_cols: agents_df[d_col] = "" # Default empty for shifts
            
            st.info("💡 Tip: You can copy-paste from Excel directly into the table below.")
            edited_df = st.data_editor(agents_df, hide_index=True)
            
            if st.button("Save & Publish Roster"):
                conn = get_connection()
                cur = conn.cursor()
                try:
                    for _, row in edited_df.iterrows():
                        for d_str in date_cols:
                            cur.execute("""
                                INSERT INTO rosters (emp_id, shift_date, shift_type, is_published) 
                                VALUES (%s, %s, %s, TRUE)
                            """, (row['emp_id'], d_str, row[d_str]))
                    conn.commit()
                    st.success("Roster Published successfully!")
                except Exception as e: st.error(f"Error: {e}")
                finally: conn.close()

    # PAGE 4: UPDATE & SWAP
    elif page == "4. Update & Swap Requests":
        st.header("🔄 Updates & Swap Approvals")
        # --- SWAP APPROVAL SECTION ---
        st.subheader("Pending Swap Requests")
        conn = get_connection()
        swaps = pd.read_sql("SELECT * FROM swap_requests WHERE status='Pending'", conn)
        
        if not swaps.empty:
            for i, row in swaps.iterrows():
                col1, col2, col3 = st.columns([3,1,1])
                col1.write(f"ID: {row['id']} | Agent {row['requested_by']} wants to swap with {row['swap_with']}")
                if col2.button("Approve", key=f"app_{row['id']}"):
                    # Logic: Swap shift_types in rosters table
                    cur = conn.cursor()
                    cur.execute("UPDATE swap_requests SET status='Approved', updated_on=NOW() WHERE id=%s", (row['id'],))
                    conn.commit()
                    st.rerun()
                if col3.button("Deny", key=f"den_{row['id']}"):
                    cur = conn.cursor()
                    cur.execute("UPDATE swap_requests SET status='Denied', updated_on=NOW() WHERE id=%s", (row['id'],))
                    conn.commit()
                    st.rerun()
        else: st.write("No pending requests.")
        conn.close()

    # PAGE 5: REPORTS
    elif page == "5. Reports":
        st.header("📊 Manpower Analytics")
        conn = get_connection()
        report_df = pd.read_sql("""
            SELECT shift_date, shift_type, COUNT(*) as count 
            FROM rosters GROUP BY shift_date, shift_type
        """, conn)
        st.dataframe(report_df)
        conn.close()

# ---------------- AGENT PORTAL ----------------
else:
    agent_page = st.sidebar.selectbox("Navigate", ["View Roster", "Request Swap", "Swap Status"])
    
    if agent_page == "Request Swap":
        st.header("📤 New Swap Request")
        with st.form("swap_form"):
            col1, col2 = st.columns(2)
            my_id = col1.text_input("Your Employee ID")
            my_date = col1.date_input("Your Shift Date")
            
            with col2:
                other_id = st.text_input("Swap With (Agent ID)")
                other_date = st.date_input("Their Shift Date")
            
            if st.form_submit_button("Submit Swap Request"):
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO swap_requests (requested_by, swap_with, req_date_1, req_date_2, status)
                    VALUES (%s, %s, %s, %s, 'Pending')
                """, (my_id, other_id, my_date, other_date))
                conn.commit()
                conn.close()
                st.success("Request sent to Admin!")

    elif agent_page == "View Roster":
        st.header("📋 Published Roster")
        channel = st.selectbox("Filter by Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
        conn = get_connection()
        # Query to show agents and their shifts in a pivot view
        query = f"""
            SELECT a.name, r.shift_date, r.shift_type, r.status
            FROM rosters r JOIN agents a ON r.emp_id = a.emp_id
            WHERE a.channel = '{channel}'
        """
        df = pd.read_sql(query, conn)
        st.dataframe(df)
        conn.close()
