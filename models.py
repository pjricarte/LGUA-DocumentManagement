from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declared_attr

class Base(DeclarativeBase):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

db = SQLAlchemy(model_class=Base)

class User(db.Model, UserMixin):
    id = db.Column(Integer, primary_key=True)
    username = db.Column(String(150), unique=True, nullable=False, index=True)
    email = db.Column(String(150), unique=True, nullable=False)
    first_name = db.Column(String(100), nullable=False)
    last_name = db.Column(String(100), nullable=False)
    password_hash = db.Column(String(256), nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationship with files - passive_deletes=True ensures files aren't deleted when user is deleted
    files = db.relationship('File', backref=db.backref('user', passive_deletes=True), 
                           foreign_keys='File.user_id', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Category(db.Model):
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(100), unique=True, nullable=False, index=True)
    description = db.Column(String(500))
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    files = db.relationship('File', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<Category {self.name}>'
        
    def file_count(self):
        return self.files.count()

class File(db.Model):
    id = db.Column(Integer, primary_key=True)
    filename = db.Column(String(255), nullable=False, index=True)
    original_filename = db.Column(String(255), nullable=False)
    description = db.Column(Text, nullable=True)
    file_type = db.Column(String(20), index=True)
    file_size = db.Column(Integer)
    storage_path = db.Column(String(500), nullable=False)
    upload_date = db.Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Recycle bin related fields
    is_deleted = db.Column(db.Boolean, default=False, index=True)
    deleted_at = db.Column(DateTime, nullable=True, index=True)
    
    # Store uploader information directly to preserve it even if the user is deleted
    uploader_username = db.Column(String(150), nullable=False, index=True)
    uploader_full_name = db.Column(String(200), nullable=False)
    
    # Optional foreign key to user (can be null if user is deleted)
    user_id = db.Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Foreign key to category
    category_id = db.Column(Integer, ForeignKey('category.id'), nullable=True, index=True)
    
    def __repr__(self):
        return f'<File {self.filename}>'
    
    @property
    def file_size_formatted(self):
        if not self.file_size:
            return "0 B"
            
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                return f"{size:.2f} {unit}"
            size /= 1024
            
    @property
    def extension(self):
        return self.original_filename.rsplit('.', 1)[1].lower() if '.' in self.original_filename else ''
