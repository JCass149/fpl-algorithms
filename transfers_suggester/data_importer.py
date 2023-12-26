from io import StringIO

import pandas as pd
import requests

from constants import POSITIONS


def get_starting_transfers_available(team_id):
    r = requests.get(f'https://fantasy.premierleague.com/api/entry/{team_id}/history/').json()

    wildcards = set()
    for chip in r['chips']:
        if chip['name'] == "wildcard":
            wildcards.add(chip['event'])
    print(f'wildcards: {wildcards}')

    transfers_available = 0
    for gw in r['current']:
        if gw['event'] in wildcards:
            transfers_available = 1
            transfers = 0
        else:
            transfers = gw['event_transfers']
            transfers_available = min(max(transfers_available - transfers + 1, 1), 2)

        print(f'gw: {gw["event"]}, transfers: {transfers}, transfers_available_next_gameweek: {transfers_available}')

    print(f'transfers_available: {transfers_available}')
    return transfers_available


def get_gameweek():
    # get data from bootstrap-static endpoint
    r = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/').json()

    for gw in r['events']:
        if gw['is_next']:
            print("Gameweek: " + str(gw['id']))
            return gw['id']

    raise Exception("Couldn't get current gameweek")


def get_team(team_id, previous_gw, players_details_per_gameweek):
    r = requests.get(f'https://fantasy.premierleague.com/api/entry/{team_id}/event/{previous_gw}/picks/').json()

    starting_squad = {
        'GK': [],
        'DEF': [],
        'MID': [],
        'FWD': [],
        'best_lineup_predicted_points': 0,
        'starting_budget': cost_to_float(r['entry_history']['bank'])
    }
    for player in r['picks']:
        player_id = player['element']
        player_pos = players_details_per_gameweek['players_information'][player_id]['position']
        starting_squad[player_pos].append(player_id)

    squad_value = cost_to_float(r['entry_history']['value'])

    print(f'starting_squad: {starting_squad}')
    return starting_squad, squad_value


def get_signing_costs(team_id, squad):
    """
    Stores the value that each player in the squad was bought for.

    .. code-block:: text
        {
            308: {
                purchased_for: 12.1,
                sell_for: 12.1,
            },
            ...
        }
    ::
    """
    r = requests.get(f'https://fantasy.premierleague.com/api/entry/{team_id}/transfers/').json()
    signing_costs = {}
    for transfer in reversed(r):
        in_squad = False
        for pos in POSITIONS:
            for player_id in squad[pos]:
                if player_id == transfer['element_in']:
                    in_squad = True
                    break
            if in_squad:
                break
        if not in_squad:
            continue
        purchased_for = cost_to_float(transfer['element_in_cost'])
        signing_costs[transfer['element_in']] = {
            'purchased_for': purchased_for
        }

    r = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/').json()
    for pos in POSITIONS:
        for player_id in squad[pos]:
            for player in r['elements']:
                if player['id'] == player_id:
                    cost_now = cost_to_float(player['now_cost'])
                    if player_id in signing_costs:
                        sell_cost = get_sell_cost(cost_now, signing_costs[player_id]['purchased_for'])
                        signing_costs[player_id]['sell_for'] = sell_cost
                    else:
                        starting_cost = cost_to_float(player['now_cost'] - player['cost_change_start'])
                        cost_details = {
                            'purchased_for': starting_cost,
                            'sell_for': get_sell_cost(cost_now, starting_cost),
                        }
                        signing_costs[player_id] = cost_details
                    break

    return signing_costs


def get_sell_cost(cost_now, purchase_cost):
    if cost_now < purchase_cost:
        return cost_now
    sell_cost = purchase_cost + round((cost_now - purchase_cost) / 2, 1)
    return round(sell_cost, 1)


def get_data(gameweeks_to_plan_for, current_gameweek):
    """
    Each gameweek stores the id and predicted points of each player ordered descending by predicted points.

    .. code-block:: text

        {
          "gw_9": [
            {
              "id": 308,
              "predicted_points": 6.471
            },
            {
              "id": 355,
              "predicted_points": 5.43294
            },
            ...
          ],
          "gw_10": [
            {
              "id": 308,
              "predicted_points": 7.01591
            },
            {
              "id": 355,
              "predicted_points": 6.26126
            },
            ...
          ],
          "players_information": {
            308: {
              "cost": 12.6,
              "name": "Salah",
              "position": "MID",
              "team": "LIV",
              "predicted_points_per_gameweek": {
                "gw_9": 7.54673,
                "gw_10": 7.51178,
                ...
              }
            },
            355: {
              "cost": 14.1,
              "name": "Haaland",
              "position": "FWD",
              "team": "MCI",
              "predicted_points_per_gameweek": {
                "gw_9": 6.0505,
                "gw_10": 5.02906,
                ...
              }
            },
            ...
          }
        }
    ::
    """

    target_gameweek = get_target_gameweek(current_gameweek, gameweeks_to_plan_for)

    df, target_gameweek = get_fpl_form_data(current_gameweek, target_gameweek)

    players_details_per_gameweek = {
        "players_information": {}
    }

    for index, performer in df.iterrows():
        players_details_per_gameweek["players_information"][performer['ID']] = {
            "cost": performer['Price'],
            "name": performer['Name'],
            "position": performer['Pos'],
            "team": performer['Team'],
            "predicted_points_per_gameweek": {}
        }

    for gw in range(current_gameweek, target_gameweek + 1):
        performers = df.sort_values(str(gw) + '_pts', ascending=False)

        gw_str = "gw_" + str(gw)
        players_details_per_gameweek[gw_str] = []

        for index, performer in performers.iterrows():
            pp = performer[str(gw) + "_pts"]
            p_id = int(performer['ID'])
            players_details_per_gameweek[gw_str].append({
                "id": p_id,
                "predicted_points": pp
            })
            players_details_per_gameweek["players_information"][p_id]["predicted_points_per_gameweek"][gw_str] = pp

    return players_details_per_gameweek


def get_target_gameweek(current_gameweek, gameweeks_to_plan_for):
    return min(int(current_gameweek) + gameweeks_to_plan_for - 1, 38)


def get_fpl_form_data(current_gameweek, target_gameweek):
    url = 'https://fplform.com/export-fpl-form-data.php'
    headers = {
        'content-type': 'application/x-www-form-urlencoded'
    }
    data = {
        'firstgw': str(current_gameweek),
        'lastgw': str(target_gameweek)
    }
    r = requests.post(url, data, headers=headers)
    print(r)

    # Convert String into StringIO
    csv_string_io = StringIO(r.text)
    df = pd.read_csv(csv_string_io)
    return df, target_gameweek


def cost_to_float(cost):
    return round(float(cost) / 10, 1)
