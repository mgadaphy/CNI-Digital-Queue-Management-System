from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from pytz import utc

# Initialize extensions
socketio = SocketIO(cors_allowed_origins="*")
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)
cache = Cache()
cors = CORS()
csrf = CSRFProtect()
login_manager = LoginManager()

# Initialize queue scheduler - will be configured after app creation
queue_scheduler = None

# Initialize transaction manager - will be configured after app creation
transaction_manager = None
