from flask import redirect, url_for
from . import main_bp

@main_bp.route('/')
def index():
    return redirect(url_for('kiosk.welcome'))

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect to the styled auth login page
    return redirect(url_for('auth.login_page'))

# Old agent dashboard route removed - use /agent/dashboard instead
