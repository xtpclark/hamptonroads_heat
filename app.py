# app.py
import logging
from flask import Flask, request # The 'request' object must be imported here
from db import engine 
from routes.main import main_bp
from routes.simulation import sim_bp

# Configure logging
logging.basicConfig(level=logging.INFO)

def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__)

    # Register the blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(sim_bp)

    @app.before_request
    def log_request_info():
        """Logs incoming request details."""
        # Added a check to avoid logging requests for static files, which can be noisy
        if not request.path.startswith('/static'):
            logging.info(f'Request: {request.method} {request.path}')

    return app

app = create_app()

if __name__ == '__main__':
    # Initialization is handled by entrypoint.sh and the loader script
    app.run(host='0.0.0.0', port=8000, debug=True)
