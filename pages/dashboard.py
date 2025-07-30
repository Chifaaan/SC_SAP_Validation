import streamlit as st
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Dashboard Validasi", layout="wide", page_icon="📊")
st.title("📊 Dashboard Validasi Retur")

with st.sidebar:
    st.info(f"Login sebagai:\n**{st.session_state.get('name', 'N/A')}**\n({st.session_state.get('role', 'N/A')})")
    st.divider()
    st.header("Navigasi")
    st.page_link("pages/retur.py", label="Retur", icon="📚")
    st.divider()
    if st.button("Logout", use_container_width=True, type="secondary"):
        auth_keys_to_reset = ['authenticated', 'role', 'name']
        for key in auth_keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        st.switch_page("pages/login.py")


# Gatekeeper: Periksa apakah semua data yang diperlukan ada
if 'validasi' in st.session_state and 'sap_col_suffixed' in st.session_state:
    # --- 1. PENGATURAN DAN PENGAMBILAN DATA ---
    validasi = st.session_state['validasi'].copy()
    sap_col = st.session_state['sap_col_suffixed']
    sc_col = st.session_state['sc_col_suffixed']
    
    # --- 2. METRIK UTAMA DAN INDIKATOR ---
    valid_percent = st.session_state.get('valid_percent', 0)
    if valid_percent >= 95:
        st.success(f"Validasi data sangat baik ✅ ({valid_percent:.2f}% VALID)")
    elif valid_percent >= 80:
        st.warning(f"Validasi data cukup baik ⚠️ ({valid_percent:.2f}% VALID)")
    else:
        st.error(f"Validasi data perlu perhatian ❌ ({valid_percent:.2f}% VALID)")


    # --- TABS SECTION ---
    tab1, tab2 = st.tabs(["🧾 Tabel Detail Validasi", "📈 Metrik & Visualisasi"])

    with tab1:
        st.subheader("Detail Data Validasi")

        colf1, colf2, colf3 = st.columns(3)

        # Filter tanggal
        with colf2:
            date_range = st.date_input(
                "Pilih Rentang Tanggal",
                value=[],
                min_value=validasi['tanggal'].min().date(),
                max_value=validasi['tanggal'].max().date()
            )

        # Filter kategori selisih
        with colf3:
            kategori_selected = st.multiselect(
                "Pilih Kategori Validasi",
                options=validasi['kategori_selisih'].unique(),
                default=[]
            )

        with colf1:
            outlet_selected = st.multiselect(
                "Pilih Outlet",
                options=validasi['outlet'].unique(),
                default=[]
            )

        # Apply filtering
        filtered_validasi = validasi.copy()
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_validasi = filtered_validasi[
                (filtered_validasi['tanggal'].dt.date >= start_date) &
                (filtered_validasi['tanggal'].dt.date <= end_date)
            ]

        if kategori_selected:
            filtered_validasi = filtered_validasi[filtered_validasi['kategori_selisih'].isin(kategori_selected)]

        if outlet_selected:
            filtered_validasi = filtered_validasi[filtered_validasi['outlet'].isin(outlet_selected)]

        koloms = ['outlet', 'tanggal', sap_col, sc_col, 'selisih', 'status', 'kategori_selisih']
        st.dataframe(filtered_validasi[koloms])


    with tab2:
        col1, col2 = st.columns([1, 3])

        with col2:
            summary_df = filtered_validasi.groupby('tanggal')[[sap_col, sc_col]].sum().reset_index()
            line_plot = px.line(
                summary_df,
                x='tanggal',
                y=[sap_col, sc_col],
                labels={'value': 'Total Nilai', 'variable': 'Sumber Data'},
                title='Perbandingan Total Nilai Retur per Tanggal'
            )
            new_names = {sap_col: 'SAP', sc_col: 'Supply Chain'}
            line_plot.for_each_trace(lambda t: t.update(name=new_names[t.name]))
            st.plotly_chart(line_plot, use_container_width=True)

        with col1:
            total_rows = len(filtered_validasi)
            valid_count = (filtered_validasi['status'] == 'VALID').sum()
            mismatch_count = (filtered_validasi['status'].isin(['TIDAK VALID', 'MISSING'])).sum()

            st.container(border=True).metric("Total Baris Data", total_rows)
            st.container(border=True).metric("Jumlah Data VALID", valid_count, help="Data yang cocok atau hanya selisih pembulatan.")
            st.container(border=True).metric("Jumlah Data TIDAK COCOK", mismatch_count, help="Data yang tidak valid atau hilang di salah satu sistem.")

        colr1, colr2 = st.columns(2)

        with colr1:
            distribusi_selisih = filtered_validasi['kategori_selisih'].value_counts().reset_index()
            distribusi_selisih.columns = ['kategori_selisih', 'count']
            kategori_order = ['VALID', 'Pembulatan (1–9.999)', 'Sedang (10rb–999rb)', 'Besar (≥1jt)', 'MISSING']
            distribusi_selisih['kategori_selisih'] = pd.Categorical(distribusi_selisih['kategori_selisih'], categories=kategori_order, ordered=True)

            bar_chart = px.bar(
                distribusi_selisih.sort_values('kategori_selisih'),
                x='kategori_selisih', y='count', color='kategori_selisih', text_auto=True,
                title='Distribusi Status dan Ukuran Selisih',
                labels={'kategori_selisih': 'Kategori Selisih', 'count': 'Jumlah'},
                color_discrete_map={
                    'VALID': '#636EFA', 'Pembulatan (1–9.999)': '#ABECD6',
                    'Sedang (10rb–999rb)': '#EFB261', 'Besar (≥1jt)': '#E45757', 'MISSING': '#B0B0B0'
                }
            )
            st.plotly_chart(bar_chart, use_container_width=True)

        with colr2:
            status_counts = filtered_validasi['status'].value_counts().reset_index()
            status_counts.columns = ['status', 'count']
            pie_chart = px.pie(
                status_counts, names='status', values='count', title='Distribusi Status Validasi Final',
                color='status', color_discrete_map={'VALID': '#2CA02C', 'TIDAK VALID': '#D62728', 'MISSING': 'grey'}
            )
            st.plotly_chart(pie_chart, use_container_width=True)

else:
    st.warning("Data validasi belum tersedia. Silakan unggah dan proses file terlebih dahulu.")
    st.switch_page("pages/retur.py")

