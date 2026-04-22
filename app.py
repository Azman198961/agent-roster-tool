import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, date

# --- 1. DATABASE CONNECTION (SQLAlchemy Engine for Pandas compatibility) ---
def get_engine():
    try:
        user = "postgres.cvmuxfdixhtbuuxqcijl"
        password = "M198961Asik%21"  
        host = "aws-1-ap-southeast-1.pooler.southeast-1.pooler.supabase.com" # আপনার অরিজিনাল হোস্ট
        port = "5432"
        dbname = "postgres"
        
        # SQLAlchemy connection string
        conn_str = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"
        engine = create_engine(conn_str)
        return engine
    except Exception as e:
        st.error(f"❌ Database Connection Error: {e}")
        return None

# --- NEW: LOGGING FUNCTION ---
def log_activity(user_identity, action):
    try:
        engine = get_engine()
        with engine.begin() as conn:
            query = text("INSERT INTO activity_logs (user_identity, action_details) VALUES (:user, :action)")
            conn.execute(query, {"user": user_identity, "action": action})
    except Exception as e:
        print(f"Logging error: {e}")

# --- 2. HELPERS ---
def get_roster_dates(target_month, target_year):
    if target_month == 1:
        start_date = date(target_year - 1, 12, 21)
    else:
        start_date = date(target_year, target_month - 1, 21)
    end_date = date(target_year, target_month, 20)
    delta = end_date - start_date
    return [start_date + timedelta(days=i) for i in range(delta.days + 1)]

# --- 3. SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': None, 'user_email': None})

st.set_page_config(page_title="CX Advanced Roster Tool", layout="wide")

# --- 4. LOGIN INTERFACE ---
if not st.session_state['logged_in']:
    st.title("🔐 CX Roster Login")
    email_input = st.text_input("Enter Your Email")
    role = st.selectbox("Select Role", ["Admin", "Agent"])
    pwd = st.text_input("Enter Password", type="password")
    
    if st.button("Login"):
        if not email_input:
            st.warning("Please enter your email to proceed.")
        elif role == "Admin" and pwd == "Win@1234":
            st.session_state.update({'logged_in': True, 'role': 'Admin', 'user_email': email_input})
            log_activity(email_input, "Admin Logged In")
            st.rerun()
        elif role == "Agent" and pwd == "123456":
            st.session_state.update({'logged_in': True, 'role': 'Agent', 'user_email': email_input})
            log_activity(email_input, "Agent Logged In")
            st.rerun()
        else:
            st.error("❌ Invalid Password!")
    st.stop()

# --- 5. LOGOUT ---
if st.sidebar.button("Logout"):
    log_activity(st.session_state['user_email'], "Logged Out")
    st.session_state.update({'logged_in': False, 'role': None, 'user_email': None})
    st.rerun()

engine = get_engine()
months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
channels = ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"]

# ---------------- ADMIN PORTAL ----------------
if st.session_state['role'] == "Admin":
    page = st.sidebar.selectbox("Navigate", ["1. Agent Details", "2. Create Roster", "3. Review & Publish", "4. Update & Swap Requests", "5. Reports", "6. System Activity Log"])

    if page == "1. Agent Details":
        st.header("👤 Agent Management")
        with st.form("agent_form"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Agent Name")
            emp = c2.text_input("Employee ID")
            chan = c3.selectbox("Channel", channels)
            if st.form_submit_button("Save Agent"):
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO agents (emp_id, name, channel) VALUES (:id, :name, :chan)"),
                                 {"id": emp, "name": name, "chan": chan})
                log_activity(st.session_state['user_email'], f"Created Agent: {name} ({emp})")
                st.success(f"Agent {name} added!")

    elif page == "2. Create Roster":
        st.header("📅 Create Monthly Roster (21st - 20th)")
        c1, c2 = st.columns(2)
        chan = c1.selectbox("Select Channel", channels)
        sel_m_name = c2.selectbox("Select Cycle Month", months, index=datetime.now().month-1)
        sel_m = months.index(sel_m_name) + 1
        
        agents_df = pd.read_sql(f"SELECT emp_id, name FROM agents WHERE channel='{chan}'", engine)
        if not agents_df.empty:
            dates = get_roster_dates(sel_m, 2026)
            date_cols = [d.strftime("%Y-%m-%d") for d in dates]
            for d in date_cols: agents_df[d] = "OFF"
            
            st.info("💡 Tip: Excel theke shifts copy kore ekhane paste korte parben.")
            edited_df = st.data_editor(agents_df, hide_index=True)
            
            if st.button("Save Roster Data"):
                with engine.begin() as conn:
                    for _, row in edited_df.iterrows():
                        for d_str in date_cols:
                            conn.execute(text("""INSERT INTO rosters (emp_id, shift_date, shift_type, is_published) 
                                           VALUES (:id, :date, :type, FALSE) ON CONFLICT (emp_id, shift_date) 
                                           DO UPDATE SET shift_type=EXCLUDED.shift_type"""), 
                                           {"id": row['emp_id'], "date": d_str, "type": row[d_str]})
                log_activity(st.session_state['user_email'], f"Saved Roster Draft for {chan} ({sel_m_name})")
                st.success("Data saved!")

    elif page == "3. Review & Publish":
        st.header("📢 Review & Publish")
        chan = st.selectbox("Select Channel", channels)
        data = pd.read_sql(f"SELECT r.emp_id, a.name, r.shift_date, r.shift_type FROM rosters r JOIN agents a ON r.emp_id = a.emp_id WHERE a.channel='{chan}' AND r.is_published=FALSE", engine)
        if not data.empty:
            pivot = data.pivot(index=['emp_id','name'], columns='shift_date', values='shift_type')
            st.dataframe(pivot)
            if st.button("🚀 Publish Roster"):
                with engine.begin() as conn:
                    conn.execute(text("UPDATE rosters SET is_published=TRUE FROM agents WHERE rosters.emp_id = agents.emp_id AND agents.channel=:chan"), {"chan": chan})
                log_activity(st.session_state['user_email'], f"Published Roster for {chan}")
                st.success("Published!")
        else: st.info("No unpublished roster found.")

    elif page == "6. System Activity Log":
        st.header("📜 System Activity Log")
        logs = pd.read_sql("SELECT user_identity as \"User\", action_details as \"Action\", action_time as \"Time\" FROM activity_logs ORDER BY action_time DESC LIMIT 150", engine)
        st.dataframe(logs, use_container_width=True)

# ---------------- AGENT PORTAL (Summary) ----------------
else:
    a_page = st.sidebar.selectbox("Navigate", ["Published Roster", "Swap Request History"])
    if a_page == "Published Roster":
        st.header("📖 Published Roster View")
        sel_c = st.selectbox("Channel", channels)
        data = pd.read_sql(f"SELECT a.name, r.shift_date, r.shift_type FROM rosters r JOIN agents a ON r.emp_id = a.emp_id WHERE a.channel='{sel_c}' AND r.is_published=TRUE", engine)
        if not data.empty:
            st.dataframe(data.pivot(index='name', columns='shift_date', values='shift_type'))
