import os
import pandas as pd
import requests
from sqlalchemy import create_engine, text
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import argparse

# Import the mapping
from crime_mappings import map_crime_type, get_crime_weight

# Database connection
DB_USER = os.environ.get('POSTGRES_USER', 'postgres')
DB_PASS = os.environ.get('POSTGRES_PASSWORD', 'password')
DB_NAME = os.environ.get('POSTGRES_DB', 'hamptonroads')
DB_HOST = 'localhost'
DB_PORT = '5433'
CONN_STR = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(CONN_STR)

geolocator = Nominatim(user_agent="hampton_roads_crime_simulator_v8", timeout=10)
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def download_data(csv_url):
    """Downloads data from the specified URL and returns a pandas DataFrame."""
    print(f"Downloading data from {csv_url}...")
    try:
        df = pd.read_csv(csv_url)
        print(f"Successfully downloaded {len(df)} records.")
        return df
    except Exception as e:
        print(f"Error downloading or parsing CSV: {e}")
        return None

def analyze_crime_types(df):
    """Analyze crime type distribution before and after mapping."""
    print("\n=== ORIGINAL CRIME TYPES ===")
    original_counts = df['offense'].value_counts()
    print(f"Total unique types: {len(original_counts)}")
    print("\nTop 10:")
    print(original_counts.head(10))
    
    # Apply mapping
    df['game_type'] = df['offense'].apply(map_crime_type)
    
    print("\n=== MAPPED GAME TYPES ===")
    mapped_counts = df['game_type'].value_counts()
    print(mapped_counts)
    
    print(f"\nMapping coverage: {(1 - (mapped_counts.get('other', 0) / len(df))) * 100:.1f}%")
    
    return df

def process_data(df):
    """Cleans, processes, geocodes, and maps crime data."""
    if df is None or df.empty:
        return pd.DataFrame()

    required_csv_columns = ['offense', 'streetno', 'street', 'date_occu', 'hour_occu']
    if not all(col in df.columns for col in required_csv_columns):
        print("Error: The CSV file does not contain the expected columns.")
        return pd.DataFrame()

    df = df[required_csv_columns].copy()
    
    # Data cleaning
    df['streetno'] = df['streetno'].fillna('').astype(str).str.replace('.0', '', regex=False)
    df['street'] = df['street'].fillna('').astype(str)
    df['address'] = (df['streetno'] + ' ' + df['street']).str.strip()
    
    df['date_part'] = pd.to_datetime(df['date_occu']).dt.strftime('%Y-%m-%d')
    df['time_part'] = df['hour_occu'].astype(str).str.replace('.0', '', regex=False).str.zfill(4)
    df['timestamp'] = pd.to_datetime(df['date_part'] + ' ' + df['time_part'], format='%Y-%m-%d %H%M', errors='coerce')
    df.dropna(subset=['timestamp'], inplace=True)
    
    # Apply crime type mapping
    df['game_type'] = df['offense'].apply(map_crime_type)
    
    print(f"Geocoding {len(df)} addresses... (This may take a while)")
    incidents = []
    
    for index, row in df.iterrows():
        # Clean address
        import re
        clean_address = re.sub(r'\b(AVENUE|AVE|STREET|ST|TERRACE|TER|ROAD|RD|LANE|LN)\s+\1\b', 
                              r'\1', row['address'], flags=re.IGNORECASE)
        full_address = f"{clean_address}, Norfolk, VA"
        
        location = geocode(full_address)
        if location:
            game_type = row['game_type']
            weight = get_crime_weight(game_type)
            
            incidents.append({
                'lat': location.latitude,
                'lon': location.longitude,
                'type': game_type,  # Use mapped type
                'original_type': row['offense'],  # Store original for reference
                'weight': weight,  # Use intelligent weighting
                'timestamp': row['timestamp'],
                'locality': 'Norfolk'
            })
            
        if (index + 1) % 50 == 0:
            print(f"Geocoded {index + 1}/{len(df)} addresses...")
    
    result_df = pd.DataFrame(incidents)
    
    if not result_df.empty:
        print("\n=== GEOCODED CRIME DISTRIBUTION ===")
        print(result_df['type'].value_counts())
        print(f"\nTotal geocoded: {len(result_df)} incidents")
    
    return result_df

def insert_incidents(df):
    """Inserts new incidents into the database, avoiding duplicates."""
    if df.empty:
        print("No geocoded incidents to insert.")
        return
    
    with engine.connect() as conn:
        existing_incidents = pd.read_sql(
            text("SELECT lat, lon, type, timestamp FROM incidents WHERE timestamp > NOW() - INTERVAL '30 days'"), 
            conn
        )
        
        if not existing_incidents.empty:
            df['lat_round'] = df['lat'].round(4)
            df['lon_round'] = df['lon'].round(4)
            existing_incidents['lat_round'] = existing_incidents['lat'].round(4)
            existing_incidents['lon_round'] = existing_incidents['lon'].round(4)
            
            merged = df.merge(existing_incidents, 
                            on=['lat_round', 'lon_round', 'type', 'timestamp'], 
                            how='left', indicator=True)
            new_incidents = merged[merged['_merge'] == 'left_only'].drop(
                columns=['_merge', 'lat_round', 'lon_round']
            )
        else:
            new_incidents = df
        
        if not new_incidents.empty:
            print(f"\nInserting {len(new_incidents)} new unique incidents...")
            
            # Only insert columns that exist in the database
            db_columns = ['lat', 'lon', 'type', 'weight', 'timestamp', 'locality']
            insert_df = new_incidents[db_columns]
            
            insert_df.to_sql('incidents', engine, if_exists='append', index=False)
            print("Insertion complete.")
            
            print("\n=== INSERTED CRIME BREAKDOWN ===")
            print(insert_df['type'].value_counts())
        else:
            print("No new unique incidents to add.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and load crime data for Hampton Roads Heat.")
    parser.add_argument("--limit", type=int, help="Limit the number of records to process for testing.")
    parser.add_argument("--local-file", type=str, help="Load data from a local CSV file instead of downloading.")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze crime types without geocoding.")
    args = parser.parse_args()

    initial_df = None

    if args.local_file:
        print(f"Loading data from local file: {args.local_file}")
        try:
            initial_df = pd.read_csv(args.local_file)
            print(f"Successfully loaded {len(initial_df)} records from file.")
        except FileNotFoundError:
            print(f"Error: The file '{args.local_file}' was not found.")
            exit(1)
    else:
        norfolk_csv_url = "https://data.norfolk.gov/resource/r7bn-2egr.csv"
        initial_df = download_data(norfolk_csv_url)

    if initial_df is not None:
        if args.limit:
            print(f"Truncating records to the first {args.limit} rows.")
            initial_df = initial_df.head(args.limit)
        
        if args.analyze_only:
            analyze_crime_types(initial_df)
        else:
            processed_incidents_df = process_data(initial_df)
            insert_incidents(processed_incidents_df)
