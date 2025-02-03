from flask import Flask, render_template, jsonify, request
import requests
from datetime import datetime, timedelta
import pytz
from collections import defaultdict
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

API_KEY5 = '5cf3f3f76908a816e01f63c75d31155f'
API_KEY4 = 'c82096ea7ad53c56496e186ab2f0d220'
API_KEY3 = '421148b2d1d0e8011cfc4ff48ed24a29'
API_KEY2 = '56055190125d6193cd689437a531a0c5'
API_KEY1 = 'fdc5fe0b12f3aede43825dbfd23563fa'
API_KEY = '8a7da33a9d9cdc48234d7cd8a591f7cd'
REGIONS = 'au'  # Australian region
MARKETS = ['h2h', 'totals']  # Include both head-to-head and totals markets
TIME_THRESHOLD = 5  # Threshold in minutes for considering the odds as up-to-date
STAKE = 100  # Fixed stake amount in dollars

# Global variables for caching odds data and next update times
cached_data = {}
next_update_times = {}

def fetch_odds(sport):
    url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds'
    params = {
        'api_key': API_KEY,
        'regions': REGIONS,
        'markets': ','.join(MARKETS),
        'oddsFormat': 'decimal'
    }
    response = requests.get(url, params=params)
    return response.json()

def calculate_implied_probability(odds):
    return 1 / odds

def convert_to_aest(utc_time_str):
    utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
    utc_zone = pytz.timezone('UTC')
    utc_time = utc_zone.localize(utc_time)

    # Convert to AEST
    aest_zone = pytz.timezone('Australia/Sydney')
    aest_time = utc_time.astimezone(aest_zone)

    # Format the time as a string
    return aest_time.strftime('%Y-%m-%d %H:%M:%S')

def calculate_profit_and_roi(odds1, odds2, stake):
    total_stake = stake
    # Calculate stakes for each outcome
    stake1 = total_stake / (1 + odds1 / odds2)
    stake2 = total_stake / (1 + odds2 / odds1)
    # Calculate profit if either outcome wins
    profit_win1 = stake1 * odds1 - total_stake
    profit_win2 = stake2 * odds2 - total_stake
    # ROI based on the worst-case profit
    roi = min(profit_win1, profit_win2) / total_stake * 100
    return profit_win1, profit_win2, roi

def find_arbitrage_opportunities(data):
    arbitrage_opportunities = []
    all_opportunities = []  # Logs all calculated games

    for match in data:
        commence_time = match['commence_time']
        commence_time_aest = convert_to_aest(commence_time)
        teams = match['home_team'] + ' vs ' + match['away_team']
        league = match.get('sport_nice', 'Unknown League')

        best_h2h_odds = defaultdict(lambda: {"odds": 0, "bookmaker": None})
        best_totals_odds = defaultdict(lambda: {"odds": 0, "bookmaker": None})

        for bookmaker in match['bookmakers']:
            last_update = convert_to_aest(bookmaker.get('last_update', 'Unknown Time'))
            for market in bookmaker['markets']:
                if market['key'] == 'h2h':  
                    for outcome in market['outcomes']:
                        team = outcome['name']
                        odds = outcome['price']
                        if odds > best_h2h_odds[team]["odds"]:
                            best_h2h_odds[team] = {"odds": odds, "bookmaker": bookmaker['title']}
                elif market['key'] == 'totals':  
                    totals_outcome = market['outcomes']
                    if len(totals_outcome) == 2:
                        line = totals_outcome[0]['point']
                        if totals_outcome[0]['price'] > best_totals_odds[f"Over {line}"]["odds"]:
                            best_totals_odds[f"Over {line}"] = {
                                "odds": totals_outcome[0]['price'],
                                "bookmaker": bookmaker['title'],
                                "line": line
                            }
                        if totals_outcome[1]['price'] > best_totals_odds[f"Under {line}"]["odds"]:
                            best_totals_odds[f"Under {line}"] = {
                                "odds": totals_outcome[1]['price'],
                                "bookmaker": bookmaker['title'],
                                "line": line
                            }

        # Check for h2h (Win/Loss) bets
        teams_list = list(best_h2h_odds.keys())
        if len(teams_list) == 2:
            team1, team2 = teams_list
            odds1, bookmaker1 = best_h2h_odds[team1]["odds"], best_h2h_odds[team1]["bookmaker"]
            odds2, bookmaker2 = best_h2h_odds[team2]["odds"], best_h2h_odds[team2]["bookmaker"]
            profit_win1, profit_win2, roi = calculate_profit_and_roi(odds1, odds2, STAKE)

            all_opportunities.append({
                'teams': teams,
                'league': league,
                'commence_time': commence_time_aest,
                'market': 'h2h (Win/Loss)',
                'outcome1': team1,
                'outcome2': team2,
                'bookmaker1': bookmaker1,
                'bookmaker2': bookmaker2,
                'odds1': odds1,
                'odds2': odds2,
                'profit_win1': profit_win1,
                'profit_win2': profit_win2,
                'roi': roi
            })

            if roi > 0:
                arbitrage_opportunities.append({
                    'teams': teams,
                    'league': league,
                    'commence_time': commence_time_aest,
                    'market': 'h2h (Win/Loss)',
                    'outcome1': team1,
                    'outcome2': team2,
                    'bookmaker1': bookmaker1,
                    'bookmaker2': bookmaker2,
                    'odds1': odds1,
                    'odds2': odds2,
                    'profit_win1': profit_win1,
                    'profit_win2': profit_win2,
                    'roi': roi,
                    'stake': STAKE
                })

        # Check for Over/Under bets
        over_lines = {k for k in best_totals_odds.keys() if k.startswith("Over")}
        under_lines = {k for k in best_totals_odds.keys() if k.startswith("Under")}

        for over_key in over_lines:
            line = best_totals_odds[over_key]["line"]
            under_key = f"Under {line}"
            if under_key in best_totals_odds:
                over_odds, bookmaker_over = best_totals_odds[over_key]["odds"], best_totals_odds[over_key]["bookmaker"]
                under_odds, bookmaker_under = best_totals_odds[under_key]["odds"], best_totals_odds[under_key]["bookmaker"]
                profit_win1, profit_win2, roi = calculate_profit_and_roi(over_odds, under_odds, STAKE)

                all_opportunities.append({
                    'teams': teams,
                    'league': league,
                    'commence_time': commence_time_aest,
                    'market': f'totals (Over/Under {line})',
                    'outcome1': f'Over {line}',
                    'outcome2': f'Under {line}',
                    'bookmaker1': bookmaker_over,
                    'bookmaker2': bookmaker_under,
                    'odds1': over_odds,
                    'odds2': under_odds,
                    'profit_win1': profit_win1,
                    'profit_win2': profit_win2,
                    'roi': roi
                })

                if roi > 0:
                    arbitrage_opportunities.append({
                        'teams': teams,
                        'league': league,
                        'commence_time': commence_time_aest,
                        'market': f'totals (Over/Under {line})',
                        'outcome1': f'Over {line}',
                        'outcome2': f'Under {line}',
                        'bookmaker1': bookmaker_over,
                        'bookmaker2': bookmaker_under,
                        'odds1': over_odds,
                        'odds2': under_odds,
                        'profit_win1': profit_win1,
                        'profit_win2': profit_win2,
                        'roi': roi,
                        'stake': STAKE
                    })

    return arbitrage_opportunities, all_opportunities

# Function to fetch odds periodically and record the next update time (12 hours later)
def fetch_odds_periodically(sport):
    global cached_data, next_update_times
    print(f"Fetching odds data for {sport}...")
    cached_data[sport] = fetch_odds(sport)
    next_update_times[sport] = datetime.now() + timedelta(hours=12)

# List of sports to monitor
sports = [
    'americanfootball_nfl',
    'aussierules_afl',
    'baseball_mlb',
    'soccer_australia_aleague',
    'soccer_uefa_champs_league',
    'soccer_spain_la_liga'
]

# Schedule the task to run every 12 hours (720 minutes) for each sport
scheduler = BackgroundScheduler()
for sport in sports:
    scheduler.add_job(fetch_odds_periodically, 'interval', minutes=720, args=[sport])
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html', sports=sports)

@app.route('/fetch-opportunities')
def fetch_opportunities():
    sport = request.args.get('sport')
    if sport in cached_data:
        arbitrage_opportunities, all_opportunities = find_arbitrage_opportunities(cached_data[sport])
        next_update = next_update_times.get(sport)
        if next_update:
            next_update_str = next_update.strftime('%Y-%m-%d %H:%M:%S')
            # Calculate seconds remaining until the next update
            time_remaining = int((next_update - datetime.now()).total_seconds())
        else:
            next_update_str = "Not scheduled"
            time_remaining = None

        return jsonify({
            'arbitrage_opportunities': arbitrage_opportunities,
            'all_opportunities': all_opportunities,
            'next_update': next_update_str,
            'time_remaining': time_remaining
        })
    else:
        return jsonify({'error': 'Data not available yet'}), 503

if __name__ == '__main__':
    # Immediately fetch odds for all sports at startup
    for sport in sports:
        fetch_odds_periodically(sport)
    app.run(debug=True)
