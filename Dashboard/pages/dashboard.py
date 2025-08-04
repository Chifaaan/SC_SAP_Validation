import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Validation Dashboard", layout="wide")

# --- Authentication and Session State Check ---
if not st.session_state.get('logged_in'):
    st.error("Access denied. Please log in first.")
    st.switch_page("pages/login.py")
    st.stop()

if 'result_df' not in st.session_state:
    st.warning("No data found. Please upload and process a file on the 'retur' page first.")
    st.page_link("pages/retur.py", label="Go to Validation Page", icon="📄")
    st.stop()

# --- Load Data From Session ---
# 'df' is the original, complete dataset. It will be used for global insights.
if st.session_state['sc_df'] is not None:
    sc_df = st.session_state['sc_df']
else:
    sc_df = None
if st.session_state['sap_df'] is not None:
    sap_df = st.session_state['sap_df']
else:
    sap_df = None

val_df = st.session_state['val_df']
df = st.session_state['result_df']
df['date'] = pd.to_datetime(df['date'])
role = st.session_state.get('role')


st.title("📊 Validation Dashboard")

with st.sidebar:
    st.info(f"Welcome, **{role}**!")
    st.page_link("pages/retur.py", label="Go to Validation Page", icon="📄")
    st.header("Controls")
    if st.button("Logout"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.session_state.logged_in = False
        st.switch_page("pages/login.py")
        st.stop()

# --- Create Tabs ---
tab1, tab2 = st.tabs(["Validation Results", "Dashboard Insights"])

# --- Tab 1: Filterable Results Table ---
with tab1:
    st.header("Validation Results")

    discrepancy_in_view = (df['status'] == 'Discrepancy').sum()
    st.warning(f"**{discrepancy_in_view}** discrepancies found in total {len(df)} records.")

    st.divider()
    st.write("Use the filters below to narrow down the results. Leave a filter empty to ignore it.")
    filter_cols = st.columns([2, 2, 2, 2, 2])
    
    with filter_cols[0]:
        status_options = ['Matched', 'Discrepancy']
        selected_status = st.multiselect("Status", options=status_options, default=[])

    with filter_cols[1]:
        outlet_options = sorted(df['outlet_code'].unique())
        selected_outlets = st.multiselect("Outlet Code", options=outlet_options, default=[])

    with filter_cols[2]:
        id_col = 'transaction_code' if 'transaction_code' in df.columns else 'document_id'
        search_id = st.text_input(f"Search by {id_col.replace('_', ' ').title()}")

    with filter_cols[3]:
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()
        selected_date_range = st.date_input("Date Range", value=(), min_value=min_date, max_value=max_date)

    with filter_cols[4]:
        dis_cat= ['Valid', 'Rounding (< 2k)', 'Small (2k-10k)', 'Medium (10k-100k)', 'Big (> 100k)']
        selected_discrepancy = st.multiselect("Discrepancy Category", options=dis_cat, default=[])

    # 'filtered_df' is used ONLY for this tab's display
    filtered_df = df.copy()
    if selected_status:
        filtered_df = filtered_df[filtered_df['status'].isin(selected_status)]
    if selected_outlets:
        filtered_df = filtered_df[filtered_df['outlet_code'].isin(selected_outlets)]
    if search_id:
        filtered_df = filtered_df[filtered_df[id_col].astype(str).str.contains(search_id, case=False, na=False)]
    if len(selected_date_range) == 2:
        start_date, end_date = pd.to_datetime(selected_date_range[0]), pd.to_datetime(selected_date_range[1])
        filtered_df = filtered_df[(filtered_df['date'] >= start_date) & (filtered_df['date'] <= end_date)]

    
    # --- MODIFICATION START ---
    # 1. Create the Discrepancy Category column for the filtered view
    bins = [0, 2001, 10001, 100001, float('inf')]
    labels = ["Rounding (< 2k)", "Small (2k-10k)", "Medium (10k-100k)", "Big (> 100k)"]
    
    # Use pd.cut and fill non-discrepancy rows with 'Valid'
    discrepancy_mask = filtered_df['status'] == 'Discrepancy'
    filtered_df['Discrepancy_category'] = pd.cut(
        abs(filtered_df.loc[discrepancy_mask, 'difference']),
        bins=bins,
        labels=labels,
        right=False
    )
    # Use .cat.add_categories to allow 'Valid' before filling
    if pd.api.types.is_categorical_dtype(filtered_df['Discrepancy_category']):
        filtered_df['Discrepancy_category'] = filtered_df['Discrepancy_category'].cat.add_categories('Valid').fillna('Valid')
    else:
        filtered_df['Discrepancy_category'] = filtered_df['Discrepancy_category'].fillna('Valid')

    if selected_discrepancy:
        filtered_df = filtered_df[filtered_df['Discrepancy_category'].isin(selected_discrepancy)]

    # 2. Define the exact column order for display
    display_order = [
        id_col,
        'outlet_code',
        'date',
        'validation_total',
        'target_col_value',
        'difference',
        'status',
        'Discrepancy_category'
    ]

    # 3. Display the dataframe with the specified columns in order
    st.dataframe(filtered_df[display_order], use_container_width=True)
    # --- MODIFICATION END ---


# --- Tab 2: Dashboard Insights ---
with tab2:
    st.header("Global Dashboard Insights")

    total_count = len(df)
    matched_count = len(df[df['status'] == 'Matched'])
    discrepancy_count = len(df[df['status'] == 'Discrepancy'])
    validation_pct = (matched_count / total_count * 100) if total_count > 0 else 0

    # Key Metrics
    discrepancy_df = df[df['status'] == 'Discrepancy'].copy()
    top_outlet = discrepancy_df['outlet_code'].value_counts().idxmax()
    top_outlet_count = discrepancy_df['outlet_code'].value_counts().max()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Overall Validation Success", f"{validation_pct:.2f}%", border=True, width=225)
        st.metric("Total Matched Records", f"{matched_count}", border=True, width=225)
        st.metric("Total Discrepancy Records", f"{discrepancy_count}", border=True, width=225)   
        st.metric("Highest Discrepancy Outlet", f"{top_outlet}", delta=f"{top_outlet_count} records", border=True, delta_color="off", width=225)
            
    
    st.divider()

    discrepancy_df = df[df['status'] == 'Discrepancy'].copy()

    if discrepancy_df.empty:
        st.success("🎉 No discrepancies found in the entire dataset!")
    else:
        ("No outlets with discrepancies.")

    with col2:
        # Re-using the same bins and labels for consistency
        bins = [0, 2001, 10001, 100001, float('inf')]
        labels = ["Rounding (< 2k)", "Small (2k-10k)", "Medium (10k-100k)", "Big (> 100k)"]
        discrepancy_df['category'] = pd.cut(
            abs(discrepancy_df['difference']),
            bins=bins,
            labels=labels,
            right=False
        )
        st.subheader("Discrepancy Categories")
        category_counts = discrepancy_df['category'].value_counts().reset_index()
        category_counts.columns = ['category', 'count']
        
        fig = px.pie(
            category_counts,
            names='category',
            values='count',
            title='Distribution of Discrepancy Types (Overall)',
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        fig.update_layout(legend_title_text='Categories')
        st.plotly_chart(fig, use_container_width=True)

