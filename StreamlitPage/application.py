import streamlit as st
import folium
import numpy as np
import pandas as pd
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import matplotlib.colors as mcolors
import plotly.express as px
import plotly.graph_objects as go
import calendar
from pathlib import Path
import plotly.colors
import random

# Load data
@st.cache_data
def load_data():
    data = pd.read_csv(r"data\Applications.csv")
    df_Mapped = pd.read_csv("data/dataMapping.csv")
    data['Month_Name'] = data['Month'].apply(lambda x: calendar.month_abbr[x]) 
    return data, df_Mapped

data, df_Mapped = load_data()
df_Large = data.copy()


# Group definitions
group_small = [
    "AIRMASS", "ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_UVA", "ALLSKY_SFC_UVB",
    "ALLSKY_SFC_UV_INDEX", "CLOUD_AMT", "CLOUD_AMT_DAY", "CLOUD_AMT_NIGHT",
    "CLRSKY_DAYS", "MIDDAY_INSOL", "PSH", "PW"
]

group_large = [
    "EVLAND", "GWETPROF", "GWETROOT", "GWETTOP", "PRECSNO", "PRECTOTCORR",
    "QV2M", "RH2M", "RHOA", "T10M", "T10M_MAX", "T10M_MIN", "T2M",
    "T2M_MAX", "T2M_MIN", "TO3", "TS", "TSOIL1", "TSOIL2", "TSOIL3",
    "TSOIL4", "TSOIL5", "TSOIL6", "TS_MAX", "TS_MIN", "WD2M", "WD50M",
    "WS2M", "WS2M_MAX", "WS2M_MIN", "WS50M", "WS50M_MAX", "WS50M_MIN", "Z0M"
]

# Combine groups for the dropdown
attribute_options = df_Mapped["Code"]

# Streamlit UI
st.title("Egypt Climate Data Report")

# Create tabs for different sections
tab1, tab2, tab3 = st.tabs(["Visualization", "LSTM Prediction", "AgriCluster"])

with tab1:
    # =============================================
    # SECTION 1: ATTRIBUTE AND YEAR SELECTION
    # =============================================
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.selectbox("Select Year:", 
                                   options=sorted(data['YEAR'].unique()),
                                   index=0)
    with col2:
        selected_attribute = st.selectbox("Select Attribute:", 
                                        options=attribute_options,
                                        index=attribute_options.to_list().index("PRECTOTCORR") if "PRECTOTCORR" in attribute_options.to_list() else 0)

    # Display attribute information
    attribute_info = df_Mapped[df_Mapped["Code"] == selected_attribute].iloc[0]
    st.markdown("### Attribute Information")
    
    # Create a table with the attribute information
    info_table = pd.DataFrame({
        'Property': ['Physical Meaning', 'Economic Usage', 'Unit'],
        'Value': [
            attribute_info['Physical Meaning'],
            attribute_info['Economic Usage'],
            attribute_info['Unit']
        ]
    })
    st.table(info_table)

    # =============================================
    # SECTION 2: FOLIUM MAP
    # =============================================
    st.header("Geospatial Visualization")
    
    map_agg_mode = st.selectbox("Aggregation Mode:", ["Week", "Month", "DOY"])
    map_period = st.number_input("Period:", min_value=1, max_value=366, value=13)

    def display_aggregated_map(year, attribute, agg_mode, period):

        EGYPT_BOUNDS = {
            'min_lat': 22.0,  
            'max_lat': 31.8, 
            'min_lon': 24.5,  
            'max_lon': 37.0    
        }

        

        df_year = data[data['YEAR'] == year].copy()
        if df_year.empty:
            st.warning(f"No data available for Year {year}")
            return

        if agg_mode == "Week":
            df_agg = df_year[df_year['Week'] == period]
            title_period = f"Week: {period}"
        elif agg_mode == "Month":
            df_agg = df_year[df_year['Month'] == period]
            title_period = f"Month: {period}"
        elif agg_mode == "DOY":
            df_agg = df_year[df_year['DOY'] == period]
            title_period = f"DOY: {period}"
        else:
            df_agg = df_year
            title_period = "All Days"

        if df_agg.empty:
            st.warning(f"No data available for {agg_mode} {period} in Year {year}")
            return

        
        bounded_df = df_agg[
            (df_agg['LAT'] >= EGYPT_BOUNDS['min_lat']) & 
            (df_agg['LAT'] <= EGYPT_BOUNDS['max_lat']) & 
            (df_agg['LON'] >= EGYPT_BOUNDS['min_lon']) & 
            (df_agg['LON'] <= EGYPT_BOUNDS['max_lon'])
        ]

        group_cols = ['LAT', 'LON']
        agg_df = bounded_df.groupby(group_cols)[attribute].mean().reset_index()

        min_value = agg_df[attribute].min()
        max_value = agg_df[attribute].max()
        
        agg_df['Intensity'] = agg_df[attribute].apply(
            lambda x: (x - min_value) / (max_value - min_value) if max_value > min_value else min_value
        )

        
        center_lat = (EGYPT_BOUNDS['min_lat'] + EGYPT_BOUNDS['max_lat']) / 2
        center_lon = (EGYPT_BOUNDS['min_lon'] + EGYPT_BOUNDS['max_lon']) / 2

        
        egypt_map = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=6,
            min_lat=EGYPT_BOUNDS['min_lat'],
            max_lat=EGYPT_BOUNDS['max_lat'],
            min_lon=EGYPT_BOUNDS['min_lon'],
            max_lon=EGYPT_BOUNDS['max_lon'],
            max_bounds=True,
            control_scale=True,
            min_zoom=6,  # Set minimum zoom level
            zoom_control=True
        )
        


        title_html = f'<h3 align="center" style="font-size:20px"><b>Year: {year} - {title_period} - Attribute: {attribute}</b></h3>'
        egypt_map.get_root().html.add_child(folium.Element(title_html))
        
        
        if not agg_df.empty:
            heatmap_data = agg_df[agg_df['Intensity'] > 0][['LAT', 'LON', 'Intensity']].values.tolist()
            HeatMap(heatmap_data, radius=10, blur=15, max_zoom=10).add_to(egypt_map)

            colors = ["black", "blue", "cyan", "yellow", "orange", "red"]
            quantiles = np.quantile(agg_df["Intensity"], [0.01, 0.55, 0.7, 0.85, 0.95, 1.0])

            def intensity_to_color(intensity):
                if intensity <= quantiles[0]:
                    return mcolors.to_hex(colors[0])
                elif intensity <= quantiles[1]:
                    return mcolors.to_hex(colors[1])
                elif intensity <= quantiles[2]:
                    return mcolors.to_hex(colors[2])
                elif intensity <= quantiles[3]:
                    return mcolors.to_hex(colors[3])
                elif intensity <= quantiles[4]:
                    return mcolors.to_hex(colors[4])
                else:
                    return mcolors.to_hex(colors[5])

            for _, row in agg_df.iterrows():
                if row["Intensity"] > 0:
                    tooltip_text = f"{attribute}: {row[attribute]:.5f}"
                    if 'City' in agg_df.columns:
                        tooltip_text = f"City: {row['City']}, " + tooltip_text
                    folium.CircleMarker(
                        location=[row['LAT'], row['LON']],
                        radius=7,
                        color=intensity_to_color(row['Intensity']),
                        fill=True,
                        fill_color=intensity_to_color(row['Intensity']),
                        fill_opacity=0.6,
                        tooltip=tooltip_text
                    ).add_to(egypt_map)
        else:
            st.warning("No data points within Egypt's boundaries")

        return egypt_map

    m = display_aggregated_map(selected_year, selected_attribute, map_agg_mode, map_period)
    if m:
        st_data = st_folium(m, width=700, height=600)

    if st.button("Save Map as HTML"):
        if m:
            filename = f"Aggregated_{selected_attribute}{selected_year}{map_agg_mode}{map_period}.html"
            m.save(filename)
            with open(filename, "rb") as f:
                st.download_button(
                    label="Download HTML",
                    data=f,
                    file_name=filename,
                    mime="text/html"
                )
        else:
            st.warning("No map to save")

    # =============================================
    # SECTION 3: GRAPHS VISUALIZATION
    # =============================================
    st.header("Statistical Visualizations")

    graph_month = st.selectbox("Select Month:", 
                             options=list(calendar.month_abbr)[1:],
                             index=0)

    # Get attribute name for display
    Att_Name = df_Mapped.loc[df_Mapped["Code"] == selected_attribute, "Name"].iloc[0]


    month_num = list(calendar.month_abbr).index(graph_month)
    df_filtered = data[(data['YEAR'] == selected_year) & (data['Month'] == month_num)]

    if not df_filtered.empty:
        
        base_dir = Path(f"resources/{selected_attribute}")
        base_dir.mkdir(parents=True, exist_ok=True)

        # ======================
        # HISTOGRAM
        # ======================
        st.subheader(f"Histogram of {Att_Name}")
        fig_hist = px.histogram(df_filtered, 
                               x=selected_attribute, 
                               nbins=80,
                               title=f"{Att_Name} Distribution for {graph_month} {selected_year}",
                               labels={selected_attribute: Att_Name, "count": "Frequency"},
                               color_discrete_sequence=["royalblue"])
        
        fig_hist.update_layout(template="plotly_white")
        st.plotly_chart(fig_hist, use_container_width=True)

        # ======================
        # MONTHLY STATS BAR PLOT
        # ======================
        st.subheader(f"Monthly Statistics for {Att_Name}")
        
        month_stats = data[data['YEAR'] == selected_year].groupby("Month")[selected_attribute].agg(["min", "max", "mean"]).reset_index()
        month_stats['Month_Name'] = month_stats['Month'].apply(lambda x: calendar.month_abbr[x])
        
        fig_stats = px.bar(month_stats, 
                          x="Month_Name", 
                          y=["min", "max", "mean"],
                          title=f"Min, Max, and Mean {Att_Name} for {selected_year}",
                          labels={"value": Att_Name, "Month_Name": "Month"},
                          barmode="group")
        
        st.plotly_chart(fig_stats, use_container_width=True)

        # ======================
        # CITY STATS BAR PLOT
        # ======================
        st.subheader(f"City Statistics for {Att_Name}")
        
        city_stats = df_filtered.groupby("City")[selected_attribute].agg(["min", "max", "mean"]).reset_index()
        # Sort cities by max value in descending order
        city_stats = city_stats.sort_values(by="max", ascending=False)
        
        fig_city = px.bar(city_stats, 
                         x="City", 
                         y=["min", "max", "mean"],
                         title=f"City-wise {Att_Name} Statistics for {graph_month} {selected_year}",
                         labels={"value": Att_Name, "City": "City"},
                         barmode="group")
        
        st.plotly_chart(fig_city, use_container_width=True)


        st.subheader(f"Top 10 Highest {Att_Name} Values")
        top_10_points = df_filtered.nlargest(10, selected_attribute)[["City", selected_attribute, "Date"]]
        st.dataframe(top_10_points)

    else:
        st.warning(f"No data available for {graph_month} {selected_year}")
        
data = pd.read_csv("data/forecasted_data.csv")  
with tab2:
    # =============================================
    # SECTION 3: LSTM MODEL DEPLOYMENT
    # =============================================
    st.header("LSTM Model Prediction")
    
    st.subheader("LSTM Model Parameters")
    
    # Date range selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=pd.to_datetime("2025-05-17"))
    with col2:
        end_date = st.date_input("End Date", value=pd.to_datetime("2025-12-31"))
    
    # Location selection
    col3, col4 = st.columns(2)
    with col3:
        lon = st.number_input("Longitude", min_value=data["LON"].min(), max_value=data["LON"].max(), value=30.0, step=0.5,format="%.1f")
    with col4:
        lat = st.number_input("Latitude", min_value=data["LAT"].min(), max_value=data["LAT"].max(), value=26.0, step=0.5,format="%.1f")
    
    # Attribute selection
    lstm_attribute = st.selectbox("Select Attribute for Prediction:", 
                                options=attribute_options,
                                index=attribute_options.to_list().index("PRECTOTCORR") if "PRECTOTCORR" in attribute_options.to_list() else 0)
    
if st.button("Generate Predictions"):
    # تحويل عمود التاريخ لضمان إنه datetime
    data["Date"] = pd.to_datetime(data["Date"])

    # فلترة البيانات حسب التواريخ والموقع
    filtered_data = data[
        (data["LON"] == lon) & 
        (data["LAT"] == lat) & 
        (data["Date"] >= pd.to_datetime(start_date)) & 
        (data["Date"] <= pd.to_datetime(end_date))
    ][["Date", "LON", "LAT", lstm_attribute]]


    if filtered_data.empty:
        st.warning("No data found for the selected location and date range.")
    else:
        
        filtered_data = filtered_data.rename(columns={"Date": "Day"})
        filtered_data["Location"] = f"LON: {lon}, LAT: {lat}"
        filtered_data = filtered_data[["Day", "Location", lstm_attribute]]

        
        st.subheader("LSTM Model Output (From Historical Data)")
        st.dataframe(filtered_data)

        
        fig_pred = px.line(filtered_data, 
                          x='Day', 
                          y=lstm_attribute,
                          title=f"{lstm_attribute} Over Time at LON: {lon}, LAT: {lat}")
        st.plotly_chart(fig_pred, use_container_width=True)



with tab3:
    st.header("Agricultural Cluster Map")
    st.markdown("""
    ### Egypt Agricultural Cluster Map
    This section provides access to the Agricultural Cluster Map visualization tool.
    """)
    
    # Create a button that opens the link in a new tab
    if st.button("Open Agricultural Cluster Map"):
        st.markdown("[Click here to open the Agricultural Cluster Map in a new tab](https://mariamehab66.github.io/Cluster_Map/)")
    
    # Display some information about the cluster map
    st.markdown("""
    ### About the Cluster Map
    The Cluster Map provides:
    - distribution clusters across Egypt
    - Interactive visualization of agricultural zones
    
    Use the link above to explore the full interactive map.
    """)