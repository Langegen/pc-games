import json

games = json.load(open('data/pc_games.json', encoding='utf-8'))

for i, g in enumerate(games[:2]):
    print(f"\n================ Game {i+1} ================")
    for k, v in g.items():
        if k == 'description':
            print(f"  {k}: {repr(v[:120])}...")
        elif k == 'screenshots':
            print(f"  {k}: ({len(v)}) {v[:3]}")
        else:
            print(f"  {k}: {repr(v)}")
