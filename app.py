import streamlit as st
import pandas as pd
import plotly.express as px
import joblib
from sqlalchemy import create_engine
import streamlit_authenticator as stauth

# ----------------------
# CONFIGURATION (EDIT AS NEEDED)
# ----------------------
DB_URI = "mysql+pymysql://username:password@host/dbname" # <-- Set with your DB details
YIELD_MODEL_PATH = "models/yield_model.pkl"
PRICE_MODEL_PATH = "models/price_model.pkl"

# ----------------------
# AUTHENTICATION SETUP
# ----------------------
names = ['Alice', 'Bob']
usernames = ['alice', 'bob']
passwords = stauth.Hasher(['pwd1', 'pwd2']).generate()
authenticator = stauth.Authenticate(
    names, usernames, passwords, 
    'aqua_cookie', 'aqua_signature_key', cookie_expiry_days=1
)
name, authentication_status, username = authenticator.login('Login', 'main')
if not authentication_status:
    st.warning('Please login to access the dashboard.')
    st.stop()
st.sidebar.success(f'Welcome, {name}!')

# ----------------------
# SIDEBAR FILTERS
# ----------------------
st.sidebar.header("Filter Data")
species = st.sidebar.selectbox("Species", ["Shrimp", "Rohu", "Catla"])
region = st.sidebar.text_input("Region (e.g. Andhra Pradesh)", "Andhra Pradesh")

# ----------------------
# DATA LOADING FUNCTION
# ----------------------
@st.cache_data(show_spinner=False)
def load_data(species, region):
    engine = create_engine(DB_URI)
    query = f"SELECT * FROM production WHERE species='{species}' AND region LIKE '%{region}%'"
    df = pd.read_sql(query, engine)
    return df

# ----------------------
# LOAD DATA
# ----------------------
try:
    data = load_data(species, region)
except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.stop()
if data.empty:
    st.error("No records found for these filters.")
    st.stop()
st.write("### Sample Input Data", data.head())

# ----------------------
# FORECASTING UTILITIES
# ----------------------
def forecast_yield(data):
    model = joblib.load(YIELD_MODEL_PATH)
    # Dummy: use last yield as baseline (replace with your feature extraction)
    features = data[["yield"]].values[-1].reshape(1, -1)
    preds = model.predict(features)  # For sequence models, adjust accordingly
    dates = pd.date_range(start=data["date"].max(), periods=12, freq="M")
    return pd.DataFrame({"date": dates, "forecast_yield": preds.flatten()})

def forecast_price(data):
    model = joblib.load(PRICE_MODEL_PATH)
    features = data[["price"]].values[-1].reshape(1, -1)
    preds = model.predict(features)
    dates = pd.date_range(start=data["date"].max(), periods=12, freq="M")
    return pd.DataFrame({"date": dates, "forecast_price": preds.flatten()})

# ----------------------
# FORECAST VISUALIZATION
# ----------------------
st.write("## Forecasts")

col1, col2 = st.columns(2)
with col1:
    st.write("### Yield Forecast")
    yield_df = forecast_yield(data)
    fig1 = px.line(yield_df, x="date", y="forecast_yield", title="Yield Forecast")
    st.plotly_chart(fig1, use_container_width=True)
with col2:
    st.write("### Price Forecast")
    price_df = forecast_price(data)
    fig2 = px.line(price_df, x="date", y="forecast_price", title="Market Price Forecast")
    st.plotly_chart(fig2, use_container_width=True)

# ----------------------
# MAP VISUALIZATION (PLOTLY)
# Requires latitude/longitude columns in your source data
# ----------------------
if {"latitude", "longitude"}.issubset(data.columns):
    st.write("### Map: Farm Locations")
    figmap = px.scatter_mapbox(
        data,
        lat="latitude", lon="longitude",
        color="yield",
        hover_data=["region", "yield", "price"],
        mapbox_style="carto-positron", zoom=4, title="Farm Sites"
    )
    st.plotly_chart(figmap, use_container_width=True)

# ----------------------
# DATA EXPORT OPTION
# ----------------------
def convert_df(df):
    return df.to_csv(index=False).encode("utf-8")

csv = convert_df(pd.concat([yield_df, price_df], axis=1))
st.download_button(
    "Download Forecasts as CSV",
    csv,
    "forecast_results.csv",
    "text/csv"
)

# ----------------------
# FOOTER
# ----------------------
st.sidebar.markdown("---")
st.sidebar.write("Secure | Real-time | AI-powered Forecasts")
