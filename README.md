= Hampton Roads Heat: A Crime Simulation Game
:toc:
:sectnums:
:icons: font
:docinfo: shared
:date: October 6, 2025

== Introduction

Hampton Roads Heat is a dynamic, configuration-driven crime simulation game built with Flask and PostgreSQL/PostGIS. Players take on the role of a Regional Response Director, tasked with managing crime in Norfolk, Virginia. The game uses a game theory framework to model the complex consequences of policy decisions, challenging players to balance `Budget`, `Public Trust` (Reputation), and `Civil Unrest` (Backlash).

The simulation is data-driven, with initial crime data seeded from real-world sources via a helper script (`fetch_crime_data.py`). The gameplay is powered by a dynamic engine that generates new crimes based on configurable hotspots and triggers a wide variety of "Community Pulse" and "Major Interactive" events based on the current state of the city. These events, from citizen complaints to political and environmental crises, are defined in external `.toml` configuration files, making the simulation highly customizable and expandable.

An interactive Leaflet.js map provides the main user interface, allowing players to visualize crime data via a heatmap or clustered icon view, filter incidents by type, and see key city entities.

== Gameplay Dynamics

The game operates on a turn-based system where the player's actions have immediate and long-term consequences. Each turn, the simulation progresses *first*, generating new crimes and events, after which the player's chosen action is applied.

=== Core Metrics

* **Budget**: The financial resources available. Depleted by player actions and events, and required to avoid bankruptcy.
* **Reputation**: Represents public trust in your leadership. Affects event outcomes and crime generation.
* **Backlash**: Represents public anger and social friction. High backlash can increase crime and trigger unrest events.

=== Player Actions

Player actions are defined in `actions.toml` and loaded dynamically. The current actions for Norfolk include:
* **Sweep Hotspot**: A costly, aggressive action to suppress crime in a hotspot, which negatively impacts Reputation and Backlash.
* **Increase Patrols**: A moderately expensive action that reduces the severity of opportunistic crimes like theft and vandalism.
* **Provide Aid**: A cooperative action that invests in social programs, boosting Reputation at a budget cost.

=== Dynamic Simulation Engine

The world evolves each turn through several systems driven by configuration files:

* **Dynamic Hotspot Discovery**: At startup, the engine analyzes the initial `incidents` data to automatically identify the densest areas for specific crime types and designates them as hotspots for the crime generator. This logic is in `routes/simulation.py`.
* **Crime Generator**: Each turn, the engine uses the discovered hotspots to generate new crimes. The probability is modified by the current `Reputation` and `Backlash` levels.
* **Community Pulse System (`pulse_events.toml`)**: Frequent, low-impact "Nextdoor-style" notifications are triggered by the game state (e.g., low budget, high backlash). These add flavor and apply minor, persistent pressure on metrics.
* **Major Interactive Events (`major_events.toml`)**: Rare, high-impact events that pause the game and require a player choice. These include:
    * **Political Events**: "Corruption Investigation," "Annual Property Assessment."
    * **Environmental Events**: "Hurricane Watch," "Nuisance Flooding."
    * **Social Events**: "Officer-Involved Shooting," "Population Influx."

=== Win/Loss Conditions

The game is won by achieving stability or lost by letting the city fall into crisis.
* **Loss Conditions**:
    * **Bankruptcy**: `Budget` drops to $0.
    * **State of Emergency**: The homicide rate (tracked via `Funeral Load`) exceeds a critical threshold.
* **Win Condition**:
    * **Golden Age**: Successfully maintain high `Reputation` (>80), low `Backlash` (<10), and a positive `Budget` for 12 consecutive turns.

== User Interface

The UI is served via `templates/dashboard.html` and features:
* An interactive map with toggleable **Heatmap** and **Icon Cluster** views.
* Filters to display all crimes or a specific **Crime Type**.
* A sidebar with dynamically generated **Action Buttons**.
* Real-time metric displays for **Budget**, **Backlash**, **Reputation**, **Funeral Load**, and a **Top 5 Incidents** counter.
* Floating "pop-up" notifications for **Community Pulse** events.
* Modal windows for **Interactive Major Events** and **Game Over** screens.

== Technical Architecture

The project is a containerized Flask application using a PostgreSQL/PostGIS backend, designed to be modular and configuration-driven.

* **Application (`app.py`, `routes/`, `actions.py`)**: A Flask application using a blueprint structure to separate routes by function. An action handler system makes player actions fully configurable.
* **Configuration (`*.toml`)**: All dynamic aspects of the simulation are controlled by external TOML files:
    * `actions.toml`: Defines player actions, their costs, and effects.
    * `entities.toml`: Defines static map entities like hospitals and funeral homes.
    * `pulse_events.toml`: Defines frequent, minor notification events.
    * `major_events.toml`: Defines rare, interactive wildcard events.
* **Database**: A PostgreSQL database with the PostGIS extension, managed by the `postgis/postgis` image. The schema is created and seeded by the `entrypoint.sh` script.
* **Data Pipeline**:
    * `fetch_crime_data.py`: A standalone script to download and process real-world CSV data from the Norfolk Open Data portal into a geocoded format.
    * `initial_incidents.sql`: A SQL dump file created by the `fetch_crime_data.py` script, used as the primary source for initial seed data.
* **Deployment**: Deployed with Podman via `podman-compose`. The environment is defined in the `Dockerfile`.

== Setup Instructions

1.  **Prerequisites**:
    * `podman` and `podman-compose` installed.
    * Python 3.12+ installed on the host for running helper scripts.
    * An `.env` file in the project root with `POSTGRES_USER` and `POSTGRES_PASSWORD` variables.

2.  **Generate Initial Seed Data**:
    Before the first run, you must generate the `initial_incidents.sql` file.
    * Set up a Python virtual environment and install dependencies:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        ```
    * Run the data fetching script. This will download the latest crime data, geocode it (this will take several minutes), and save it to the database.
        ```bash
        # Ensure the application is running so the script can connect to the DB
        podman-compose up --build
        # In a new terminal, run the script
        python3 fetch_crime_data.py 
        ```
    * Create the backup file that will be used for all future seeding:
        ```bash
        # Find your postgres container name
        podman ps
        # Run pg_dump
        podman exec <postgres_container_name> pg_dump -U postgres -d hamptonroads --table=incidents --column-inserts > initial_incidents.sql
        ```

3.  **Run the Application**:
    With the `initial_incidents.sql` file now in your project directory, you can build and run the application. This command will create a fresh database and seed it from your backup file.
    ```bash
    podman-compose down -v
    podman-compose up --build
    ```
    Access the application at `http://localhost:8000`.
