import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, date

# --- 1. DATABASE CONNECTION (SQLAlchemy) ---
def get_engine():
    try:
        user = "postgres.cvmuxfdixhtbuuxqcijl"
        password = "M198961Asik%21"  
        host = "aws-1-ap-southeast-1.pooler.supabase.com"
        port = "5432"
        dbname = "postgres"
        
        # SQLAlchemy connection string
        conn_str = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"
        
        # পলিং সমস্যা এড়াতে pool_pre_ping ব্যবহার করা হয়েছে
        engine = create_engine(conn_str, pool_pre_ping=True)
        return engine
    except Exception as e:
        st.error(f"❌ Database Connection Error: {e}")
        return None

# --- ACTIVITY LOGGING FUNCTION ---
def log_activity(user_identity, action):
    try:
        temp_engine = get_engine()
        with temp_engine.begin() as conn:
            conn.execute(
                text("INSERT INTO activity_logs (user_identity, action_details) VALUES (:user, :action)"),
                {"user": user_identity, "action": action}
            )
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
    email_input = st.text_input("Enter Email / Username")
    role = st.selectbox("Select Role", ["Admin", "Agent"])
    pwd = st.text_input("Enter Password", type="password")
    
    if st.button("Login"):
        if not email_input:
            st.warning("⚠️ Please enter your email.")
        elif role == "Admin" and pwd == "Win@1234":
            st.session_state.update({'logged_in': True, 'role': 'Admin', 'user_email': email_input})
            log_activity(email_input, "Logged in as Admin")
            st.rerun()
        elif role == "Agent" and pwd == "123456":
            st.session_state.update({'logged_in': True, 'role': 'Agent', 'user_email': email_input})
            log_activity(email_input, "Logged in as Agent")
            st.rerun()
        else:
            st.error("❌ Invalid Password!")
    st.stop()

# --- 5. LOGOUT ---
if st.sidebar.button("Logout"):
    log_activity(st.session_state['user_email'], "Logged out")
    st.session_state.update({'logged_in': False, 'role': None, 'user_email': None})
    st.rerun()

# Initialize Engine
engine = get_engine()
months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
channels = ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"]

# ---------------- ADMIN PORTAL ----------------
if st.session_state['role'] == "Admin":
    page = st.sidebar.selectbox("Navigate", [
        "1. Agent Details", 
        "2. Create Roster", 
        "3. Review & Publish", 
        "4. Update & Swap Requests", 
        "5. Reports",
        "6. System Activity Log"
    ])

    if page == "1. Agent Details":
        st.header("👤 Agent Management")
        with st.form("agent_form"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Agent Name")
            emp = c2.text_input("Employee ID")
            chan = c3.selectbox("Channel", channels)
            if st.form_submit_button("Save Agent"):
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO agents (emp_id, name, channel) VALUES (:id, :name, :chan)"),
                        {"id": emp, "name": name, "chan": chan}
                    )
                log_activity(st.session_state['user_email'], f"Added Agent: {name} ({emp})")
                st.success(f"Agent {name} added!")

    elif page == "2. Create Roster":
        st.header("📅 Create Monthly Roster (21st - 20th)")
        c1, c2 = st.columns(2)
        chan = c1.selectbox("Select Channel", channels)
        sel_m_name = c2.selectbox("Select Cycle Month", months, index=datetime.now().month-1)
        sel_m = months.index(sel_m_name) + 1
        
        # Read agents
        agents_df = pd.read_sql(text(f"SELECT emp_id, name FROM agents WHERE channel='{chan}'"), engine)
        if not agents_df.empty:
            dates = get_roster_dates(sel_m, 2026)
            date_cols = [d.strftime("%Y-%m-%d") for d in dates]
            for d in date_cols: agents_df[d] = "OFF"
            
            st.info("💡 Tip: Excel থেকে কপি করে এখানে পেস্ট করতে পারবেন।")
            edited_df = st.data_editor(agents_df, hide_index=True)
            
            if st.button("Save Roster Data"):
                with engine.begin() as conn:
                    for _, row in edited_df.iterrows():
                        for d_str in date_cols:
                            conn.execute(text("""
                                INSERT INTO rosters (emp_id, shift_date, shift_type, is_published) 
                                VALUES (:id, :date, :type, FALSE) 
                                ON CONFLICT (emp_id, shift_date) 
                                DO UPDATE SET shift_type = EXCLUDED.shift_type
                            """), {"id": row['emp_id'], "date": d_str, "type": row[d_str]})
                log_activity(st.session_state['user_email'], f"Saved Draft Roster for {chan} ({sel_m_name})")
                st.success("Draft saved successfully!")

    elif page == "3. Review & Publish":
        st.header("📢 Review & Publish")
        chan = st.selectbox("Select Channel", channels)
        query = text(f"""
            SELECT r.emp_id, a.name, r.shift_date, r.shift_type 
            FROM rosters r JOIN agents a ON r.emp_id = a.emp_id 
            WHERE a.channel='{chan}' AND r.is_published=FALSE
        """)
        data = pd.read_sql(query, engine)
        if not data.empty:
            pivot = data.pivot(index=['emp_id','name'], columns='shift_date', values='shift_type')
            st.dataframe(pivot)
            if st.button("🚀 Publish Roster"):
                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE rosters SET is_published=TRUE FROM agents 
                        WHERE rosters.emp_id = agents.emp_id AND agents.channel=:chan
                    """), {"chan": chan})
                log_activity(st.session_state['user_email'], f"Published Roster for {chan}")
                st.success("Roster Published!")
        else: st.info("No unpublished roster found.")

    elif page == "4. Update & Swap Requests":
        tab1, tab2 = st.tabs(["Update Roster", "Swap Approvals"])
        with tab1:
            st.subheader("🛠 Bulk Update Published Roster")
            # Filter logic here...
            st.info("Agent roster আপডেট করলে স্বয়ংক্রিয়ভাবে লগ জেনারেট হবে।")

        with tab2:
            st.subheader("🔄 Pending Swap Requests")
            swaps_query = text("""
                SELECT s.id, a1.name as req_by, a2.name as swap_with, s.req_date_1, s.req_date_2, s.status 
                FROM swap_requests s JOIN agents a1 ON s.requested_by_id = a1.emp_id 
                JOIN agents a2 ON s.swap_with_id = a2.emp_id WHERE s.status='Pending'
            """)
            swaps = pd.read_sql(swaps_query, engine)
            if not swaps.empty:
                for _, s_row in swaps.iterrows():
                    st.write(f"**{s_row['req_by']}** ({s_row['req_date_1']}) ↔️ **{s_row['swap_with']}** ({s_row['req_date_2']})")
                    if st.button(f"Approve ID {s_row['id']}"):
                        # (Swap logic executes here)
                        log_activity(st.session_state['user_email'], f"Approved Swap ID {s_row['id']}")
                        st.rerun()

    elif page == "6. System Activity Log":
        st.header("📜 System Activity Log")
        try:
            log_sql = text("SELECT user_identity as \"User\", action_details as \"Action\", action_time as \"Time\" FROM activity_logs ORDER BY action_time DESC LIMIT 150")
            logs = pd.read_sql(log_sql, engine)
            st.dataframe(logs, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading logs: {e}")

# ---------------- AGENT PORTAL ----------------
else:
    a_page = st.sidebar.selectbox("Navigate", ["Published Roster", "Swap Request"])
    if a_page == "Published Roster":
        st.header("📖 Published Roster View")
        sel_c = st.selectbox("Channel", channels)
        view_query = text(f"""
            SELECT a.name, r.shift_date, r.shift_type FROM rosters r 
            JOIN agents a ON r.emp_id = a.emp_id 
            WHERE a.channel='{sel_c}' AND r.is_published=TRUE
        """)
        data = pd.read_sql(view_query, engine)
        if not data.empty:
            st.dataframe(data.pivot(index='name', columns='shift_date', values='shift_type'))
