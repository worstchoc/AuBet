import requests

API_KEY = '8a7da33a9d9cdc48234d7cd8a591f7cd'
SPORT = 'upcoming'  # You can specify a particular sport or keep 'upcoming' to get all upcoming events
REGIONS = 'au'  # Australian region

def fetch_matches():
    url = f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds'
    params = {
        'api_key': API_KEY,
        'regions': REGIONS,
        'markets': 'h2h,totals',  # Request multiple markets
        'oddsFormat': 'decimal'
    }
    response = requests.get(url, params=params)
    data = response.json()
    print(data)  # Print the raw data to inspect the structure
    return data

def print_matches(matches):
    # Adjust depending on the data structure
    for match in matches:
        if isinstance(match, dict):  # Ensure match is a dictionary
            teams = match.get('home_team', 'Unknown Team') + ' vs ' + match.get('away_team', 'Unknown Team')
            commence_time = match.get('commence_time', 'Unknown Time')
            league = match.get('sport_nice', 'Unknown League')
            print(f"League: {league}")
            print(f"Match: {teams}")
            print(f"Commence Time: {commence_time}")
            
            for bookmaker in match.get('bookmakers', []):
                print(f"Bookmaker: {bookmaker['title']}")
                for market in bookmaker['markets']:
                    market_type = market['key']
                    
                    if market_type == 'h2h':
                        outcomes = market['outcomes']
                        print("  Market: Head to Head (Moneyline)")
                        for outcome in outcomes:
                            print(f"    {outcome['name']}: {outcome['price']}")
                    
                    elif market_type == 'totals':
                        outcomes = market['outcomes']
                        print("  Market: Totals (Over/Under)")
                        for outcome in outcomes:
                            print(f"    {outcome['name']} ({outcome['point']}): {outcome['price']}")
                    
                    elif market_type == 'h2h_lay':
                        outcomes = market['outcomes']
                        print("  Market: Head to Head Lay")
                        for outcome in outcomes:
                            print(f"    {outcome['name']}: {outcome['price']}")
            
            print("-" * 40)
        else:
            print("Unexpected data structure:", match)

# Fetch match data
matches = fetch_matches()

# Print match details
print_matches(matches)
