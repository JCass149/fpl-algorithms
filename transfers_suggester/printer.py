from constants import POSITIONS


def print_players(players, gw_str, players_details_per_gameweek):
    largest_pp = 0
    captain_id = 0
    for pos in POSITIONS:
        for player_id in players[pos]:
            pp = players_details_per_gameweek["players_information"][player_id]["predicted_points_per_gameweek"][gw_str]
            if pp > largest_pp:
                largest_pp = pp
                captain_id = player_id

    for pos in POSITIONS:
        to_print = []
        for player_id in players[pos]:
            player_details = players_details_per_gameweek["players_information"][player_id]
            team = player_details['team']
            name = player_details['name']
            cost = str(player_details['cost'])
            pp = player_details["predicted_points_per_gameweek"][gw_str]
            player_print = f'({name}, {team}, £{cost}'

            if player_id == captain_id:
                pp = pp * 2
                player_print = player_print + f', {pp:.2f}, (c))'
            else:
                player_print = player_print + f', {pp:.2f})'

            to_print.append(player_print)
        print(pos + "s: " + str(to_print))


def print_player_names(player_ids, players_details_per_gameweek):
    players = set()
    for player_id in player_ids:
        player_details = players_details_per_gameweek["players_information"][player_id]
        players.add((player_id, player_details["name"], "£" + str(player_details["cost"]), player_details["team"]))
    print(players)
