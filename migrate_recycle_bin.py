import os
import sys
from app import app, db
from models import User, Category, File
import logging
from sqlalchemy import text
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_recycle_bin_fields():
    """Add is_deleted and deleted_at fields to the File table for recycle bin functionality"""
    with app.app_context():
        try:
            # Use text() for raw SQL with proper connection handling
            with db.engine.connect() as conn:
                # Check if columns exist
                result = conn.execute(text("SELECT * FROM information_schema.columns WHERE table_name = 'file' AND column_name = 'is_deleted'"))
                if result.rowcount == 0:
                    logger.info("Adding is_deleted column to File table...")
                    conn.execute(text("ALTER TABLE file ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE"))
                    conn.execute(text("CREATE INDEX idx_file_is_deleted ON file (is_deleted)"))
                    logger.info("is_deleted column added successfully")
                else:
                    logger.info("is_deleted column already exists")
                
                result = conn.execute(text("SELECT * FROM information_schema.columns WHERE table_name = 'file' AND column_name = 'deleted_at'"))
                if result.rowcount == 0:
                    logger.info("Adding deleted_at column to File table...")
                    conn.execute(text("ALTER TABLE file ADD COLUMN deleted_at TIMESTAMP"))
                    conn.execute(text("CREATE INDEX idx_file_deleted_at ON file (deleted_at)"))
                    logger.info("deleted_at column added successfully")
                else:
                    logger.info("deleted_at column already exists")
                
                # Commit the transaction
                conn.commit()
                
            logger.info("Recycle bin migration completed successfully")
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    add_recycle_bin_fields()
