import streamlit as st
from pymongo import MongoClient
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Airbnb Insights", layout="wide", page_icon="🏠")

# --- CSS Styling ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 20px;
    }
    .metric-title { color: #6c757d; font-size: 1.2rem; font-weight: 600; margin-bottom: 10px; }
    .metric-value { color: #007bff; font-size: 2rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_connection():
    uri = "mongodb+srv://nanthiwat2590_db_user:CU0CI6uilM2bDpgs@cluster0.dz13uyy.mongodb.net/?appName=Cluster0"
    return MongoClient(uri)

@st.cache_data(ttl=600)
def get_countries():
    client = init_connection()
    db = client['sample_airbnb']
    # Get distinct countries from the collection
    return db['listingsAndReviews'].distinct('address.country')

@st.cache_data(ttl=600)
def load_data(country):
    client = init_connection()
    db = client['sample_airbnb']
    collection = db['listingsAndReviews']
    
    projection = {
        'name': 1, 'summary': 1, 'property_type': 1, 'room_type': 1,
        'accommodates': 1, 'bedrooms': 1, 'beds': 1, 'price': 1,
        'cleaning_fee': 1, 'number_of_reviews': 1, 'review_scores.review_scores_rating': 1,
        'address.location.coordinates': 1, 'address.market': 1,
        'host.host_is_superhost': 1, 'host.host_response_time': 1,
        'images.picture_url': 1, 'minimum_nights': 1, 'cancellation_policy': 1,
        'amenities': 1, 'address.country': 1
    }
    
    # Query using the selected country or all
    if country == "Select All":
        cursor = collection.find({}, projection)
    else:
        cursor = collection.find({'address.country': country}, projection)
    
    data = []
    for doc in cursor:
        try:
            # Convert Decimal128 to float
            price = float(str(doc.get('price', 0)))
        except:
            price = 0.0
            
        coords = doc.get('address', {}).get('location', {}).get('coordinates', [0, 0])
        
        data.append({
            '_id': str(doc['_id']),
            'name': doc.get('name', ''),
            'summary': doc.get('summary', ''),
            'property_type': doc.get('property_type', ''),
            'room_type': doc.get('room_type', ''),
            'accommodates': doc.get('accommodates', 0),
            'bedrooms': doc.get('bedrooms', 0),
            'price': price,
            'number_of_reviews': doc.get('number_of_reviews', 0),
            'rating': doc.get('review_scores', {}).get('review_scores_rating', None),
            'longitude': coords[0] if len(coords) > 0 else 0,
            'latitude': coords[1] if len(coords) > 1 else 0,
            'market': doc.get('address', {}).get('market', ''),
            'is_superhost': doc.get('host', {}).get('host_is_superhost', False),
            'host_response_time': doc.get('host', {}).get('host_response_time', 'N/A'),
            'picture_url': doc.get('images', {}).get('picture_url', ''),
            'minimum_nights': int(doc.get('minimum_nights', 0)),
            'cancellation_policy': doc.get('cancellation_policy', ''),
            'country': doc.get('address', {}).get('country', '')
        })
    return pd.DataFrame(data)

# --- Sidebar ---
st.sidebar.title("🏠 Airbnb Dashboard")

try:
    countries = get_countries()
    if not countries:
        countries = ["United States", "Brazil", "Portugal", "Hong Kong", "Turkey"]
except Exception as e:
    st.error(f"Database connection error: {e}")
    st.stop()

country_options = ["Select All"] + sorted([c for c in countries if c])
selected_country = st.sidebar.selectbox("🌍 Select Country", country_options)

with st.spinner(f"Loading data for {selected_country}..."):
    df = load_data(selected_country)

# Only keeping the single combined page, no View selector needed in sidebar.

if df.empty:
    st.warning(f"No data available for {selected_country}")
    st.stop()

# Prepare string representation for charts
df['superhost_str'] = df['is_superhost'].map({True: 'Yes', False: 'No'})

# --- Main Content ---
st.title(f"Airbnb Insights: {selected_country}")

# Summary Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Total Listings</div><div class="metric-value">{len(df)}</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Avg Price</div><div class="metric-value">${df["price"].mean():.2f}</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Avg Rating</div><div class="metric-value">{df["rating"].mean():.1f}/100</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Superhosts</div><div class="metric-value">{df["is_superhost"].sum()}</div></div>', unsafe_allow_html=True)

st.markdown("---")

# 1. Average Price by Property Type (Top 10)
# This is affected ONLY by the country selection, so it uses the unfiltered df.
st.subheader("Average Price by Property Type (Top 10)")
avg_price = df.groupby('property_type')['price'].mean().sort_values(ascending=False).head(10).reset_index()
fig_bar = px.bar(avg_price, x='property_type', y='price', color='price', color_continuous_scale='Blues')
st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# 2. Interactive Charts (Map, Superhost Status, Host Response Time)
st.header("Interactive Map & Host Insights")
st.markdown("Select items in the charts below to cross-filter. (Map selections are not supported in this map type, but charts filter the map!)")

# Slices (Filters) like the old one
col_f1, col_f2 = st.columns(2)
with col_f1:
    price_range = st.slider("Price Range ($)", float(df['price'].min()), float(df['price'].max()), (0.0, float(df['price'].quantile(0.95))))
with col_f2:
    top_props = df['property_type'].value_counts().head(5).index.tolist()
    prop_types = st.multiselect("Property Type", df['property_type'].unique(), default=top_props)

interactive_df = df[(df['price'] >= price_range[0]) & (df['price'] <= price_range[1]) & (df['property_type'].isin(prop_types))]

# Determine filters based on current session state selections
mask_pie = pd.Series(True, index=interactive_df.index)
if 'superhost_pie' in st.session_state:
    sel = st.session_state['superhost_pie'].get('selection', {}).get('points', [])
    if sel:
        selected = [p.get('x', p.get('label')) for p in sel]
        mask_pie = interactive_df['superhost_str'].isin(selected)

mask_hist = pd.Series(True, index=interactive_df.index)
if 'response_hist' in st.session_state:
    sel = st.session_state['response_hist'].get('selection', {}).get('points', [])
    if sel:
        selected = [p['x'] for p in sel]
        mask_hist = interactive_df['host_response_time'].isin(selected)

# Datasets for each chart
df_pie = interactive_df[mask_hist]
df_hist = interactive_df[mask_pie]
df_map = interactive_df[mask_pie & mask_hist]

col1, col2, col3 = st.columns([1, 1.5, 1.5])

with col1:
    st.subheader("Filtered Listings")
    st.markdown(f'<div class="metric-card" style="margin-top: 1rem;"><div class="metric-title">Listings Found</div><div class="metric-value">{len(df_map)}</div></div>', unsafe_allow_html=True)

with col2:
    st.subheader("Superhost Status")
    # Using histogram instead of pie because Plotly pie charts don't support selection events natively
    fig_superhost = px.histogram(df_pie, x='superhost_str', color='superhost_str', color_discrete_map={'Yes': '#ffc107', 'No': '#6c757d'})
    fig_superhost.update_layout(xaxis_title="Is Superhost?", yaxis_title="Count", showlegend=False)
    st.plotly_chart(fig_superhost, use_container_width=True, on_select="rerun", key="superhost_pie")

with col3:
    st.subheader("Host Response Time")
    resp_data = df_hist[df_hist['host_response_time'] != 'N/A']
    fig_resp = px.histogram(resp_data, x='host_response_time', color='host_response_time')
    st.plotly_chart(fig_resp, use_container_width=True, on_select="rerun", key="response_hist")

st.subheader("Interactive Location Map")
if not df_map.empty:
    st.map(df_map, latitude='latitude', longitude='longitude')
else:
    st.warning("No listings match the selected filters.")

st.markdown("---")