import streamlit as st
import pandas as pd
import numpy as np
import gspread
import json
import os
from google.oauth2.service_account import Credentials
from datetime import datetime
import hashlib

st.set_page_config(page_title="MT-NER ENTERPRISE v13.2", layout="wide")
st.title("🗳️ MT-NER ENTERPRISE v13.2")
st.caption("Mission Tracker - National Election Results | T-SMART + OMNISCORE | OFFLINE READY")
PARTIES = ["APC", "PDP", "LP", "NNPP", "OTHERS"]
OFFLINE_FILE = "offline_reports.json"

@st.cache_resource
def connect_gsheets():
    SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    client = gspread.authorize(Credentials.from_service_account_info(creds_dict, scopes=SCOPE))
    sheet = client.open_by_key(st.secrets["SHEET_ID"])
    tabs = [ws.title for ws in sheet.worksheets()]
    if "AGENTS_DB" not in tabs:
        ws = sheet.add_worksheet("AGENTS_DB", 1000, 10)
        ws.append_row(["OBSERVER_ID","PASSWORD_HASH","ROLE","STATE","LGA","WARD","STATUS"])
        admin_hash = hashlib.sha256("123".encode()).hexdigest()
        ws.append_row(["ADMIN001", admin_hash, "ADMIN", "NATIONAL", "NATIONAL", "NATIONAL", "ACTIVE"])
    if "RAW_DATA" not in tabs:
        ws = sheet.add_worksheet("RAW_DATA", 100000, 20)
        headers = ["TIMESTAMP","OBSERVER_ID","STATE","LGA","WARD","PU_CODE","ELECTION_TYPE"] + PARTIES + ["TOTAL_VOTES","OMNISCORE","T_SMART_SCORE","WINNER","NOTES","SYNC_STATUS"]
        ws.append_row(headers)
    return sheet

# ===== OFFLINE FUNCTIONS ADDED =====
def save_offline(data):
    reports = []
    if os.path.exists(OFFLINE_FILE):
        with open(OFFLINE_FILE, 'r') as f:
            reports = json.load(f)
    reports.append(data)
    with open(OFFLINE_FILE, 'w') as f:
        json.dump(reports, f)

def sync_offline(sheet):
    if os.path.exists(OFFLINE_FILE):
        with open(OFFLINE_FILE, 'r') as f:
            reports = json.load(f)
        count = 0
        for data in reports:
            try:
                sheet.worksheet("RAW_DATA").append_row(data)
                count += 1
            except: pass
        if count == len(reports):
            os.remove(OFFLINE_FILE)
        return count
    return 0
# ===== END OFFLINE FUNCTIONS =====

sheet = connect_gsheets()

def calculate_scores(df):
    df['TOTAL_VOTES'] = df[PARTIES].sum(axis=1)
    df['OMNISCORE'] = 100
    df['OMNISCORE'] -= np.where(df['TOTAL_VOTES'] > 1500, 25, 0)
    df['OMNISCORE'] -= df[PARTIES].apply(lambda x: sum(1 for v in x if v>0 and v%10==0 and v%100!=0))*2
    df['OMNISCORE'] = df['OMNISCORE'].clip(0, 100)
    df['TURNOUT_%'] = (df['TOTAL_VOTES'] / 500) * 100
    df['T_SMART_SCORE'] = (df['OMNISCORE'] * 0.7 + df['TURNOUT_%'] * 0.3).round(2)
    df['WINNER'] = df[PARTIES].idxmax(axis=1)
    return df

def check_login(oid, pwd):
    df = pd.DataFrame(sheet.worksheet("AGENTS_DB").get_all_records())
    user = df[df['OBSERVER_ID'] == oid]
    if not user.empty:
        if hashlib.sha256(pwd.encode()).hexdigest() == user.iloc[0]['PASSWORD_HASH'] and user.iloc[0]['STATUS']=='ACTIVE':
            return user.iloc[0].to_dict()
    return None

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.header("🔒 MT-NER Secure Login")
    with st.form("login"):
        oid = st.text_input("Observer ID")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            u = check_login(oid, pwd)
            if u:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Invalid Login")
    st.info("TEST: ID=ADMIN001 | PASS=123")
    st.stop()

user = st.session_state.user
st.sidebar.success(f"User: {user['OBSERVER_ID']} | {user['ROLE']}")

# ===== SYNC BUTTON ADDED TO SIDEBAR =====
if st.sidebar.button("🔄 SYNC OFFLINE DATA"):
    with st.spinner("Syncing..."):
        count = sync_offline(sheet)
        if count > 0: st.sidebar.success(f"Synced {count} reports to HQ!")
        else: st.sidebar.info("No offline data to sync")

if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()

st.header(f"Welcome {user['OBSERVER_ID']}")
with st.form("report"):
    state = st.text_input("State", user['STATE'])
    lga = st.text_input("LGA", user['LGA'])
    ward = st.text_input("Ward", user['WARD'])
    pu = st.text_input("PU Code")
    votes = {p: st.number_input(p, 0, 10000, 0) for p in PARTIES}
    notes = st.text_area("Notes")
    
    # ===== 2 BUTTONS ADDED HERE =====
    c1, c2 = st.columns(2)
    submit_online = c1.form_submit_button("📶 SUBMIT ONLINE")
    save_off = c2.form_submit_button("💾 SAVE OFFLINE")
    
    if submit_online or save_off:
        df_temp = pd.DataFrame([votes])
        df_temp = calculate_scores(df_temp)
        status = "ONLINE" if submit_online else "OFFLINE"
        data = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user['OBSERVER_ID'], state, lga, ward, pu, "PRESIDENTIAL",
                *votes.values(), df_temp['TOTAL_VOTES'][0], df_temp['OMNISCORE'][0], df_temp['T_SMART_SCORE'][0], df_temp['WINNER'][0], notes, status]
        
        if submit_online:
            try:
                sheet.worksheet("RAW_DATA").append_row(data)
                st.success("✅ Report Submitted to HQ")
            except:
                st.error("No Internet. Click 'SAVE OFFLINE' instead")
        if save_off:
            save_offline(data)
            st.warning("💾 Saved to phone. Click 'SYNC OFFLINE DATA' in sidebar when online")

if user['ROLE'] == 'ADMIN':
    st.header("📊 HQ DASHBOARD - LIVE RESULTS")
    df = pd.DataFrame(sheet.worksheet("RAW_DATA").get_all_records())
    if not df.empty:
        df[PARTIES] = df[PARTIES].apply(pd.to_numeric)
        level = st.selectbox("View Level", ["NATIONAL","STATE","LGA","WARD","PU"])
        if level!="PU": df = df.groupby([level] if level=="STATE" else ["STATE",level]).sum().reset_index()
        df = calculate_scores(df)
        st.subheader("🏆 PARTY RANKING")
        totals = df[PARTIES].sum().sort_values(ascending=False)
        st.table(pd.DataFrame({'PARTY':totals.index,'VOTES':totals.values,'RANK':range(1,len(totals)+1)}))
        st.dataframe(df, use_container_width=True)