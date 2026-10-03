"""Manager dashboard preview. Reads meal_history.csv (real) or meal_history_demo.csv (simulated).

This is a quick Python preview of the metrics the Power BI dashboard should show.
"""
import os

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="SmartPlate · Manager", page_icon="📊", layout="wide")
st.title("📊 Dining hall dashboard (preview)")

REAL, DEMO = "meal_history.csv", "meal_history_demo.csv"


def load(path):
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["has_waste"] = df["waste_level"] != "Nothing"
    return df


have_real = os.path.exists(REAL) and os.path.getsize(REAL) > 0
have_demo = os.path.exists(DEMO)
choices = ([f"Real app data ({REAL})"] if have_real else []) + \
          ([f"SIMULATED demo data ({DEMO})"] if have_demo else [])
if not choices:
    st.info("No data yet. Run `python3 generate_demo_data.py`, or submit a meal in the student app.")
    st.stop()
pick = st.sidebar.radio("Data source", choices)
df = load(REAL if pick.startswith("Real") else DEMO)
if pick.startswith("SIMULATED"):
    st.warning("This is SIMULATED demo data. It is not data from real FIU students.")

c1, c2, c3 = st.columns(3)
c1.metric("Total meals tracked", f"{len(df):,}")
c2.metric("Waste rate", f"{df['has_waste'].mean():.0%}",
          help="Share of meals where the student reported any food left.")
c3.metric("Average SmartPoints", f"{df['smartpoints'].mean():.1f}")

left, right = st.columns(2)
with left:
    st.subheader("Most wasted foods")
    foods = df[df["leftover_food"] != "None"]["leftover_food"].value_counts().rename_axis("Food").reset_index(name="Times left the most")
    st.plotly_chart(px.bar(foods.sort_values("Times left the most"), x="Times left the most",
                           y="Food", orientation="h"), use_container_width=True)
with right:
    st.subheader("Waste by hunger level")
    by_h = df.groupby("hunger_level")["has_waste"].mean().mul(100).round(1).reset_index()
    by_h.columns = ["Hunger level", "Meals with waste (%)"]
    st.plotly_chart(px.bar(by_h, x="Hunger level", y="Meals with waste (%)",
                           category_orders={"Hunger level": ["Light", "Moderate", "Very Hungry"]}),
                    use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Recommended vs custom plates")
    by_t = df.groupby("meal_type").agg(meals=("has_waste", "size"),
                                       waste=("has_waste", "mean")).reset_index()
    by_t["Meals with waste (%)"] = (by_t["waste"] * 100).round(1)
    st.plotly_chart(px.bar(by_t, x="meal_type", y="Meals with waste (%)",
                           hover_data=["meals"]), use_container_width=True)
    st.caption("Compare the number of meals before reading anything into a gap.")
with right:
    st.subheader("How often each food is selected")
    freq = df["foods_selected"].str.split(" | ", regex=False).explode().value_counts()
    freq = freq.rename_axis("Food").reset_index(name="Times selected")
    st.plotly_chart(px.bar(freq.sort_values("Times selected"), x="Times selected", y="Food",
                           orientation="h"), use_container_width=True)

st.subheader("Waste trend over time")
daily = df.set_index("timestamp").resample("D")["has_waste"].agg(["size", "mean"])
daily = daily[daily["size"] > 0].reset_index()
daily["Waste rate (%)"] = (daily["mean"] * 100).round(1)
st.plotly_chart(px.line(daily, x="timestamp", y="Waste rate (%)", markers=True),
                use_container_width=True)
