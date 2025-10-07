import os
import random
import toml
from flask import Blueprint, jsonify, request
import folium
from folium.plugins import HeatMap, MarkerCluster
import geopandas as gpd
import pandas as pd
from sqlalchemy import text
from db import engine
from actions import (
    handle_sweep_action, handle_increase_patrols_action, handle_aid_action,
    handle_community_policing_action, handle_task_force_action, 
    handle_transparency_action, handle_technology_action,
    handle_youth_programs_action, handle_crisis_training_action,
    handle_business_incentives_action, handle_infrastructure_action,
    handle_accountability_action, handle_no_action
)

sim_bp = Blueprint('simulation', __name__)

# --- CONFIGURATION LOADING ---
def _create_trigger_from_conditions(conditions):
    def trigger_func(state):
        for cond in conditions:
            parts = cond.split()
            if len(parts) != 3: continue
            metric, operator, value = parts
            metric_val = state.get(metric)
            if metric_val is None: return False
            try:
                compare_val = type(metric_val)(value)
                if operator == '<' and not (metric_val < compare_val): return False
                if operator == '>' and not (metric_val > compare_val): return False
            except (ValueError, TypeError): return False
        return True
    return trigger_func

def load_config_file(config_path, section_key, sub_key):
    try:
        config = toml.load(config_path)
        data = config.get(section_key, {}).get(sub_key, [])
        print(f"Successfully loaded {len(data)} items from [{section_key}.{sub_key}] in {config_path}.")
        return data
    except Exception as e:
        print(f"Warning: Could not load from {config_path}. {e}")
        return []

def load_actions(config_path="actions.toml", locality_key="hamptonroads"):
    try:
        config = toml.load(config_path)
        actions_list = config.get(locality_key, {}).get('actions', [])
        actions_dict = {action['id']: action for action in actions_list}
        print(f"Successfully loaded {len(actions_dict)} player actions from {config_path}.")
        return actions_dict
    except Exception as e:
        print(f"Warning: Could not load player actions. {e}")
        return {}

PULSE_EVENTS = load_config_file("pulse_events.toml", "hamptonroads", "pulse_events")
for event in PULSE_EVENTS: 
    event['trigger'] = _create_trigger_from_conditions(event.get('triggers', []))
CRIME_HOTSPOTS = load_config_file("crime_hotspots.toml", "hamptonroads", "hotspots")
MAJOR_EVENTS = load_config_file("major_events.toml", "hamptonroads", "major_events")
for event in MAJOR_EVENTS: 
    if 'triggers' in event:
        event['trigger'] = _create_trigger_from_conditions(event.get('triggers', []))
PLAYER_ACTIONS = load_actions()

# --- EVENT HANDLERS ---
def handle_generic_event(event_definition, choice_id, locality):
    """Handles simple events where the choice has a direct effect in the TOML."""
    choice = next((c for c in event_definition.get('choices', []) if c['id'] == choice_id), None)
    if not choice:
        return {}, []
    
    effect = choice.get('effect', {})
    outcome_text = f"Response to '{event_definition['name']}': {choice.get('text', '')}"
    return effect, [outcome_text]

def handle_shooting_event(event_definition, choice_id, locality):
    """Handles Officer-Involved Shooting with dynamic outcomes."""
    with engine.connect() as conn:
        current_backlash = conn.execute(text(
            "SELECT backlash FROM sim_states ORDER BY id DESC LIMIT 1"
        )).scalar() or 0
        
    justification = random.randint(20, 80)
    base_penalty = min(20, current_backlash / 5)
    justification = max(0, justification - base_penalty)
    
    outcomes = [f"Preliminary justification assessment: {int(justification)}/100."]
    effect = {}

    with engine.connect() as conn:
        funeral_homes = conn.execute(text(
            "SELECT name FROM entities WHERE type = 'funeral' AND locality = :loc"
        ), {'loc': locality}).fetchall()
        chosen_funeral = random.choice([r[0] for r in funeral_homes]) if funeral_homes else None

    if chosen_funeral:
        homicide_incident = {
            'lat': 36.87 + random.uniform(-0.02, 0.02), 
            'lon': -76.28 + random.uniform(-0.02, 0.02),
            'type': 'homicide', 'weight': 10, 
            'timestamp': pd.to_datetime('now', utc=True),
            'locality': locality, 'funeral_id': chosen_funeral
        }
        pd.DataFrame([homicide_incident]).to_sql('incidents', engine, if_exists='append', index=False)
        outcomes.append(f"Funeral arrangements made at {chosen_funeral}.")
    
    if choice_id == 'release_footage':
        outcomes.append("DECISION: Release bodycam footage immediately.")
        if justification > 60:
            outcomes.append("Footage largely supports officer's account. Some tensions eased.")
            effect = {'reputation': 5, 'backlash': 10}
        else:
            outcomes.append("Footage is damning. Public outrage intensifies.")
            effect = {'reputation': -25, 'backlash': 40}
    elif choice_id == 'delay_release':
        outcomes.append("DECISION: Issue vague statement, delay transparency.")
        outcomes.append("Trust eroding. Protests growing.")
        effect = {'reputation': -15, 'backlash': 20}
    elif choice_id == 'suspend_officer':
        outcomes.append("DECISION: Immediate suspension, reform promises.")
        outcomes.append("Swift action de-escalates crisis but alienates police union.")
        effect = {'reputation': -10, 'backlash': -10, 'budget': -2}
        
    return effect, outcomes

def handle_corruption_event(event_definition, choice_id, locality):
    """Federal corruption investigation with budget-dependent outcomes."""
    outcomes = []
    effect = {}
    
    with engine.connect() as conn:
        budget = conn.execute(text(
            "SELECT budget FROM sim_states ORDER BY id DESC LIMIT 1"
        )).scalar() or 100
    
    if choice_id == 'cooperate':
        if budget < 40:
            outcomes.append("DECISION: Full cooperation.")
            outcomes.append("Audit revealed severe budget mismanagement. Investigation deepens.")
            effect = {'budget': -10, 'reputation': -15, 'backlash': 10}
        else:
            outcomes.append("DECISION: Full cooperation with federal investigators.")
            outcomes.append("Clean books vindicated. Investigation concludes favorably.")
            effect = {'budget': -10, 'reputation': 10, 'backlash': -10}
    elif choice_id == 'lawyer_up':
        outcomes.append("DECISION: Mount aggressive legal defense.")
        outcomes.append("Expensive lawyers hired. You look guilty. Trial drags on.")
        effect = {'budget': -15, 'reputation': -10, 'backlash': 15}
    elif choice_id == 'obstruct':
        roll = random.randint(1, 100)
        if roll < 30:
            outcomes.append("DECISION: Stonewall the investigation.")
            outcomes.append("Obstruction succeeded. Probe stalls for lack of evidence.")
            effect = {'reputation': 5, 'backlash': -5}
        else:
            outcomes.append("DECISION: Deny everything and obstruct.")
            outcomes.append("CRITICAL FAILURE: Federal charges filed. Your administration is under indictment.")
            effect = {'reputation': -35, 'backlash': 40, 'budget': -20}
    
    return effect, outcomes

EVENT_HANDLERS = {
    "handle_generic_event": handle_generic_event,
    "handle_shooting_event": handle_shooting_event,
    "handle_corruption_event": handle_corruption_event,
}

# --- ACTION HANDLERS ---
ACTION_HANDLERS = {
    "handle_sweep_action": handle_sweep_action,
    "handle_increase_patrols_action": handle_increase_patrols_action,
    "handle_aid_action": handle_aid_action,
    "handle_community_policing_action": handle_community_policing_action,
    "handle_task_force_action": handle_task_force_action,
    "handle_transparency_action": handle_transparency_action,
    "handle_technology_action": handle_technology_action,
    "handle_youth_programs_action": handle_youth_programs_action,
    "handle_crisis_training_action": handle_crisis_training_action,
    "handle_business_incentives_action": handle_business_incentives_action,
    "handle_infrastructure_action": handle_infrastructure_action,
    "handle_accountability_action": handle_accountability_action,
    "handle_no_action": handle_no_action,
}

# --- SIMULATION ENGINE ---
def run_simulation_tick(locality, reputation, backlash, budget):
    new_incidents, pulse_outcomes, triggered_major_event = [], [], None
    metric_deltas = {'budget': 0, 'reputation': 0, 'backlash': 0}
    current_state = {'reputation': reputation, 'backlash': backlash, 'budget': budget}
    major_event_fired = False
    
    for event in MAJOR_EVENTS:
        if 'trigger' in event and event['trigger'](current_state) and random.random() < event.get('chance', 0.05):
            if 'choices' in event:
                triggered_major_event = event
            else:
                pulse_outcomes.append(event['text'])
                for key, value in event.get('effect', {}).items():
                    metric_deltas[key] += value
            major_event_fired = True
            break
    
    if not major_event_fired:
        random.shuffle(PULSE_EVENTS)
        for event in PULSE_EVENTS:
            if 'trigger' in event and event['trigger'](current_state) and random.random() < event.get('chance', 0.1):
                pulse_outcomes.append(event['text'])
                for key, value in event.get('effect', {}).items():
                    metric_deltas[key] += value
                break
    
    reputation_modifier = 1 + ((50 - reputation) / 50)
    backlash_modifier = 1 + (backlash / 100)
    
    for hotspot in CRIME_HOTSPOTS:
        if hotspot.get('locality') != locality: continue
        final_chance = hotspot.get('base_chance', 0.0)
        if 'reputation' in hotspot.get('modifiers', []): 
            final_chance *= reputation_modifier
        if 'backlash' in hotspot.get('modifiers', []): 
            final_chance *= backlash_modifier
        
        if random.random() < final_chance:
            center_lat, center_lon = hotspot['center_coords']
            radius = hotspot.get('radius', 0.01)
            lat = center_lat + random.uniform(-radius, radius)
            lon = center_lon + random.uniform(-radius, radius)
            new_incidents.append({
                'lat': lat, 'lon': lon, 
                'type': hotspot['crime_type'], 
                'weight': random.randint(3, 8), 
                'timestamp': pd.to_datetime('now', utc=True), 
                'locality': locality
            })
    
    if new_incidents:
        print(f"SIM TICK: Generating {len(new_incidents)} new incidents.")
        pd.DataFrame(new_incidents).to_sql('incidents', engine, if_exists='append', index=False)
    
    return pulse_outcomes, metric_deltas, triggered_major_event

def check_game_state(budget, reputation, backlash):
    if budget <= 0:
        return "loss_bankruptcy", "Your city budget has reached zero. The state has taken over financial control. Game Over."
    
    with engine.connect() as conn:
        homicide_count = conn.execute(text(
            "SELECT COUNT(*) FROM incidents WHERE type = 'homicide' AND timestamp > (NOW() - INTERVAL '15 days')"
        )).scalar()
        if homicide_count > 10:
            return "loss_crime", f"Crime has spiraled out of control ({homicide_count} homicides in 15 days). State of emergency declared. Game Over."
    
    with engine.connect() as conn:
        last_12_turns = pd.read_sql(text(
            "SELECT reputation, backlash, budget FROM sim_states ORDER BY id DESC LIMIT 12"
        ), conn)
        if len(last_12_turns) == 12:
            if (last_12_turns['reputation'] > 80).all() and (last_12_turns['backlash'] < 10).all() and (last_12_turns['budget'] > 0).all():
                return "win_golden_age", "You have successfully maintained a golden age of stability and prosperity for 12 turns! You have won!"
    
    return "active", ""

@sim_bp.route('/<locality>/map')
def get_map(locality):
    crime_type = request.args.get('crime_type', 'all')
    view_type = request.args.get('view_type', 'heatmap')
    
    with engine.connect() as conn:
        map_center = conn.execute(text(
            "SELECT lat, lon FROM localities WHERE name = :loc"
        ), {'loc': locality}).fetchone() or [36.85, -76.28]
        
        top_crimes_result = conn.execute(text(
            "SELECT type, COUNT(*) as crime_count FROM incidents WHERE locality = :loc GROUP BY type ORDER BY crime_count DESC LIMIT 5"
        ), {'loc': locality}).fetchall()
        top_crimes = [{'type': row[0], 'count': row[1]} for row in top_crimes_result]
    
    params = {'loc': locality}
    query_str = "SELECT lat, lon, weight, type FROM incidents WHERE locality = :loc"
    if crime_type != 'all':
        query_str += " AND type = :crime_type"
        params['crime_type'] = crime_type
    
    incidents = pd.read_sql(text(query_str), engine, params=params)
    m = folium.Map(location=map_center, zoom_start=13)
    
    if not incidents.empty:
        if view_type == 'icon':
            color_map = {
                'shooting': 'red', 'homicide': 'black', 'od': 'blue',
                'vandalism': 'orange', 'robbery': 'purple', 'assault': 'darkred',
                'petty_theft': 'yellow', 'larceny_auto': 'brown'
            }
            marker_cluster = MarkerCluster().add_to(m)
            for _, row in incidents.iterrows():
                color = color_map.get(row['type'], 'gray')
                folium.CircleMarker(
                    location=[row['lat'], row['lon']], 
                    radius=5, color=color, fill=True, 
                    fill_color=color, fill_opacity=0.7, 
                    popup=f"Type: {row['type']}"
                ).add_to(marker_cluster)
        else:
            HeatMap(incidents[['lat', 'lon', 'weight']].values.tolist()).add_to(m)
    
    entities_gdf = gpd.read_postgis('entities', engine, geom_col='geometry')
    entities_gdf.apply(lambda row: folium.Marker(
        [row.geometry.y, row.geometry.x], 
        popup=row['name']
    ).add_to(m), axis=1)
    
    funeral_query = text("""
        SELECT e.name, COUNT(i.id) as services 
        FROM entities e 
        LEFT JOIN incidents i ON e.name = i.funeral_id AND i.type='homicide' 
        WHERE e.type='funeral' 
        GROUP BY e.name
    """)
    funeral_load_df = pd.read_sql(funeral_query, engine)
    
    os.makedirs('static', exist_ok=True)
    map_path = os.path.join('static', 'map.html')
    m.save(map_path)
    
    return jsonify({
        'map_url': f'/{map_path}',
        'funeral_load': funeral_load_df.set_index('name')['services'].to_dict(),
        'top_crimes': top_crimes
    })

@sim_bp.route('/<locality>/action', methods=['POST'])
def take_action(locality):
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT budget, backlash, reputation, police_force FROM sim_states ORDER BY id DESC LIMIT 1"
        )).fetchone()
    
    budget, backlash, reputation, police_force = result or (100.0, 0.0, 50.0, 100.0)
    
    # Convert Decimal types to float for calculations
    budget = float(budget)
    backlash = float(backlash)
    reputation = float(reputation)
    police_force = float(police_force) if police_force is not None else 100.0
    
    payload = request.json
    action_id = payload.get('action')
    event_response = payload.get('event_response')
    
    pulse_outcomes, metric_deltas, triggered_major_event = run_simulation_tick(
        locality, reputation, backlash, budget
    )
    
    budget += metric_deltas['budget']
    reputation += metric_deltas['reputation']
    backlash += metric_deltas['backlash']
    
    # Natural police force regeneration: 3 points per turn, capped at 100
    police_force = min(100.0, police_force + 3.0)
    
    action_outcomes = []
    action_name = None
    
    if event_response:
        event_name = event_response.get('name')
        choice_id = event_response.get('choice_id')
        event_definition = next((e for e in MAJOR_EVENTS if e['name'] == event_name), None)
        action_name = f"Event: {event_name}"
        
        if event_definition:
            handler_name = event_definition.get('handler', 'handle_generic_event')
            handler_func = EVENT_HANDLERS.get(handler_name)
            if handler_func:
                effect, outcomes = handler_func(event_definition, choice_id, locality)
                action_outcomes.extend(outcomes)
                budget += effect.get('budget', 0)
                reputation += effect.get('reputation', 0)
                backlash += effect.get('backlash', 0)
    
    elif action_id:
        action_def = PLAYER_ACTIONS.get(action_id)
        if action_def:
            action_name = action_def.get('name', action_id)
            budget -= action_def.get('cost', 0.0)
            
            handler_name = action_def.get('handler')
            handler_func = ACTION_HANDLERS.get(handler_name)
            
            if handler_func:
                result = handler_func(locality)
                
                if isinstance(result, dict):
                    if 'message' in result:
                        action_outcomes.append(result['message'])
                    
                    # Apply police force cost
                    if 'police_force_cost' in result:
                        police_force -= result['police_force_cost']
                        police_force = max(0.0, min(100.0, police_force))
                    
                    # Apply effects from TOML
                    for key, value in action_def.get('effects', {}).items():
                        if key == 'reputation': reputation += value
                        if key == 'backlash': backlash += value
                    
                    # Override with handler results if provided
                    if 'reputation_override' in result:
                        reputation = reputation - action_def.get('effects', {}).get('reputation', 0) + result['reputation_override']
                    if 'backlash_override' in result:
                        backlash = backlash - action_def.get('effects', {}).get('backlash', 0) + result['backlash_override']
                else:
                    action_outcomes.append(action_def.get('log_text', '').format(locality=locality))
                    for key, value in action_def.get('effects', {}).items():
                        if key == 'reputation': reputation += value
                        if key == 'backlash': backlash += value
            else:
                action_outcomes.append(action_def.get('log_text', '').format(locality=locality))
                for key, value in action_def.get('effects', {}).items():
                    if key == 'reputation': reputation += value
                    if key == 'backlash': backlash += value
        else:
            action_outcomes.append(f"Unknown action: {action_id}")
    
    all_outcomes_for_db = pulse_outcomes + action_outcomes
    
    with engine.connect() as conn:
        next_turn = conn.execute(text(
            "SELECT COALESCE(MAX(turn), 0) + 1 FROM sim_states"
        )).scalar()
        
        pd.DataFrame([{
            'turn': next_turn, 
            'action': action_id or 'event', 
            'outcome': '; '.join(all_outcomes_for_db), 
            'budget': budget, 
            'backlash': backlash, 
            'reputation': reputation,
            'police_force': police_force
        }]).to_sql('sim_states', engine, if_exists='append', index=False)
        conn.commit()
    
    game_over_state, game_over_message = check_game_state(budget, reputation, backlash)
    
    event_to_send = None
    if triggered_major_event:
        event_to_send = triggered_major_event.copy()
        if 'trigger' in event_to_send:
            del event_to_send['trigger']
    
    return jsonify({
        'pulse_events': pulse_outcomes,
        'action_outcomes': action_outcomes,
        'action_name': action_name,
        'budget': budget,
        'backlash': backlash,
        'reputation': reputation,
        'police_force': police_force,
        'game_over_state': game_over_state,
        'game_over_message': game_over_message,
        'triggered_major_event': event_to_send
    })

@sim_bp.route('/<locality>/history')
def get_history(locality):
    with engine.connect() as conn:
        history = pd.read_sql(text("""
            SELECT turn, budget, reputation, backlash 
            FROM sim_states 
            ORDER BY turn DESC LIMIT 20
        """), conn)
    return jsonify(history.to_dict('records'))

@sim_bp.route('/reset', methods=['POST'])
def reset_game():
    try:
        with engine.connect() as conn:
            # Clear game state tables
            conn.execute(text("TRUNCATE TABLE sim_states RESTART IDENTITY"))
            conn.execute(text("DELETE FROM incidents WHERE 1=1"))
            
            # Try to load from initial_incidents.sql if it exists
            if os.path.exists('initial_incidents.sql'):
                print("Loading from initial_incidents.sql...")
                with open('initial_incidents.sql', 'r') as f:
                    seed_sql = f.read()
                    # Execute the SQL
                    for statement in seed_sql.split(';'):
                        if statement.strip():
                            conn.execute(text(statement))
            else:
                # Fallback to minimal seed data if initial_incidents.sql doesn't exist
                print("initial_incidents.sql not found, using fallback seed data...")
                seed_data = text("""
                    INSERT INTO incidents (lat, lon, type, weight, timestamp, locality) VALUES 
                    (36.875, -76.285, 'assault', 8, NOW(), 'Norfolk'),
                    (36.872, -76.281, 'assault', 6, NOW(), 'Norfolk'),
                    (36.88, -76.29, 'petty_theft', 3, NOW(), 'Norfolk'),
                    (36.86, -76.28, 'vandalism', 4, NOW(), 'Norfolk'),
                    (36.855, -76.29, 'traffic', 3, NOW(), 'Norfolk')
                """)
                conn.execute(seed_data)
            
            # Initialize game state
            pd.DataFrame([{
                'turn': 0, 'action': 'reset', 'outcome': 'Game reset',
                'budget': 100.0, 'backlash': 0.0, 'reputation': 50.0, 'police_force': 100.0
            }]).to_sql('sim_states', engine, if_exists='append', index=False)
            
            conn.commit()
        
        return jsonify({"message": "Game reset successfully", "status": "ok"}), 200
    except Exception as e:
        print(f"Reset error: {str(e)}")
        return jsonify({"message": f"Reset failed: {str(e)}", "status": "error"}), 500
