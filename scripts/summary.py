import json

games = json.load(open('data/pc_games.json', encoding='utf-8'))
subforums = json.load(open('data/subforums.json', encoding='utf-8'))

print(f"Total games in data/pc_games.json: {len(games)}")
print(f"Total subforums in data/subforums.json: {len(subforums)}")
print("\nSubforums by count:")
sorted_sf = sorted(subforums, key=lambda x: x.get('games_count', 0), reverse=True)
for sf in sorted_sf:
    print(f"  f={sf['id']:4s} | {sf['name']:35s} | {sf['games_count']:4d} games | slug: {sf['slug']}")

sizes = [g['size_bytes'] for g in games if g.get('size_bytes')]
print(f"\nGames with size_bytes: {len(sizes)} / {len(games)}")
max_size = max(sizes) / (1024**3) if sizes else 0
print(f"Max size in GB: {max_size:.2f} GB (filter <= 60 GB: {max_size <= 60.0})")

# Sample games
print("\nSample 3 games from database:")
for g in games[:3]:
    print(f"  [{g.get('subforum')}] {g.get('title')} ({g.get('size')}) -> {g.get('url')}")
