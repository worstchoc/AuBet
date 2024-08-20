import requests
import pandas as pd
from datetime import datetime

API_KEY = '8a7da33a9d9cdc48234d7cd8a591f7cd'
SPORT = 'upcoming'  # Change this to the specific sport you are interested in
REGIONS = 'au'  # Australian region
MARKETS = 'h2h'  # Only include head-to-head (win/loss) markets
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
        teams = match['home_team'] + ' vs ' + match['away_team']
        league = match.get('sport_nice', 'Unknown League')
        
        # Initialize dictionaries to collect odds for win and loss outcomes
        win_odds_dict = {}
        loss_odds_dict = {}
        
        # Iterate over each bookmaker for the current match
        for bookmaker in match['bookmakers']:
            for market in bookmaker['markets']:
                if market['key'] == 'h2h':  # Win/Loss market
                    h2h_outcome = market['outcomes']
                    if len(h2h_outcome) == 2:  # Ensure there are exactly two outcomes
                        # Extract the odds for win and loss
                        win_odds = h2h_outcome[0]['price']
                        loss_odds = h2h_outcome[1]['price']
                        
                        if bookmaker['title'] not in win_odds_dict:
                            win_odds_dict[bookmaker['title']] = []
                        if bookmaker['title'] not in loss_odds_dict:
                            loss_odds_dict[bookmaker['title']] = []
                        
                        win_odds_dict[bookmaker['title']].append(win_odds)
                        loss_odds_dict[bookmaker['title']].append(loss_odds)
        
        # Check for arbitrage opportunities in win/loss market
        for bookmaker1, win_odds_list in win_odds_dict.items():
            for win_odds in win_odds_list:
                for bookmaker2, loss_odds_list in loss_odds_dict.items():
                    for loss_odds in loss_odds_list:
                        if bookmaker1 != bookmaker2:
                            # Calculate profit and ROI for this combination
                            profit_win1, profit_win2, roi = calculate_profit_and_roi(win_odds, loss_odds, STAKE)
                            
                            # Print the details including the profit/loss
                            print(f"Match: {teams}")
                            print(f"Bookmaker 1: {bookmaker1}, Win Odds: {win_odds}")
                            print(f"Bookmaker 2: {bookmaker2}, Loss Odds: {loss_odds}")
                            print(f"Profit if Win: {profit_win1:.2f}, Profit if Loss: {profit_win2:.2f}, ROI: {roi:.2f}%\n")
                            
                            # If an arbitrage opportunity is found
                            if check_arbitrage(win_odds, loss_odds):
                                arbitrage_opportunities.append({
                                    'teams': teams,
                                    'commence_time': commence_time,
                                    'market': 'h2h (Win/Loss)',
                                    'outcome1': 'Win',
                                    'outcome2': 'Loss',
                                    'bookmaker1': bookmaker1,
                                    'bookmaker2': bookmaker2,
                                    'odds1': win_odds,
                                    'odds2': loss_odds,
                                    'last_update1': match['commence_time'],
                                    'last_update2': match['commence_time'],
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
