import requests
import sqlite3
import json
import time # Needed for the retry delay

API_BASE_URL = "https://pokeapi.co/api/v2"
DB_NAME = "pokemon_data.db"
TABLE_NAME = "moves"

# Retry configuration
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 10 # Wait 10 seconds before retrying

def setup_database():
    """Connects to DB and creates the moves table if it doesn't exist."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                accuracy INTEGER, -- Can be NULL
                pp INTEGER,
                priority INTEGER,
                power INTEGER, -- Can be NULL
                damage_class TEXT,
                type TEXT,           -- Added move type
                effect TEXT,
                effect_chance INTEGER, -- Can be NULL
                target TEXT,
                learned_by_pokemon_json TEXT -- Store list of pokemon names as JSON string
            );
        """)
        conn.commit()
        print(f"Database '{DB_NAME}' and table '{TABLE_NAME}' ready.")
    except sqlite3.Error as e:
        print(f"Database error during setup: {e}")
        if conn:
            conn.close()
        return None
    return conn

def fetch_with_retry(url, retries=MAX_RETRIES, delay=RETRY_DELAY_SECONDS):
    """Fetches data from a URL with retry logic."""
    for attempt in range(retries + 1):
        try:
            response = requests.get(url)
            response.raise_for_status() # Raise an exception for bad status codes
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}/{retries + 1} failed for {url}: {e}")
            if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"Max retries reached for {url}. Skipping or failing.")
                return None # Return None if all retries fail
        except json.JSONDecodeError as e:
             print(f"JSON decode error for {url}: {e}. Data might be corrupted.")
             if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
             else:
                print(f"Max retries reached for {url}. Skipping or failing.")
                return None


def fetch_all_moves_list():
    """Fetches the initial list of all moves from the API."""
    # Request a high limit to get all moves in one go. PokeAPI has ~900 moves.
    url = f"{API_BASE_URL}/move/?limit=10000"
    print(f"Fetching list of all moves from {url}...")

    data = fetch_with_retry(url)

    if data and data.get('results'):
        print(f"Successfully fetched {len(data['results'])} move entries.")
        return data.get('results', [])
    else:
        print("Failed to fetch move list after multiple retries.")
        return []

def process_and_store_move(move_data, conn):
    """Extracts data from move_data and inserts it into the database."""
    if not move_data:
        return False # Indicate failure

    try:
        # Extract required fields, handling potential missing keys gracefully
        move_id = move_data.get('id')
        name = move_data.get('name')
        accuracy = move_data.get('accuracy') # Can be None in API
        pp = move_data.get('pp')
        priority = move_data.get('priority')
        power = move_data.get('power') # Can be None in API (for status moves)
        damage_class = move_data.get('damage_class', {}).get('name')
        move_type = move_data.get('type', {}).get('name') # Added move type
        effect_chance = move_data.get('effect_chance') # Can be None in API

        # Extract target name
        target = move_data.get('target', {}).get('name')

        # Extract English effect text (short_effect preferred)
        effect_text = ""
        for entry in move_data.get('effect_entries', []):
            if entry.get('language', {}).get('name') == 'en':
                effect_text = entry.get('short_effect') or entry.get('effect', '')
                break # Found English, no need to continue
        # Fallback if no English entry is found or empty
        if not effect_text and move_data.get('effect_entries'):
             # Use the first available effect text if English is missing
             effect_text = move_data['effect_entries'][0].get('short_effect') or move_data['effect_entries'][0].get('effect', '')
        if not effect_text:
             effect_text = "No effect description available." # Default if no entries at all

        # Extract learned_by_pokemon names and format as JSON string
        # Use .get([], []) to safely handle potentially missing 'learned_by_pokemon' key
        pokemon_names = [p.get('pokemon', {}).get('name') for p in move_data.get('learned_by_pokemon', []) if p.get('pokemon', {}).get('name')]
        learned_by_json = json.dumps(pokemon_names)

        # Prepare data for insertion
        data_tuple = (
            move_id,
            name,
            accuracy,
            pp,
            priority,
            power,
            damage_class,
            move_type, # Added move type to tuple
            effect_text,
            effect_chance,
            target,
            learned_by_json
        )

        # Insert into database
        cursor = conn.cursor()
        # Updated INSERT statement to include the 'type' column
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME} (id, name, accuracy, pp, priority, power, damage_class, type, effect, effect_chance, target, learned_by_pokemon_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data_tuple)
        # We will commit in batches in the main loop
        return True # Indicate success

    except sqlite3.IntegrityError as e:
         # Handle cases where the move already exists (e.g., running script again)
         print(f"Skipping duplicate move {move_data.get('name', 'N/A')} (ID: {move_data.get('id', 'N/A')}): {e}")
         return False # Indicate failure (or skipping duplicate)
    except sqlite3.Error as e:
        print(f"Database insertion error for move {move_data.get('name', 'N/A')} (ID: {move_data.get('id', 'N/A')}): {e}")
        return False # Indicate failure
    except Exception as e:
         print(f"Processing error for move {move_data.get('name', 'N/A')} (ID: {move_data.get('id', 'N/A')}): {e}")
         return False # Indicate failure


def main():
    conn = setup_database()
    if not conn:
        return

    all_moves_list = fetch_all_moves_list()

    if not all_moves_list:
        print("No moves found or critical error fetching list. Exiting.")
        conn.close()
        return

    total_moves = len(all_moves_list)
    print(f"Starting to fetch details and store {total_moves} moves...")

    # Use a counter for batch commits and progress
    processed_count = 0
    successful_count = 0
    batch_size = 50 # Commit every 50 moves

    for i, move_entry in enumerate(all_moves_list):
        move_url = move_entry['url']
        move_name = move_entry['name'] # Use name from the list for easier printing

        # Progress indicator
        print(f"Processing move {i + 1}/{total_moves}: {move_name}...", end='\r')

        move_details = fetch_with_retry(move_url)

        if move_details:
            if process_and_store_move(move_details, conn):
                successful_count += 1

            processed_count += 1 # Count goes up regardless of insertion success (duplicate or DB error)

            # Commit periodically
            if processed_count % batch_size == 0:
                try:
                    conn.commit()
                    print(f"\nCommitted batch of {batch_size}. Total processed: {processed_count}/{total_moves}, Successfully stored: {successful_count}")
                except sqlite3.Error as e:
                    print(f"\nError committing batch at count {processed_count}: {e}")
                    # Decide whether to continue or stop on commit failure
                    # For this script, we'll print the error and continue

        else:
             # If fetch_with_retry returns None, it means all retries failed
             print(f"\nFailed to fetch details for move {i+1}/{total_moves}: {move_name} ({move_url}) after multiple retries. Skipping.")
             processed_count += 1 # Still count it as processed for progress

    # Commit any remaining moves
    try:
        conn.commit()
        print(f"\nFinished processing. Committed final batch. Total moves processed: {processed_count}/{total_moves}, Successfully stored: {successful_count}")
    except sqlite3.Error as e:
        print(f"\nError committing final batch: {e}")

    conn.close()
    print("Database connection closed.")

if __name__ == "__main__":
    main()