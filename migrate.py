import os
import sys
from app import app, db
from models import User, Category, File
from werkzeug.security import generate_password_hash
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_tables():
    with app.app_context():
        logger.info("Creating database tables...")
        db.create_all()
        logger.info("Database tables created successfully")

def create_admin_user():
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            logger.info("Creating default admin user...")
            admin = User(
                username='admin',
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()
            logger.info("Default admin user created successfully")
        else:
            logger.info("Admin user already exists")

def create_default_categories():
    default_categories = [
        {'name': 'Administrative Documents', 'description': 'Internal office communications and general operations'},
        {'name': 'Personnel Records', 'description': 'HR and employee-specific documentation'},
        {'name': 'Finance Records', 'description': 'Budget, accounting, and fund tracking'},
        {'name': 'Project & Program Files', 'description': 'Implementation of local government programs and services'},
        {'name': 'Legal & Compliance', 'description': 'Regulatory, legal, and audit-related documents'},
        {'name': 'Barangay Communications', 'description': 'Correspondence and reports from barangays under the LGU'},
        {'name': 'Public Services', 'description': 'Delivery of community services to residents'},
        {'name': 'Planning & Development', 'description': 'Strategic, demographic, and land-use planning'},
        {'name': 'Citizen Records', 'description': 'Files directly involving individuals or groups from the public'},
        {'name': 'Environmental Documents', 'description': 'Files related to ecological compliance and initiatives'}
    ]
    
    with app.app_context():
        for cat_data in default_categories:
            # Check if category already exists
            category = Category.query.filter_by(name=cat_data['name']).first()
            if not category:
                logger.info(f"Creating category: {cat_data['name']}")
                category = Category(
                    name=cat_data['name'],
                    description=cat_data['description']
                )
                db.session.add(category)
        
        db.session.commit()
        logger.info("Default categories created successfully")

if __name__ == '__main__':
    try:
        create_tables()
        create_admin_user()
        create_default_categories()
        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)
