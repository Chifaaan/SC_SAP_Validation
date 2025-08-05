import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

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
role = st.session_state.get('role')
sc_df = st.session_state.get('sc_df')
sap_df = st.session_state.get('sap_df')

df['date'] = pd.to_datetime(df['date'])

st.title("📊 Validation Dashboard")

with st.sidebar:
    st.info(f"Welcome, **{role}**!")
    st.page_link("pages/retur.py", label="Go to Validation Page", icon="📄")
    st.header("Controls")
    if st.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.page_link("pages/login.py", label="Logged out. Go to Login.", icon="🔒")
        st.stop()

# --- Create Tabs ---
tab1, tab2 = st.tabs(["Validation Results", "Dashboard Insights"])

# --- Tab 1: Filterable Results Table ---
with tab1:
    st.header("Validation Results (Based on 'DPP')")
    discrepancy_total = (df['status'] == 'Discrepancy').sum()
    st.info(f"A total of **{discrepancy_total}** discrepancies were found out of **{len(df)}** records.")
    
    st.divider()
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

    # Define and display the main results table
    id_col = 'transaction_code' if role == 'Supply Chain' else 'document_id'
    display_order = [id_col, 'outlet_code', 'date', 'target_col_value', 'validation_total', 'difference', 'status', 'Discrepancy_category']

    st.dataframe(filtered_df[display_order], use_container_width=True)

    # --- MODIFICATION: Discrepancy Analysis Table (Recalculated) ---
    st.divider()
    st.header("Discrepancy Analysis (Recalculated with 'Total')")
    
    # Check if 'total' column exists in val_df to perform this analysis
    if 'total' in val_df.columns:
        discrepancy_records = filtered_df[filtered_df['status'] == 'Discrepancy'].copy()
        
        if not discrepancy_records.empty:
            
            # Aggregate the 'total' column from the raw validation file
            if role == 'Supply Chain':
                val_total_agg = val_df.groupby('no_transaksi')['total'].sum().reset_index()
                # Merge to get the new total
                recalc_df = pd.merge(discrepancy_records, val_total_agg, left_on='transaction_code', right_on='no_transaksi', how='left')
            else: # Accountant role
                val_total_agg = val_df.groupby('document_id')['total'].sum().reset_index()
                # Merge to get the new total
                recalc_df = pd.merge(discrepancy_records, val_total_agg, on='document_id', how='left')

            # Calculate the new difference
            recalc_df['new_difference'] = recalc_df['target_col_value'] - recalc_df['total'].fillna(0)
            
            # Define columns for the new table and display it
            recalc_display_order = [id_col, 'outlet_code','date', 'target_col_value', 'total', 'new_difference', 'status']
            recalc_df['status'] = recalc_df['new_difference'].apply(lambda x: 'Discrepancy' if abs(x) > 0.01 else 'Matched')
            recalc_status = recalc_df['status']
            total_discre = (recalc_status == 'Discrepancy').sum()
            
            st.info(f"**{total_discre}** discrepancies found after recalculating with 'Total'.")
            st.dataframe(recalc_df[recalc_display_order].rename(columns={'total': 'validation_raw_total', 'new_difference': 'recalculated_difference'}), use_container_width=True)
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
                st.write(f"Total from Source: **{abs(sum_source):,}**")
                st.dataframe(source_drill)
            with drill_col2:
                st.subheader(f"Validation Data (VAL)")
                val_drill = val_df[val_df['no_transaksi'].astype(str) == drill_down_id]
                # Bug Fix: Sum 'total' as it's the reliably available column
                sum_val_tot = val_drill['total'].sum() if not val_drill.empty else 0
                sum_val_dpp = val_drill['dpp'].sum() if 'dpp' in val_drill.columns else 0
                st.write(f"Sum total from Validation: **{sum_val_tot:,}**")
                st.write(f"Sum dpp from Validation: **{sum_val_dpp:,}**")
                st.dataframe(val_drill)
        elif role == 'Accountant' and sap_df is not None:
            with drill_col1:
                st.subheader(f"Source Data (SAP)")
                source_drill = sap_df[sap_df['doc_id'].astype(str) == drill_down_id]
                sum_source = source_drill['kredit'].sum() if not source_drill.empty else 0
                st.write(f"Total from Source: **{abs(sum_source):,}**")
                st.dataframe(source_drill)
            with drill_col2:
                st.subheader(f"Validation Data (VAL)")
                val_drill = val_df[val_df['document_id'].astype(str) == drill_down_id]
                # Bug Fix: Sum 'total' as it's the reliably available column
                sum_val_tot = val_drill['total'].sum() if not val_drill.empty else 0
                sum_val_dpp = val_drill['dpp'].sum() if 'dpp' in val_drill.columns else 0
                st.write(f"Sum total from Validation: **{sum_val_tot:,}**")
                st.write(f"Sum dpp from Validation: **{sum_val_dpp:,}**")
                st.dataframe(val_drill)

# --- Tab 2: Dashboard Insights ---
with tab2:
    # This tab remains unchanged and provides global insights
    st.header("Global Dashboard Insights")
    total_count = len(df)
    matched_count = total_count - total_discre
    validation_pct = (matched_count / total_count * 100) if total_count > 0 else 0
    discrepancy_insights_df = recalc_df[recalc_df['status'] == 'Discrepancy'].copy()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Overall Validation Success", f"{validation_pct:.2f}%", border=True, height=125)
    with col2:
        st.metric("Total Matched Records", f"{matched_count}", border=True, height=125)
    with col3:
        st.metric("Total Discrepancy Records", f"{total_discre}", border=True, height=125)
    with col4:
        if not discrepancy_insights_df.empty:
            top_outlet = discrepancy_insights_df['outlet_code'].value_counts().idxmax()
            top_outlet_count = discrepancy_insights_df['outlet_code'].value_counts().max()
            st.metric("Highest Discrepancy Outlet", f"{top_outlet}", delta=f"{top_outlet_count} records", delta_color="off", border=True, height=125)

    st.divider()

    if discrepancy_insights_df.empty:
        st.success("🎉 No discrepancies found in the entire dataset!")
    else:
        st.subheader("Discrepancy Categories")
        category_counts = discrepancy_insights_df['Discrepancy_category'].value_counts().reset_index()
        fig = px.pie(category_counts, names='Discrepancy_category', values='count', title='Distribution of Discrepancy Types (Overall)')
        st.plotly_chart(fig, use_container_width=True)