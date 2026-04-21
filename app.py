import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta, date

# --- 1. DATABASE CONNECTION ---
def get_connection():
    try:
        # Apnar deya Session Pooler details onujayi
        user = "postgres.cvmuxfdixhtbuuxqcijl"
        password = "M198961Asik%21"  # M198961Asik! encoded
        host = "aws-1-ap-southeast-1.pooler.supabase.com"
        port = "5432"
        dbname = "postgres"
        
        conn_str = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"
        return psycopg2.connect(conn_str)
    except Exception as e:
        st.error(f"❌ Database Connection Error: {e}")
        return None

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
    st.session_state.update({'logged_in': False, 'role': None, 'emp_id': None})

st.set_page_config(page_title="CX Advanced Roster Tool", layout="wide")

# --- 4. LOGIN INTERFACE ---
if not st.session_state['logged_in']:
    st.title("🚀 CX Roster Management System")
    role = st.selectbox("Select Role", ["Admin", "Agent"])
    pwd = st.text_input("Password", type="password")
    e_id = ""
    if role == "Agent":
        e_id = st.text_input("Employee ID")

    if st.button("Login"):
        if role == "Admin" and pwd == "Win@1234":
            st.session_state.update({'logged_in': True, 'role': 'Admin'})
            st.rerun()
        elif role == "Agent" and pwd == "123456" and e_id:
            st.session_state.update({'logged_in': True, 'role': 'Agent', 'emp_id': e_id})
            st.rerun()
        else:
            st.error("Invalid Credentials!")
    st.stop()

# --- 5. LOGOUT ---
if st.sidebar.button("Logout"):
    st.session_state.update({'logged_in': False, 'role': None})
    st.rerun()

role = st.session_state['role']
conn = get_connection()

# ---------------- ADMIN PORTAL ----------------
if role == "Admin":
    page = st.sidebar.selectbox("Navigate", ["1. Agent Details", "2. Create Roster", "3. Review & Publish", "4. Update & Swap Requests", "5. Reports"])

    if page == "1. Agent Details":
        st.header("👤 Agent Management")
        with st.form("agent_form"):
            n, i, c = st.columns(3)
            name = n.text_input("Name")
            emp = i.text_input("Emp ID")
            chan = c.selectbox("Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
            if st.form_submit_button("Save"):
                cur = conn.cursor()
                cur.execute("INSERT INTO agents (emp_id, name, channel) VALUES (%s,%s,%s)", (emp, name, chan))
                conn.commit()
                st.success("Saved!")

    elif page == "2. Create Roster":
        st.header("📅 Create Monthly Roster")
        c1, c2 = st.columns(2)
        chan = c1.selectbox("Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        sel_m = months.index(c2.selectbox("Select Month", months, index=datetime.now().month-1)) + 1
        
        agents_df = pd.read_sql(f"SELECT emp_id, name FROM agents WHERE channel='{chan}'", conn)
        if not agents_df.empty:
            dates = get_roster_dates(sel_m, 2026)
            date_cols = [d.strftime("%Y-%m-%d") for d in dates]
            for d in date_cols: agents_df[d] = "OFF"
            
            st.info("💡 Tip: You can copy-paste shift types across cells.")
            edited_df = st.data_editor(agents_df, hide_index=True)
            
            if st.button("Save Roster Data"):
                cur = conn.cursor()
                for _, row in edited_df.iterrows():
                    for d_str in date_cols:
                        cur.execute("""INSERT INTO rosters (emp_id, shift_date, shift_type, is_published) 
                                       VALUES (%s,%s,%s,FALSE) ON CONFLICT (emp_id, shift_date) 
                                       DO UPDATE SET shift_type=EXCLUDED.shift_type""", (row['emp_id'], d_str, row[d_str]))
                conn.commit()
                st.success("Data saved for Review.")

    elif page == "3. Review & Publish":
        st.header("📢 Review & Publish")
        chan = st.selectbox("Select Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
        view_df = pd.read_sql(f"SELECT r.emp_id, a.name, r.shift_date, r.shift_type FROM rosters r JOIN agents a ON r.emp_id = a.emp_id WHERE a.channel='{chan}' AND r.is_published=FALSE", conn)
        
        if not view_df.empty:
            st.dataframe(view_df.pivot(index=['emp_id', 'name'], columns='shift_date', values='shift_type'))
            if st.button("🚀 Publish Roster Now"):
                cur = conn.cursor()
                cur.execute(f"UPDATE rosters SET is_published=TRUE FROM agents WHERE rosters.emp_id = agents.emp_id AND agents.channel='{chan}'")
                conn.commit()
                st.success("Roster is now live for Agents!")
        else: st.write("No unpublished roster found.")

    elif page == "4. Update & Swap Requests":
        tab1, tab2 = st.tabs(["Update Roster", "Swap Requests"])
        
        with tab1:
            st.subheader("🛠 Bulk Update Published Roster")
            col1, col2, col3 = st.columns(3)
            u_chan = col1.selectbox("Update Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
            u_month = col2.selectbox("Update Month", ["April", "May", "June"]) # Expand list
            u_agent = col3.selectbox("Agent Name", pd.read_sql(f"SELECT name FROM agents WHERE channel='{u_chan}'", conn)['name'])
            
            # Logic for update visibility and saving...
            st.warning("Feature: After update, label will show 'Updated/Changed'")

        with tab2:
            st.subheader("🔄 Agent Swap Requests")
            swaps = pd.read_sql("""SELECT s.id, a1.name as req_by, a2.name as swap_with, s.req_date_1, s.req_date_2, s.status 
                                   FROM swap_requests s JOIN agents a1 ON s.requested_by_id = a1.emp_id 
                                   JOIN agents a2 ON s.swap_with_id = a2.emp_id WHERE s.status='Pending'""", conn)
            st.table(swaps)
            # Add buttons for Approve/Decline based on Swap ID...

    elif page == "5. Reports":
        st.header("📊 Manpower Overview")
        # Custom logic for Manpower count per date...
        st.info("Reporting Dashboard: Day-off/Leave/Shift counts will appear here.")

# ---------------- AGENT PORTAL ----------------
else:
    a_page = st.sidebar.selectbox("Menu", ["Published Roster", "Swap Request", "Request Overview"])
    my_id = st.session_state['emp_id']

    if a_page == "Published Roster":
        st.header("📖 My Roster")
        # Pivot view for the selected agent...
        
    elif a_page == "Swap Request":
        st.header("🔄 Generate Swap Request")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Swap Requested By")
            st.write(f"Agent: {my_id}")
            d1 = st.date_input("My Shift Date")
        with col2:
            st.subheader("Swap With")
            other_agent = st.selectbox("Select Peer Agent", pd.read_sql("SELECT name FROM agents", conn)['name'])
            d2 = st.date_input("Peer's Shift Date")
        
        if st.button("Request Swap"):
            st.success("Swap request sent to Admin.")

    elif a_page == "Request Overview":
        st.header("🕒 My Request Status")
        # History table...
