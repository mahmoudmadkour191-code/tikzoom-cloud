## About the project:

The Telegram bot store is written in Python using frameworks such as Django and Aiogram. It features a Django admin
panel that allows creating/editing/deleting categories, subcategories, products, and users. The bot itself includes a
registration system, login functionality, and a password reset option. User passwords are hashed and cannot be modified.
The administrator will not be able to change a user's username or password; only the user can reset and change their
password to a new one. After logging in, the user will have access to commands such as help, description, and catalog.
When the catalog command is selected, an inline keyboard with product categories will appear, and after choosing a
category, another inline keyboard with subcategories will show up. Then, the user will see the products. There are also
commands for the administrator, such as broadcasting messages to users of the Telegram bot. Additionally, handlers for
unknown or unclear commands and messages have been created for the bot. PostgreSQL is used as the database.
___________

## Installation instructions

### 1. Clone the repository

Copy the repository: `git clone https://github.com/ddosmukhambetov/ecommerce-telegram-bot`

### 2. Update keys, tokens and other settings

Rename the file: `.env.example` to `.env`
Modify the variables in the `.env` file

### 3. Run the project

To start the project, you can use the following commands from the Makefile:

- `make all` - Starts both the database and the application containers. It builds and runs them in detached mode (-d).
- `make create-superuser` - Creates a superuser for the Django admin panel by running python manage.py createsuperuser
- `make bot-logs` - Shows the logs for the application container (bot) in real-time.

### 4. Available commands

Here is a list of the available commands from the Makefile. Each command can be run manually or through make:

- `make all` - Starts both the database and the application containers. It builds and runs them in detached mode (-d).
- `make all-down` - Stops and removes both the database and the application containers.
- `make bot` - Builds and starts the application container (bot) with Docker Compose.
- `make bot-down` - Stops and removes the application container (bot), including orphaned containers.
- `make bot-exec` - Accesses the application container and opens a bash shell inside it.
- `make bot-logs` - Shows the logs for the application container (bot) in real-time.
- `make create-superuser` - Creates a superuser for the Django admin panel by running python manage.py createsuperuser
  inside the application container.
- `make make-migrations` - Creates migrations for the Django application by running python manage.py makemigrations
  inside the application container.
- `make migrate` - Applies the migrations to the database by running python manage.py migrate inside the application
  container.
- `make collectstatic` - Collects static files for the Django application by running python manage.py collectstatic
  --noinput inside the application container.
- `make db` - Builds and starts the database container (postgres) with Docker Compose.
- `make db-down` - Stops and removes the database container (postgres), including orphaned containers.
- `make db-exec` - Accesses the database container and opens a bash shell inside it.
- `make db-logs` - Shows the logs for the database container (postgres) in real-time.

## Telegram Bot Functionality

- The bot has commands such as Sign Up, Sign In, Forgot Password, Help, Description, Catalog, Admin Menu, etc.
  Below is an example of how the bot works ⬇️

### 1. Authorization Commands (Sign Up, Sign In, Forgot Password)

<p><img src="https://i.ibb.co/wYq9bWp/Group-1-1.png", alt="authentification"></p>

This section implements a registration and login system. It also includes a "Forgot Password" function. When creating a
password, it is hashed. The user can only create one profile, as their user ID will be assigned to the profile during
registration. The "Sign Up" command first asks for a username, then checks if that username is already taken by
another user. If it is, the bot will ask for a new, unique username. If the username is available, the bot proceeds to
the password creation step. The password must contain at least one digit and only consist of Latin characters. If the
user creates an incorrect password, they will be informed about the required password format. Once the password is
successfully created, it is hashed, and the user is saved in the database, appearing in the Django admin panel. The
administrator does not have the ability to edit user data.

### 2. Catalog Command (Categories, Subcategories, Products)

<p><img src="https://i.ibb.co/JtCVDzb/view-products-3.png", alt="view products"></p>

The "Catalog" command is responsible for displaying categories, subcategories, and products. This command is only
accessible once the user has logged in (authenticated). The image shows how this command works. There may be cases where
a category or subcategory has no products; in such cases, the bot will inform the user that there are no products in
that category/subcategory. Categories, subcategories, and products are sorted in the order they were added. These
objects can be added, edited, and deleted in the Django admin panel. Additionally, the category model can be easily
modified and made recursive, allowing for the creation of multiple subcategories under each category. This makes it
flexible and scalable for organizing products in a hierarchical structure.

### 3. Default Commands (Help, Description, Admin -> Broadcast)

<p><img src="https://i.ibb.co/BGmCShZ/default-commands-1.png", alt="default commands"></p>

The "Default" commands section includes commands such as "Help," which provides assistance regarding the bot. There is
also the "Description" command, which gives an overview of the Telegram store/bot. Additionally, there is an interesting
command called "Admin." To use this command, the user must be on the list of Telegram administrators. Once the "Admin"
button is pressed, the user is redirected to the admin menu. Currently, this menu contains one command: "Broadcast,"
along with buttons for "Home" and "Help." The "Help" button provides instructions for the administrator, including
available commands and their descriptions. The "Home" button simply returns the user to the main menu. Thanks to the "
Broadcast" command, the administrator can send messages to all registered users of the Telegram bot.
___________

## Django Admin Panel:

- The project uses Django to handle models, the admin panel, relationships between models, and more.

### 1. Simple Home Page

<p><img src="https://i.postimg.cc/t4tVC0Sr/image.png", alt="simple main page"></p>

**The simplest home page (HTML + Bootstrap).** with a brief description of the project.

___________

### 2. Admin Panel:

<p><img src="https://i.ibb.co/JwD88m4S/image.png", alt="admin panel"></p>

___________

### 3. Products in the Admin Panel:

<p><img src="https://i.ibb.co/Zp6g8jkb/image.png", alt="creating_product"></p>

The product accepts a photo, title, description, price, whether it is published, as well as category and subcategory.
The subcategory is linked to the category. All created products are displayed in the Django admin panel.

___________

### 4. Categories in the Admin Panel:

<p><img src="https://i.ibb.co/WNPmKqwR/image.png", alt="creating_category"></p>

The category accepts a name and description. All created categories are displayed in the Django admin panel.

___________

### 5. SubCategories in the Admin Panel:

<p><img src="https://i.ibb.co/39G3t3tD/image.png", alt="creating_subcategory"></p>

The subcategory accepts the subcategory name, description, and also the category. All created subcategories are
displayed in the Django admin panel.

___________

### 6. Telegram Bot Users in the Admin Panel:

<p><img src="https://i.ibb.co/zh73Kj4y/Untitled.png", alt="user"></p>

The user accepts the user ID, login, password, and whether they are registered. Users are created within the Telegram
bot, and their data, such as the user ID and registration status, are automatically obtained. All users registered in
the Telegram bot are displayed in the Django admin panel. The administrator does not have the ability to edit user data.
User passwords are hashed.

___________

<p align="center">
  <img src="https://img.shields.io/badge/python-3x-yellow", alt="Python Version">
  <img src="https://img.shields.io/badge/aiogram-2.25.1-blue", alt="Aiogram Version">
  <img src="https://img.shields.io/badge/Django-4.2-success", alt="Django Version">
</p>

___________