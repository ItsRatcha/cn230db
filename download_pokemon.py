import requests
import sqlite3
import time

# --- Configuration ---
DATABASE_NAME = 'pokemon_data.db'
TABLE_NAME = 'pokemon'
MAX_POKEMON_ID = 1026 # Note: PokeAPI has data for 1026 Pokemon as of April 2025
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
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        time.sleep(REQUEST_DELAY)
        return response.json()
    except requests.exceptions.Timeout:
        print(f"Timeout error fetching {url}. Retrying in 5 seconds...")
        time.sleep(5)  # Wait 5 seconds before retrying
        return fetch_api_data(url)  # Retry the request
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
        is_fully_evolved = not bool(chain_node.get('evolves_to'))
        return current_stage, is_fully_evolved
    for evolution in chain_node.get('evolves_to', []):
        result = find_evolution_details(evolution, target_pokemon_name, current_stage + 1)
        if result:
            return result
    return None #

# --- Data Processing ---
def get_pokemon_data(pokemon_id):
    """Fetches and processes data for a single Pokemon."""
    print(f"Fetching data for Pokemon ID: {pokemon_id}...")

    # 1. Fetch basic Pokemon data
    pokemon_url = f"{POKEAPI_BASE_URL}pokemon/{pokemon_id}"
    pokemon_data = fetch_api_data(pokemon_url)
    if not pokemon_data:
        return None

    name = pokemon_data['name']

    # 2. Fetch species data
    species_url = pokemon_data.get('species', {}).get('url')
    if not species_url:
        print(f"Warning: Could not find species URL for {name} (ID: {pokemon_id}). Some fields will be missing.")
        species_data = None
    else:
        species_data = fetch_api_data(species_url)

    # Initialize variables that depend on species_data
    evolution_chain_data = None
    generation_num = None
    dex_entry = "No dex entry data available." # Default if species fails

    if not species_data:
        print(f"Warning: Could not fetch species data for {name}. Some fields will be missing.")
    else:
        # 3. Fetch evolution chain data
        evolution_chain_url = species_data.get('evolution_chain', {}).get('url')
        if evolution_chain_url:
            evolution_chain_data = fetch_api_data(evolution_chain_url)
            if not evolution_chain_data:
                print(f"Warning: Failed to fetch evolution chain from {evolution_chain_url} for {name}")
        else:
            print(f"Warning: No evolution chain URL found for {name}.")

        # 4. Extract generation number
        gen_info = species_data.get('generation')
        if gen_info and 'name' in gen_info:
            gen_name = gen_info['name']
            try:
                roman_numeral = gen_name.split('-')[1].lower()
                generation_num = ROMAN_TO_INT.get(roman_numeral)
                if generation_num is None:
                    print(f"Warning: Could not map Roman numeral '{roman_numeral}' from '{gen_name}' to integer for {name}.")
            except (IndexError, AttributeError):
                generation_num = None # Explicitly set to None on failure
                print(f"Warning: Unexpected generation name format '{gen_name}'. Could not extract number for {name}.")
        else:
            generation_num = None # Explicitly set to None if missing
            print(f"Warning: Generation info missing or incomplete in species data for {name}")

        # 5. Extract a Dex Entry
        dex_entry = "No English dex entry found." # Reset default for successful species fetch
        flavor_texts = species_data.get('flavor_text_entries', [])
        found_en = False
        for entry in flavor_texts:
            if entry.get('language', {}).get('name') == 'en':
                dex_entry = entry['flavor_text'].replace('\n', ' ').replace('\f', ' ').strip()
                found_en = True
                break
        # Fallback to first available entry if no English one found
        if not found_en and flavor_texts:
            dex_entry = flavor_texts[0]['flavor_text'].replace('\n', ' ').replace('\f', ' ').strip()
            lang_name = flavor_texts[0].get('language', {}).get('name', 'unknown')
            print(f"Warning: No English dex entry for {name}. Using first available entry (language: {lang_name}).")

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

    # Calculate BST only if all stats are available
    all_stats = [hp, attack, defense, special_attack, special_defense, speed]
    bst = sum(all_stats) if all(s is not None for s in all_stats) else None

    # Evolution details
    stage = None
    is_fully_evolved = None
    if evolution_chain_data and 'chain' in evolution_chain_data:
        evo_details = find_evolution_details(evolution_chain_data['chain'], name)
        if evo_details:
            stage, is_fully_evolved = evo_details
        else:
            # Check if it's the base form in the chain if not found recursively
            # (Handles cases like Eevee or single-stage Pokemon)
            if evolution_chain_data['chain']['species']['name'] == name:
                stage = 1
                is_fully_evolved = not bool(evolution_chain_data['chain'].get('evolves_to'))
            else:
                print(f"Warning: Could not find {name} in its evolution chain starting with {evolution_chain_data['chain']['species']['name']}.")
    elif species_data: # If we have species data but no chain data (e.g., legendary)
        print(f"Info: No evolution chain data processed for {name}. Assuming stage 1, fully evolved depends on API structure (usually true for no chain).")
        # Typically single-stage pokemon have no 'evolves_to' at the base level if chain exists,
        # or might lack the chain URL entirely. Let's assume stage 1.
        stage = 1
        # We can't definitively know if it's fully evolved without the chain context,
        # but often Pokemon without chains *are* fully evolved. Set to True as a likely default.
        is_fully_evolved = True


    # Prepare data tuple for DB insertion (order matters)
    pokemon_tuple = (
        pokemon_id, name, generation_num, type1, type2,
        hp, attack, defense, special_attack, special_defense, speed,
        bst, stage, is_fully_evolved, dex_entry
    )
    # Basic validation before returning
    if not name or type1 is None or hp is None or bst is None: # Check critical fields
        print(f"Warning: Critical data missing for ID {pokemon_id} ({name}). Tuple: {pokemon_tuple}")
        # Decide if you want to return None or the partial data
        # return None # Option 1: Skip insertion if critical data missing
        pass # Option 2: Return partial data (current behavior)


    return pokemon_tuple


# --- Database Population Function ---
def populate_database(conn, cursor):
    """Fetches Pokemon data from API and populates the database."""
    print("\n--- Starting Database Population/Update ---")
    pokemon_added_count = 0
    pokemon_failed_count = 0
    pokemon_skipped_existing = 0  # Count how many we skip due to already existing

    for i in range(1, MAX_POKEMON_ID + 1):
        print(f"Processing Pokemon ID {i}/{MAX_POKEMON_ID}... ({MAX_POKEMON_ID - i} remaining)")

        # Optional: More granular check - skip if *this specific ID* already exists
        # cursor.execute(f"SELECT 1 FROM {TABLE_NAME} WHERE id = ?", (i,))
        # if cursor.fetchone():
        #     # print(f"Skipping fetch for ID {i}: Already exists in DB.")
        #     pokemon_skipped_existing += 1
        #     continue # Skip API call and insert if row exists

        processed_data = get_pokemon_data(i)

        if processed_data:
            try:
                # Use INSERT OR REPLACE to handle both new inserts and updates if needed
                cursor.execute(f'''
                    INSERT OR REPLACE INTO {TABLE_NAME} (
                        id, name, generation, type1, type2, hp, attack, defense,
                        special_attack, special_defense, speed, bst, stage,
                        is_fully_evolved, dex_entry
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', processed_data)
                # Check if replace happened (usually means 1 row changed)
                if cursor.rowcount > 0:
                    pokemon_added_count += 1
                # Note: INSERT OR REPLACE makes it hard to distinguish between add and update counts easily

            except sqlite3.Error as e:
                print(f"Database error inserting/replacing ID {i} ({processed_data[1] if processed_data else 'N/A'}): {e}")
                pokemon_failed_count += 1
        else:
            print(f"Failed to process data for Pokemon ID: {i}")
            pokemon_failed_count += 1

        # Commit changes periodically
        if i % 50 == 0 or i == MAX_POKEMON_ID:
            print(f"--- Processed up to ID {i}. Committing batch. ---")
            conn.commit()

    print("\n--- Population Loop Complete ---")
    conn.commit()  # Final commit
    print(f"Finished population attempt.")
    print(f"Successfully added/updated in this run: {pokemon_added_count}")  # This count reflects successful INSERT/REPLACE operations
    print(f"Failed to process/insert in this run: {pokemon_failed_count}")
    print(f"Total processed: {pokemon_added_count + pokemon_failed_count}/{MAX_POKEMON_ID}")


# --- Main Execution ---
if __name__ == "__main__":
    # 1. Setup Database Connection
    conn, cursor = setup_database()
    needs_population = True # Assume we need to populate by default

    if needs_population:
        populate_database(conn, cursor)
    else:
        print("--- Population step skipped. ---")
