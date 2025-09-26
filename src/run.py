import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app, socketio

app = create_app()


if __name__ == '__main__':
    socketio.run(app, debug=True)
