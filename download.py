import requests
import sqlite3
import time

# --- Configuration ---
DATABASE_NAME = 'pokemon_data.db'
TABLE_NAME = 'pokemon'
MAX_POKEMON_ID = 151 # Start with a smaller number for testing
POKEAPI_BASE_URL = 'https://pokeapi.co/api/v2/'
REQUEST_DELAY = 0.1 # seconds
ROMAN_TO_INT = {
    'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5,
    'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10
}

# --- Database Setup ---
def setup_database():
    """Creates the SQLite database and the pokemon table if they don't exist."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            generation INTEGER,
            type1 TEXT,
            type2 TEXT, -- Allows NULL for single-type Pokemon
            hp INTEGER,
            attack INTEGER,
            defense INTEGER,
            special_attack INTEGER,
            special_defense INTEGER,
            speed INTEGER,
            bst INTEGER, -- Base Stat Total
            stage INTEGER,
            is_fully_evolved BOOLEAN,
            dex_entry TEXT
        )
    ''')
    conn.commit()
    print(f"Database '{DATABASE_NAME}' and table '{TABLE_NAME}' checked/created.")
    return conn, cursor

# --- API Fetching ---
def fetch_api_data(url):
    """Fetches JSON data from a given API URL with error handling."""
    try:
        response = requests.get(url, timeout=10) # Added timeout
        response.raise_for_status() # Raises HTTPError for bad responses (4XX, 5XX)
        # Add a small delay after each successful request
        time.sleep(REQUEST_DELAY)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
    except requests.exceptions.JSONDecodeError:
        print(f"Error decoding JSON from {url}")
        return None


# --- Evolution Chain Parsing ---
def find_evolution_details(chain_node, target_pokemon_name, current_stage=1):
    """
    Recursively searches the evolution chain for the target Pokemon
    and returns its stage and whether it's fully evolved.
    """
    if chain_node['species']['name'] == target_pokemon_name:
        is_fully_evolved = not bool(chain_node.get('evolves_to')) # True if 'evolves_to' is empty or missing
        return current_stage, is_fully_evolved

    # Check next evolution possibilities
    for evolution in chain_node.get('evolves_to', []):
        result = find_evolution_details(evolution, target_pokemon_name, current_stage + 1)
        if result:
            return result
    # Not found in this branch
    return None

# --- Data Processing ---
def get_pokemon_data(pokemon_id):
    """Fetches and processes data for a single Pokemon."""
    print(f"Fetching data for Pokemon ID: {pokemon_id}...")

    # 1. Fetch basic Pokemon data
    pokemon_url = f"{POKEAPI_BASE_URL}pokemon/{pokemon_id}"
    pokemon_data = fetch_api_data(pokemon_url)
    if not pokemon_data:
        return None # Skip if basic data fails

    # 2. Fetch species data (for dex entry, generation, evolution chain)
    species_url = pokemon_data['species']['url']
    species_data = fetch_api_data(species_url)
    if not species_data:
        # Allow proceeding without species data, but some fields will be null
        print(f"Warning: Could not fetch species data for {pokemon_data['name']}. Some fields will be missing.")
        evolution_chain_data = None
        generation_num = None
        dex_entry = None
    else:
        # 3. Fetch evolution chain data
        evolution_chain_url = species_data.get('evolution_chain', {}).get('url')
        if evolution_chain_url:
            evolution_chain_data = fetch_api_data(evolution_chain_url)
        else:
            evolution_chain_data = None
            print(f"Warning: No evolution chain URL found for {pokemon_data['name']}.")

        # 4. Extract generation number from species data
        gen_info = species_data.get('generation')
        if gen_info and 'name' in gen_info:
            gen_name = gen_info['name'] # e.g., "generation-i"
            try:
                # Split "generation-i" -> ["generation", "i"]
                roman_numeral = gen_name.split('-')[1].lower()
                generation_num = ROMAN_TO_INT.get(roman_numeral) # Use .get for safety
                if generation_num is None:
                    print(f"Warning: Could not map Roman numeral '{roman_numeral}' from '{gen_name}' to integer.")
            except (IndexError, AttributeError):
                print(f"Warning: Unexpected generation name format '{gen_name}'. Could not extract number.")
        else:
            print(f"Warning: Generation info missing or incomplete in species data for {pokemon_data['name']}")

        # Extract a Dex Entry
        dex_entry = "No English dex entry found." # Default
        flavor_texts = species_data.get('flavor_text_entries', [])
        for entry in flavor_texts:
            if entry.get('language', {}).get('name') == 'en':
                dex_entry = entry['flavor_text'].replace('\n', ' ').replace('\f', ' ')
                break
        # If no English found, try to take the first one available (if any)
        if dex_entry == "No English dex entry found." and flavor_texts:
            dex_entry = flavor_texts[0]['flavor_text'].replace('\n', ' ').replace('\f', ' ')


    # --- Parse collected data ---
    name = pokemon_data['name']

    # Types
    types_list = pokemon_data.get('types', [])
    type1 = types_list[0]['type']['name'] if len(types_list) > 0 else None
    type2 = types_list[1]['type']['name'] if len(types_list) > 1 else None

    # Stats
    stats_dict = {stat['stat']['name']: stat['base_stat'] for stat in pokemon_data.get('stats', [])}
    hp = stats_dict.get('hp')
    attack = stats_dict.get('attack')
    defense = stats_dict.get('defense')
    special_attack = stats_dict.get('special-attack')
    special_defense = stats_dict.get('special-defense')
    speed = stats_dict.get('speed')
    bst = sum(filter(None, [hp, attack, defense, special_attack, special_defense, speed])) # Sum ignoring None

    # Evolution details
    stage = None
    is_fully_evolved = None
    if evolution_chain_data and 'chain' in evolution_chain_data:
        evo_details = find_evolution_details(evolution_chain_data['chain'], name)
        if evo_details:
            stage, is_fully_evolved = evo_details
        else:
            print(f"Warning: Could not find {name} in its own evolution chain data.")
            # This might happen for base forms if the API structure is odd, or edge cases
            # Check if it's the base form in the chain
            if evolution_chain_data['chain']['species']['name'] == name:
                stage = 1
                is_fully_evolved = not bool(evolution_chain_data['chain'].get('evolves_to'))
            else:
                print(f"Error: {name} not found in chain starting with {evolution_chain_data['chain']['species']['name']}")


    # Prepare data tuple for DB insertion (order matters!)
    pokemon_tuple = (
        pokemon_id,
        name,
        generation_num,
        type1,
        type2,
        hp,
        attack,
        defense,
        special_attack,
        special_defense,
        speed,
        bst,
        stage,
        is_fully_evolved,
        dex_entry
    )

    return pokemon_tuple

# --- Main Execution ---
if __name__ == "__main__":
    conn, cursor = setup_database()
    pokemon_added_count = 0
    pokemon_failed_count = 0

    for i in range(1, MAX_POKEMON_ID + 1):
        processed_data = get_pokemon_data(i)

        if processed_data:
            try:
                # Use INSERT OR REPLACE to update existing entries if the script is run again
                cursor.execute(f'''
                    INSERT OR REPLACE INTO {TABLE_NAME} (
                        id, name, generation, type1, type2, hp, attack, defense,
                        special_attack, special_defense, speed, bst, stage,
                        is_fully_evolved, dex_entry
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', processed_data)
                pokemon_added_count += 1
            except sqlite3.Error as e:
                print(f"Database error inserting ID {i}: {e}")
                pokemon_failed_count += 1
        else:
            print(f"Failed to process data for Pokemon ID: {i}")
            pokemon_failed_count += 1

        # Commit changes periodically to save progress
        if i % 50 == 0:
            print(f"--- Committing batch up to ID {i} ---")
            conn.commit()

    # Final commit and close
    print("\n--- Processing Complete ---")
    conn.commit()
    conn.close()
    print(f"Finished fetching {MAX_POKEMON_ID} Pokemon.")
    print(f"Successfully added/updated: {pokemon_added_count}")
    print(f"Failed to process: {pokemon_failed_count}")
    print(f"Data stored in '{DATABASE_NAME}'")