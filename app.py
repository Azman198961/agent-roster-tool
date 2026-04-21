import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta, date

# --- 1. DATABASE CONNECTION ---
def get_connection():
    # Apnar notun project ref: cvmuxfdixhtbuuxcijl
    # User format obosshoi 'postgres.project_ref' hote hobe
    user = "postgres.cvmuxfdixhtbuuxcijl"
    password = "M198961Asik%21" # Password encode kora hoyeche
    host = "aws-1-ap-southeast-1.pooler.supabase.com"
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

# --- 3. LOGIN SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None

# --- 4. APP CONFIG ---
st.set_page_config(page_title="CX Roster Management", layout="wide")

# LOGIN INTERFACE
if not st.session_state['logged_in']:
    st.title("🔐 CX Roster Login")
    user_role = st.selectbox("Select Role", ["Admin", "Agent"])
    password = st.text_input("Enter Password", type="password")
    
    if st.button("Login"):
        if user_role == "Admin" and password == "Win@1234":
            st.session_state['logged_in'] = True
            st.session_state['role'] = "Admin"
            st.rerun()
        elif user_role == "Agent" and password == "123456":
            st.session_state['logged_in'] = True
            st.session_state['role'] = "Agent"
            st.rerun()
        else:
            st.error("❌ Invalid Password! Please try again.")
    st.stop()

# LOGOUT BUTTON
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.rerun()

# ---------------- MAIN APP (AFTER LOGIN) ----------------

role = st.session_state['role']

if role == "Admin":
    st.sidebar.title(f"Admin Portal")
    page = st.sidebar.selectbox("Navigate", ["1. Agent Details", "2. Create Roster", "3. Review & Publish", "4. Swap Approvals"])

    # PAGE 1: AGENT DETAILS
    if page == "1. Agent Details":
        st.header("👤 Agent Management")
        with st.form("add_agent"):
            col1, col2, col3 = st.columns(3)
            name = col1.text_input("Agent Name")
            emp_id = col2.text_input("Employee ID")
            channel = col3.selectbox("Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
            if st.form_submit_button("Save Agent"):
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO agents (emp_id, name, channel) VALUES (%s, %s, %s)", (emp_id, name, channel))
                    conn.commit()
                    st.success(f"Agent {name} added successfully!")
                    conn.close()
                except Exception as e: st.error(f"Error: {e}")

    # PAGE 2: CREATE ROSTER (FIXED)
    elif page == "2. Create Roster":
        st.header("📅 Monthly Roster Creation")
        col1, col2 = st.columns(2)
        sel_channel = col1.selectbox("Select Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
        
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        curr_month = datetime.now().month
        sel_month_name = col2.selectbox("Select Cycle Month (Ends 20th)", months, index=curr_month-1)
        sel_month = months.index(sel_month_name) + 1
        
        # Load Agents from DB
        conn = get_connection()
        agents_df = pd.read_sql(f"SELECT emp_id, name FROM agents WHERE channel='{sel_channel}'", conn)
        conn.close()

        if agents_df.empty:
            st.warning(f"No agents found in {sel_channel}. Please add agents first.")
        else:
            dates = get_roster_dates(sel_month, 2026) # 2026 fix
            date_cols = [d.strftime("%Y-%m-%d") for d in dates]
            
            # Create editable table
            for d_col in date_cols: agents_df[d_col] = "OFF" # Default OFF
            
            st.write(f"Editing Roster for: {sel_month_name}")
            edited_df = st.data_editor(agents_df, hide_index=True)
            
            if st.button("Save Roster"):
                conn = get_connection()
                cur = conn.cursor()
                try:
                    for _, row in edited_df.iterrows():
                        emp_id = row['emp_id']
                        for d_str in date_cols:
                            shift = row[d_str]
                            cur.execute("""
                                INSERT INTO rosters (emp_id, shift_date, shift_type, is_published) 
                                VALUES (%s, %s, %s, TRUE)
                                ON CONFLICT (emp_id, shift_date) DO UPDATE SET shift_type = EXCLUDED.shift_type
                            """, (emp_id, d_str, shift))
                    conn.commit()
                    st.success("Roster Saved & Published Successfully!")
                except Exception as e: st.error(f"Error: {e}")
                finally: conn.close()

# ---------------- AGENT PORTAL ----------------
else:
    st.sidebar.title("Agent Portal")
    st.header(f"📋 My Shift Roster")
    emp_id = st.sidebar.text_input("Enter Your Employee ID to View")
    
    if emp_id:
        conn = get_connection()
        query = f"SELECT shift_date, shift_type FROM rosters WHERE emp_id = '{emp_id}' ORDER BY shift_date ASC"
        my_roster = pd.read_sql(query, conn)
        conn.close()
        
        if not my_roster.empty:
            st.dataframe(my_roster, use_container_width=True)
        else:
            st.info("No roster published for this ID yet.")
