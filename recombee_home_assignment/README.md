
### Directory/Files breakdown

- **`clients/`**: contains db and rabbitmq client classes for easier connection management
- **`consumer/`**: holds the consumer service, service responsible for consuming from queue, parsing incoming xml and eventually saving new feed
- **`db_init/`**: contains initialization script (referenced in docker-compose.yml) for setting up the PostgreSQL database tables when starting up a container
- **`models/`**: contains data models represent database schemas or Pydantic models
- **`main.py`**: the FastAPI entry point, all the endpoints are accesible through this api
- **`logger.py`**: utility file used in multiple modules for simple logging purposes
- **`nginx.conf`**: configuration file for Nginx container (referenced in docker-compose.yml).

### How to Set Up the Project

#### Run whole project using `docker compose`

1. `cd` into the root of the project
2. To start the services build the images first with `docker compose build` and run them with `docker compose up`.
3. Access the (all of the provided are defaults in *docker-compose.yaml*): 
   - api service on port *4444*
   - adminer on port *8080*
   - rabbitmq management console on port *15672*
   - feed images will be stored in *{project_root}/app/images*


#### Run python services locally (e.g. for dev) and  the rest of the services using  `docker compose`

1. `cd` into the root of the project
2. **Set up a virtual environment (from root of the project)**:
   - If you're starting with a clean environment, run `python3 -m venv .venv` to create a new virtual environment.
   - Activate it with `source .venv/bin/activate` (Linux/MacOS) or `.venv\Scripts\activate` (Windows).
3. Run `pip install -r requirements.txt` to install all the required packages.
4. Run non-python services with `docker compose up db rabbitmq adminer` (no nginx)
5. Run FastAPI entrypoint in dev mode `fastapi dev main.py`
6. Run consumer service as module `python -m consumer.consumer`
7. Access the (all of the provided are defaults in *docker-compose.yaml* + defaults in python services if not overriden by env variables): 
   - api service on port *8000*
   - adminer on port *8080*
   - rabbitmq management console on port *15672*
   - feed images will be stored in *{project_root}/app/images*

