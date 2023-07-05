import os

from waitress import serve

import app

host = os.getenv("JAGEOCODER_SERVER_HOST", '0.0.0.0')
port = os.getenv("JAGEOCODER_SERVER_PORT", 5000)
serve(app.app, host=host, port=port)
