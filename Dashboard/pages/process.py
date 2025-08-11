import streamlit as st
import pandas as pd
import requests
from streamlit_extras.add_vertical_space import add_vertical_space

st.set_page_config(page_title="Process Log", layout="wide", initial_sidebar_state="expanded")
role = st.session_state.get('role')
user = st.session_state.get('user')

# --- Sidebar Navigation ---
with st.sidebar:
    # st.info(f"Welcome, **{role}**!")
    st.image("kf.png")
    st.divider()
    with st.container(border=True, height=110):
        st.markdown(f'''Selamat Datang :green[ **{user}**]''')
        st.markdown(f''':blue-background[Role User: **{role}**]''')
    st.divider()
    st.header("Navigation")
    if st.button("Upload File Kembali", use_container_width=True, type="secondary", icon=":material/upload:"):
        st.session_state.data_sent = False
        st.switch_page("pages/retur.py")
    if st.button("Lihat Dashboard", use_container_width=True, type="secondary", icon=":material/dataset:"):
        st.session_state.data_sent = True
        st.switch_page("pages/dashboard.py")
    st.divider()
    st.header("Controls")
    if st.button("Logout", use_container_width=True, type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("pages/login.py")
        st.stop()

# --- Authentication ---
if not st.session_state.get('logged_in'):
    st.switch_page("pages/login.py")
    st.stop()

st.title("🗂️ Log Proses Validasi")

# --- Inisialisasi kolom tabel ---
expected_columns = ['user', 'file_type', 'role', 'uploaded_at', 'val_score', 'val_status']
df = pd.DataFrame(columns=expected_columns)

# --- Ambil data dari Supabase via REST API ---
try:
    response = requests.get("http://localhost:5678/webhook/get-process")
    if response.status_code == 200:
        process_data = response.json()
        if process_data:
            df = pd.DataFrame(process_data)
            df['uploaded_at'] = pd.to_datetime(df['uploaded_at'], errors='coerce') if 'uploaded_at' in df.columns else pd.Timestamp.now()
            # 🔹 Filter berdasarkan role
            if role != "Admin":  
                df = df[df['role'] == role]
    else:
        st.warning(f"Gagal mengambil data. Status code: {response.status_code}")
except Exception as e:
    st.error(f"Database Kosong")

# --- UI Section ---
col1, col2, col3 = st.columns([7, 1, 1])
col1.markdown("### Riwayat Validasi Dokumen")
with col2:
    if st.button("Refresh", use_container_width=True, type="secondary"):
        st.rerun()
with col3:
    if st.button("Add Process", type="primary"):
        st.session_state['selected_log'] = None
        st.session_state.data_sent = False
        st.switch_page("pages/retur.py")

# --- Table Header ---
with st.container(border=True):
    header_cols = st.columns([1.5, 1.5, 2, 1.5, 2, 2, 2.2, 1.5])
    header_cols[0].markdown("**👤 User**")
    header_cols[1].markdown("**🧾 File Type**")
    header_cols[2].markdown("**🔰 File Name**")
    header_cols[3].markdown("**🔐 Role**")
    header_cols[4].markdown("**📅 Upload Time**")
    header_cols[5].markdown("**📊 Validation Score**")
    header_cols[6].markdown("**✅ Validation Status**")
    header_cols[7].markdown("**🔍 Action**")
    add_vertical_space(1)

    # Tambahkan CSS supaya tombol Detail sejajar ke atas
    st.markdown("""
        <style>
        div[data-testid="stButton"] > button {
            padding-top: 0.25rem;
            padding-bottom: 0.25rem;
            margin-top: -6px; /* geser tombol ke atas */
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Table Rows ---
    for i, row in df.iterrows():
        row_cols = st.columns([1.5, 1.5, 2, 1.5, 2, 2, 2.2, 1.5])
        st.markdown(" ")
        row_cols[0].write(row.get('user', ''))
        row_cols[1].write(row.get('file_type', ''))
        row_cols[2].write(row.get('file_name', ''))
        row_cols[3].write(row.get('role', ''))

        uploaded_at = row.get('uploaded_at')
        row_cols[4].write(uploaded_at.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(uploaded_at) else "N/A")

        row_cols[5].write(f"{row['val_score']}%" if pd.notna(row.get('val_score')) else "N/A")

        val_status = row.get('val_status', '')
        if val_status == 'Valid':
            row_cols[6].markdown(f":green-background[✅ Valid]")
        elif val_status == 'Invalid':
            row_cols[6].markdown(f":red-background[❌ Invalid]")
        else:
            row_cols[6].write(val_status)

        # Tombol Detail
        if row_cols[7].button("Detail", key=f"detail_{i}"):
            st.session_state['minio_path'] = row.get('id', '')
            st.switch_page("pages/dashboard.py")
