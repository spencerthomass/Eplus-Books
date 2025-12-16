import streamlit as st
import requests
import pandas as pd
from datetime import date

# CONFIGURATION
# If running inside Docker Compose, the backend host is 'web'
API_URL = "http://web:8000" 

st.set_page_config(page_title="Emissions Tracker", layout="wide")

# --- SIDEBAR: Location Selector ---
st.sidebar.title("📍 Location")
location_name = st.sidebar.selectbox(
    "Select Shop", 
    ["Taylorsville", "West Jordan", "Sandy", "Draper"] # Add all 10 here
)

# You would ideally fetch IDs from the backend, but mapping manually for now:
LOC_MAP = {"Taylorsville": 1, "West Jordan": 2, "Sandy": 3, "Draper": 4}
loc_id = LOC_MAP[location_name]

# --- MAIN PAGE ---
st.title(f"🛠️ {location_name} - Daily Log")
selected_date = st.date_input("Date", date.today())

# 1. Start Day Section
st.subheader("1. Start the Day")
col1, col2 = st.columns([1, 3])
with col1:
    opening_cash = st.number_input("Opening Cash ($)", value=0.0, step=0.01)
    if st.button("Open Drawer"):
        try:
            res = requests.post(f"{API_URL}/start-day/", json={
                "location_id": loc_id,
                "starting_cash": opening_cash
            })
            if res.status_code == 200:
                st.success("Drawer Opened!")
                st.session_state['daily_log_id'] = res.json()['log_id']
            else:
                st.error("Error opening day.")
        except:
            st.error("Cannot connect to backend. Is Docker running?")

# 2. Add Transaction Form
st.markdown("---")
st.subheader("2. New Transaction")

# Create a form so the page doesn't reload on every keystroke
with st.form("entry_form", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    vehicle = c1.text_input("Vehicle (Year/Make/Model)")
    vin = c2.text_input("VIN (Last 8)")
    plate = c3.text_input("License Plate")
    
    st.markdown("**Services:**")
    check_cols = st.columns(4)
    is_dmv = check_cols[0].checkbox("DMV")
    is_tsi = check_cols[1].checkbox("TSI")
    is_safety = check_cols[2].checkbox("Safety")
    is_renewal = check_cols[3].checkbox("Renewal")
    
    st.markdown("**Cert Numbers:**")
    cert_cols = st.columns(2)
    emis_num = cert_cols[0].text_input("Emissions Cert #")
    dmv_num = cert_cols[1].text_input("DMV #")
    
    st.markdown("**Payment:**")
    pay_cols = st.columns(2)
    amount = pay_cols[0].number_input("Total Amount ($)", step=1.00)
    method = pay_cols[1].selectbox("Method", ["CASH", "CC", "FLEET", "CHECK"])
    
    submitted = st.form_submit_button("💾 Save Transaction")
    
    if submitted:
        # Check if we have an active day
        if 'daily_log_id' in st.session_state:
            payload = {
                "daily_log_id": st.session_state['daily_log_id'],
                "vehicle_make": vehicle,
                "vin": vin,
                "plate": plate,
                "is_dmv": is_dmv,
                "is_tsi": is_tsi,
                "is_safety": is_safety,
                "is_renewal": is_renewal,
                "emis_cert_num": emis_num,
                "dmv_num": dmv_num,
                "total_amount": amount,
                "payment_method": method
            }
            requests.post(f"{API_URL}/add-transaction/", json=payload)
            st.success("Saved!")
        else:
            st.warning("Please OPEN THE DRAWER first (Step 1).")

# 3. Live Dashboard (Replaces 'Month Totals')
st.markdown("---")
st.subheader("3. Live Balance")

if 'daily_log_id' in st.session_state:
    try:
        data = requests.get(f"{API_URL}/balance-day/{st.session_state['daily_log_id']}").json()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Sales", f"${data['total_sales']:,.2f}")
        m2.metric("Cash In Drawer", f"${data['cash_sales']:,.2f}")
        m3.metric("CC Sales", f"${data['credit_card_sales']:,.2f}")
        m4.metric("EXPECTED CLOSING", f"${data['expected_drawer_cash']:,.2f}", delta_color="inverse")
    except:
        st.info("No data yet for today.")