import streamlit as st
import pandas as pd
import plotly.express as px
import joblib
from sqlalchemy import create_engine
import streamlit_authenticator as stauth

# ----------------------
# CONFIG (🔒 Replace with your values)
# ----------------------
DB_URI = "mysql+pymysql://username:password@127.0.0.1:3306/aquadb"  # Update your DB creds
YIELD_MODEL_PATH = "models/yield_model.pkl"
PRICE_MODEL_PATH = "models/price_model.pkl"

# ----------------------
# AUTHENTICATION 🔐
# ----------------------
names = ['Alice', 'Bob']
usernames = ['alice', 'bob']
# Passwords were hashed with stauth.Hasher(['pwd1', 'pwd2']).generate()
hashed_passwords = [
    'pbkdf2:sha256:260000$ZPwmAm...FhSYMEK73E',  # Replace with actual hashed passwords!
    'pbkdf2:sha256:260000$jdks3m...Kw87hdls983'
]

authenticator = stauth.Authenticate(
    names=names,
    usernames=usernames,
    passwords=hashed_passwords,
    cookie_name="aqua_cookie",
    key="aqua_secret_key",
    cookie_expiry_days=1
)

name, auth_status, username = authenticator.login("Login", "main")

if not auth_status:
    st.warning("Please login to access the dashboard.")
    st.stop()

# ----------------------
# PAGE CONFIG
# ----------------------
st.set_page_config(page_title="Aqua Forecast", layout="wide")
st.title("📈 Aquaculture Yield & Market Price Forecast Dashboard")

# ----------------------
# SIDEBAR FILTERS
# ----------------------
st.sidebar.subheader("🔍 Filter Data")
species = st.sidebar.selectbox("Species", ["Shrimp", "Rohu", "Catla"])
region = st.sidebar.text_input("Region (e.g. Andhra Pradesh)", "Andhra Pradesh")

# ----------------------
# DATA LOADING
# ----------------------
@st.cache_data(show_spinner=False)
def load_data(species, region):
    try:
        engine = create_engine(DB_URI)
        query = f"""
        SELECT * FROM production 
        WHERE species='{species}' AND region LIKE '%{region}%'
        """
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        st.error(f"Failed to connect to the database: {e}")
        return pd.DataFrame()

data = load_data(species, region)

if data.empty:
    st.error("No data found for selected filters.")
    st.stop()

st.write(f"### {species} Data for {region}")
st.dataframe(data.head())

# ----------------------
# FORECAST FUNCTIONS
# ----------------------
def forecast_yield(data):
    try:
        model = joblib.load(YIELD_MODEL_PATH)
        recent_yield = data["yield"].values[-1].reshape(1, -1)
        predictions = model.predict(recent_yield)
        dates = pd.date_range(data["date"].max(), periods=12, freq="M")
        return pd.DataFrame({"date": dates, "forecast_yield": predictions.flatten()})
    except Exception as e:
        st.error(f"Yield prediction error: {e}")
        return pd.DataFrame()

def forecast_price(data):
    try:
        model = joblib.load(PRICE_MODEL_PATH)
        recent_price = data["price"].values[-1].reshape(1, -1)
        predictions = model.predict(recent_price)
        dates = pd.date_range(data["date"].max(), periods=12, freq="M")
        return pd.DataFrame({"date": dates, "forecast_price": predictions.flatten()})
    except Exception as e:
        st.error(f"Price prediction error: {e}")
        return pd.DataFrame()

# ----------------------
# FORECAST VISUALIZATION
# ----------------------
st.subheader("📊 Forecasts")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Yield Forecast")
    yield_forecast = forecast_yield(data)
    if not yield_forecast.empty:
        fig1 = px.line(yield_forecast, x="date", y="forecast_yield", title="Projected Yield")
        st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.markdown("### Price Forecast")
    price_forecast = forecast_price(data)
    if not price_forecast.empty:
        fig2 = px.line(price_forecast, x="date", y="forecast_price", title="Projected Price")
        st.plotly_chart(fig2, use_container_width=True)

# ----------------------
# MAP VISUALIZATION (OPTIONAL)
# ----------------------
if {"latitude", "longitude"}.issubset(data.columns):
    st.subheader("🗺️ Farm Map")
    fig3 = px.scatter_mapbox(
        data,
        lat="latitude",
        lon="longitude",
        color="yield",
        zoom=4,
        mapbox_style="carto-positron",
        hover_data=["region", "yield", "price"],
    )
    st.plotly_chart(fig3, use_container_width=True)

# ----------------------
# DOWNLOAD BUTTON
# ----------------------
st.subheader("⬇️ Download Forecast Data")
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

if not yield_forecast.empty and not price_forecast.empty:
    forecast_combined = pd.merge(yield_forecast, price_forecast, on="date")
    csv = convert_df(forecast_combined)
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name="aqua_forecast.csv",
        mime="text/csv",
    )

# ----------------------
# FOOTER
# ----------------------
st.sidebar.markdown("---")
st.sidebar.caption(f"🧑 Logged in as: {name}")
st.sidebar.caption("Built with ❤️ using Streamlit, SQL & AI")
