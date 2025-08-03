import os
import logging.config
# uncomment the following line to enable endpoint profiling
# from werkzeug.middleware.profiler import ProfilerMiddleware

from app import create_app, init_mongo_indexes
from app.logs import webapp_logging_config

logger = logging.getLogger(__name__)

# configure application logging
logging.config.dictConfig(webapp_logging_config)

app = create_app()
init_mongo_indexes()

# uncomment the following line to enable endpoint profiling
# app.wsgi_app = ProfilerMiddleware(app.wsgi_app, sort_by=("cumtime", "calls"))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
