# flask-boilerplate
A Flask web application boilerplate, already integrating MongoEngine Celery, Redis, RabbitMQ and much more.


## Description

This repository provides a practical reference for structuring Flask applications and integrating them with common external services.

The application consists of three separate components:
- Flask web application
- Websocket server
- Celery tasks

and it includes:
- JWT authentication with cookie-based auth and automatic token refresh
- CORS handling
- JSON schema validation
- MongoDB with MongoEngine ODM for object modeling
- Redis for caching and pub/sub messaging
- Celery for background task processing with beat scheduler
- RabbitMQ message queuing with flask-pika
- Real-time WebSockets using Starlette with Redis pub/sub integration
- S3-compatible object storage via Boto3
- Swagger/OpenAPI documentation with Flasgger
- Role-based access control and security features
- Structured logging with request ID tracking
- Comprehensive testing with pytest, mocking, freezegun and more
- Docker containerization with docker-compose
- Marshmallow serialization


## Project Structure

The project is organized with the following structure:

```
flask-boilerplate/
├── flask-boilerplate/      # Application source code
│   ├── app/                # Core Flask application modules
│   ├── webapp.py           # Flask web server entry point
│   ├── websocket.py        # WebSocket server entry point
│   ├── celery_worker.py    # Celery worker entry point
│   └── config.py           # Application configuration
├── tests/                  # Test suite
├── docker/                 # Docker configuration
│   └── docker-compose.yml  # Container orchestration
├── webapp.local.env        # Environment variables
├── README.md               # Project documentation
├── LICENSE                 # License file
├── pyproject.toml          # Poetry dependency management
└── poetry.lock             # Locked dependencies
```


## Running the application

Start the required services:
```bash
docker-compose -f docker/docker-compose.yml up -d mongodb redis rabbitmq
```

Import the environment variables for local development:
```bash
set -a; source webapp.local.env; set +a
```

## Webapp server

Run the Flask webapp:
```bash
python3 flask-boilerplate/webapp.py
```

The webapp will be available at `http://localhost:5000`

## Running the websocket server

Run the websocket server:
```bash
python3 flask-boilerplate/websocket.py
```

The websocket server will be available at `http://localhost:5000`

## Running the celery worker

Run the Celery worker:
```bash
python3 flask-boilerplate/celery_worker.py
```

Or run with specific queues and concurrency:
```bash
celery -A flask-boilerplate.celery_worker.celery worker -Q celery,report --concurrency 4 --loglevel=info
```

For scheduled tasks, also run Celery Beat:
```bash
celery -A flask-boilerplate.celery_worker.celery beat --loglevel=info
```

### Running the application in docker

Alternatively, run any or all the application components in docker:

```bash
docker-compose -f docker/docker-compose.yml up api
docker-compose -f docker/docker-compose.yml up websocket
docker-compose -f docker/docker-compose.yml up celery beat
docker-compose -f docker/docker-compose.yml up
```

Docker exposes the webapp on port `5000` and the websocket on `5001`


## Running tests

Start the services containers:
```bash
docker-compose up redis mongodb rabbitmq
```
**IMPORTANT:** make sure the `celery` container is not running when running tests. It conflicts with the 
test celery worker and causes some tests to fail.

Import the environment variables for local development:
```bash
set -a; source webapp.local.env; set +a
```

Run the tests:
```bash
# run the python script (remove # to log the output to a file)
python3 -m pytest -v
```

Run a specific module, directory or test function:
```bash
python3 -m pytest tests/unit/domains/test_user.py -v
python3 -m pytest tests/unit/domains/test_auth.py::test_login -v
python3 -m pytest tests/unit/domains/ -v
```
