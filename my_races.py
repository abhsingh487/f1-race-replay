"""
my_races.py
-----------
Personal quick-launch file for favourite F1 races.
Run with: python my_races.py
"""

import subprocess
import sys

FAVOURITES = {
    "1": {"name": "2023 Bahrain GP",   "year": 2023, "round": 1},
    "2": {"name": "2023 Monaco GP",    "year": 2023, "round": 8},
    "3": {"name": "2024 Las Vegas GP", "year": 2024, "round": 22},
    "4": {"name": "2024 British GP",   "year": 2024, "round": 12},
    "5": {"name": "2021 Abu Dhabi GP", "year": 2021, "round": 22},
}

def main():
    print("\n🏎️  My Favourite Races\n")
    for key, race in FAVOURITES.items():
        print(f"  [{key}] {race['name']}")
    print()
    choice = input("Pick a race (1-5): ").strip()
    if choice not in FAVOURITES:
        print("Invalid choice.")
        sys.exit(1)
    race = FAVOURITES[choice]
    print(f"\nLoading {race['name']}...\n")
    subprocess.run([
        sys.executable, "main.py",
        "--viewer",
        "--year", str(race["year"]),
        "--round", str(race["round"])
    ])

if __name__ == "__main__":
    main()