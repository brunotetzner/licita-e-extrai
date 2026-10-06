from flask import Flask

from controllers.hello_controller import bp


def create_app():
    app = Flask(__name__)
    # Enable UTF-8 in JSON responses (handles Portuguese characters: é, ã, ç, etc.)
    app.config['JSON_AS_ASCII'] = False
    # Ensure all responses use UTF-8 encoding
    app.config['JSON_SORT_KEYS'] = False

    @app.after_request
    def set_utf8_charset(response):
        """Ensure all responses explicitly declare UTF-8 charset."""
        if response.content_type and 'charset' not in response.content_type:
            response.headers['Content-Type'] = f'{response.content_type}; charset=utf-8'
        return response

    app.register_blueprint(bp)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
