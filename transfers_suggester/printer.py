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
            player_print = f'({name}, {team}, {format_cost(cost)}'

            if player_id == captain_id:
                pp = pp * 2
                player_print = player_print + f', {pp:.2f}, (c))'
            else:
                player_print = player_print + f', {pp:.2f})'

            to_print.append(player_print)
        print(pos + "s: " + str(to_print))


def print_player_name(player_id, players_details_per_gameweek, gw=None):
    print_player_names([player_id], players_details_per_gameweek, gw)


def print_player_names(player_ids, players_details_per_gameweek, gw=None):
    players = []
    for player_id in player_ids:
        player_details = players_details_per_gameweek["players_information"][player_id]
        team = player_details['team']
        name = player_details['name']
        cost = player_details['cost']
        to_print = f'({name}, {team}, {format_cost(cost)}'
        if gw:
            pp = player_details['predicted_points_per_gameweek'][gw]
            to_print = to_print + (f', {pp:.2f}')

        to_print = to_print + ")"

        players.append(to_print)

    if len(players) == 1:
        print(players[0])
    else:
        print(players)


def print_output(remaining_budget, transfers_available, gameweeks_to_plan_for, best_predicted_points,
                 target_predicted_points):
    print(
        f'Remaining budget: {format_cost(remaining_budget)}\n'
        f'Transfers remaining: {transfers_available}\n'
        f'Total Predicted Points in next {gameweeks_to_plan_for} gameweeks: {best_predicted_points:.2f}\n'
        f'Average Predicted Points per gameweek over next {gameweeks_to_plan_for} gameweeks: {(best_predicted_points / gameweeks_to_plan_for):.2f}\n'
        f'Target Average Predicted Points: {(target_predicted_points / gameweeks_to_plan_for):.2f}\n'
    )


def format_cost(cost):
    return "£" + str(round(float(cost) / 10, 1)) + "m"
