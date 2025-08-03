from datetime import datetime
import logging
from flask_log_request_id import RequestIDLogFilter
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError
from flask import request


class TaskFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            from celery._state import get_current_task
            self.get_current_task = get_current_task
        except ImportError:
            self.get_current_task = lambda: None

    def format(self, record):
        task = self.get_current_task()
        if task and task.request:
            record.__dict__.update(task_id=task.request.id,
                                   task_name=task.name)
        else:
            record.__dict__.setdefault('task_name', '')
            record.__dict__.setdefault('task_id', '')
        return super().format(record)


class ContextualFilter(logging.Filter):
    def filter(self, log_record):
        """ Provide some extra variables to give our logs some better info """
        log_record.utcnow = datetime.utcnow().isoformat(sep=' ', timespec='milliseconds')
        log_record.url = request.path
        log_record.method = request.method
        # try to get the IP address of the user through reverse proxy
        # log_record.ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        # try to get the user id from the JWT if the endpoint is authenticated and the JWT token valid
        log_record.user_id = None

        try:
            if verify_jwt_in_request():
                log_record.user_id = get_jwt_identity()
        except (PyJWTError, JWTExtendedException, RuntimeError):
            pass

        log_record.user_id = log_record.user_id or 'unauthenticated'
        return True


class ContextualFilterCelery(ContextualFilter):
    def filter(self, log_record):
        """ Provide some extra variables to give our logs some better info """
        log_record.utcnow = datetime.utcnow().isoformat(sep=' ', timespec='milliseconds')
        return True


webapp_logger_format = '[%(utcnow)s][user:%(user_id)s][%(url)s %(method)s %(request_id)8.8s] ' \
                       '%(levelname)s - %(message)s'
celery_logger_format = '[%(utcnow)s] Task %(task_name)s[%(task_id)s] %(levelname)s - %(message)s'


webapp_logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'webapp': {
            'format': webapp_logger_format
        }
    },
    'filters': {
        'contextual_filter': {
            '()': ContextualFilter
        },
        'request_id_filter': {
            '()': RequestIDLogFilter
        }
    },
    'handlers': {
        'webapp': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'webapp',
            'filters': ['contextual_filter', 'request_id_filter'],
            'stream': 'ext://sys.stdout'
        },
        'debugging': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'webapp',
            'filters': ['contextual_filter', 'request_id_filter'],
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        'app': {
            'level': 'INFO',  # if os.environ.get('DEBUG') else 'INFO',
            'handlers': ['webapp'],
            'propagate': False
        },
        'app.domains.event': {
            'level': 'DEBUG',
            'handlers': ['debugging'],
            'propagate': False
        }
    }
}


logging_config_celery = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'celery': {
            '()': TaskFormatter,
            'format': celery_logger_format
        }
    },
    'filters': {
        'contextual_filter': {
            '()': ContextualFilterCelery
        }
    },
    'handlers': {
        'celery': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'celery',
            'filters': ['contextual_filter'],
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        'app': {
            'level': 'INFO',  # if os.environ.get('DEBUG') else 'INFO',
            'handlers': ['celery'],
            'propagate': False
        }
    }
}


websocket_logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console_formatter': {
            'format': '[%(asctime)s][%(process)d][%(name)s:%(lineno)d][%(levelname)s] - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'console_formatter',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        '': {  # root logger
            'level': 'INFO',  # if os.environ.get('DEBUG') else 'INFO',
            'handlers': ['console']
        }
    }
}
