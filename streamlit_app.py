"""SmartPlate student app. Run:  python3 -m streamlit run streamlit_app.py"""

import csv
import os
from datetime import datetime

import streamlit as st

from live_menu import get_fiu_time, determine_meal_period, get_menu, LOCATION_NAME
from recommendation import get_target_calories, find_meal_options

HISTORY_FILE = "meal_history.csv"
HISTORY_COLUMNS = ["timestamp", "panther_id", "student_name", "hunger_level", "meal_type",
                   "foods_selected", "total_calories", "waste_level", "leftover_food",
                   "smartpoints"]
SMARTPOINTS = {"Nothing": 20, "A little": 10, "Some": 5, "A lot": 0}
MEAL_PERIODS = ["Breakfast", "Lunch", "Dinner"]

st.set_page_config(page_title="SmartPlate", page_icon="🥗", layout="centered")

S = st.session_state
for key, value in {"logged_in": False, "name": "", "panther_id": "", "options": None,
                   "meal": None, "total": 0, "hunger": None, "meal_type": None,
                   "confirmed": False, "feedback_done": False, "points": 0}.items():
    S.setdefault(key, value)


def save_meal_history(waste_level, leftover_food, smartpoints):
    """Append one finished meal to meal_history.csv (the link to the dashboard)."""
    new_file = not os.path.exists(HISTORY_FILE) or os.path.getsize(HISTORY_FILE) == 0
    with open(HISTORY_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(HISTORY_COLUMNS)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), S.panther_id, S.name, S.hunger,
            S.meal_type, " | ".join(food["food_name"] for food in S.meal), S.total,
            waste_level, leftover_food, smartpoints])


@st.cache_data(ttl=300, show_spinner=False)
def cached_menu(meal_period, day, use_live):
    """Fetch the menu at most once every 5 minutes."""
    return get_menu(meal_period, get_fiu_time(), use_live)


def reset_meal():
    for key in ["options", "meal", "hunger", "meal_type"]:
        S[key] = None
    S.total, S.confirmed, S.feedback_done, S.points = 0, False, False, 0


st.title("🥗 SmartPlate")

# ------------------------------------------------------------------ Step 1: login
if not S.logged_in:
    st.subheader(f"Welcome to {LOCATION_NAME}")
    st.write("Choose smarter portions, reduce food waste, and earn SmartPoints.")
    name = st.text_input("Name")
    panther_id = st.text_input("Panther ID")
    st.caption("Prototype login only. It is not connected to FIU's real sign-in system. Please use a fake name and a made-up ID while testing online.")
    if st.button("Login", type="primary", use_container_width=True):
        if name.strip() and panther_id.strip():
            S.logged_in, S.name, S.panther_id = True, name.strip(), panther_id.strip()
            st.rerun()
        else:
            st.warning("Please enter your name and Panther ID.")
    st.stop()

# ------------------------------------------------------------------ Step 2: dining context
now = get_fiu_time()

with st.sidebar:
    st.header("Dining context")
    demo_mode = st.checkbox(
        "Demo mode: ignore the clock", value=False,
        help="menu.csv only has breakfast items, so use this to demo outside breakfast hours.")
    if demo_mode:
        period = st.selectbox("Meal period", MEAL_PERIODS)
    else:
        period = determine_meal_period(now)
    use_live = st.checkbox("Try the live DineOnCampus menu", value=True)
    st.caption("Serving times in this prototype are test rules, not FIU's official hours.")
    if st.button("Log out"):
        for key in list(S.keys()):
            del S[key]
        st.rerun()

st.write(f"Hi, **{S.name}**! 👋")
st.caption(f"{now:%A, %B %d, %Y · %I:%M %p} · {LOCATION_NAME}")

if period is None:
    st.info("The dining hall is closed right now. Come back at breakfast, lunch or dinner.")
    st.stop()

menu, source, note = cached_menu(period, now.strftime("%Y-%m-%d"), use_live)
if note:
    st.caption(f"ℹ️ {note}")
st.caption(f"**{period} menu** · source: "
           f"{'live DineOnCampus' if source == 'live' else 'local menu.csv (fallback)'}")

if not menu:
    st.warning(f"menu.csv has no {period} items. Turn on Demo mode in the sidebar and "
               "choose Breakfast, or add rows to menu.csv.")
    st.stop()


def food_line(food):
    st.write(f"• {food['food_name']} — {food['portion']} — {food['calories']} cal")


# ------------------------------------------------------------------ Steps 3-9: pick a plate
if not S.confirmed:
    st.subheader("1️⃣ How hungry are you right now?")
    hunger = st.radio("Hunger level", ["Light", "Moderate", "Very Hungry"], horizontal=True)
    st.caption("Meal sizes of about 500, 600 and 700 calories are prototype settings, "
               "not medical or dietary advice.")

    if st.button("Find my meal 🍽️", type="primary"):
        S.hunger = hunger
        S.options = find_meal_options(menu, get_target_calories(hunger))
        S.meal, S.total, S.meal_type = None, 0, None

    if S.options is not None:
        st.divider()
        st.subheader("2️⃣ Choose your plate")
        if not S.options:
            st.info("No combination matched this menu. Build your own plate below.")
        for i, (meal, total) in enumerate(S.options, start=1):
            with st.container(border=True):
                st.markdown(f"**🍽️ Option {i}**")
                for food in meal:
                    food_line(food)
                st.write(f"**Total: {total} calories**")
                if st.button("Select this meal", key=f"select_{i}"):
                    S.meal, S.total, S.meal_type = list(meal), total, "Recommended"
                    S.hunger = S.hunger or hunger
                    st.rerun()

    st.divider()
    st.subheader("Or build your own plate 🥣")
    st.caption("You never have to accept a recommendation.")
    names = [food["food_name"] for food in menu]
    chosen = st.multiselect("Choose foods from the menu:", names)
    custom = [food for food in menu if food["food_name"] in chosen]
    if custom:
        custom_total = sum(food["calories"] for food in custom)
        st.write(f"**Current total: {custom_total} calories**")
        if st.button("Use my custom plate"):
            S.meal, S.total, S.meal_type = custom, custom_total, "Custom"
            S.hunger = S.hunger or hunger
            st.rerun()

    if S.meal:
        st.divider()
        st.subheader("3️⃣ Your selected plate")
        with st.container(border=True):
            for food in S.meal:
                food_line(food)
            st.write(f"**Total: {S.total} calories**")
            st.caption(f"Plate type: {S.meal_type}")
        if st.button("Confirm my plate ✅", type="primary", use_container_width=True):
            S.confirmed = True
            st.rerun()

# ------------------------------------------------------------------ Step 10: waste feedback
elif not S.feedback_done:
    st.success("Your plate is confirmed! 🍽️")
    st.subheader("4️⃣ After your meal")
    st.write("Your feedback helps SmartPlate reduce food waste at the dining hall.")
    waste = st.radio("How much food was left on your plate?",
                     ["Nothing", "A little", "Some", "A lot"])
    if waste == "Nothing":
        leftover = "None"
        st.write("🎉 Great! That portion worked well for you.")
    else:
        leftover = st.selectbox("Which food did you leave the most?",
                                [food["food_name"] for food in S.meal])
    if st.button("Submit feedback", type="primary", use_container_width=True):
        S.points = SMARTPOINTS[waste]
        save_meal_history(waste, leftover, S.points)
        S.feedback_done = True
        st.rerun()

# ------------------------------------------------------------------ Step 11: SmartPoints
else:
    st.success("Feedback submitted! 🎉")
    st.header(f"⭐ +{S.points} SmartPoints")
    st.write(f"Thanks for helping reduce food waste at {LOCATION_NAME}.")
    st.caption("SmartPoints are a prototype feature, not connected to FIU's reward systems.")
    st.divider()
    st.subheader("Your SmartPlate summary")
    st.write(f"**Hunger level:** {S.hunger}")
    st.write(f"**Plate type:** {S.meal_type}")
    st.write(f"**Meal size:** {S.total} calories")
    if st.button("Start another meal 🔄", use_container_width=True):
        reset_meal()
        st.rerun()
