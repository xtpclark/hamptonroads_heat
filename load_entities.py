import os
import toml
import geopandas as gpd
from sqlalchemy import create_engine, text

def get_db_engine():
    """Establishes database connection using environment variables."""
    db_user = os.environ.get('POSTGRES_USER', 'postgres')
    db_pass = os.environ.get('POSTGRES_PASSWORD', 'password')
    db_name = os.environ.get('POSTGRES_DB', 'hamptonroads')
    db_host = os.environ.get('POSTGRES_HOST', 'postgres')
    conn_str = f'postgresql://{db_user}:{db_pass}@{db_host}:5432/{db_name}'
    return create_engine(conn_str)

def load_entities_from_config(engine, config_path="entities.toml", locality_key="hamptonroads"):
    """Parses the TOML config and loads entity data into the database."""
    print(f"Loading entities from '{config_path}'...")
    config = toml.load(config_path)
    
    entities_data = config.get(locality_key, {}).get('entities', [])
    if not entities_data:
        print("No entities found in config file.")
        return

    try:
        # Create a GeoDataFrame, setting geometry from the 'coords' field [lon, lat]
        gdf = gpd.GeoDataFrame(
            entities_data,
            geometry=gpd.points_from_xy([e['coords'][0] for e in entities_data], [e['coords'][1] for e in entities_data]),
            crs="EPSG:4326"
        ).drop(columns=['coords'])

        # Insert into the database
        gdf.to_postgis('entities', engine, if_exists='append', index=False)
        print(f"Successfully inserted {len(gdf)} entities into the database.")
    
    except Exception as e:
        print(f"An error occurred while inserting entities: {e}")

if __name__ == "__main__":
    db_engine = get_db_engine()
    with db_engine.connect() as conn:
        # Only seed data if the table is empty
        result = conn.execute(text("SELECT COUNT(*) FROM entities")).scalar()
        if result == 0:
            load_entities_from_config(db_engine)
        else:
            print("Entities table already populated. Skipping.")
