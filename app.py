import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta, date

# --- 1. DATABASE CONNECTION ---
def get_connection():
    try:
        user = "postgres.cvmuxfdixhtbuuxqcijl"
        password = "M198961Asik%21"  
        host = "aws-1-ap-southeast-1.pooler.supabase.com"
        port = "5432"
        dbname = "postgres"
        conn_str = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"
        return psycopg2.connect(conn_str)
    except Exception as e:
        st.error(f"❌ Database Connection Error: {e}")
        return None

# --- NEW: LOGGING FUNCTION ---
def log_activity(user_identity, action):
    try:
        conn_log = get_connection()
        if conn_log:
            cur = conn_log.cursor()
            cur.execute("INSERT INTO activity_logs (user_identity, action_details) VALUES (%s, %s)", (user_identity, action))
            conn_log.commit()
            cur.close()
            conn_log.close()
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
    email_input = st.text_input("Enter Your Email") # কে লগইন করছে তা ট্র্যাক করতে
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

conn = get_connection()
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
        "6. System Activity Log" # নতুন মেনু
    ])

    if page == "1. Agent Details":
        st.header("👤 Agent Management")
        with st.form("agent_form"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Agent Name")
            emp = c2.text_input("Employee ID")
            chan = c3.selectbox("Channel", channels)
            if st.form_submit_button("Save Agent"):
                cur = conn.cursor()
                cur.execute("INSERT INTO agents (emp_id, name, channel) VALUES (%s,%s,%s)", (emp, name, chan))
                conn.commit()
                log_activity(st.session_state['user_email'], f"Created Agent: {name} ({emp})")
                st.success(f"Agent {name} added!")

    elif page == "2. Create Roster":
        st.header("📅 Create Monthly Roster (21st - 20th)")
        c1, c2 = st.columns(2)
        chan = c1.selectbox("Select Channel", channels)
        sel_m_name = c2.selectbox("Select Cycle Month", months, index=datetime.now().month-1)
        sel_m = months.index(sel_m_name) + 1
        
        agents_df = pd.read_sql(f"SELECT emp_id, name FROM agents WHERE channel='{chan}'", conn)
        if not agents_df.empty:
            dates = get_roster_dates(sel_m, 2026)
            date_cols = [d.strftime("%Y-%m-%d") for d in dates]
            for d in date_cols: agents_df[d] = "OFF"
            
            st.info("💡 Tip: Excel theke shifts copy kore ekhane paste korte parben.")
            edited_df = st.data_editor(agents_df, hide_index=True)
            
            if st.button("Save Roster Data"):
                cur = conn.cursor()
                for _, row in edited_df.iterrows():
                    for d_str in date_cols:
                        cur.execute("""INSERT INTO rosters (emp_id, shift_date, shift_type, is_published) 
                                       VALUES (%s,%s,%s,FALSE) ON CONFLICT (emp_id, shift_date) 
                                       DO UPDATE SET shift_type=EXCLUDED.shift_type""", (row['emp_id'], d_str, row[d_str]))
                conn.commit()
                log_activity(st.session_state['user_email'], f"Saved Roster Draft for {chan} ({sel_m_name})")
                st.success("Data saved! Review page-e publish korun.")

    elif page == "3. Review & Publish":
        st.header("📢 Review & Publish")
        chan = st.selectbox("Select Channel", channels)
        data = pd.read_sql(f"SELECT r.emp_id, a.name, r.shift_date, r.shift_type FROM rosters r JOIN agents a ON r.emp_id = a.emp_id WHERE a.channel='{chan}' AND r.is_published=FALSE", conn)
        if not data.empty:
            pivot = data.pivot(index=['emp_id','name'], columns='shift_date', values='shift_type')
            st.dataframe(pivot)
            if st.button("🚀 Publish Roster"):
                cur = conn.cursor()
                cur.execute(f"UPDATE rosters SET is_published=TRUE FROM agents WHERE rosters.emp_id = agents.emp_id AND agents.channel='{chan}'")
                conn.commit()
                log_activity(st.session_state['user_email'], f"Published Roster for Channel: {chan}")
                st.success("Roster Published Successfully!")
        else: st.info("No unpublished roster found.")

    elif page == "4. Update & Swap Requests":
        tab1, tab2 = st.tabs(["Update Roster", "Swap Approvals"])
        with tab1:
            st.subheader("🛠 Bulk Update Published Roster")
            col1, col2, col3 = st.columns(3)
            u_chan = col1.selectbox("Filter Channel", channels)
            u_m_name = col2.selectbox("Filter Month", months)
            
            agent_names_df = pd.read_sql(f"SELECT name FROM agents WHERE channel='{u_chan}'", conn)
            if not agent_names_df.empty:
                agents_list = agent_names_df['name'].tolist()
                u_agent = col3.selectbox("Select Agent", agents_list)
                
                sel_m = months.index(u_m_name) + 1
                dates = get_roster_dates(sel_m, 2026)
                date_strs = [d.strftime("%Y-%m-%d") for d in dates]
                
                agent_data = pd.read_sql(f"""SELECT r.shift_date, r.shift_type, r.label FROM rosters r 
                                             JOIN agents a ON r.emp_id = a.emp_id 
                                             WHERE a.name='{u_agent}' AND r.shift_date BETWEEN '{date_strs[0]}' AND '{date_strs[-1]}'""", conn)
                
                if not agent_data.empty:
                    updated_df = st.data_editor(agent_data, hide_index=True)
                    if st.button("Bulk Update"):
                        cur = conn.cursor()
                        e_id = pd.read_sql(f"SELECT emp_id FROM agents WHERE name='{u_agent}'", conn)['emp_id'][0]
                        for _, row in updated_df.iterrows():
                            cur.execute("UPDATE rosters SET shift_type=%s, label='Updated/Changed' WHERE emp_id=%s AND shift_date=%s", 
                                        (row['shift_type'], e_id, row['shift_date']))
                        conn.commit()
                        log_activity(st.session_state['user_email'], f"Updated Roster for Agent: {u_agent}")
                        st.success(f"Updates saved for {u_agent}!")

        with tab2:
            st.subheader("🔄 Pending Swap Requests")
            swaps = pd.read_sql("""SELECT s.id, a1.name as req_by, a2.name as swap_with, s.req_date_1, s.req_date_2, s.status 
                                   FROM swap_requests s JOIN agents a1 ON s.requested_by_id = a1.emp_id 
                                   JOIN agents a2 ON s.swap_with_id = a2.emp_id WHERE s.status='Pending'""", conn)
            if not swaps.empty:
                for _, s_row in swaps.iterrows():
                    st.write(f"**{s_row['req_by']}** ({s_row['req_date_1']}) ↔️ **{s_row['swap_with']}** ({s_row['req_date_2']})")
                    if st.button(f"Approve ID {s_row['id']}"):
                        cur = conn.cursor()
                        id1 = pd.read_sql(f"SELECT emp_id FROM agents WHERE name='{s_row['req_by']}'", conn)['emp_id'][0]
                        id2 = pd.read_sql(f"SELECT emp_id FROM agents WHERE name='{s_row['swap_with']}'", conn)['emp_id'][0]
                        s1 = pd.read_sql(f"SELECT shift_type FROM rosters WHERE emp_id='{id1}' AND shift_date='{s_row['req_date_1']}'", conn)['shift_type'][0]
                        s2 = pd.read_sql(f"SELECT shift_type FROM rosters WHERE emp_id='{id2}' AND shift_date='{s_row['req_date_2']}'", conn)['shift_type'][0]
                        
                        cur.execute("UPDATE rosters SET shift_type=%s, label='Swapped' WHERE emp_id=%s AND shift_date=%s", (s2, id1, s_row['req_date_1']))
                        cur.execute("UPDATE rosters SET shift_type=%s, label='Swapped' WHERE emp_id=%s AND shift_date=%s", (s1, id2, s_row['req_date_2']))
                        cur.execute("UPDATE swap_requests SET status='Approved', updated_on=CURRENT_TIMESTAMP WHERE id=%s", (s_row['id'],))
                        conn.commit()
                        log_activity(st.session_state['user_email'], f"Approved Swap ID {s_row['id']} ({s_row['req_by']} <-> {s_row['swap_with']})")
                        st.rerun()
            else: st.write("No pending requests.")

    elif page == "5. Reports":
        st.header("📊 Total Overview & Manpower Reports")
        rep_date = st.date_input("Select Date", date.today())
        rep_data = pd.read_sql(f"""SELECT a.channel, r.shift_type, COUNT(*) as count 
                                   FROM rosters r JOIN agents a ON r.emp_id = a.emp_id 
                                   WHERE r.shift_date='{rep_date}' GROUP BY a.channel, r.shift_type""", conn)
        st.write(f"Manpower on {rep_date}:")
        st.dataframe(rep_data)

    elif page == "6. System Activity Log":
        st.header("📜 System Activity Log")
        try:
            logs = pd.read_sql("SELECT user_identity as \"User\", action_details as \"Action\", action_time as \"Time\" FROM activity_logs ORDER BY action_time DESC LIMIT 150", conn)
            st.dataframe(logs, use_container_width=True)
        except:
            st.error("Activity logs table issue. Please check database.")

# ---------------- AGENT PORTAL ----------------
else:
    a_page = st.sidebar.selectbox("Navigate", ["Published Roster", "Swap Request", "Swap Request Overview"])
    
    if a_page == "Published Roster":
        st.header("📖 Published Roster View")
        c1, c2 = st.columns(2)
        sel_c = c1.selectbox("Channel", channels)
        sel_m_name = c2.selectbox("Month", months)
        sel_m = months.index(sel_m_name) + 1
        dates = get_roster_dates(sel_m, 2026)
        
        data = pd.read_sql(f"""SELECT a.name, r.shift_date, r.shift_type, r.label FROM rosters r 
                               JOIN agents a ON r.emp_id = a.emp_id 
                               WHERE a.channel='{sel_c}' AND r.is_published=TRUE 
                               AND r.shift_date BETWEEN '{dates[0]}' AND '{dates[-1]}'""", conn)
        if not data.empty:
            data['display'] = data['shift_type'] + " (" + data['label'].fillna('') + ")"
            pivot = data.pivot(index='name', columns='shift_date', values='display')
            st.dataframe(pivot)
        else: st.info("No roster published for this selection.")

    elif a_page == "Swap Request":
        st.header("🔄 Generate Swap Request")
        agents = pd.read_sql(f"SELECT emp_id, name FROM agents", conn)
        
        with st.container(border=True):
            req_name = st.selectbox("Your Name", agents['name'])
            req_date = st.date_input("Your Shift Date")
            with_name = st.selectbox("Peer Name", agents[agents['name']!=req_name]['name'])
            with_date = st.date_input("Peer Shift Date")
            
        if st.button("Submit Request"):
            id1 = agents[agents['name']==req_name]['emp_id'].values[0]
            id2 = agents[agents['name']==with_name]['emp_id'].values[0]
            cur = conn.cursor()
            cur.execute("INSERT INTO swap_requests (requested_by_id, swap_with_id, req_date_1, req_date_2) VALUES (%s,%s,%s,%s)", 
                        (id1, id2, req_date, with_date))
            conn.commit()
            log_activity(st.session_state['user_email'], f"Agent {req_name} requested swap with {with_name}")
            st.success("Swap request sent to Admin!")

    elif a_page == "Swap Request Overview":
        st.header("🕒 Swap Request History")
        history = pd.read_sql("""SELECT s.applied_on as "Requested Date", a1.name as "Requested By", 
                                 a2.name as "Swap With", s.req_date_1 as "Date 1", s.req_date_2 as "Date 2", 
                                 s.status, s.updated_on as "Updated Date" 
                                 FROM swap_requests s JOIN agents a1 ON s.requested_by_id = a1.emp_id 
                                 JOIN agents a2 ON s.swap_with_id = a2.emp_id ORDER BY s.applied_on DESC""", conn)
        st.dataframe(history)
