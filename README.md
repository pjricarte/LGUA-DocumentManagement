# LGUA Document Management System

A comprehensive document management system designed to efficiently organize, store, and retrieve administrative documents.

## Features

- User authentication and account management
- File upload, download, and management
- Document categorization
- Advanced search functionality
- Recycle bin with automatic cleanup
- User profile management

## System Requirements

- Python 3.8 or higher
- MySQL 8.0 or higher
- Pip package manager
- Virtual environment (recommended)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/LGUA-DocumentManagement.git
cd LGUA-DocumentManagement
```

### 2. Set Up Virtual Environment (Recommended)

```bash
# For Windows
python -m venv venv
venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Application configuration
SECRET_KEY=your_secret_key_here
LOG_LEVEL=INFO

# Database configuration
DB_NAME=lgua_document_db
DB_USER=your_db_username
DB_PASSWORD=your_db_password
MYSQL_ROOT_PASSWORD=your_mysql_root_password
DB_HOST=localhost
DB_PORT=3306
```

> **Note:** Replace the placeholder values with your actual configuration details. The SECRET_KEY should be a secure random string.

### 5. Set Up the Database

1. Create a MySQL database:

```sql
CREATE DATABASE lgua_document_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Initialize the database tables:

```bash
# Start Python shell
python

# In the Python shell
from app import app, db
with app.app_context():
    db.create_all()
    exit()
```

### 6. Create Upload Directory

The system will automatically create the required directories, but you can manually create them:

```bash
mkdir -p uploads
mkdir -p data
```

## Running the Application

### Development Mode

```bash
python app.py
```

The application will be available at `http://localhost:5000`.

### Production Deployment

For production deployment, it's recommended to use Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Initial Setup

1. After starting the application, navigate to `http://localhost:5000/register` to create an admin account.
2. Log in with your newly created credentials.
3. Set up document categories through the category management interface.

## System Structure

- `app.py` - Main application file with routes and core functionality
- `models.py` - Database models and relationships
- `settings.py` - Application configuration and settings
- `requirements.txt` - Python dependencies
- `uploads/` - Directory for uploaded files
- `data/` - Directory for application data
- `templates/` - HTML templates for the web interface
- `static/` - Static files (CSS, JavaScript, images)




