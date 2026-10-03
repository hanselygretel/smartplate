"""Create SIMULATED meal records for dashboard development.

    python3 generate_demo_data.py          -> writes meal_history_demo.csv (200 rows)

This is DEMO DATA, not FIU student data. Names and Panther IDs are fake ("Demo Student 01",
"DEMO0001"). It is written to a separate file so it never mixes with real app data.

What is assumed (made up, so do not present any of it as a finding):
  * which foods tend to be left (LEFTOVER_TENDENCY below, e.g. grits)
  * how often a plate has leftovers: set only by the foods on it
  * the SAME waste rule applies to every plate. Gaps between Recommended and Custom, or between
    hunger levels, come only from which foods happened to be on the plates plus random noise.
"""
import csv
import random
from datetime import datetime, timedelta

from live_menu import load_csv_menu
from recommendation import get_target_calories, find_meal_options

random.seed(11)
N_ROWS = 200
OUT = "meal_history_demo.csv"
COLUMNS = ["timestamp", "panther_id", "student_name", "hunger_level", "meal_type",
           "foods_selected", "total_calories", "waste_level", "leftover_food", "smartpoints"]
POINTS = {"Nothing": 20, "A little": 10, "Some": 5, "A lot": 0}
LEFTOVER_TENDENCY = {"Grits": 3.0, "Pancakes": 1.4, "Vegetable Frittata": 1.3,
                     "Fresh Fruit Salad": 0.8, "Fried Hash Brown Patty": 0.6,
                     "Shredded Cheddar Cheese": 0.3}

menu = [f for f in load_csv_menu() if f["meal_period"] == "Breakfast"]
options = {h: find_meal_options(menu, get_target_calories(h), limit=8)
           for h in ("Light", "Moderate", "Very Hungry")}

rows = []
for n in range(N_ROWS):
    student = random.randint(1, 60)
    hunger = random.choices(["Light", "Moderate", "Very Hungry"], [0.25, 0.5, 0.25])[0]
    if random.random() < 0.55 and options[hunger]:
        meal, total = random.choice(options[hunger])
        meal_type = "Recommended"
    else:
        meal = random.sample(menu, random.randint(2, 6))
        total, meal_type = sum(f["calories"] for f in meal), "Custom"

    tendency = [LEFTOVER_TENDENCY.get(f["food_name"], 1.0) for f in meal]
    p_left = min(0.25 + 0.15 * sum(tendency) / len(tendency), 0.85)
    if random.random() > p_left:
        waste, leftover = "Nothing", "None"
    else:
        waste = random.choices(["A little", "Some", "A lot"], [0.5, 0.33, 0.17])[0]
        leftover = random.choices([f["food_name"] for f in meal], tendency)[0]

    when = (datetime(2026, 9, 18) + timedelta(days=random.randint(0, 13))
            + timedelta(hours=7, minutes=random.randint(15, 210)))
    rows.append([when.strftime("%Y-%m-%d %H:%M:%S"), f"DEMO{student:04d}",
                 f"Demo Student {student:02d}", hunger, meal_type,
                 " | ".join(f["food_name"] for f in meal), total, waste, leftover,
                 POINTS[waste]])

rows.sort()
with open(OUT, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(COLUMNS)
    writer.writerows(rows)
print(f"Wrote {len(rows)} SIMULATED rows to {OUT}")
