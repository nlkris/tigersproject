import json
from datetime import datetime

def fix_tweets_file():
    with open('data/tweets.json', 'r') as f:
        tweets = json.load(f)
    
    print(f"Found {len(tweets)} tweets")
    
    # Track issues
    issues_fixed = 0
    
    for tweet in tweets:
        # 1. Fix created_at - ensure it ends with Z
        ts = tweet.get('created_at', '')
        if ts:
            # Remove any existing Z
            ts = ts.rstrip('Z')
            # Ensure it's a valid ISO format
            try:
                # Parse to validate
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                # Reformat with Z
                tweet['created_at'] = dt.isoformat().replace('+00:00', 'Z')
                issues_fixed += 1
            except ValueError:
                # Invalid date, set to old date
                tweet['created_at'] = '1970-01-01T00:00:00Z'
                issues_fixed += 1
        else:
            # No created_at, set to old date
            tweet['created_at'] = '1970-01-01T00:00:00Z'
            issues_fixed += 1
        
        # 2. Ensure comments field exists
        if 'comments' not in tweet:
            tweet['comments'] = []
            issues_fixed += 1
        
        # 3. Ensure retweets field exists
        if 'retweets' not in tweet:
            tweet['retweets'] = []
            issues_fixed += 1
        
        # 4. Ensure likes field exists
        if 'likes' not in tweet:
            tweet['likes'] = []
            issues_fixed += 1
    
    # 5. Sort all tweets by created_at
    tweets.sort(key=lambda t: t.get('created_at', '1970-01-01T00:00:00Z'), reverse=True)
    
    # 6. Reassign IDs in order (newest = highest ID)
    for i, tweet in enumerate(tweets):
        tweet['id'] = i + 1
    
    # Save back
    with open('data/tweets.json', 'w') as f:
        json.dump(tweets, f, indent=4)
    
    print(f"Fixed {issues_fixed} issues")
    print(f"Sample of first 3 tweets after fix:")
    for i in range(min(3, len(tweets))):
        print(f"  {i+1}. ID: {tweets[i]['id']}, Date: {tweets[i]['created_at']}, Content: {tweets[i]['content'][:30]}...")

if __name__ == '__main__':
    fix_tweets_file()