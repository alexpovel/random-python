from dataclasses import dataclass
import random

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


def draw_card(cards, from_position=0):
    # print(cards)
    drawn_card = cards.pop(from_position)
    # print(first_card, cards)
    cards.append(drawn_card)
    return drawn_card, cards


LOCALE = "en_US"

# test = [1, 2, 3, 4]

# print(draw_card(draw_card(test)[1])[1])

# somecard = Card("wow", money_change=100)

# print(somecard.category)

# chestcard = Chest_Card("rofl")

# print(chestcard.category)
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
                advance_to_nearest="nearest railroad"
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
        "chest": [
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

for category in card_sets[LOCALE]:
    random.shuffle(card_sets[LOCALE][category])

# for cat in card_sets["en_US"]:
    # for card in card_sets["en_US"][cat]:
        # print(card, "\n")

card_set = card_sets[LOCALE]

for _ in range(len(card_set["chance"]) * 2 + 1):
    my_card, card_set["chance"] = draw_card(card_set["chance"])

    # print(my_card)

# print(card_sets["en_US"]["chance"])

# random.shuffle(card_sets["en_US"]["chance"])

# print(card_sets["en_US"]["chance"])

def distance(x, y=0):
    return abs(x - y)
    # return min(possible_positions, key=)



position = 15

poss = [22, 10, 20]

newpos = min(poss, key=lambda x: abs(x - position))#[abs(position - x) for x in poss]

print(newpos)
