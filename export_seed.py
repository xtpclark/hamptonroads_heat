#!/usr/bin/env python3
"""
Export geocoded incidents from the database to initial_incidents.sql
This creates the seed file that will be used for game resets.
"""

import os
import subprocess
import sys

def export_seed_data():
    """Export incidents table to initial_incidents.sql"""
    
    # Database configuration from environment
    db_user = os.environ.get('POSTGRES_USER', 'postgres')
    db_name = os.environ.get('POSTGRES_DB', 'hamptonroads')
    db_host = os.environ.get('POSTGRES_HOST', 'localhost')
    db_port = os.environ.get('POSTGRES_PORT', '5433')
    
    output_file = 'initial_incidents.sql'
    
    print(f"Exporting incidents table from database '{db_name}'...")
    print(f"Host: {db_host}:{db_port}")
    print(f"Output: {output_file}")
    
    # Build pg_dump command
    # Using --inserts for better readability and easier debugging
    # --data-only to only export data, not schema
    cmd = [
        'pg_dump',
        '-h', db_host,
        '-p', db_port,
        '-U', db_user,
        '-d', db_name,
        '--table=incidents',
        '--data-only',
        '--inserts',
        '--column-inserts'
    ]
    
    try:
        # Run pg_dump and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write(result.stdout)
        
        print(f"\nSuccess! Exported to {output_file}")
        
        # Show stats
        with open(output_file, 'r') as f:
            content = f.read()
            insert_count = content.count('INSERT INTO')
            print(f"Total INSERT statements: {insert_count}")
            print(f"File size: {len(content)} bytes")
        
        # Verify the file is valid SQL
        if insert_count == 0:
            print("\nWARNING: No INSERT statements found. The incidents table may be empty.")
            print("Run fetch_crime_data.py first to populate the database.")
            return False
        
        print("\nThe file is ready to use for game resets.")
        print("Next time you reset the game, it will load from this file.")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\nError running pg_dump: {e}")
        print(f"stderr: {e.stderr}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. The database exists and has data")
        print("3. pg_dump is installed and in your PATH")
        return False
    
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return False

def verify_export():
    """Quick verification of the export file"""
    if not os.path.exists('initial_incidents.sql'):
        print("Error: initial_incidents.sql not found")
        return False
    
    with open('initial_incidents.sql', 'r') as f:
        content = f.read()
    
    # Check for required columns
    required_fields = ['lat', 'lon', 'type', 'weight', 'timestamp', 'locality']
    missing_fields = [field for field in required_fields if field not in content]
    
    if missing_fields:
        print(f"Warning: Missing expected fields: {missing_fields}")
    
    # Show sample
    lines = content.split('\n')
    insert_lines = [line for line in lines if line.startswith('INSERT INTO')]
    
    if insert_lines:
        print("\nSample INSERT statement:")
        print(insert_lines[0][:200] + '...')
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Hampton Roads Heat - Export Seed Data")
    print("=" * 60)
    print()
    
    # Check if we should use Docker/Podman
    if '--docker' in sys.argv or '--podman' in sys.argv:
        print("Docker/Podman mode detected.")
        print("You'll need to run pg_dump inside the container:")
        print()
        print("podman exec <postgres_container_name> pg_dump -U postgres -d hamptonroads \\")
        print("  --table=incidents --data-only --inserts --column-inserts > initial_incidents.sql")
        print()
        sys.exit(0)
    
    success = export_seed_data()
    
    if success:
        print("\n" + "=" * 60)
        verify_export()
        print("=" * 60)
    else:
        sys.exit(1)
