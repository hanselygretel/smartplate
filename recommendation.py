"""SmartPlate recommendation engine (hunger level -> meal combinations)."""

import itertools

from live_menu import categorize_food

# Prototype meal-size targets. NOT medical or nutritional guidelines.
HUNGER_TARGETS = {"Light": 500, "Moderate": 600, "Very Hungry": 700}


def calculate_total_calories(meal):
    return sum(food["calories"] for food in meal)


def is_valid_meal(meal):
    """Basic meal rule: at least one protein, and at least one grain or side."""
    categories = {food["category"] for food in meal}
    return "Protein" in categories and ("Grain" in categories or "Side" in categories)


def get_target_calories(hunger_level):
    return HUNGER_TARGETS.get(hunger_level, 600)


def find_meal_options(menu, target_calories, tolerance=50, limit=5, max_foods=35):
    """Rank 3-5 food combinations by how close their calories are to the target.

    If nothing fits within `tolerance`, the window is widened a little at a time.
    `max_foods` keeps the search fast when a live menu has dozens of items.
    """
    foods = []
    for food in menu:
        food = dict(food)
        if not food.get("category") or food["category"] == "Other":
            food["category"] = categorize_food(food["food_name"])
        foods.append(food)
    foods = [f for f in foods if f["calories"] > 0 and f["calories"] <= target_calories]
    # keep a balanced shortlist (a live menu can have 60+ foods): spread across categories
    foods.sort(key=lambda f: f["food_name"])
    by_cat = {}
    for f in foods:
        by_cat.setdefault(f["category"], []).append(f)
    limits = {"Protein": 10, "Grain": 8, "Side": 8}
    foods = []
    for cat, group in by_cat.items():
        foods += group[:limits.get(cat, 3)]
    foods = foods[:max_foods]

    options = []
    for size in range(3, 6):
        for meal in itertools.combinations(foods, size):
            if is_valid_meal(meal):
                options.append((meal, calculate_total_calories(meal)))

    for window in (tolerance, tolerance * 2, tolerance * 3):
        close = [o for o in options if abs(o[1] - target_calories) <= window]
        if close:
            close.sort(key=lambda o: abs(o[1] - target_calories))
            return close[:limit]
    return []
