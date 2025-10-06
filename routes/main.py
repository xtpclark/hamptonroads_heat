# routes/main.py
from flask import Blueprint, render_template
from sqlalchemy import text
from db import engine
# Import the loaded actions from the simulation blueprint
from routes.simulation import PLAYER_ACTIONS

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Serves the main dashboard page."""
    with engine.connect() as conn:
        localities_result = conn.execute(text("SELECT name FROM localities ORDER BY name ASC"))
        cities = [row[0] for row in localities_result]
        
        types_result = conn.execute(text("SELECT DISTINCT type FROM incidents ORDER BY type ASC"))
        crime_types = [row[0] for row in types_result]
        
    # Pass the actions to the template
    return render_template(
        'dashboard.html', 
        localities=cities, 
        crime_types=crime_types,
        actions=PLAYER_ACTIONS.values()
    )
