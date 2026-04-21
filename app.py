import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta, date

# --- 1. DATABASE CONNECTION ---
def get_connection():
    # Apnar deya finalized pooling URI
    conn_str = "postgresql://postgres.cvmuxfdixhtbuuxqcijl:M198961Asik%21@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
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
    page = st.sidebar.selectbox("Navigate", ["1. Agent Details", "2. Create Roster", "3. Review & Publish", "4. Swap Requests", "5. Reports"])

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
                except Exception as e:
                    st.error(f"Error: {e}")

    elif page == "2. Create Roster":
        st.header("📅 Monthly Roster Creation")
        # Roster creation logic here (Same as before)
        st.info("Agent list load korar age Agent Details-e data entry korun.")

# ---------------- AGENT PORTAL ----------------
else:
    st.header("📋 Agent View")
    st.write("Ekhane agents ra tader shift dekhte pabe.")
