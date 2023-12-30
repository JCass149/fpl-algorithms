import copy

from constants import POSITIONS


def navigate_through_gameweeks(gw_best_teams, player_details, transfers_available, starting_gw, ending_gw,
                               consider_transfer_hits):
    gw_best_teams = copy.deepcopy(gw_best_teams)
    gw_changes = {}
    best_gw_changes = {}
    best_starting_team = {}
    remaining_transfers_available = 0
    remaining_budget = 0

    best_predicted_points = 0.0

    def traverse(gw, source_team, budget, predicted_points, transfers_available):
        nonlocal best_predicted_points
        nonlocal remaining_budget
        nonlocal best_gw_changes
        nonlocal remaining_transfers_available
        nonlocal best_starting_team

        if gw == ending_gw:
            if predicted_points > best_predicted_points:
                best_predicted_points = predicted_points
                remaining_budget = budget
                best_gw_changes = copy.deepcopy(gw_changes)
                remaining_transfers_available = transfers_available
                best_starting_team = copy.deepcopy(starting_team)
                print("New best route found woo!")
                print(f'New best predicted points: {best_predicted_points}, best_gw_changes: {best_gw_changes}')
                print(f'Final team: {source_team}')
                print("Traversing out <-")
            return

        for target_team_idx in source_team["reaches_next_gameweek_team_ids"]:

            target_team = gw_best_teams["gw_" + str(gw + 1)][target_team_idx]
            cost, transfers_in, transfers_out = navigate_between_teams(
                player_details,
                source_team,
                target_team,
                target_team_idx
            )

            if len(transfers_in) > transfers_available + consider_transfer_hits:
                continue

            if cost > budget:
                continue

            if gw_changes.get("gw_" + str(gw + 1)) is None:
                gw_changes["gw_" + str(gw + 1)] = {}
            gw_changes["gw_" + str(gw + 1)]["transfers_out"] = transfers_out
            gw_changes["gw_" + str(gw + 1)]["transfers_in"] = transfers_in

            gw_predicted_points = target_team["best_lineup_predicted_points"]
            if len(transfers_in) > transfers_available:
                gw_predicted_points += 4 * (transfers_available - len(transfers_in))

            traverse(
                gw + 1,
                target_team,
                budget - cost,
                predicted_points + gw_predicted_points,
                next_week_transfers_available(transfers_available, transfers_in)
            )

    for starting_team in gw_best_teams["gw_" + str(starting_gw)]:
        starting_budget = starting_team["starting_budget"]
        print("Testing starting from team: " + str(starting_team))
        traverse(starting_gw, starting_team, starting_budget, starting_team["best_lineup_predicted_points"],
                 transfers_available)
        print(" ")
        print("-------------------")
        print(" ")

    return best_gw_changes, remaining_budget, remaining_transfers_available, best_predicted_points, best_starting_team


def next_week_transfers_available(transfers_available, transfers_in):
    if transfers_available - len(transfers_in) > 0:
        return 2
    else:
        return 1


def navigate_between_teams(player_details, source_team, target_team, target_team_idx):
    """
    negative transfers_cost -> profit
    """

    if 'cached_target_teams' in source_team:
        if target_team_idx in source_team['cached_target_teams']:
            cached_values = source_team['cached_target_teams'][target_team_idx]
            return cached_values["cost"], cached_values["transfers_in"], cached_values["transfers_out"]

    transfers_in = set()
    transfers_out = set()
    transfers_cost = 0.0

    for pos in POSITIONS:
        transfers_out.update(set(source_team[pos]) - set(target_team[pos]))
        transfers_in.update(set(target_team[pos]) - set(source_team[pos]))

    assert len(transfers_in) == len(transfers_out)

    for player in transfers_out:
        transfers_cost -= player_details[player]['cost']

    for player in transfers_in:
        transfers_cost += player_details[player]['cost']

    cost = round(transfers_cost, 1)
    cache_target_weeks(cost, source_team, target_team_idx, transfers_in, transfers_out)

    return cost, transfers_in, transfers_out


def cache_target_weeks(cost, source_team, target_team_idx, transfers_in, transfers_out):
    if 'cached_target_teams' in source_team:
        source_team['cached_target_teams'][target_team_idx] = {
            "cost": cost,
            "transfers_in": transfers_in,
            "transfers_out": transfers_out
        }
    else:
        source_team['cached_target_teams'] = {
            target_team_idx: {
                "cost": cost,
                "transfers_in": transfers_in,
                "transfers_out": transfers_out
            }
        }
