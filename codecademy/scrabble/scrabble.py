letters = [
    "A", "B", "C", "D", "E", "F", "G",
    "H", "I", "J", "K", "L", "M", "N",
    "O", "P", "Q", "R", "S", "T", "U",
    "V", "W", "X", "Y", "Z"]
points = [
    1, 3, 3, 2, 1, 4, 2, 4, 1, 8, 5, 1, 3,
    4, 1, 3, 10, 1, 1, 1, 1, 4, 4, 8, 4, 10]

letter_to_points = {key: value for key, value in zip(letters, points)}

letter_to_points[" "] = 0  # blank tile points


def score_words(word: str) -> int:
    point_total = 0
    for char in word:
        try:
            point_total += letter_to_points[char.upper()]
        except KeyError:
            point_total += 0
    return point_total
    

def update_point_totals() -> dict:
    player_to_points = {}
    for player, words in player_to_words.items():
        player_points = 0
        for word in words:
            player_points += score_words(word)
        player_to_points[player] = player_points
    return player_to_points


def play_word(player: str, word: str):
    player_to_words[player].append(word)
    update_point_totals()


player_to_words = {
    "player1": ["BLUE", "TENNIS", "EXIT"],
    "wordNerd": ["EARTH", "EYES", "MACHINE"],
    "Lexi Con": ["ERASER", "BELLY", "HUSKY"],
    "Prof Reader": ["ZAP", "COMA", "PERIOD"]
}
print(update_point_totals())

play_word("player1", "tower")
play_word("player1", "no")

print(update_point_totals())
