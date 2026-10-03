"""
SmartPlate live-menu module
===========================
DineOnCampus  ->  this module  ->  recommendation engine  ->  student interface

Rule from the guide:
    live menu works  -> use live DineOnCampus data
    live menu fails  -> use the local menu.csv, so the demo never breaks

HOW THE LIVE MENU WORKS: DineOnCampus has no public documentation, but its own website
loads the daily menu from apiv4.dineoncampus.com. This module calls the same two addresses
(periods, then menu) for 8th Street Campus Kitchen. The response format was checked against
the real site for Oct 2, 2026 (Breakfast, Lunch, Dinner). If anything fails (no internet,
address changed, kitchen closed), it returns menu.csv and says why.
NOTE: unofficial endpoints; ask FIU Dining for permission before any real deployment.
"""

import csv
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

# ----------------------------------------------------------------------------------
# SETTINGS
# ----------------------------------------------------------------------------------
LOCATION_NAME = "8th Street Campus Kitchen"
TIMEOUT_SECONDS = 6         # never let a slow website freeze the demo
CSV_FALLBACK = "menu.csv"


def get_fiu_time():
    """Current date and time in Miami (FIU local time)."""
    return datetime.now(ZoneInfo("America/New_York"))


def determine_meal_period(now=None):
    """TEMPORARY time rules. These are NOT FIU's official serving hours."""
    now = now or get_fiu_time()
    if 7 <= now.hour < 11:
        return "Breakfast"
    if 11 <= now.hour < 16:
        return "Lunch"
    if 16 <= now.hour < 22:
        return "Dinner"
    return None          # closed (overnight)


# ----------------------------------------------------------------------------------
# SIMPLE KEYWORD CATEGORIES (used when the live data has no SmartPlate category)
# ----------------------------------------------------------------------------------
_WORDS = [
    ("Protein", ["egg", "sausage", "chicken", "turkey", "beef", "pork", "fish", "salmon",
                 "tofu", "frittata", "omelet", "bacon", "ham", "burger", "steak", "tilapia",
                 "hot dog", "bolognese", "shaved beef", "hummus", "garbanzo", "tagine"]),
    ("Grain", ["pancake", "waffle", "grits", "rice", "bread", "toast", "pasta", "noodle",
               "cereal", "oatmeal", "bagel", "muffin", "pizza", "quinoa", "farro", "tortilla",
               "penne", "roll", "lo mein", "breadstick", "rotini"]),
    ("Side", ["potato", "hash brown", "puff", "vegetable", "veggie", "fries", "beans",
              "broccoli", "salad", "corn", "mushroom", "squash", "chili", "soup", "kale"]),
    ("Fruit", ["fruit", "apple", "banana", "orange", "berry", "berries", "melon"]),
    ("Dairy", ["yogurt", "milk"]),
    ("Topping", ["cheese", "syrup"]),
]


def categorize_food(food_name):
    """Guess a SmartPlate category from the food's name."""
    name = food_name.lower()
    for category, words in _WORDS:
        if any(word in name for word in words):
            return category
    return "Other"


# ----------------------------------------------------------------------------------
# LOCAL CSV MENU (the fallback)
# ----------------------------------------------------------------------------------
def load_csv_menu(filename=CSV_FALLBACK):
    """Read menu.csv. Columns: food_id, food_name, category, portion, calories, meal_period."""
    menu = []
    with open(filename, "r", newline="") as file:
        for food in csv.DictReader(file):
            food["calories"] = int(food["calories"])
            menu.append(food)
    return menu


# ----------------------------------------------------------------------------------
# LIVE DINEONCAMPUS MENU
# ----------------------------------------------------------------------------------
# These addresses were read from the DineOnCampus website itself (the same ones the page
# uses to show "What's on the menu" for 8th Street Campus Kitchen). They are unofficial
# and undocumented, so they can change; that is why the menu.csv fallback exists.
API = "https://apiv4.dineoncampus.com"
LOCATION_ID = "5b9fda57f3eeb60c6e592caf"        # 8th Street Campus Kitchen (FIU)
PERIODS_URL = API + "/locations/{loc}/periods/?date={date}"
MENU_URL = API + "/locations/{loc}/menu?date={date}&period={period}"

# Things that are not part of a plate: condiments, dressings, toppings, desserts.
_NOT_A_PLATE = ["sauce", "dressing", "vinegar", "olive oil", "mustard", "mayonnaise",
                "ketchup", "pepper", "furikake", "seasoning", "sesame seed", "ginger root",
                "garlic", "cracker", "croutons", "french fried onions", "dried cranberries",
                "cheez-it", "parmesan", "chili crisp", "chips", "syrup", "butter",
                "cookie", "cake", "brownie", "blondie", "pudding", "ice cream", "pie",
                "monkey bread", "pickle", "kimchi", "dill", "chow mein noodles",
                "sliced ", "shredded ", "chopped ", "julienne", "cherry tomatoes",
                "romaine", "spinach", "lettuce"]


def _calories_of(item):
    """Calories of a DineOnCampus menu item (a plain field, or a 'Calories' nutrient row)."""
    value = item.get("calories")
    if value is None:
        for nutrient in item.get("nutrients") or []:
            if str(nutrient.get("name", "")).strip().lower() == "calories":
                value = nutrient.get("valueNumeric") or nutrient.get("value")
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _is_plate_food(name, calories):
    """Keep real foods; drop 0-calorie items, condiments and desserts."""
    lowered = name.lower()
    if calories is None or calories < 20:
        return False
    return not any(word in lowered for word in _NOT_A_PLATE)


def parse_menu_response(data, meal_period):
    """Turn a DineOnCampus menu response into SmartPlate food dictionaries.

    Response shape (verified on the live site, Oct 2026):
        data["period"]["categories"][i]["items"][j] -> {id, name, portion, calories, ...}
    """
    categories = (data.get("period") or {}).get("categories") or []
    menu, seen = [], set()
    for station in categories:
        for item in station.get("items") or []:
            name = str(item.get("name", "")).strip()
            calories = _calories_of(item)
            if not name or name.lower() in seen or not _is_plate_food(name, calories):
                continue
            seen.add(name.lower())
            menu.append({
                "food_id": str(item.get("id", "")),
                "food_name": name,
                "category": categorize_food(name),
                "portion": str(item.get("portion") or "1 serving"),
                "calories": calories,
                "meal_period": meal_period,
            })
    return menu


def fetch_live_menu(date, meal_period):
    """Ask DineOnCampus for one date + one meal period. Raises an error on any problem."""
    day = date.strftime("%Y-%m-%d")
    session = requests.Session()
    session.headers.update({"User-Agent": "SmartPlate-student-prototype",
                            "Accept": "application/json"})

    # 1) Which meal periods exist on this date, and what is the id of ours?
    r = session.get(PERIODS_URL.format(loc=LOCATION_ID, date=day), timeout=TIMEOUT_SECONDS)
    r.raise_for_status()
    periods = r.json().get("periods") or []
    match = [p for p in periods if str(p.get("name", "")).lower() == meal_period.lower()]
    if not match:
        raise RuntimeError(f"no '{meal_period}' period listed for {day}")

    # 2) The menu for that period.
    r = session.get(MENU_URL.format(loc=LOCATION_ID, date=day, period=match[0]["id"]),
                    timeout=TIMEOUT_SECONDS)
    r.raise_for_status()
    data = r.json()
    if data.get("closedOnDate"):
        raise RuntimeError(f"{LOCATION_NAME} is closed on {day}")

    menu = parse_menu_response(data, meal_period)
    if not menu:
        raise RuntimeError("the live response had no foods with calories")
    return menu


# ----------------------------------------------------------------------------------
# THE ONE FUNCTION THE APP CALLS
# ----------------------------------------------------------------------------------
def get_menu(meal_period, date=None, use_live=True):
    """Return (menu, source, note).

    source is "live" or "csv". note explains a fallback in plain words, or is "".
    """
    date = date or get_fiu_time()
    note = ""

    if use_live:
        try:
            return fetch_live_menu(date, meal_period), "live", ""
        except Exception as error:                      # ANY failure -> fall back
            note = f"Live menu unavailable ({error}). Using the local menu.csv instead."

    csv_menu = [f for f in load_csv_menu() if f["meal_period"] == meal_period]
    return csv_menu, "csv", note


if __name__ == "__main__":
    now = get_fiu_time()
    period = determine_meal_period(now) or "Breakfast"
    print(f"FIU time: {now:%Y-%m-%d %I:%M %p}   meal period: {period}")
    menu, source, note = get_menu(period, now)
    print("source:", source)
    if note:
        print(note)
    for food in menu:
        print(f"  {food['food_name']:<28} {food['category']:<8} {food['portion']:<14} {food['calories']} cal")
