import streamlit as st
import pandas as pd
import time
import os

# --- Konfigurasi dan Pengecekan Keamanan ---
st.set_page_config(
    page_title="Upload Data Retur",
    page_icon="📤",
    layout="wide"
)

if not st.session_state.get('authenticated', False):
    st.error("Akses ditolak. Silakan login terlebih dahulu.")
    time.sleep(1)
    st.switch_page("pages/login.py")
    st.stop()

# --- Inisialisasi State ---
for key in ['sc_df', 'sap_df', 'sc_outlet_col', 'sc_date_col', 'sc_tar_col', 
            'sap_outlet_col', 'sap_date_col', 'sap_tar_col', 'validation_triggered']:
    if key not in st.session_state:
        st.session_state[key] = None if 'df' in key else False

# --- Tampilan Utama Halaman ---
st.title("Portal Upload & Validasi Data Retur")

with st.sidebar:
    st.info(f"Login sebagai:\n**{st.session_state.get('name', 'N/A')}**\n({st.session_state.get('role', 'N/A')})")
    st.divider()
    if st.button("Logout", use_container_width=True, type="secondary"):
        auth_keys_to_reset = ['authenticated', 'role', 'name']
        for key in auth_keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("pages/login.py")

st.header("Langkah 1: Siapkan File Retur")

# Tampilan Dinamis Berbasis Peran (Dua Kolom)
if st.session_state.get('role') == "Supply Chain":
    col_input, col_status = st.columns(2)
    with col_input:
        st.subheader("Input Data Supply Chain")
        # (Le code de l'interface utilisateur reste le même)
        if st.session_state.sc_df is not None:
            st.success("File SC Retur sudah dikonfirmasi.")
            if st.button("Ganti File SC", key="replace_sc"):
                keys_to_reset = ['sc_df', 'sc_outlet_col', 'sc_date_col', 'sc_tar_col', 'validation_triggered', 'validasi']
                for key in keys_to_reset:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()
        else:
            sc_file = st.file_uploader("Upload file retur dari Supply Chain", type=["csv", "xlsx"], key="sc_uploader")
            if sc_file:
                try:
                    temp_df = pd.read_csv(sc_file) if sc_file.name.endswith('.csv') else pd.read_excel(sc_file)
                    st.dataframe(temp_df.head())
                    available_cols = temp_df.columns.tolist()
                    sc_outlet_selection = 'kode_outlet' if 'kode_outlet' in available_cols else st.selectbox("Pilih kolom outlet SC:", available_cols, key="sc_outlet_manual")
                    sc_date_selection = 'tgl_penerimaan' if 'tgl_penerimaan' in available_cols else st.selectbox("Pilih kolom tanggal SC:", available_cols, key="sc_date_manual")
                    sc_tar_selection = 'jml_neto' if 'jml_neto' in available_cols else st.selectbox("Pilih kolom indikator SC:", available_cols, key="sc_tar_manual")
                    
                    if st.button("Konfirmasi File & Kolom SC", type="primary"):
                        st.session_state.sc_df, st.session_state.sc_outlet_col, st.session_state.sc_date_col, st.session_state.sc_tar_col = temp_df, sc_outlet_selection, sc_date_selection, sc_tar_selection
                        st.rerun()
                except Exception as e:
                    st.error(f"Gagal membaca file SC: {e}")
    with col_status:
        st.subheader("Status Data File SAP")
        if st.session_state.sap_df is not None:
            st.success("✅ File SAP sudah dikonfirmasi oleh tim Akuntansi.")
        else:
            st.info("Status: Menunggu file dari role Akuntansi.")

elif st.session_state.get('role') == "Akuntansi":
    col_input, col_status = st.columns(2)
    with col_input:
        st.subheader("Input Data SAP")
        # (Le code de l'interface utilisateur reste le même)
        if st.session_state.sap_df is not None:
            st.success("File SAP Retur sudah dikonfirmasi.")
            if st.button("Ganti File SAP", key="replace_sap"):
                keys_to_reset = ['sap_df', 'sap_outlet_col', 'sap_date_col', 'sap_tar_col', 'validation_triggered', 'validasi']
                for key in keys_to_reset:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()
        else:
            sap_file = st.file_uploader("Upload file retur dari SAP", type=["csv", "xlsx"], key="sap_uploader")
            if sap_file:
                try:
                    temp_sap = pd.read_csv(sap_file) if sap_file.name.endswith('.csv') else pd.read_excel(sap_file)
                    st.dataframe(temp_sap.head())
                    available_cols = temp_sap.columns.tolist()
                    sap_outlet_selection = 'profit_center' if 'profit_center' in available_cols else st.selectbox("Pilih kolom outlet SAP:", available_cols, key="sap_outlet_manual")
                    sap_date_selection = 'posting_date' if 'posting_date' in available_cols else st.selectbox("Pilih kolom tanggal SAP:", available_cols, key="sap_date_manual")
                    sap_tar_selection = 'kredit' if 'kredit' in available_cols else st.selectbox("Pilih kolom indikator SAP:", available_cols, key="sap_tar_manual")
                    
                    if st.button("Konfirmasi File & Kolom SAP", type="primary"):
                        st.session_state.sap_df, st.session_state.sap_outlet_col, st.session_state.sap_date_col, st.session_state.sap_tar_col = temp_sap, sap_outlet_selection, sap_date_selection, sap_tar_selection
                        st.rerun()
                except Exception as e:
                    st.error(f"Gagal membaca file SAP: {e}")
    with col_status:
        st.subheader("Status Data File SC")
        if st.session_state.sc_df is not None:
            st.success("✅ File SC sudah dikonfirmasi oleh tim Supply Chain.")
        else:
            st.info("Status: Menunggu file dari role Supply Chain.")

# Tombol Proses Validasi
st.divider()
st.header("Langkah 2: Jalankan Validasi")
if st.session_state.sc_df is not None and st.session_state.sap_df is not None:
    if st.button("🚀 Proses Validasi dan Lihat Dashboard", type="primary", use_container_width=True):
        with st.spinner("Memproses validasi data... Mohon tunggu."):
            try:
                st.session_state.validation_triggered = True
                sc_df, sap_df = st.session_state.sc_df, st.session_state.sap_df
                sc_outlet, sc_date, sc_tar = st.session_state.sc_outlet_col, st.session_state.sc_date_col, st.session_state.sc_tar_col
                sap_outlet, sap_date, sap_tar = st.session_state.sap_outlet_col, st.session_state.sap_date_col, st.session_state.sap_tar_col

                sap_df[sap_date] = pd.to_datetime(sap_df[sap_date])
                sc_df[sc_date] = pd.to_datetime(sc_df[sc_date])

                sc_grouped = sc_df.groupby([sc_outlet, sc_date])[sc_tar].sum().reset_index()
                sap_grouped = sap_df.groupby([sap_outlet, sap_date])[sap_tar].sum().reset_index()

                # ===== PERBAIKAN BUG DI SINI: Menggunakan .rename() yang lebih aman =====
                sc_grouped = sc_grouped.rename(columns={sc_outlet: 'outlet', sc_date: 'tanggal', sc_tar: 'nilai_target'})
                sap_grouped = sap_grouped.rename(columns={sap_outlet: 'outlet', sap_date: 'tanggal', sap_tar: 'nilai_target'})
                # =======================================================================
                
                validasi = pd.merge(sap_grouped, sc_grouped, on=["outlet", "tanggal"], how="outer", suffixes=('_sap', '_sc'))
                
                sap_col_name, sc_col_name = 'nilai_target_sap', 'nilai_target_sc'
                st.session_state['sap_col_suffixed'], st.session_state['sc_col_suffixed'] = sap_col_name, sc_col_name
                
                validasi["selisih"] = validasi[sap_col_name].fillna(0) - validasi[sc_col_name].fillna(0)

                def classify_status(row):
                    if pd.isna(row[sap_col_name]) or pd.isna(row[sc_col_name]): return "MISSING"
                    elif abs(row['selisih']) < 1: return "VALID"
                    else: return "TIDAK VALID"
                validasi["status"] = validasi.apply(classify_status, axis=1)
                validasi = validasi[validasi["status"] != "MISSING"]

                def kategori_selisih(x):
                    if pd.isna(x): return "MISSING"
                    if abs(x) < 1: return "VALID"
                    elif 1 <= abs(x) <= 9_999: return "Pembulatan (1–9.999)"
                    elif abs(x) <= 999_999: return "Sedang (10rb–999rb)"
                    else: return "Besar (≥1jt)"
                validasi["kategori_selisih"] = validasi["selisih"].apply(kategori_selisih)
                st.session_state['validasi'] = validasi

                valid_count = (validasi['status'] == 'VALID').sum()
                total_data = len(validasi)
                st.session_state['valid_percent'] = (valid_count / total_data) * 100 if total_data > 0 else 0
                
                time.sleep(1) 
                st.success("Validasi selesai!")
                st.switch_page("pages/dashboard.py")

            except Exception as e:
                st.error(f"Terjadi kesalahan saat memproses data: {e}. Pastikan kolom yang dipilih pada langkah 1 sudah benar.")
                st.session_state.validation_triggered = False # Reset trigger agar tombol bisa ditekan lagi
else:
    st.warning("Harap pastikan kedua file (SC dan SAP) sudah dikonfirmasi untuk dapat melanjutkan proses validasi.")