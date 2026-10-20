import os

from flask import Flask

from controllers.router import register_routes


app = Flask(__name__)
register_routes(app)


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug_mode)
