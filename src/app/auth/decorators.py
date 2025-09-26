from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from ..models import Agent

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        agent_id = get_jwt_identity()
        agent = Agent.query.get(int(agent_id))
        if not agent or agent.role != 'admin':
            return jsonify({'message': 'Admins only!'}), 403
        return fn(*args, **kwargs)
    return wrapper

def agent_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        agent_id = get_jwt_identity()
        agent = Agent.query.get(int(agent_id))
        if not agent:
            return jsonify({'message': 'Agent authentication required!'}), 403
        return fn(*args, **kwargs)
    return wrapper
