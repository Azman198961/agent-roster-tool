import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta, date

# --- 1. DATABASE CONNECTION ---
def get_connection():
    try:
        conn_str = "postgresql://postgres.cvmuxfdixhtbuuxcijl:M198961Asik%21@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
        return psycopg2.connect(conn_str)
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

# --- 2. LOGIN LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None

st.set_page_config(page_title="CX Roster Management", layout="wide")

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
            st.error("❌ Invalid Password!")
    st.stop()

# --- 3. APP LOGIC (AFTER LOGIN) ---
role = st.session_state['role']
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

if role == "Admin":
    st.sidebar.title("Admin Portal")
    page = st.sidebar.selectbox("Navigate", ["1. Agent Details", "2. Create Roster", "3. Review & Publish"])
    
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
                if conn:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO agents (emp_id, name, channel) VALUES (%s, %s, %s)", (emp_id, name, channel))
                    conn.commit()
                    st.success(f"Agent {name} added successfully!")
                    conn.close()

    # PAGE 2: CREATE ROSTER (FIXED LOGIC)
    elif page == "2. Create Roster":
        st.header("📅 Monthly Roster Creation")
        # Load agents for selected channel
        sel_channel = st.selectbox("Select Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
        conn = get_connection()
        if conn:
            agents_df = pd.read_sql(f"SELECT emp_id, name FROM agents WHERE channel='{sel_channel}'", conn)
            conn.close()
            
            if not agents_df.empty:
                st.write("Edit Shifts below (Double-click cells):")
                # Add columns for dates if needed or simple shifts
                st.data_editor(agents_df, hide_index=True)
            else:
                st.warning("No agents found. Add agents first!")
