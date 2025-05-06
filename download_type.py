import sqlite3
import json

# List of all types and their matchups (names for now)
types_data = [
    {
        "name": "Normal",
        "no_damage_from": ["Ghost"], "weak_to": ["Fighting"], "resist_from": [],
        "no_damage_to": ["Ghost"], "double_to": [], "half_to": ["Rock", "Steel"]
    },
    {
        "name": "Fire",
        "no_damage_from": [], "weak_to": ["Water", "Ground", "Rock"], "resist_from": ["Fire", "Grass", "Ice", "Bug", "Steel", "Fairy"],
        "no_damage_to": [], "double_to": ["Grass", "Ice", "Bug", "Steel"], "half_to": ["Fire", "Water", "Rock", "Dragon"]
    },
    {
        "name": "Water",
        "no_damage_from": [], "weak_to": ["Electric", "Grass"], "resist_from": ["Fire", "Water", "Ice", "Steel"],
        "no_damage_to": [], "double_to": ["Fire", "Ground", "Rock"], "half_to": ["Water", "Grass", "Dragon"]
    },
    {
        "name": "Electric",
        "no_damage_from": [], "weak_to": ["Ground"], "resist_from": ["Electric", "Flying", "Steel"],
        "no_damage_to": ["Ground"], "double_to": ["Water", "Flying"], "half_to": ["Electric", "Grass", "Dragon"]
    },
    {
        "name": "Grass",
        "no_damage_from": [], "weak_to": ["Fire", "Ice", "Poison", "Flying", "Bug"], "resist_from": ["Water", "Electric", "Grass", "Ground"],
        "no_damage_to": [], "double_to": ["Water", "Ground", "Rock"], "half_to": ["Fire", "Grass", "Poison", "Flying", "Bug", "Dragon", "Steel"]
    },
    {
        "name": "Ice",
        "no_damage_from": [], "weak_to": ["Fire", "Fighting", "Rock", "Steel"], "resist_from": ["Ice"],
        "no_damage_to": [], "double_to": ["Grass", "Ground", "Flying", "Dragon"], "half_to": ["Fire", "Water", "Ice", "Steel"]
    },
    {
        "name": "Fighting",
        "no_damage_from": [], "weak_to": ["Flying", "Psychic", "Fairy"], "resist_from": ["Bug", "Rock", "Dark"],
        "no_damage_to": ["Ghost"], "double_to": ["Normal", "Ice", "Rock", "Dark", "Steel"], "half_to": ["Poison", "Flying", "Psychic", "Bug", "Fairy"]
    },
    {
        "name": "Poison",
        "no_damage_from": [], "weak_to": ["Ground", "Psychic"], "resist_from": ["Grass", "Fighting", "Poison", "Bug", "Fairy"],
        "no_damage_to": ["Steel"], "double_to": ["Grass", "Fairy"], "half_to": ["Poison", "Ground", "Rock", "Ghost"]
    },
    {
        "name": "Ground",
        "no_damage_from": ["Electric"], "weak_to": ["Water", "Ice", "Grass"], "resist_from": ["Poison", "Rock"],
        "no_damage_to": ["Flying"], "double_to": ["Fire", "Electric", "Poison", "Rock", "Steel"], "half_to": ["Grass", "Bug"]
    },
    {
        "name": "Flying",
        "no_damage_from": ["Ground"], "weak_to": ["Electric", "Ice", "Rock"], "resist_from": ["Grass", "Fighting", "Bug"],
        "no_damage_to": [], "double_to": ["Grass", "Fighting", "Bug"], "half_to": ["Electric", "Rock", "Steel"]
    },
    {
        "name": "Psychic",
        "no_damage_from": [], "weak_to": ["Bug", "Ghost", "Dark"], "resist_from": ["Fighting", "Psychic"],
        "no_damage_to": ["Dark"], "double_to": ["Fighting", "Poison"], "half_to": ["Psychic", "Steel"]
    },
    {
        "name": "Bug",
        "no_damage_from": [], "weak_to": ["Fire", "Flying", "Rock"], "resist_from": ["Grass", "Fighting", "Ground"],
        "no_damage_to": [], "double_to": ["Grass", "Psychic", "Dark"], "half_to": ["Fire", "Fighting", "Poison", "Flying", "Ghost", "Steel", "Fairy"]
    },
    {
        "name": "Rock",
        "no_damage_from": [], "weak_to": ["Water", "Grass", "Fighting", "Ground", "Steel"], "resist_from": ["Normal", "Fire", "Poison", "Flying"],
        "no_damage_to": [], "double_to": ["Fire", "Ice", "Flying", "Bug"], "half_to": ["Fighting", "Ground", "Steel"]
    },
    {
        "name": "Ghost",
        "no_damage_from": ["Normal", "Fighting"], "weak_to": ["Ghost", "Dark"], "resist_from": ["Poison", "Bug"],
        "no_damage_to": ["Normal"], "double_to": ["Psychic", "Ghost"], "half_to": ["Dark"]
    },
    {
        "name": "Dragon",
        "no_damage_from": [], "weak_to": ["Ice", "Dragon", "Fairy"], "resist_from": ["Fire", "Water", "Electric", "Grass"],
        "no_damage_to": ["Fairy"], "double_to": ["Dragon"], "half_to": ["Steel"]
    },
    {
        "name": "Dark",
        "no_damage_from": ["Psychic"], "weak_to": ["Fighting", "Bug", "Fairy"], "resist_from": ["Ghost", "Dark"],
        "no_damage_to": [], "double_to": ["Psychic", "Ghost"], "half_to": ["Fighting", "Dark", "Fairy"]
    },
    {
        "name": "Steel",
        "no_damage_from": ["Poison"], "weak_to": ["Fire", "Fighting", "Ground"], "resist_from": ["Normal", "Grass", "Ice", "Flying", "Psychic", "Bug", "Rock", "Dragon", "Steel", "Fairy"],
        "no_damage_to": [], "double_to": ["Ice", "Rock", "Fairy"], "half_to": ["Fire", "Water", "Electric", "Steel"]
    },
    {
        "name": "Fairy",
        "no_damage_from": ["Dragon"], "weak_to": ["Poison", "Steel"], "resist_from": ["Fighting", "Bug", "Dark"],
        "no_damage_to": [], "double_to": ["Fighting", "Dragon", "Dark"], "half_to": ["Fire", "Poison", "Steel"]
    }
]

# Assign type IDs
type_name_to_id = {t["name"]: i+1 for i, t in enumerate(types_data)}

# Convert all names in the matchup lists to IDs
for t in types_data:
    t["id"] = type_name_to_id[t["name"]]
    for key in ["no_damage_from", "weak_to", "resist_from", "no_damage_to", "double_to", "half_to"]:
        t[key] = [type_name_to_id[name] for name in t[key]]

# Connect to DB and create the table
conn = sqlite3.connect("pokemon_data.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS type (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    no_damage_from TEXT,
    weak_to TEXT,
    resist_from TEXT,
    no_damage_to TEXT,
    double_to TEXT,
    half_to TEXT
)
''')

# Insert into DB
for t in types_data:
    cursor.execute('''
    INSERT OR REPLACE INTO type (
        id, name,
        no_damage_from, weak_to, resist_from,
        no_damage_to, double_to, half_to
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        t["id"], t["name"],
        json.dumps(t["no_damage_from"]),
        json.dumps(t["weak_to"]),
        json.dumps(t["resist_from"]),
        json.dumps(t["no_damage_to"]),
        json.dumps(t["double_to"]),
        json.dumps(t["half_to"])
    ))

conn.commit()
conn.close()
