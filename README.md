# E-commerce Store Project

A modern, full-featured e-commerce platform built with Django. This project provides a comprehensive solution for an online store, featuring a product catalog, a shopping cart, and a secure payment flow.
**Project Updates**: This project is actively maintained to enhance features & improve performance.

## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Running the Project](#running-the-project)
- [Technologies Used](#technologies-used)
- [License](#license)
- [Contributing](#contributing)

## Features
- **User Authentication**: Secure user signup, login, and password reset.
- **Shopping Cart**: A robust, persistent shopping cart for managing products before checkout.
- **Payment Integration**: Seamless integration with the Zarinpal payment gateway for secure transactions.
- **Product Catalog**: Products can be easily filtered by category, enhancing the user's browsing experience.
- **Advanced Search**: Efficient full-text search capabilities powered by PostgreSQL.
- **Modern Admin Dashboard**: A polished and user-friendly Django administration panel powered by the Unfold library.

## Prerequisites
Before you get started, ensure you have the following software installed on your system:
- Python 3.12+
- PostgreSQL
- Git

## Installation and Setup
Follow these steps to get the project up and running on your local machine.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/great-orion/django-store.git
   cd django-store
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Create the virtual environment
   python -m venv venv

   # Activate on macOS and Linux
   source venv/bin/activate

   # Activate on Windows
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Create a `.env` file in the root of the project and add your sensitive information. This file is crucial for security and is ignored by Git.
   ```plaintext
   # Email Configuration
    EMAIL_HOST=smtp.gmail.com
    EMAIL_HOST_USER=your_gmail_account
    EMAIL_HOST_PASSWORD=your_gmail_app_pass

    # Postgres
    DB_NAME=your_DB_NAME
    DB_USER=your_DB_USER
    DB_PASSWORD=your_DB_PASS
    DB_HOST=localhost

    # Django
    SECRET_KEY=your_secret_key
   ```

5. **Run migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create a superuser**:
   To access the Unfold admin dashboard, create an admin account.
   ```bash
   python manage.py createsuperuser
   ```

## Running the Project
To start the development server, run the following command. The application will be accessible at `http://127.0.0.1:8000`.
```bash
python manage.py runserver
```

You can access the Unfold admin dashboard at `http://127.0.0.1:8000/admin`.

## Technologies Used
- **Framework**: Django5
- **Database**: PostgreSQL
- **Admin Panel**: Unfold
- **Payment Gateway**: Zarinpal

## License
This project is licensed under the MIT License - see the `LICENSE` file for details.

## Contributing
We welcome contributions! Please feel free to open a pull request or submit an issue on the repository.
