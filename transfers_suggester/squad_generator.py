import copy
import itertools

from constants import POSITIONS, PLACES_PER_POSITION, TOTAL_PLACES
from lineup_picker import select_best_lineup_from_squad


def generate_best_squad(
        gw_str,
        current_gameweek_str,
        enforce_player_ids,
        exclude_player_ids,
        squad_value,
        players_to_search_per_place,
        players_details_per_gameweek
):
    budget = squad_value
    team = {
        "GK": [],
        "DEF": [],
        "MID": [],
        "FWD": []
    }

    enforced_players_in_team_count, budget_remaining = apply_enforced_players(enforce_player_ids, team, budget,
                                                                              players_details_per_gameweek)

    player_pool_to_consider = get_player_pool(enforce_player_ids, exclude_player_ids, team, gw_str,
                                              players_to_search_per_place, players_details_per_gameweek)

    def get_form_team(budget, nth_best_performer, total_players_in_team):
        nonlocal max_squad
        nonlocal max_score
        nonlocal max_lineup
        nonlocal budget_remaining

        if budget < 0:
            return

        if total_players_in_team == TOTAL_PLACES:
            players_information = players_details_per_gameweek["players_information"]
            best_lineup, best_lineup_predicted_points = select_best_lineup_from_squad(team, players_information, gw_str)
            if best_lineup_predicted_points > max_score:
                max_squad = copy.deepcopy(team)
                max_score = best_lineup_predicted_points
                max_lineup = copy.deepcopy(best_lineup)
                budget_remaining = budget
                return

        if nth_best_performer == player_pool_to_consider_size:
            return

        player_id = player_pool_to_consider[nth_best_performer]
        player_details = players_details_per_gameweek["players_information"][player_id]
        position = player_details['position']

        players_in_current_position = team[position]
        if len(players_in_current_position) < PLACES_PER_POSITION[position]:
            cost = player_details['cost']

            players_in_current_position.append(player_id)
            get_form_team(
                budget - cost,
                nth_best_performer + 1,
                total_players_in_team + 1
            )
            players_in_current_position.pop()

        get_form_team(budget, nth_best_performer + 1, total_players_in_team)

    player_pool_to_consider_size = len(player_pool_to_consider)

    max_score = 0
    max_squad = {}
    max_lineup = {}

    get_form_team(budget_remaining, 0, enforced_players_in_team_count)

    max_squad["best_lineup_predicted_points"] = max_score

    if gw_str == current_gameweek_str:
        max_squad["starting_budget"] = round(budget_remaining, 1)

    return max_squad, max_lineup


def get_best_player_pp(team, gw_str, players_details_per_gameweek):
    best_player_pp = 0
    for pos in team:
        for enforced_player_id in team[pos]:
            enforced_player_pp = players_details_per_gameweek[gw_str][enforced_player_id]['predicted_points']
            if enforced_player_pp > best_player_pp:
                best_player_pp = enforced_player_pp
    return best_player_pp


def get_player_pool(enforce_player_ids, exclude_player_ids, team, gw_str, players_to_search_per_place,
                    players_details_per_gameweek):
    places_remaining = copy.deepcopy(PLACES_PER_POSITION)
    for pos in POSITIONS:
        places_remaining[pos] = (places_remaining[pos] - len(team[pos])) * players_to_search_per_place

    player_pool = []
    for player in players_details_per_gameweek[gw_str]:
        if are_places_remaining(places_remaining):
            break

        player_id = player["id"]

        if player_id in exclude_player_ids or player_id in enforce_player_ids:
            continue

        player_pos = players_details_per_gameweek["players_information"][player_id]["position"]
        if places_remaining[player_pos] > 0:
            player_pool.append(player_id)
            places_remaining[player_pos] = places_remaining[player_pos] - 1

    return player_pool


def are_places_remaining(places_remaining):
    return places_remaining["GK"] == 0 and \
        places_remaining["DEF"] == 0 and \
        places_remaining["MID"] == 0 and \
        places_remaining["FWD"] == 0


def apply_enforced_players(enforce_players_ids, team, budget, players_details_per_gameweek):
    total_players_in_team = 0

    for player_id in enforce_players_ids:
        player_details = players_details_per_gameweek["players_information"][player_id]
        team[player_details['position']].append(player_id)
        total_players_in_team += 1
        budget -= player_details['cost']

    return total_players_in_team, budget


def complete_team(max_team):
    if ('best_lineup_predicted_points' not in max_team) or (max_team['best_lineup_predicted_points'] == 0):
        return False
    for pos in POSITIONS:
        if (pos not in max_team) or (len(max_team[pos]) != PLACES_PER_POSITION[pos]):
            return False
    return True


def generate_alternative_teams_from_previous_gameweeks(
        gw_str,
        current_gameweek_str,
        players_details_per_gameweek,
        enforce_players_ids,
        exclude_player_ids,
        players_to_search_per_place,
        gw_best_squads,
        squad_value,
        consider_swaps=2
):
    # consider swapping 0, 1, or 2 players from each possible previous gameweek
    previous_gw_str = "gw_" + str(int(gw_str[3:]) - 1)
    for previous_gameweek_possible_sqaud in gw_best_squads[previous_gw_str]:
        non_enforced_or_excluded_players_in_squad = []
        players_in_squad = set()
        for pos in POSITIONS:
            for player_id in previous_gameweek_possible_sqaud[pos]:
                players_in_squad.add(player_id)
                if player_id in enforce_players_ids or player_id in exclude_player_ids:
                    continue
                non_enforced_or_excluded_players_in_squad.append(player_id)

        if "possible_transfers_for_next_week" in previous_gameweek_possible_sqaud:
            consider_swaps = previous_gameweek_possible_sqaud["possible_transfers_for_next_week"]

        for number_of_players_to_not_keep in range(0, consider_swaps + 1):
            for combination in itertools.combinations(non_enforced_or_excluded_players_in_squad,
                                                      number_of_players_to_not_keep):
                players_to_enforce = players_in_squad.copy()
                players_to_enforce.difference_update(set(combination))
                max_team, _ = generate_best_squad(gw_str, current_gameweek_str, players_to_enforce, exclude_player_ids,
                                                  squad_value, players_to_search_per_place,
                                                  players_details_per_gameweek)

                if not complete_team(max_team):
                    # print(f"Generated garbage team from enforcing players: \n"
                    #       f"max_team: {max_team}\n"
                    #       f"players_to_enforce: {players_to_enforce}\n"
                    #       f"exclude_player_ids: {exclude_player_ids}\n")
                    continue

                if "reaches_next_gameweek_squad_ids" not in previous_gameweek_possible_sqaud:
                    previous_gameweek_possible_sqaud["reaches_next_gameweek_squad_ids"] = set()

                possible_transfers_for_next_week = min(consider_swaps - number_of_players_to_not_keep + 1, 2)

                if max_team in gw_best_squads[gw_str]:
                    previous_gameweek_possible_sqaud["reaches_next_gameweek_squad_ids"].add(
                        gw_best_squads[gw_str].index(max_team)
                    )
                    if max_team["possible_transfers_for_next_week"] < possible_transfers_for_next_week:
                        max_team["possible_transfers_for_next_week"] = possible_transfers_for_next_week
                else:
                    max_team["possible_transfers_for_next_week"] = possible_transfers_for_next_week
                    gw_best_squads[gw_str].append(max_team)
                    previous_gameweek_possible_sqaud["reaches_next_gameweek_squad_ids"].add(
                        len(gw_best_squads[gw_str]) - 1
                    )
