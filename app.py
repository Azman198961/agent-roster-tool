import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta, date
from psycopg2 import extras

# --- DATABASE CONNECTION ---
def get_connection():
    return psycopg2.connect(
        dbname="roster_db",
        user="postgres",
        password="Win@1234", # <--- Reset kora password ta ekhane din
        host="localhost",
        port="5432"
    )

# --- HELPER: DATE GENERATOR (21st to 20th) ---
def get_roster_dates(target_month, target_year):
    # Current cycle: 21st of PREVIOUS month to 20th of TARGET month
    if target_month == 1:
        start_date = date(target_year - 1, 12, 21)
    else:
        start_date = date(target_year, target_month - 1, 21)
    
    end_date = date(target_year, target_month, 20)
    
    delta = end_date - start_date
    return [start_date + timedelta(days=i) for i in range(delta.days + 1)]

# --- APP SETUP ---
st.set_page_config(page_title="Support Roster Tool", layout="wide")
st.sidebar.title("Navigation")
auth_mode = st.sidebar.radio("Authorization", ["Admin Portal", "Agent Portal"])

# ---------------- ADMIN PORTAL ----------------
if auth_mode == "Admin Portal":
    page = st.sidebar.selectbox("Page", ["1. Agent Details", "2. Create Roster", "3. Review & Publish", "4. Update & Swap Requests", "5. Reports"])

    # 1. AGENT DETAILS
    if page == "1. Agent Details":
        st.header("Agent Management")
        with st.form("add_agent"):
            col1, col2, col3 = st.columns(3)
            name = col1.text_input("Agent Name")
            emp_id = col2.text_input("Employee ID")
            channel = col3.selectbox("Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
            if st.form_submit_button("Save Agent"):
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO agents (emp_id, name, channel) VALUES (%s, %s, %s)", (emp_id, name, channel))
                conn.commit()
                st.success(f"Agent {name} added!")

    # 2. CREATE ROSTER
    elif page == "2. Create Roster":
        st.header("Step 2: Create Roster")
        col1, col2 = st.columns(2)
        sel_channel = col1.selectbox("Select Channel", ["Inbound", "Live Chat", "Report Issue", "Email & Complaint"])
        
        today = date.today()
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        sel_month_name = col2.selectbox("Select Month Cycle", months, index=today.month-1)
        sel_month = months.index(sel_month_name) + 1
        
        dates = get_roster_dates(sel_month, today.year)
        date_cols = [d.strftime("%Y-%m-%d") for d in dates]
        
        conn = get_connection()
        agents_df = pd.read_sql(f"SELECT emp_id, name FROM agents WHERE channel='{sel_channel}'", conn)
        conn.close()

        if not agents_df.empty:
            # Create a matrix
            for d_col in date_cols:
                agents_df[d_col] = "Day Off"
            
            st.write(f"Editing Roster for {sel_month_name} (21st to 20th)")
            edited_df = st.data_editor(agents_df, hide_index=True)
            
            if st.button("Save Draft"):
                conn = get_connection()
                cur = conn.cursor()
                for _, row in edited_df.iterrows():
                    eid = row['emp_id']
                    for d_str in date_cols:
                        shift = row[d_str]
                        # Check if exists, then update or insert
                        cur.execute("""
                            INSERT INTO rosters (emp_id, shift_date, shift_type, is_published)
                            VALUES (%s, %s, %s, FALSE)
                            ON CONFLICT DO NOTHING
                        """, (eid, d_str, shift))
                conn.commit()
                st.success("Roster saved as draft!")
        else:
            st.warning("No agents found in this channel.")

    # 4. UPDATE & SWAP REQUESTS
    elif page == "4. Update & Swap Requests":
        st.subheader("Swap Requests from Agents")
        conn = get_connection()
        # Logic to show Pending Swaps and Approve/Deny buttons
        swaps = pd.read_sql("SELECT * FROM swap_requests WHERE status='Pending'", conn)
        st.table(swaps)
        st.info("Approval logic will auto-update the Roster table.")

# ---------------- AGENT PORTAL ----------------
else:
    agent_page = st.sidebar.selectbox("Page", ["Published Roster", "Swap Request"])
    
    if agent_page == "Swap Request":
        st.header("Generate Swap Request")
        # Swap logic selection
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Swap Request By")
            my_name = st.text_input("Your Name/ID")
            my_date = st.date_input("Your Shift Date")
        with col2:
            st.subheader("Swap With")
            other_name = st.text_input("Colleague Name/ID")
            other_date = st.date_input("Their Shift Date")
            
        if st.button("Submit Request"):
            st.success("Request sent to Admin!")