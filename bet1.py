import requests
import pandas as pd
from datetime import datetime
import pytz

API_KEY = '8a7da33a9d9cdc48234d7cd8a591f7cd'
SPORT = 'upcoming'  # Change this to the specific sport you are interested in
REGIONS = 'au'  # Australian region
MARKETS = 'totals'  # Only include totals (over/under) markets
TIME_THRESHOLD = 5  # Threshold in minutes for considering the odds as up-to-date
STAKE = 100  # Fixed stake amount in dollars

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

def fetch_odds():
    url = f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds'
    params = {
        'api_key': API_KEY,
        'regions': REGIONS,
        'markets': MARKETS,
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

def check_arbitrage(odds1, odds2):
    implied_prob1 = calculate_implied_probability(odds1)
    implied_prob2 = calculate_implied_probability(odds2)
    return implied_prob1 + implied_prob2 < 1

def is_recent_update(last_update, commence_time):
    update_time = datetime.strptime(last_update, "%Y-%m-%dT%H:%M:%SZ")
    commence_time = datetime.strptime(commence_time, "%Y-%m-%dT%H:%M:%SZ")
    current_time = datetime.utcnow()
    
    # Ensure the update is recent and before the match starts
    is_recent = (current_time - update_time).total_seconds() / 60 <= TIME_THRESHOLD
    is_before_start = current_time < commence_time
    
    return is_recent and is_before_start

def calculate_profit_and_roi(odds1, odds2, stake):
    # Total stake amount
    total_stake = stake
    # Calculate stakes
    stake1 = total_stake / (1 + odds1 / odds2)
    stake2 = total_stake / (1 + odds2 / odds1)
    # Calculate profit
    profit_win1 = stake1 * odds1 - total_stake
    profit_win2 = stake2 * odds2 - total_stake
    # ROI
    roi = min(profit_win1, profit_win2) / total_stake * 100
    
    return profit_win1, profit_win2, roi

def find_arbitrage_opportunities(data):
    arbitrage_opportunities = []
    for match in data:
        commence_time = match['commence_time']
        commence_time_aest = convert_to_aest(commence_time)
        teams = match['home_team'] + ' vs ' + match['away_team']
        league = match.get('sport_nice', 'Unknown League')
        
        # Initialize dictionaries to collect odds for over and under outcomes
        over_odds_dict = {}
        under_odds_dict = {}
        
        # Iterate over each bookmaker for the current match
        for bookmaker in match['bookmakers']:
            last_update = bookmaker.get('last_update', 'Unknown Time')
            last_update_aest = convert_to_aest(last_update)

            for market in bookmaker['markets']:
                if market['key'] == 'totals':  # Over/under market
                    totals_outcome = market['outcomes']
                    if len(totals_outcome) == 2:  # Ensure there are exactly two outcomes
                        # Extract the line (e.g., 5.5 points) and odds
                        line = totals_outcome[0]['point']
                        over_odds = totals_outcome[0]['price']
                        under_odds = totals_outcome[1]['price']
                        
                        if bookmaker['title'] not in over_odds_dict:
                            over_odds_dict[bookmaker['title']] = []
                        if bookmaker['title'] not in under_odds_dict:
                            under_odds_dict[bookmaker['title']] = []
                        
                        over_odds_dict[bookmaker['title']].append((line, over_odds))
                        under_odds_dict[bookmaker['title']].append((line, under_odds))
        
        # Check for arbitrage opportunities in totals (over/under) market
        for bookmaker1, over_odds_list in over_odds_dict.items():
            for line1, over_odds in over_odds_list:
                for bookmaker2, under_odds_list in under_odds_dict.items():
                    for line2, under_odds in under_odds_list:
                        if bookmaker1 != bookmaker2 and line1 == line2:
                            # Calculate profit and ROI for this combination
                            profit_win1, profit_win2, roi = calculate_profit_and_roi(over_odds, under_odds, STAKE)
                            
                            # Print the details including the profit/loss
                            print(f"Match: {teams}")
                            print(f"Commence Time (AEST): {commence_time_aest}")
                            print(f"Bookmaker 1: {bookmaker1}, Over {line1} Odds: {over_odds}")
                            print(f"Bookmaker 2: {bookmaker2}, Under {line1} Odds: {under_odds}")
                            print(f"Last Update 1 (AEST): {last_update_aest}")
                            print(f"Profit if Over wins: {profit_win1:.2f}, Profit if Under wins: {profit_win2:.2f}, ROI: {roi:.2f}%\n")
                            
                            # If an arbitrage opportunity is found
                            if check_arbitrage(over_odds, under_odds):
                                arbitrage_opportunities.append({
                                    'teams': teams,
                                    'league': league,
                                    'commence_time': commence_time_aest,
                                    'market': f'totals (Over/Under {line1})',
                                    'outcome1': f'Over {line1}',
                                    'outcome2': f'Under {line1}',
                                    'bookmaker1': bookmaker1,
                                    'bookmaker2': bookmaker2,
                                    'odds1': over_odds,
                                    'odds2': under_odds,
                                    'last_update1': last_update_aest,
                                    'last_update2': last_update_aest,
                                    'profit_win1': profit_win1,
                                    'profit_win2': profit_win2,
                                    'roi': roi,
                                    'stake': STAKE
                                })
    
    return arbitrage_opportunities

def display_arbitrage_opportunities(opportunities):
    if opportunities:
        df = pd.DataFrame(opportunities)
        print(df)
    else:
        print("No arbitrage opportunities found.")

# Fetch odds data
data = fetch_odds()

# Find arbitrage opportunities
arbitrage_opportunities = find_arbitrage_opportunities(data)

# Display arbitrage opportunities
display_arbitrage_opportunities(arbitrage_opportunities)
