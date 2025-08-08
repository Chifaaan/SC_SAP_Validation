import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_extras.metric_cards import style_metric_cards
import requests

st.set_page_config(page_title="Validation Dashboard", layout="wide")

# --- Authentication and Session State Check ---
if not st.session_state.get('logged_in'):
    st.error("Access denied. Please log in first.")
    st.switch_page("pages/login.py")
    st.stop()

# Check for all required dataframes
required_keys = ['result_df', 'val_df', 'role']
if not all(key in st.session_state for key in required_keys):
    st.warning("No data found or session is incomplete. Please upload and process a file on the 'retur' page first.")
    st.page_link("pages/retur.py", label="Go to Validation Page", icon="📄")
    st.stop()

# --- Load Data From Session ---
df = st.session_state['result_df']
val_df = st.session_state['val_df']
user = st.session_state.get('user')
role = st.session_state.get('role')
sc_df = st.session_state.get('sc_df')
sap_df = st.session_state.get('sap_df')

df['date'] = pd.to_datetime(df['date'])

# --- Main Dashboad ---
st.title("📊 Validation Dashboard")

# --- Sidebar Navigation ---
with st.sidebar:
    # st.info(f"Welcome, **{role}**!")
    st.image("kf.png")
    st.divider()
    st.header("Navigation")
    if st.button("Upload File Kembali", use_container_width=True, type="secondary", icon=":material/upload:"):
        st.switch_page("pages/retur.py")
    if st.button("Lihat Log Proses", use_container_width=True, type="secondary", icon=":material/history:"):
        st.switch_page("pages/process.py")
    st.divider()
    st.header("Controls")
    if st.button("Logout", use_container_width=True, type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("pages/login.py")
        st.stop()


# --- Create Tabs ---
tab1, tab2 = st.tabs(["Validation Summary", "Dashboard Insights"])

# --- Tab 1: Filterable Results Table ---
with tab2:
    st.header("Validation Results (Based on 'DPP')")
    filter_cols = st.columns(4)
    
    with filter_cols[0]:
        selected_status = st.multiselect("Status", options=['Matched', 'Discrepancy'], default=[])

    with filter_cols[1]:
        selected_outlets = st.multiselect("Outlet Code", options=sorted(df['outlet_code'].unique()), default=[])

    with filter_cols[2]:
        min_date, max_date = df['date'].min().date(), df['date'].max().date()
        selected_date_range = st.date_input("Date Range", value=(), min_value=min_date, max_value=max_date)
    
    bins = [0, 2001, 10001, 100001, float('inf')]
    labels = ["Rounding (< 2k)", "Small (2k-10k)", "Medium (10k-100k)", "Big (> 100k)"]
    discrepancy_mask = df['status'] == 'Discrepancy'
    df['Discrepancy_category'] = pd.cut(abs(df.loc[discrepancy_mask, 'difference']), bins=bins, labels=labels, right=False)
    if pd.api.types.is_categorical_dtype(df['Discrepancy_category']):
        df['Discrepancy_category'] = df['Discrepancy_category'].cat.add_categories('Valid').fillna('Valid')
    else:
        df['Discrepancy_category'] = df['Discrepancy_category'].fillna('Valid')
        
    with filter_cols[3]:
        selected_discrepancy = st.multiselect("Discrepancy Category", options=sorted(df['Discrepancy_category'].unique()), default=[])

    # Apply filters to create a view
    filtered_df = df.copy()
    if selected_status:
        filtered_df = filtered_df[filtered_df['status'].isin(selected_status)]
    if selected_outlets:
        filtered_df = filtered_df[filtered_df['outlet_code'].isin(selected_outlets)]
    if len(selected_date_range) == 2:
        start_date, end_date = pd.to_datetime(selected_date_range[0]), pd.to_datetime(selected_date_range[1])
        filtered_df = filtered_df[(filtered_df['date'] >= start_date) & (filtered_df['date'] <= end_date)]
    if selected_discrepancy:
        filtered_df = filtered_df[filtered_df['Discrepancy_category'].isin(selected_discrepancy)]

    discrepancy_total = (df['status'] == 'Discrepancy').sum()
    st.info(f"**{discrepancy_total}** data yang tidak sesuai dari **{len(df)}** data berdasarkan perhitungan kolom 'dpp'.")

    # Define and display the main results table
    id_col = 'transaction_code' if role == 'Supply Chain' else 'document_id'
    display_order = [id_col, 'outlet_code', 'date', 'target_col_value', 'validation_total', 'difference', 'status', 'Discrepancy_category']

    st.dataframe(filtered_df[display_order], use_container_width=True, column_config={
        'target_col_value': st.column_config.NumberColumn(format="localized"),
        'validation_total': st.column_config.NumberColumn(format="localized"),
        'difference': st.column_config.NumberColumn(format="localized"),
    })

    # --- MODIFICATION: Discrepancy Analysis Table (Recalculated) ---
    st.divider()
    st.header("Discrepancy Analysis (Recalculated with 'Total')")

    if 'total' in val_df.columns:
        discrepancy_records = filtered_df[filtered_df['status'] == 'Discrepancy'].copy()

        if not discrepancy_records.empty:

            # Aggregate the 'total' column from the raw validation file
            if role == 'Supply Chain':
                val_total_agg = val_df.groupby('no_transaksi')['total'].sum().reset_index()
                recalc_df = pd.merge(discrepancy_records, val_total_agg, left_on='transaction_code', right_on='no_transaksi', how='left')
            else:  # Accountant role
                val_total_agg = val_df.groupby('document_id')['total'].sum().reset_index()
                recalc_df = pd.merge(discrepancy_records, val_total_agg, on='document_id', how='left')

            # Calculate absolute difference
            recalc_df['recalculated_difference'] = (recalc_df['target_col_value'] - recalc_df['total'].fillna(0)).abs()

            # Set status based on recalculated difference
            recalc_df['status'] = recalc_df['recalculated_difference'].apply(lambda x: 'Discrepancy' if x >= 10 else 'Matched')

            # Define display columns
            id_col = 'transaction_code' if role == 'Supply Chain' else 'document_id'
            recalc_display_order = [id_col, 'outlet_code', 'date', 'target_col_value', 'total', 'recalculated_difference', 'status']

            # --- FILTERS ---
            filter_cols = st.columns(4)

            with filter_cols[0]:
                selected_status = st.multiselect("Status", options=['Matched', 'Discrepancy'], default=[], key="recalc_status_filter")

            with filter_cols[1]:
                selected_outlets = st.multiselect("Outlet Code", options=sorted(recalc_df['outlet_code'].unique()), default=[], key="recalc_outlet_filter")

            with filter_cols[2]:
                min_date, max_date = recalc_df['date'].min().date(), recalc_df['date'].max().date()
                selected_date_range = st.date_input("Date Range", value=(), min_value=min_date, max_value=max_date, key="recalc_date_filter")

            # Discrepancy Category based on recalculated_difference
            bins = [0, 2001, 10001, 100001, float('inf')]
            labels = ["Rounding (< 2k)", "Small (2k-10k)", "Medium (10k-100k)", "Big (> 100k)"]
            # Hitung Discrepancy_category
            recalc_df['Discrepancy_category'] = pd.cut(
                recalc_df['recalculated_difference'],
                bins=bins,
                labels=labels,
                right=False
            )

            # Tambahkan kategori 'Missing'
            if pd.api.types.is_categorical_dtype(recalc_df['Discrepancy_category']):
                recalc_df['Discrepancy_category'] = recalc_df['Discrepancy_category'].cat.add_categories(['Valid', 'Missing'])
            else:
                recalc_df['Discrepancy_category'] = recalc_df['Discrepancy_category'].fillna('Valid')

            # Assign 'Valid' untuk nilai recalculated_difference == 0
            recalc_df.loc[recalc_df['recalculated_difference'] == 0, 'Discrepancy_category'] = 'Valid'

            # Assign 'Missing' jika ada nilai NaN di baris mana pun
            recalc_df.loc[recalc_df.isnull().any(axis=1), 'Discrepancy_category'] = 'Missing'

            with filter_cols[3]:
                selected_discrepancy = st.multiselect("Discrepancy Category", options=sorted(recalc_df['Discrepancy_category'].unique()), default=[])

            # Apply filters
            filtered_recalc_df = recalc_df.copy()
            if selected_status:
                filtered_recalc_df = filtered_recalc_df[filtered_recalc_df['status'].isin(selected_status)]
            if selected_outlets:
                filtered_recalc_df = filtered_recalc_df[filtered_recalc_df['outlet_code'].isin(selected_outlets)]
            if len(selected_date_range) == 2:
                start_date, end_date = pd.to_datetime(selected_date_range[0]), pd.to_datetime(selected_date_range[1])
                filtered_recalc_df = filtered_recalc_df[(filtered_recalc_df['date'] >= start_date) & (filtered_recalc_df['date'] <= end_date)]
            if selected_discrepancy:
                filtered_recalc_df = filtered_recalc_df[filtered_recalc_df['Discrepancy_category'].isin(selected_discrepancy)]

            # Display filtered table
            total_discre = (filtered_recalc_df['status'] == 'Discrepancy').sum()
            st.info(f"**{total_discre}** data tidak sesuai setelah menghitung ulang dengan kolom 'Total'.")

            st.dataframe(filtered_recalc_df[recalc_display_order + ['Discrepancy_category']].rename(columns={
                'total': 'validation_raw_total'
            }), use_container_width=True, column_config={
                'target_col_value': st.column_config.NumberColumn(format="localized"),
                'validation_raw_total': st.column_config.NumberColumn(format="localized"),
                'recalculated_difference': st.column_config.NumberColumn(format="localized"),
            })

        else:
            st.success("No discrepancies in the current filtered view to analyze.")
    else:
        st.warning("The 'total' column was not found in the validation file, so the recalculated discrepancy analysis cannot be performed.")

    # --- Drill-Down Feature ---
    st.divider()
    st.header("Search Data by ID")
    drill_down_id = st.text_input(f"Enter a specific {id_col.replace('_', ' ')} to see its raw data:")

    if drill_down_id:
        drill_col1, drill_col2 = st.columns(2)
        if role == 'Supply Chain' and sc_df is not None:
            with drill_col1:
                st.subheader(f"Source Data (SC)")
                source_drill = sc_df[sc_df['no_penerimaan'].astype(str) == drill_down_id]
                sum_source = source_drill['jml_neto'].sum() if not source_drill.empty else 0
                st.write(f"Sum dari :green[Kolom Target] SC: :green-background[**{abs(sum_source):,}**]")
                st.markdown(" ")
                st.markdown(" ")
                st.markdown(" ")
                st.dataframe(source_drill)
            with drill_col2:
                st.subheader(f"Validation Data (VAL)")
                val_drill = val_df[val_df['no_transaksi'].astype(str) == drill_down_id]
                # Bug Fix: Sum 'total' as it's the reliably available column
                sum_val_tot = val_drill['total'].sum() if not val_drill.empty else 0
                sum_val_dpp = val_drill['dpp'].sum() if 'dpp' in val_drill.columns else 0
                st.write(f"Sum kolom :red[total] dari data Validation: :red-background[**{sum_val_tot:,}**]")
                st.write(f"Sum kolom :blue[dpp] dari data Validation: :blue-background[**{sum_val_dpp:,}**]")
                st.dataframe(val_drill)
        elif role == 'Accountant' and sap_df is not None:
            with drill_col1:
                st.subheader(f"Source Data (SAP)")
                source_drill = sap_df[sap_df['doc_id'].astype(str) == drill_down_id]
                sum_source = source_drill['kredit'].sum() if not source_drill.empty else 0
                st.write(f"Sum dari :green[Kolom Target] SC: :green-background[**{abs(sum_source):,}**]")
                st.dataframe(source_drill)
            with drill_col2:
                st.subheader(f"Validation Data (VAL)")
                val_drill = val_df[val_df['document_id'].astype(str) == drill_down_id]
                # Bug Fix: Sum 'total' as it's the reliably available column
                sum_val_tot = val_drill['total'].sum() if not val_drill.empty else 0
                sum_val_dpp = val_drill['dpp'].sum() if 'dpp' in val_drill.columns else 0
                st.write(f"Sum kolom :red[total] dari data Validation: :red-background[**{sum_val_tot:,}**]")
                st.write(f"Sum kolom :blue[dpp] dari data Validation: :blue-background[**{sum_val_dpp:,}**]")
                st.dataframe(val_drill)

# --- Tab 2: Dashboard Insights ---
with tab1:
    st.header("File Validation Summary")
    total_count = len(df)
    matched_count = total_count - total_discre
    validation_pct = (matched_count / total_count * 100) if total_count > 0 else 0
    discrepancy_insights_df = recalc_df[recalc_df['status'] == 'Discrepancy'].copy()
    
    bigc1, bigc2 = st.columns(2)
    with bigc1:
        if discrepancy_insights_df.empty:
            val_status = "Valid"
            st.markdown(
                """
                <div style="background-color:#d4edda; color:#155724; padding:20px; border-radius:10px; height:230px; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <div style="width:80px; height:80px; border-radius:50%; background-color:#28a745; display:flex; align-items:center; justify-content:center; font-size:40px; color:white;">
                        ✅
                    </div>
                    <div style="margin-top:15px; font-size:20px; font-weight:bold; text-align:center;">
                        Data Valid<br>Tidak ada perbedaan data ditemukan!
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            val_status = "Invalid"
            st.markdown(
                """
                <div style="background-color:#f8d7da; color:#721c24; padding:20px; border-radius:10px; height:230px; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <div style="width:80px; height:80px; border-radius:50%; background-color:#dc3545; display:flex; align-items:center; justify-content:center; font-size:40px; color:white;">
                        ❌
                    </div>
                    <div style="margin-top:15px; font-size:20px; font-weight:bold; text-align:center;">
                        Data Invalid<br>Ditemukan perbedaan dalam data!
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    with bigc2:
        smc1, smc2 = st.columns(2)
        with smc1:
            st.metric("Overall Validation Score", f"{validation_pct:.2f}%", border=True)
            st.metric("Total Records Processed", f"{total_count}", border=True)
        with smc2:
            st.metric("Total Matched Records", f"{matched_count}", border=True)
            st.metric("Total Discrepancy Records", f"{total_discre}", border=True)

            # if not discrepancy_insights_df.empty:
            #     top_outlet = discrepancy_insights_df['outlet_code'].value_counts().idxmax()
            #     top_outlet_count = discrepancy_insights_df['outlet_code'].value_counts().max()
            #     st.metric("Highest Discrepancy Outlet", f"{top_outlet}", delta=f"{top_outlet_count} records", delta_color="off", border=True, height=125)
            # else:
            #     st.metric("Highest Discrepancy Outlet", "N/A", border=True, height=125)

    st.divider()

    if discrepancy_insights_df.empty:
        st.success("🎉 No discrepancies found in the entire dataset!")
    else:
        category_counts = discrepancy_insights_df['Discrepancy_category'].value_counts().reset_index()
        category_counts = category_counts[category_counts['Discrepancy_category'] != 'Valid']

        st.subheader("📌 Jumlah per Kategori Discrepancy")
        metric_cols = st.columns(len(category_counts))

        # --- Jumlah Discrepancy per Kategori ---
        all_categories = ["Rounding (< 2k)", "Small (2k-10k)", "Medium (10k-100k)", "Big (> 100k)", "Missing"]
        category_dict = dict(zip(category_counts['Discrepancy_category'], category_counts['count']))
        metric_cols = st.columns(len(all_categories))
        for i, cat in enumerate(all_categories):
            count = int(category_dict.get(cat, 0))
            metric_cols[i].metric(label=cat, value=count, border=True)
        st.markdown(" ")

        # --- Visualisasi Kategori Discrepancy ---
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                fig = px.pie(category_counts, names='Discrepancy_category', values='count', title='Distribusi Kategori Discrepancy')
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            with st.container(border=True):
                fig_bar = px.bar(
                category_counts,
                x='Discrepancy_category',
                y='count',
                text='count',
                title="Discrepancy Category Count",
                labels={'Discrepancy_category': 'Category', 'count': 'Jumlah'},
                )
                fig_bar.update_traces(textposition='outside')
                fig_bar.update_layout(
                    xaxis_title="Discrepancy Category",
                    yaxis_title="Jumlah",
                    uniformtext_minsize=8,
                    uniformtext_mode='hide',
                )
                st.plotly_chart(fig_bar, use_container_width=True)
# Cek apakah data sudah pernah dikirim
if "data_sent" not in st.session_state:
    st.session_state.data_sent = False

if not st.session_state.data_sent:
    file_type = st.session_state.get('file_type')
    file_name = st.session_state.get('uploaded_filename', 'Unknown File')

    # --- Send Data to API ---
    payload = {
        "user": user,
        "role": role,
        "file_type": file_type,
        "val_status": val_status,
        "val_score": validation_pct,
        "file_name": file_name
    }

    try:
        response = requests.post("http://localhost:5678/webhook/insert-process", json=payload)
        if response.status_code == 200:
            st.toast("Data berhasil dikirim ke Database.")
            st.session_state.data_sent = True  # Set flag agar tidak mengirim lagi
        else:
            st.warning(f"Gagal kirim data. Status code: {response.status_code}")
    except Exception as e:
        st.error(f"Error saat mengirim data ke API: {e}")
