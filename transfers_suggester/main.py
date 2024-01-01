import copy
import json

from constants import POSITIONS
from data_importer import get_gameweek, get_data, get_team, get_signing_costs, get_starting_transfers_available
from lineup_picker import select_best_lineup_from_team
from printer import print_players, print_player_names
from team_generator import generate_best_team, generate_teams_from_previous_possible_gameweek_teams
from team_navigator import navigate_through_gameweeks

fpl_id = 4970511

enforce_number_of_players = 4
'Larger = faster. The minimum number of players to enforce keeping throughout future gameweeks'

gameweeks_to_plan_for = 4
'Smaller = faster. The number of gameweeks to produce a transfer plan for'

players_to_search_per_place = 10
'Smaller = faster. The numbers of players to consider transferring in'

transfer_predicted_points_gained_threshold = 0.2
'Larger = faster. The minimum predicted points gained required to consider making a transfer'

enforce_enabler_values = {
    "GK": 4.0,
    "DEF": 4.0,
    "MID": 4.3,
    "FWD": 4.5
}
'Any players worth less than or equal to these values will be enforced'

transfers_available = get_starting_transfers_available(fpl_id)
consider_transfer_hits = 0
enforce_haaland = False
enforce_salah = False
enforce_gks = False
live_gameweek = get_gameweek()
live_gameweek_str = "gw_" + str(live_gameweek)
exclude_player_ids = set()


def get_enforce_player_ids():
    player_ids = []
    enforced_player_ids = []

    for pos in POSITIONS:
        for player_id in starting_team[pos]:
            player_cost = players_details_per_gameweek['players_information'][player_id]['cost']
            if player_cost <= enforce_enabler_values[pos]:
                enforced_player_ids.append(player_id)
            else:
                player_ids.append(player_id)

    if enforce_haaland:
        enforced_player_ids.append(355)
        player_ids.remove(355)

    if enforce_salah:
        enforced_player_ids.append(308)
        player_ids.remove(308)

    if enforce_gks:
        for gk_id in starting_team['GK']:
            enforced_player_ids.append(gk_id)
            player_ids.remove(gk_id)

    while len(enforced_player_ids) < enforce_number_of_players:
        cheapest_player_id = None
        cheapest_player_cost = None
        cheapest_player_idx = None
        for idx, player_id in enumerate(player_ids):
            player_cost = players_details_per_gameweek['players_information'][player_id]['cost']
            if idx == 0 or player_cost < cheapest_player_cost:
                cheapest_player_id = player_id
                cheapest_player_cost = player_cost
                cheapest_player_idx = idx
        enforced_player_ids.append(cheapest_player_id)
        player_ids.pop(cheapest_player_idx)

    return enforced_player_ids


target_predicted_points = 0
total_predicted_points = 0
gw_best_teams = {}
target_gameweek = live_gameweek + gameweeks_to_plan_for

players_details_per_gameweek = get_data(gameweeks_to_plan_for, live_gameweek)
starting_team, starting_team_value = get_team(fpl_id, live_gameweek - 1, players_details_per_gameweek)
print(f'Starting budget: {starting_team_value}')

enforce_players_ids = get_enforce_player_ids()
print(f'Enforced players: ', end='')
print_player_names(enforce_players_ids, players_details_per_gameweek)

signing_costs = get_signing_costs(fpl_id, starting_team)
print(f'Signing costs: {json.dumps(signing_costs)}')

previous_gameweek_str = "gw_" + str(live_gameweek - 1)
starting_team["possible_transfers_for_next_week"] = transfers_available
gw_best_teams[previous_gameweek_str] = [starting_team]
print(f'starting_team: {starting_team}')
print("")

for gw in range(live_gameweek, target_gameweek):
    print("GW: " + str(gw))

    gw_str = "gw_" + str(gw)
    max_team, best_lineup = generate_best_team(gw_str, live_gameweek_str, enforce_players_ids, exclude_player_ids,
                                               starting_team_value, players_to_search_per_place,
                                               players_details_per_gameweek)
    print(f'Best possible lineup given restrictions: {best_lineup}')
    print(f'Predicted Points in best lineup: {max_team["best_lineup_predicted_points"]:.2f}')
    print_players(max_team, gw_str, players_details_per_gameweek)

    gw_best_teams[gw_str] = []  # since max_team isn't "reachable" don't need to consider it

    target_predicted_points += max_team["best_lineup_predicted_points"]
    print("")
    print("Generating alternative best teams...")

    if live_gameweek == gw:
        consider_swaps = transfers_available
    else:
        consider_swaps = 2

    generate_teams_from_previous_possible_gameweek_teams(gw_str,
                                                         live_gameweek_str,
                                                         players_details_per_gameweek,
                                                         enforce_players_ids,
                                                         exclude_player_ids,
                                                         players_to_search_per_place,
                                                         gw_best_teams,
                                                         starting_team_value,
                                                         transfer_predicted_points_gained_threshold,
                                                         consider_swaps)
    print("")

print("------------------------")
print("")
print("")


def serialize_sets(obj):
    if isinstance(obj, set):
        return list(obj)

    return obj


print("gw_best_teams dimensions: ")
for gw in gw_best_teams:
    print(f"GW: {gw}, teams for GW: {len(gw_best_teams[gw])}")
print("")
print(" ~~~ Finding best route through teams ~~~ ")

gw_changes, remaining_budget, transfers_available, best_predicted_points, best_starting_team = navigate_through_gameweeks(
    gw_best_teams,
    players_details_per_gameweek["players_information"],
    transfers_available,
    live_gameweek - 1,
    live_gameweek + gameweeks_to_plan_for - 1,
    consider_transfer_hits
)

print(f'starting_team: {starting_team}')
print_players(best_starting_team, live_gameweek_str, players_details_per_gameweek)

print("")
print("gw_changes: ")
current_team = copy.deepcopy(best_starting_team)

for gw in gw_changes:
    print(gw)
    for transfer_direction in gw_changes[gw]:
        print(transfer_direction)
        for player in gw_changes[gw][transfer_direction]:
            player_details = players_details_per_gameweek["players_information"][player]
            team = player_details['team']
            name = player_details['name']
            cost = player_details['cost']
            pp = player_details['predicted_points_per_gameweek'][gw]
            print(f'({name}, {team}, £{cost}, {pp:.2f})')
            if transfer_direction == "transfers_out":
                current_team[player_details['position']].remove(player)
            else:
                current_team[player_details['position']].append(player)
        print("")

    print("Best GW lineup: ")
    player_info = players_details_per_gameweek["players_information"]
    best_lineup, best_score = select_best_lineup_from_team(current_team, player_info, gw)
    print(f'best_lineup: {best_lineup}, best_score: {best_score}')
    print_players(best_lineup, gw, players_details_per_gameweek)
    print("")

print(
    f'Remaining budget: {round(remaining_budget, 1)}\n'
    f'Transfers remaining: {transfers_available}\n'
    f'Total Predicted Points in next {gameweeks_to_plan_for} gameweeks: {best_predicted_points}\n'
    f'Average Predicted Points per gameweek over next {gameweeks_to_plan_for} gameweeks: {best_predicted_points / gameweeks_to_plan_for}\n'
    f'target_avg_predicted_points: {target_predicted_points / gameweeks_to_plan_for}\n'
)
