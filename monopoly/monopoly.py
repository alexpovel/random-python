import logging
import random
from collections import namedtuple
from dataclasses import dataclass

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

logging.basicConfig(
    filename="monopoly.log",
    filemode="w",  # over_w_rite file each time
    level=logging.DEBUG,  # Only print this level and above
    format="[%(asctime)s] "\
    "%(levelname)s (%(lineno)d): %(message)s"  # Custom formatting
)


@dataclass
class Card:
    # Converted to init:
    text: str  # Mandatory: every card must have a text
    money_change: int = None
    position_shift: int = None
    new_position: int = None
    advance_to_nearest: str = None
    get_out_of_jail: bool = False

    # Not converted to init, class attribute:
    category = None


class Chest_Card(Card):
    category = "chest"


class Chance_Card(Card):
    category = "chance"


def roll_dice(no_of_dice=2, lower=1, upper=6):
    """Roll specified number of die with specified upper and lower bounds."""
    rolls = [random.randint(lower, upper) for _ in range(no_of_dice)]
    return {
        "sum": sum(rolls),
        "individual": rolls,
        "all_rolls_equal": len(set(rolls)) <= 1
    }


def draw_card(cards, from_position=0):
    """Take item from specified position of list
    (from top if from_position=0) and append it to end of list again.
    """
    drawn_card = cards.pop(from_position)
    cards.append(drawn_card)
    return drawn_card, cards


LOCALE = "en_US"

positions = {
    "go": 0,
    "jail": 10,
    "go to jail": 30,
    "chance": [7, 22, 36],
    "chest": [2, 17, 33],
    "stations": [5, 15, 25, 35],
    "utilities": [12, 28],
    "taxes": [4, 38],
    "free parking": 20,
    "brown": [1, 3],
    "light blue": [6, 8, 9],
    "pink": [11, 13, 14],
    "orange": [16, 18, 19],
    "red": [21, 23, 24],
    "yellow": [26, 27, 29],
    "green": [31, 32, 34],
    "dark blue": [37, 39]
}

# The board as a list of lists.
# The order here is highly important and translates into the later game logic!
boards = {
    "en_US": [
        ["Go", None, None],
        ["Mediterranean Avenue", "dark blue", 60],
        ["Community Chest", "chest", None],
        ["Baltic Avenue", "dark blue", 60],
        ["Income Tax", "tax", 200],
        ["Reading Railroad", "station", 200],
        ["Oriental Avenue", "light blue", 100],
        ["Chance", "chance", None],
        ["Vermont Avenue", "light blue", 100],
        ["Connecticut Avenue", "light blue", 120],
        ["Jail", None, None],
        ["St. Charles Place", "magenta", 140],
        ["Electric Company", "utilities", 150],
        ["States Avenue", "magenta", 140],
        ["Virginia Avenue", "magenta", 140],
        ["Pennsylvania Railroad", "station", 200],
        ["St. James Place", "orange", 180],
        ["Community Chest", "chest", None],
        ["Tennessee Avenue", "orange", 180],
        ["New York Avenue", "orange", 200],
        ["Free Parking", None, None],
        ["Kentucky Avenue", "red", 220],
        ["Chance", "chance", None],
        ["Indiana Avenua", "red", 220],
        ["Illinois Avenue", "red", 240],
        ["B. & O. Railroad", "station", 200],
        ["Atlantic Avenue", "yellow", 260],
        ["Ventnor Avenue", "yellow", 260],
        ["Water Works", "utilities", 160],
        ["Marvin Gardens", "yellow", 280],
        ["Go to Jail", None, None],
        ["Pacific Avenue", "green", 300],
        ["North Carolina Avenua", "green", 300],
        ["Community Chest", "chest", None],
        ["Pennsylvania Avenue", "green", 320],
        ["Short Line", "station", 200],
        ["Chance", "chance", None],
        ["Park Place", "navy blue", 350],
        ["Luxury Tax", "tax", 75],
        ["Boardwalk", "navy blue", 400]
    ],
    "en_GB": [
        ["Go", None, None],
        ["Vine Street", "brown", 15],
        ["Community Chest", "chest", None],
        ["Coventry Street", "brown", 57],
        ["Income Tax", "tax", 100],
        ["Marylebone Station", "station", 500],
        ["Leicester Square", "light blue", 68],
        ["Chance", "chance", None],
        ["Bow Street", "light blue", 71],
        ["Whitechapel Road", "light blue", 81],
        ["Jail", None, None],
        ["The Angel Islington", "magenta", 91],
        ["Electric Company", "utilities", 1240],
        ["Trafalgar Square", "magenta", 97],
        ["Northumberland Avenue", "magenta", 112],
        ["Fenchurch Station", "station", 700],
        ["Marlborough Street", "orange", 125],
        ["Community Chest", "chest", None],
        ["Fleet Street", "orange", 148],
        ["Old Kent Road", "orange", 208],
        ["Free Parking", None, None],
        ["Whitehall", "red", 211],
        ["Chance", "chance", None],
        ["Pentonville Road", "red", 215],
        ["Pall Mall", "red", 228],
        ["Kings Cross Station", "station", 1000],
        ["Bond Street", "yellow", 271],
        ["Strand", "yellow", 320],
        ["Water Works", "utilities", 8000],
        ["Regent Street", "yellow", 370],
        ["Go To Jail", None, None],
        ["Euston Road", "green", 404],
        ["Piccadilly", "green", 440],
        ["Community Chest", "chest", None],
        ["Oxford Street", "green", 550],
        ["Liverpool St. Station", "station", 1500],
        ["Chance", "chance", None],
        ["Park Lane", "navy blue", 562],
        ["Super Tax", "tax", 200],
        ["Mayfair", "navy blue", 1800]
    ]
}

board = pd.DataFrame(
    boards[LOCALE],
    columns=["Name", "Category", "Price"]
)


card_sets = {
    "en_US": {
        "chance": [  # https://monopoly.fandom.com/wiki/Chance
            Chance_Card(
                "Advance to 'Go'.",
                new_position=positions["go"]
            ),
            Chance_Card(
                "Advance to Illinois Ave. "\
                "If you pass Go, collect $200.",
                new_position=positions["red"][-1]
            ),
            Chance_Card(
                "Advance to St. Charles Place. "\
                "If you pass Go, collect $200.",
                new_position=positions["pink"][0]
            ),
            Chance_Card(
                "Advance token to nearest Utility. "\
                "If unowned, you may buy it from the Bank. "\
                "If owned, throw dice and pay owner a total "\
                "10 times the amount thrown.",
                advance_to_nearest="utilities"
            ),
            Chance_Card(
                "Advance token to the nearest Railroad and pay owner twice "\
                "the rental to which he/she is otherwise entitled. "\
                "If Railroad is unowned, you may buy it from the Bank.",
                advance_to_nearest="stations"
            ),
            Chance_Card(
                "Bank pays you dividend of $50.",
                money_change=50
            ),
            Chance_Card(
                "Get out of Jail Free. "\
                "This card may be kept until needed, or traded/sold.",
                get_out_of_jail=True
            ),
            Chance_Card(
                "Go Back Three Spaces.",
                position_shift=-3
            ),
            Chance_Card(
                "Go to Jail. Go directly to Jail. "\
                "Do not pass GO, do not collect $200.",
                new_position=positions["jail"]
            ),
            Chance_Card(
                "Make general repairs on all your property: "\
                "For each house pay $25, for each hotel $100."
            ),
            Chance_Card(
                "Pay poor tax of $15.",
                money_change=-15
            ),
            Chance_Card(
                "Take a trip to Reading Railroad. "\
                "If you pass Go, collect $200.",
                new_position=positions["stations"][0]
            ),
            Chance_Card(
                "Take a walk on the Boardwalk. Advance token to Boardwalk.",
                new_position=positions["dark blue"][-1]
            ),
            Chance_Card(
                "You have been elected Chairman of the Board. "\
                "Pay each player $50.",
                money_change=-50
            ),
            Chance_Card(
                "Your building loan matures. Receive $150.",
                money_change=150,
            ),
            Chance_Card(
                "You have won a crossword competition. Collect $100.",
                money_change=100
            )
        ],
        "chest": [  # https://monopoly.fandom.com/wiki/Community_Chest
            Chest_Card(
                "Advance to 'Go'.",
                new_position=positions["go"]
            ),
            Chest_Card(
                "Bank error in your favour. Collect $200.",
                money_change=200
            ),
            Chest_Card(
                "Doctor's fees. Pay $50.",
                money_change=-50
            ),
            Chest_Card(
                "From sale of stock you get $50.",
                money_change=50
            ),
            Chest_Card(
                "Get Out of Jail Free",
                get_out_of_jail=True
            ),
            Chest_Card(
                "Go to Jail",
                new_position=positions["jail"]
            ),
            Chest_Card(
                "Grand Opera Night. "\
                "Collect $50 from every player for opening night seats.",
                money_change=50
            ),
            Chest_Card(
                "Holiday fund matures. Receive $100.",
                money_change=100
            ),
            Chest_Card(
                "Income Tax Refund. Collect $20.",
                money_change=20
            ),
            Chest_Card(
                "It is your birthday. Collect $10 from every player.",
                money_change=10
            ),
            Chest_Card(
                "Life insurance matures. Collect $100.",
                money_change=100
            ),
            Chest_Card(
                "Hospital Fees. Pay $50.",
                money_change=-50
            ),
            Chest_Card(
                "School Fees. Pay $50.",
                money_change=-50
            ),
            Chest_Card(
                "Receive $20 Consultancy Fee.",
                money_change=20
            ),
            Chest_Card(
                "You are assessed for street repairs: "\
                "Pay $40 per house and $115 per hotel you own."
            ),
            Chest_Card(
                "You have won second prize in a beauty contest. Collect $10.",
                money_change=10
            ),
            Chest_Card(
                "You inherit $100.",
                money_change=100
            )
        ]
    }
}


board["Visited"] = 0  # Initialize column of visited places

position = None  # Initially, we are 'nowhere'
equal_rolls_in_a_row = 0

card_set = card_sets[LOCALE]

# Shuffle once, then cycle through without shuffling again after drawing:
for category in card_set:
    random.shuffle(card_set[category])

for _ in range(10**4):

    if position is None:
        position = 0
        logging.debug(f"Starting game from '{board['Name'][position]}'.")
        continue

    roll = roll_dice()
    logging.debug(f"Rolled total of {roll['sum']} from {roll['individual']}.")
    position += roll["sum"]

    if position >= len(board):  # Wrap around
        position -= len(board)

    if roll["all_rolls_equal"]:
        equal_rolls_in_a_row += 1
        # This can only happen within this if-block:
        if equal_rolls_in_a_row >= 3:
            logging.debug("Going to jail for three all-equal rolls in a row.")
            position = positions["jail"]
            equal_rolls_in_a_row = 0  # Reset
    else:
        equal_rolls_in_a_row = 0  # Reset back since streak now broken

    if position is positions["go to jail"]:
        logging.debug("Hit 'Go To Jail'.")
        position = positions["jail"]

    for category in card_set:
        if position in positions[category]:
            card, card_set[category] = draw_card(card_set[category])

            logging.debug(
                f"Hit a '{category.title()}' field at {position} "
                f"and drew '{card.text}'."
            )

            if card.position_shift:
                position += card.position_shift
            elif card.new_position is not None:  # new position 0 for 'go' evaluates falsey otherwise
                position = card.new_position
            elif card.advance_to_nearest:
                position = min(
                    positions[card.advance_to_nearest],
                    key=lambda x: abs(x - position)
                )
            elif card.money_change:
                logging.debug(
                    f"Changing player money by '{card.money_change}'. "
                    "(Not implemented yet)"
                )
            elif card.get_out_of_jail:
                logging.debug("Get ouf of Jail card not implemented yet.")
            else:
                logging.warning("No matching card attribute found.")

    logging.debug(f"Roll ended on position '{position}'.")
    # This does not seem to impact performance
    board.at[position, 'Visited'] += 1

logging.debug(board)

board["Visited (Fraction)"] = board["Visited"] * 10**2 / board["Visited"].sum()

ax = board.plot.bar(x="Name", y="Visited (Fraction)")

plt.show()
