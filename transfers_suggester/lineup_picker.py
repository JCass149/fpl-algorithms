from constants import POSITIONS, FORMATIONS


def select_best_lineup_from_team(team, players_information, gw_str):
    order_team_by_predicted_points(team, players_information, gw_str)

    best_score = 0
    best_lineup = {}
    for formation in FORMATIONS:
        best_gk_id = team["GK"][0]
        best_defs_ids = team["DEF"][:formation["DEF"]]
        best_mids_ids = team["MID"][:formation["MID"]]
        best_fwds_ids = team["FWD"][:formation["FWD"]]

        score = players_information[best_gk_id]['predicted_points_per_gameweek'][gw_str]
        score += sum([players_information[def_id]['predicted_points_per_gameweek'][gw_str] for def_id in best_defs_ids])
        score += sum([players_information[mid_id]['predicted_points_per_gameweek'][gw_str] for mid_id in best_mids_ids])
        score += sum([players_information[fwd_id]['predicted_points_per_gameweek'][gw_str] for fwd_id in best_fwds_ids])
        if score > best_score:
            best_score = score
            best_lineup = {
                "GK": [best_gk_id],
                "DEF": best_defs_ids,
                "MID": best_mids_ids,
                "FWD": best_fwds_ids
            }

    best_score += captain_bonus(team, players_information, gw_str)

    return best_lineup, best_score


def order_team_by_predicted_points(team, players_information, gw_str):
    for position in POSITIONS:
        predicted_points_and_player_ids = []
        for player_id in team[position]:
            predicted_points = players_information[player_id]['predicted_points_per_gameweek'][gw_str]
            predicted_points_and_player_ids.append((predicted_points, player_id))
        predicted_points_and_player_ids.sort(reverse=True)
        player_ids_ordered_by_predicted_points = [x[1] for x in predicted_points_and_player_ids]
        team[position] = player_ids_ordered_by_predicted_points


def captain_bonus(lineup, players_information, gw_str):
    largest_pp = 0
    captain_id = 0
    for pos in POSITIONS:
        best_player_for_position = lineup[pos][0]
        pp = players_information[best_player_for_position]["predicted_points_per_gameweek"][gw_str]
        if pp > largest_pp:
            largest_pp = pp
            captain_id = best_player_for_position

    return players_information[captain_id]["predicted_points_per_gameweek"][gw_str]
