import copy
import json

from constants import POSITIONS
from data_importer import get_gameweek, get_data, get_team, get_signing_costs, get_starting_transfers_available
from lineup_picker import select_best_lineup_from_squad
from printer import print_best_squad
from sqaud_navigator import navigate_through_gameweeks
from squad_generator import generate_best_squad, generate_alternative_teams_from_previous_gameweeks

team_id = 4970511

enforce_number_of_players = 6  # larger = faster
gameweeks_to_plan_for = 4  # smaller = faster
players_to_search_per_place = 10
transfers_available = get_starting_transfers_available(team_id)
consider_transfer_hits = 0
enforce_haaland = True
enforce_salah = False
enforce_gks = True
current_gameweek = get_gameweek()
current_gameweek_str = "gw_" + str(current_gameweek)
exclude_player_ids = set()


def get_enforce_player_ids():
    player_ids = []
    for pos in POSITIONS:
        for player_id in starting_squad[pos]:
            player_ids.append(player_id)

    enforced_player_ids = []

    if enforce_haaland:
        enforced_player_ids.append(355)
        player_ids.remove(355)

    if enforce_salah:
        enforced_player_ids.append(308)
        player_ids.remove(308)

    if enforce_gks:
        for gk_id in starting_squad['GK']:
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


total_predicted_points = 0
gw_best_squads = {}
target_gameweek = current_gameweek + gameweeks_to_plan_for

players_details_per_gameweek = get_data(gameweeks_to_plan_for, current_gameweek)
starting_squad, starting_squad_value = get_team(team_id, current_gameweek - 1, players_details_per_gameweek)
print(f'starting_budget: {starting_squad_value}')

enforce_players_ids = get_enforce_player_ids()
print(f'enforce_players_ids: {enforce_players_ids}')

signing_costs = get_signing_costs(team_id, starting_squad)
print(f'signing_costs: {json.dumps(signing_costs)}')

previous_gameweek_str = "gw_" + str(current_gameweek - 1)
starting_squad["possible_transfers_for_next_week"] = transfers_available
gw_best_squads[previous_gameweek_str] = [starting_squad]
print(f'starting_sqaud: {starting_squad}')
print("")

for gw in range(current_gameweek, target_gameweek):
    print("GW: " + str(gw))

    gw_str = "gw_" + str(gw)
    max_sqaud, best_lineup = generate_best_squad(gw_str, current_gameweek_str, enforce_players_ids, exclude_player_ids,
                                                 starting_squad_value, players_to_search_per_place,
                                                 players_details_per_gameweek)
    print(f'Best lineup: {best_lineup}')
    print(f'Predicted Points in best lineup: {max_sqaud["best_lineup_predicted_points"]:.2f}')
    print_best_squad(max_sqaud, gw_str, players_details_per_gameweek)

    gw_best_squads[gw_str] = []  # since max_squad isn't "reachable" don't need to consider it

    total_predicted_points += max_sqaud["best_lineup_predicted_points"]
    print("")
    print("Generating alternative best teams...")

    if current_gameweek == gw:
        consider_swaps = transfers_available
    else:
        consider_swaps = 2

    generate_alternative_teams_from_previous_gameweeks(gw_str,
                                                       current_gameweek_str,
                                                       players_details_per_gameweek,
                                                       enforce_players_ids,
                                                       exclude_player_ids,
                                                       players_to_search_per_place,
                                                       gw_best_squads,
                                                       starting_squad_value,
                                                       consider_swaps)
    print("")

print("------------------------")
print("")
print("")

print("Total Predicted Points in next " + str(gameweeks_to_plan_for) + " gameweeks: " + f'{total_predicted_points:.2f}')
print("Average Predicted Points per gameweek over next " + str(
    gameweeks_to_plan_for) + " gameweeks: " + f'{total_predicted_points / gameweeks_to_plan_for:.2f}')


def serialize_sets(obj):
    if isinstance(obj, set):
        return list(obj)

    return obj


print("gw_best_squads dimensions: ")
for gw in gw_best_squads:
    print(f"GW: {gw}, teams for GW: {len(gw_best_squads[gw])}")
print("")
print(" ~~~ Finding best route through sqauds ~~~ ")

gw_changes, remaining_budget, transfers_available, best_predicted_points, best_starting_sqaud = navigate_through_gameweeks(
    gw_best_squads,
    players_details_per_gameweek["players_information"],
    transfers_available,
    current_gameweek - 1,
    current_gameweek + gameweeks_to_plan_for - 1,
    consider_transfer_hits
)

print(f'starting_sqaud: {starting_squad}')
current_gameweek_str = "gw_" + str(current_gameweek)
print_best_squad(best_starting_sqaud, current_gameweek_str, players_details_per_gameweek)

print("")
print("gw_changes: ")
current_squad = copy.deepcopy(best_starting_sqaud)

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
                current_squad[player_details['position']].remove(player)
            else:
                current_squad[player_details['position']].append(player)
        print("")
    print("Best GW lineup: ")
    player_info = players_details_per_gameweek["players_information"]
    best_lineup, best_score = select_best_lineup_from_squad(current_squad, player_info, gw)
    print(f'best_lineup: {best_lineup}, best_score: {best_score}')
    print_best_squad(best_lineup, gw, players_details_per_gameweek)
    print("")

print(
    f'remaining_budget: {round(remaining_budget, 1)}\n'
    f'transfers_available: {transfers_available}\n'
    f'best_predicted_points: {best_predicted_points}\n'
    f'avg_predicted_points: {best_predicted_points / gameweeks_to_plan_for}\n'
)
