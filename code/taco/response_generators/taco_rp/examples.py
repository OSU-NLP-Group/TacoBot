import random

TASKS = [
    "Paint Cabinets",
    "Fold a Snowflake",
    "Knit a Blanket",
    "Use a French Press",
    "Decorate Living Room Walls",
    "Paint an Interior Wall",
    "Decorate Candles",
    "Set a Table",
]

RECIPES = [
    "Pumpkin Soup",
    "Prime Rib",
    "King Crab Legs",
    "Lobster Tails",
    "Chocolate Fondue",
    "Pork Ramen",
    "Korean Rice Cakes",
    "Beef Steaks",
    "Bubble Tea",
    "Matcha Ice Cream",
    "Egg Fried Rice",
]


def random_task():
    return random.choice(TASKS)


def random_recipe():
    return random.choice(RECIPES)
