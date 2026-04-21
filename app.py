import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta, date

# --- 1. DATABASE CONNECTION (Session Pooler - Port 5432) ---
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

# --- 2. LOGIC: DATE GENERATOR (21st to 20th) ---
def get_roster_dates(target_month, target_year):
    if target_month == 1:
        start_date = date(target_year - 1, 12, 21)
    else:
        start_date = date(target_year, target_month - 1, 21)
    end_date = date(target_year, target_month, 20)
    delta = end_date - start_date
    return [start_date + timedelta(days=i) for i in range(delta.days + 1)]

# --- 3. SESSION STATE FOR LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None

st.set_page_config(page_title="CX Roster Tool", layout="wide")

# --- 4. LOGIN INTERFACE ---
if not st.session_state['logged_in']:
    st.title("🔐 CX Roster Login")
    role_choice = st.selectbox("Select Role", ["Admin", "Agent"])
    pwd_input = st.text_input("Enter Password", type="password")
    
    if st.button("Login"):
        if role_choice == "Admin" and pwd_input == "Win@1234":
            st.session_state['logged_in'] = True
            st.session_state['role'] = "Admin"
            st.rerun()
        elif role_choice == "Agent" and pwd_input == "123456":
            st.session_state['logged_in'] = True
            st.session_state['role'] = "Agent"
            st.rerun()
        else:
            st.error("❌ Password bhul! Thik password din.")
    st.stop()

# --- 5. MAIN APP AFTER LOGIN ---
st.sidebar.write(f"Logged in as: **{st.session_state['role']}**")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

role = st.session_state['role']

# ADMIN PORTAL LOGIC
if role == "Admin":
    page = st.sidebar.selectbox("Navigate", ["1. Agent Details", "2. Create Roster", "3. Reports"])
    
    if page == "1. Agent Details":
        st.header("👤 Agent Management")
        with st.form("add_agent"):
            col1, col2, col3 = st.columns(3)
            name = col1.text_input("Agent Name")
            emp_id = col2.text_input("Employee ID")
            channel = col3.selectbox("Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
            if st.form_submit_button("Save Agent"):
                conn = get_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO agents (emp_id, name, channel) VALUES (%s, %s, %s)", (emp_id, name, channel))
                    conn.commit()
                    st.success(f"Agent {name} saved!")
                    conn.close()

    elif page == "2. Create Roster":
        st.header("📅 Create Monthly Roster")
        sel_channel = st.selectbox("Select Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
        
        # Date Setup
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        sel_month_name = st.selectbox("Select Roster Month (Cycle: 21st - 20th)", months, index=datetime.now().month-1)
        sel_month = months.index(sel_month_name) + 1
        
        conn = get_connection()
        if conn:
            agents_df = pd.read_sql(f"SELECT emp_id, name FROM agents WHERE channel='{sel_channel}'", conn)
            conn.close()
            
            if not agents_df.empty:
                dates = get_roster_dates(sel_month, 2026)
                date_cols = [d.strftime("%Y-%m-%d") for d in dates]
                
                # Default value "OFF" set kora
                for d_col in date_cols:
                    agents_df[d_col] = "OFF"
                
                st.write(f"Shift entry for {sel_channel} ({sel_month_name} Cycle)")
                edited_df = st.data_editor(agents_df, hide_index=True)
                
                if st.button("Save & Publish Roster"):
                    conn = get_connection()
                    if conn:
                        cur = conn.cursor()
                        try:
                            for _, row in edited_df.iterrows():
                                e_id = row['emp_id']
                                for d_str in date_cols:
                                    shift = row[d_str]
                                    cur.execute("""
                                        INSERT INTO rosters (emp_id, shift_date, shift_type) 
                                        VALUES (%s, %s, %s)
                                        ON CONFLICT (emp_id, shift_date) DO UPDATE SET shift_type = EXCLUDED.shift_type
                                    """, (e_id, d_str, shift))
                            conn.commit()
                            st.success("Roster Published Successfully!")
                        except Exception as e: st.error(f"Error: {e}")
                        finally: conn.close()
            else:
                st.warning("No agents found in this channel.")

# AGENT PORTAL LOGIC
else:
    st.header("📋 My Shift Roster")
    my_id = st.text_input("Enter your Employee ID to view roster")
    if my_id:
        conn = get_connection()
        if conn:
            query = f"SELECT shift_date, shift_type FROM rosters WHERE emp_id = '{my_id}' ORDER BY shift_date ASC"
            df = pd.read_sql(query, conn)
            conn.close()
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No roster found for this ID.")
