DC = docker compose
EXEC = docker exec -it

ENV = --env-file .env

BOT_FILE = dc/bot.yaml
DB_FILE = dc/db.yaml

BOT_CONTAINER = bot
DB_CONTAINER = postgres

# Replace with your own values
POSTGRES_USER = POSTGRES_USER
POSTGRES_DB = POSTGRES_DB

.PHONY: bot
bot:
	$(DC) -f $(BOT_FILE) $(ENV) up --build -d

.PHONY: bot-down
bot-down:
	$(DC) -f $(BOT_FILE) $(ENV) down --remove-orphans

.PHONY: bot-exec
bot-exec:
	$(EXEC) $(BOT_CONTAINER) bash

.PHONY: bot-logs
bot-logs:
	$(DC) -f $(BOT_FILE) $(ENV) logs -f

.PHONY: create-superuser
create-superuser:
	$(EXEC) $(BOT_CONTAINER) bash -c "python manage.py createsuperuser"

.PHONY: make-migrations
make-migrations:
	$(EXEC) $(BOT_CONTAINER) bash -c "python manage.py makemigrations"

.PHONY: migrate
migrate:
	$(EXEC) $(BOT_CONTAINER) bash -c "python manage.py migrate"

.PHONY: collectstatic
collectstatic:
	$(EXEC) $(BOT_CONTAINER) bash -c "python manage.py collectstatic --noinput"

.PHONY: db
db:
	$(DC) -f $(DB_FILE) $(ENV) up --build -d

.PHONY: db-down
db-down:
	$(DC) -f $(DB_FILE) $(ENV) down --remove-orphans

.PHONY: db-exec
db-exec:
	$(EXEC) $(DB_CONTAINER) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

.PHONY: db-logs
db-logs:
	$(DC) -f $(DB_FILE) $(ENV) logs -f

.PHONY: all
all:
	$(DC) -f $(DB_FILE) $(ENV) up --build -d
	$(DC) -f $(BOT_FILE) $(ENV) up --build -d

.PHONY: all-down
all-down:
	$(DC) -f $(DB_FILE) $(ENV) down --remove-orphans
	$(DC) -f $(BOT_FILE) $(ENV) down --remove-orphans
