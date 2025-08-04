# process.py

import streamlit as st
import pandas as pd
import time
import os

# --- Page Config and Authentication ---
st.set_page_config(page_title="Daftar Proses", layout="wide", page_icon="📋")

# Redirect to login if not authenticated
if not st.session_state.get('authenticated', False):
    st.warning("Akses ditolak. Silakan login terlebih dahulu.")
    st.switch_page("pages/login.py")

# --- Initialize State for Processes ---
if 'processes' not in st.session_state:
    st.session_state['processes'] = []

# --- Sidebar ---
with st.sidebar:
    st.info(f"Login sebagai:\n**{st.session_state.get('name', 'N/A')}**\n({st.session_state.get('role', 'N/A')})")
    st.divider()
    if st.button("Logout", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("pages/login.py")

# --- Main Page ---
st.title("📋 Portal Proses Dokumen")
st.markdown("Pilih proses yang sudah ada atau buat proses baru untuk memulai validasi dokumen.")

col1, col2 = st.columns([3, 1])

with col2:
    if st.button("➕ Buat Proses Baru", type="primary", use_container_width=True):
        st.session_state['show_create_dialog'] = True

# --- Dialog for Creating a New Process ---
if st.session_state.get('show_create_dialog', False):
    with st.dialog("Buat Proses Validasi Baru"):
        st.subheader("Pilih Kategori Dokumen")
        category = st.selectbox(
            "Kategori Dokumen",
            ["Retur", "Reguler", "Konsinyasi"],
            label_visibility="collapsed"
        )
        
        if st.button("Buat", key="create_confirm"):
            new_id = f"PRO-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(2).hex().upper()}"
            new_process = {
                "id_proses": new_id,
                "user": st.session_state.get('user'),
                "role": st.session_state.get('role'),
                "document_category": category,
                "created_date": pd.Timestamp.now()
            }
            st.session_state.processes.append(new_process)
            st.session_state['show_create_dialog'] = False
            st.rerun()

        if st.button("Batal", key="create_cancel"):
            st.session_state['show_create_dialog'] = False
            st.rerun()


# --- Display Processes Table ---
st.header("Daftar Proses Aktif")

if not st.session_state.processes:
    st.info("Belum ada proses yang dibuat. Klik 'Buat Proses Baru' untuk memulai.")
else:
    # Create a DataFrame from the list of process dictionaries
    processes_df = pd.DataFrame(st.session_state.processes)
    
    # Prepare DataFrame for display
    display_df = processes_df[['id_proses', 'document_category', 'role', 'user', 'created_date']].copy()
    display_df['created_date'] = display_df['created_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    display_df.rename(columns={
        'id_proses': 'ID Proses', 'document_category': 'Kategori Dokumen',
        'role': 'Role Pembuat', 'user': 'User Pembuat', 'created_date': 'Tanggal Dibuat'
    }, inplace=True)

    # Use st.column_config to add a button column - this is a modern approach
    display_df["action"] = "➡️" # Placeholder value for the column
    
    st.data_editor(
        display_df,
        column_config={
            "action": st.column_config.Column(
                "Aksi",
                width="small",
            ),
        },
        disabled=display_df.columns[:-1], # Disable editing for all but the action column
        on_edit="rerun", # Not really used here but good practice
        key="process_editor",
        hide_index=True,
        use_container_width=True
    )
    
    # Check if a click happened by checking the editor's state
    if "process_editor" in st.session_state and "edited_rows" in st.session_state["process_editor"]:
        edited_row_index = list(st.session_state["process_editor"]["edited_rows"].keys())[0]
        
        # Get the original process data using the index
        process_to_open = st.session_state.processes[edited_row_index]
        category = process_to_open['document_category']
        
        # Store current process info in session state for other pages to use
        st.session_state['current_process_id'] = process_to_open['id_proses']
        st.session_state['current_category'] = category

        # Navigate based on the document category
        if category == "Retur":
            st.switch_page("pages/retur.py")
        else:
            # Placeholder for other categories
            st.toast(f"Navigasi untuk kategori '{category}' belum diimplementasikan.")
            time.sleep(1)
            # Reset the edit state to allow clicking again
            del st.session_state["process_editor"]["edited_rows"]
            st.rerun()