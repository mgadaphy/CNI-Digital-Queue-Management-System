import os
from flask import Flask, request
from dotenv import load_dotenv
from .config import Config
from .extensions import db, jwt, migrate, socketio, csrf, login_manager, queue_scheduler
from datetime import datetime
from flask_cors import CORS

def create_app(config_class=Config):
    """Create and configure an instance of the Flask application."""
    # Load environment variables from .flaskenv and .env
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.flaskenv'))
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Socket.IO event handlers for real-time queue updates
    @socketio.on('connect')
    def handle_connect():
        print('Client connected')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')
    
    # Function to emit queue updates
    def emit_queue_update(queue_data):
        socketio.emit('queue_update', queue_data, broadcast=True)
    CORS(app, supports_credentials=True)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login_page'
    login_manager.login_message = 'Please log in to access this page.'
    
    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from .models import Agent
        return Agent.query.get(int(user_id))

    # JWT Error Handlers
    from flask import redirect, url_for, request, jsonify
    from flask_jwt_extended import JWTManager
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """Redirect to login page when token is expired"""
        if request.is_json or request.path.startswith('/api/') or request.path.startswith('/kiosk/'):
            return jsonify({'message': 'Token has expired', 'error': 'token_expired'}), 401
        return redirect(url_for('auth.login_page'))
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """Redirect to login page when token is invalid"""
        if request.is_json or request.path.startswith('/api/') or request.path.startswith('/kiosk/'):
            return jsonify({'message': 'Invalid token', 'error': 'invalid_token'}), 401
        return redirect(url_for('auth.login_page'))
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        """Redirect to login page when token is missing"""
        if request.is_json or request.path.startswith('/api/') or request.path.startswith('/kiosk/'):
            return jsonify({'message': 'Authorization token is required', 'error': 'authorization_required'}), 401
        return redirect(url_for('auth.login_page'))

    with app.app_context():
        # Import models here so they can be found by Alembic/Flask-Migrate
        from . import models

        # Register blueprints
        from .auth.routes import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')

        from .api.routes import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')

        from .main.routes import main_bp
        app.register_blueprint(main_bp)

        from .kiosk import kiosk_bp
        app.register_blueprint(kiosk_bp, url_prefix='/kiosk')
        
        from .api.performance import performance_bp
        app.register_blueprint(performance_bp, url_prefix='/api/performance')

        from .api.advanced_priority import advanced_priority_bp
        app.register_blueprint(advanced_priority_bp, url_prefix='/api/advanced_priority')
        
        from .api.position_api import position_api_bp
        app.register_blueprint(position_api_bp, url_prefix='/api/position')
        
        from .api.monitoring_api import monitoring_api_bp
    app.register_blueprint(monitoring_api_bp, url_prefix='/api/monitoring')
    
    from .api.config_api import config_api_bp
    app.register_blueprint(config_api_bp, url_prefix='/api/config')
    
    from .routes.user import user_bp
    app.register_blueprint(user_bp, url_prefix='/user')
    
    from .routes.admin import admin_bp
    app.register_blueprint(admin_bp)
    
    from .routes.agent import agent_bp
    app.register_blueprint(agent_bp)

    # Initialize performance monitoring after app is ready
    from .queue_logic.performance_monitor import metrics_collector
    metrics_collector._app = app
    metrics_collector.start_monitoring()
    
    # Initialize and start queue scheduler
    from .queue_logic.scheduler import get_queue_scheduler
    global queue_scheduler
    queue_scheduler = get_queue_scheduler()
    queue_scheduler.start()
    
    # Initialize position tracker for real-time updates
    from .queue_logic.position_tracker import get_position_tracker
    position_tracker = get_position_tracker()
    position_tracker.refresh_positions()
    
    # Initialize transaction manager
    from .utils.db_transaction_manager import get_transaction_manager
    from .extensions import transaction_manager
    global transaction_manager
    transaction_manager = get_transaction_manager()
    
    # Initialize queue logger
    from .utils.queue_logger import get_queue_logger
    queue_logger = get_queue_logger(app)
    
    # Setup request context for logging
    @app.before_request
    def setup_logging_context():
        import uuid
        from flask import g
        g.request_id = str(uuid.uuid4())
        g.queue_logger = queue_logger
        
        # Log request start
        queue_logger.log_queue_event('request_started', {
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr
        })
    
    @app.after_request
    def log_request_end(response):
        # Log request completion
        queue_logger.log_queue_event('request_completed', {
            'status_code': response.status_code,
            'content_length': response.content_length
        })
        return response

    @app.route('/test')
    def test_route():
        return "Hello, World!"

    @app.context_processor
    def inject_datetime():
        return {'datetime': datetime}
    
    # Register template filters
    @app.template_filter('moment')
    def moment_filter(dt, format='%Y-%m-%d %H:%M:%S'):
        """Format datetime using moment-like formatting"""
        if dt is None:
            return ''
        if isinstance(dt, str):
            return dt
        return dt.strftime(format)
    
    @app.template_filter('timeago')
    def timeago_filter(dt):
        """Return time ago string for datetime"""
        if dt is None:
            return ''
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"

    return app
