import streamlit as st
import plotly.express as px
import pandas as pd


st.title("Dashboard Validasi Retur")


if 'validasi' in st.session_state:
    #Initiate Validation Dataframe
    validasi = st.session_state['validasi'].copy()
    summary_df = validasi.groupby('tanggal')[[st.session_state['sap_tar'], st.session_state['sc_tar']]].sum().reset_index()

    #Initiate Valid Percentage
    valid_percent = st.session_state['valid_percent']

    if valid_percent > 90:
        st.success(f"Validasi data sangat baik ✅ ({valid_percent:.2f}% VALID)")
    elif valid_percent >= 70:
        st.warning(f"Validasi data cukup baik ⚠️ ({valid_percent:.2f}% VALID)")
    else:
        st.error(f"Validasi data perlu perhatian ❌ ({valid_percent:.2f}% VALID)")


    col1, col2 = st.columns([1,3])
    # Plot Line Chart
    with col2:
        line_plot = px.line(
            summary_df,
            x='tanggal',
            y=[st.session_state['sap_tar'], st.session_state['sc_tar']],
            labels={'value': 'Jumlah', 'variable': 'Tipe'},
            title='Total Debit dan Jml Neto per Tanggal'
        )
        st.plotly_chart(line_plot, use_container_width=True)

    # Variables for metric cards
    total_rows = len(validasi)
    valid_count = (st.session_state['validasi']['status'] == 'VALID').sum()
    invalid_count = (st.session_state['validasi']['status'] == 'TIDAK VALID').sum()
    missing_selisih = (st.session_state['validasi']['status'] == 'MISSING').sum()
    invalid_selisih = (st.session_state['validasi']['selisih'] != 0).sum()
    

    #Metrics Card Column
    with col1:
        container1 = st.container(border=True)
        container1.metric("Jumlah Data", total_rows)
        container2 = st.container(border=True)
        container2.metric("Jumlah VALID", valid_count)
        container3 = st.container(border=True)
        container3.metric("Jumlah TIDAK VALID", invalid_selisih)
        # container4 = st.container(border=True)
        # container4.metric("Selisih terbesar", st.session_state['validasi']['selisih'].abs().max())
    

    # Variables untuk distribusi selisih
    selisih_only = validasi[(validasi['selisih'].isna()) | (validasi['selisih'] != 0)].copy()

    # Hitung distribusi
    distribusi_selisih = selisih_only['kategori_selisih'].value_counts().reset_index()
    distribusi_selisih.columns = ['Kategori Selisih', 'Jumlah']

    # Tetapkan urutan kategori
    kategori_order = ['Kecil (1–9.999)', 'Sedang (10rb–999rb)', 'Besar (≥1jt)', 'MISSING']
    distribusi_selisih['Kategori Selisih'] = pd.Categorical(
        distribusi_selisih['Kategori Selisih'],
        categories=kategori_order,
        ordered=True
    )
    distribusi_selisih = distribusi_selisih.sort_values('Kategori Selisih')

    colr1, colr2 = st.columns(2)
    with colr1:
        bar_chart = px.bar(
            distribusi_selisih,
            x='Kategori Selisih',
            y='Jumlah',
            color='Kategori Selisih',
            text='Jumlah',
            title='Distribusi Ukuran Selisih (Bar Chart)',
            color_discrete_map={
                'Kecil (0–9.999)': '#2CA02C',
                'Sedang (10rb–999rb)': 'gold',
                'Besar (≥1jt)': 'red',
                'MISSING': 'gray'
            }
        )

        bar_chart.update_traces(textposition='outside')
        bar_chart.update_layout(xaxis_title='Kategori Selisih', yaxis_title='Jumlah Data')
        st.plotly_chart(bar_chart, use_container_width=True)

    with colr2:
        # Variable Pie Chart
        status_counts = validasi['status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Jumlah']

        pie_chart = px.pie(
            status_counts,
            names='Status',
            values='Jumlah',
            title='Distribusi Status Validasi',
            color='Status',
            color_discrete_map={
                'VALID': '#2CA02C',
                'TIDAK VALID': '#D62728',
                'MISSING': '#FF9900'
            }
        )
        st.plotly_chart(pie_chart, use_container_width=True)


    with st.expander("📊 Analisis Lanjutan LLM", expanded=True):
        if 'llm_analysis' in st.session_state:
            st.markdown(st.session_state['llm_analysis'])
        else:
            st.info("Analisis belum tersedia. Silakan jalankan validasi di halaman utama.")


    st.subheader("Dataframe Validasi Retur")
    st.write(f"Total baris di DataFrame: {len(st.session_state['validasi'])}")
    koloms = ['outlet', 'tanggal', st.session_state['sap_tar'], st.session_state['sc_tar'], 'selisih', 'status']
    st.dataframe(st.session_state['validasi'][koloms])
else:
    st.warning("Data belum tersedia. Silakan proses dulu di halaman utama.")
