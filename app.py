import os
import uuid
import logging
import hashlib
from datetime import datetime, timedelta
import threading
import time

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import or_

import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure app from settings
app.secret_key = settings.SECRET_KEY
app.config['UPLOAD_FOLDER'] = settings.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = settings.MAX_CONTENT_LENGTH

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = settings.DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = settings.SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = settings.SQLALCHEMY_ENGINE_OPTIONS

from models import db, User, Category, File

# Initialize database
db.init_app(app)

# Configure login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access this page."

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))

# ===============================
# Utility Functions
# ===============================

def get_file_extension(filename):
    """Extract file extension from filename"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def allowed_file(filename):
    """Check if file has an allowed extension"""
    return '.' in filename and get_file_extension(filename) in settings.ALLOWED_EXTENSIONS

def get_unique_filename(filename):
    """Generate a unique filename to prevent overwriting"""
    ext = get_file_extension(filename)
    return f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

def get_category_color(category_name):
    """Generate a color for a category based on its name"""
    category_colors = {
        'Administrative Documents': '#6610f2',
        'Personnel Records': '#fd7e14',
        'Finance Records': '#0d6efd',
        'Project & Program Files': '#20c997',
        'Legal & Compliance': '#dc3545',
        'Barangay Communications': '#17a2b8',
        'Public Services': '#28a745',
        'Planning & Development': '#6f42c1',
        'Citizen Records': '#e83e8c',
        'Environmental Documents': '#20c997',
        'Others': '#6c757d'
    }
    
    if category_name in category_colors:
        return category_colors[category_name]
    
    # Generate a color based on the hash of the category name
    hash_object = hashlib.md5(category_name.encode())
    hex_dig = hash_object.hexdigest()
    return f'#{hex_dig[:6]}'

# Register template functions
app.jinja_env.globals.update(get_category_color=get_category_color)

# ===============================
# Authentication Routes
# ===============================

@app.route("/", methods=['GET', 'POST'])
def login():
    """User login"""
    # If user is already authenticated, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid username or password', 'error')
            return render_template('login.html')
        
        # User is valid, log them in
        
        login_user(user, remember=True)
        logger.info(f"User logged in: {username}")
        
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')


@app.route("/register", methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Validate input
        if not all([username, email, password, confirm_password, first_name, last_name]):
            flash('Please fill in all fields', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('register.html')
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            logger.info(f"New user registered: {username}")
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration', 'error')
            db.session.rollback()
    
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    username = current_user.username
    logout_user()
    logger.info(f"User logged out: {username}")
    
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


# ===============================
# Dashboard Routes
# ===============================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard showing user's files"""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    date_filter = request.args.get('date', '')
    sort = request.args.get('sort', 'upload_date')
    direction = request.args.get('direction', 'desc')
    
    # Start with all files query - temporarily removing is_deleted filter
    files_query = File.query
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        files_query = files_query.filter(
            or_(
                File.filename.ilike(search_term),
                File.description.ilike(search_term),
                File.file_type.ilike(search_term),
                File.uploader_username.ilike(search_term)
            )
        )
    
    # Apply category filter if provided
    if category:
        files_query = files_query.filter(File.category_id == category)
    
    # Apply date filter if provided
    if date_filter:
        if date_filter == 'today':
            today = datetime.now().date()
            files_query = files_query.filter(db.func.date(File.upload_date) == today)
        elif date_filter == 'week':
            week_ago = datetime.now() - timedelta(days=7)
            files_query = files_query.filter(File.upload_date >= week_ago)
        elif date_filter == 'month':
            month_ago = datetime.now() - timedelta(days=30)
            files_query = files_query.filter(File.upload_date >= month_ago)
    
    files_query = files_query.order_by(File.upload_date.desc())
    
    # Get all categories for filter dropdown
    categories = Category.query.all()
    
    # Pagination
    pagination = files_query.paginate(page=page, per_page=10, error_out=False)
    files = pagination.items
    
    return render_template('dashboard.html', 
                           files=files, 
                           pagination=pagination,
                           categories=categories,
                           current_search=search,
                           current_category=category,
                           current_date=date_filter)


@app.route('/search')
@login_required
def search():
    """Advanced search page"""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '')
    category = request.args.get('category', '')
    date_filter = request.args.get('date', '')
    sort = request.args.get('sort', 'date_desc')
    
    # Start with base query
    files_query = File.query
    
    # Apply filters if provided
    if query:
        search_term = f"%{query}%"
        files_query = files_query.filter(
            or_(
                File.filename.ilike(search_term),
                File.description.ilike(search_term),
                File.file_type.ilike(search_term),
                File.uploader_username.ilike(search_term)
            )
        )
    
    if category:
        files_query = files_query.filter(File.category_id == category)
    
    # Temporarily removing is_deleted filter
    # files_query = files_query.filter(File.is_deleted == False)
    
    # Remove uploader filter as the variable is no longer defined
    
    # Apply date filter if provided
    if date_filter:
        if date_filter == 'today':
            today = datetime.now().date()
            files_query = files_query.filter(db.func.date(File.upload_date) == today)
        elif date_filter == 'week' or date_filter == 'this_week':
            week_ago = datetime.now() - timedelta(days=7)
            files_query = files_query.filter(File.upload_date >= week_ago)
        elif date_filter == 'month' or date_filter == 'this_month':
            month_ago = datetime.now() - timedelta(days=30)
            files_query = files_query.filter(File.upload_date >= month_ago)
    
    # Apply sorting based on dropdown selection
    if sort == 'name_asc':
        files_query = files_query.order_by(File.filename.asc())
    elif sort == 'name_desc':
        files_query = files_query.order_by(File.filename.desc())
    elif sort == 'date_asc':
        files_query = files_query.order_by(File.upload_date.asc())
    elif sort == 'date_desc':
        files_query = files_query.order_by(File.upload_date.desc())
    elif sort == 'size_asc':
        files_query = files_query.order_by(File.file_size.asc())
    elif sort == 'size_desc':
        files_query = files_query.order_by(File.file_size.desc())
    else:  # default
        files_query = files_query.order_by(File.upload_date.desc())
    
    # Get all categories for filter dropdown
    categories = Category.query.all()
    
    # Get distinct file types for filter dropdown
    file_types = db.session.query(File.file_type).distinct().all()
    file_types = [ft[0] for ft in file_types if ft[0]]
    
    # Get distinct uploaders for filter dropdown
    uploaders = db.session.query(File.uploader_username).distinct().all()
    uploaders = [u[0] for u in uploaders if u[0]]
    
    # Pagination
    pagination = files_query.paginate(page=page, per_page=10, error_out=False)
    files = pagination.items
    
    return render_template('search.html',
                           files=files,
                           pagination=pagination,
                           categories=categories,
                           file_types=file_types,
                           uploaders=uploaders,
                           current_query=query,
                           current_category=category,
                           current_date=date_filter,
                           current_sort=sort)


# ===============================
# File Management Routes
# ===============================

@app.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    """Upload a new file"""
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('dashboard'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('dashboard'))
    
    if not allowed_file(file.filename):
        flash(f'File type not allowed. Allowed types: {", ".join(settings.ALLOWED_EXTENSIONS)}', 'error')
        return redirect(url_for('dashboard'))
    
    filename = secure_filename(file.filename)
    unique_filename = get_unique_filename(filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    
    title = request.form.get('title', filename)
    description = request.form.get('description', '')
    category_id = request.form.get('category_id')
    
    try:
        # Save file to disk
        file.save(file_path)
        
        # Create file record in database
        new_file = File(
            filename=title,
            original_filename=filename,
            description=description,
            file_type=get_file_extension(filename),
            file_size=os.path.getsize(file_path),
            storage_path=unique_filename,
            uploader_username=current_user.username,
            uploader_full_name=f"{current_user.first_name} {current_user.last_name}",
            user_id=current_user.id,
            category_id=category_id if category_id else None
        )
        
        db.session.add(new_file)
        db.session.commit()
        logger.info(f"File uploaded: {title} by {current_user.username}")
        
        flash('File uploaded successfully', 'success')
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        flash('Error uploading file', 'error')
    
    return redirect(url_for('dashboard'))


@app.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    """Download a file"""
    file = File.query.get_or_404(file_id)
    
    # Check if file exists in the filesystem
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.storage_path)
    if not os.path.exists(file_path):
        flash('File not found on the server.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Log the download (no need to update the file record)
    
    # Return the file as an attachment
    return send_file(file_path, as_attachment=True, download_name=file.original_filename)


@app.route('/edit/<int:file_id>', methods=['GET', 'POST'])
@login_required
def edit_file(file_id):
    """Edit file metadata"""
    file = File.query.get_or_404(file_id)
    categories = Category.query.all()
    
    # Check if the current user has permission to edit this file
    if current_user.username != file.uploader_username:
        flash('You do not have permission to edit this file.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Get form data
        new_title = request.form.get('title')
        new_description = request.form.get('description')
        new_category_id = request.form.get('category_id')
        
        # Validate title
        if not new_title or new_title.strip() == '':
            flash('Title cannot be empty.', 'danger')
            return render_template('edit_file.html', file=file, categories=categories)
        
        # Update file metadata
        file.filename = new_title
        file.description = new_description
        
        # Update category if provided
        if new_category_id and new_category_id != '':
            file.category_id = new_category_id
        else:
            file.category_id = None
        
        # The updated_at field will be automatically updated by SQLAlchemy
        
        # Commit changes
        db.session.commit()
        
        flash('File updated successfully.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_file.html', file=file, categories=categories)


@app.route('/delete/<int:file_id>', methods=['GET', 'POST'])
@login_required
def delete_file(file_id):
    """Move a file to the recycle bin (soft delete)"""
    file = File.query.get_or_404(file_id)
    
    # Check if the current user has permission to delete this file
    if current_user.username != file.uploader_username:
        flash('You do not have permission to delete this file.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Soft delete the file (move to recycle bin)
    file.is_deleted = True
    file.deleted_at = datetime.utcnow()
    db.session.commit()
    
    flash('File moved to recycle bin. It will be permanently deleted after 15 days.', 'success')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/recycle-bin')
@login_required
def recycle_bin():
    """Recycle bin page showing deleted files"""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    
    # Get deleted files for the current user
    query = File.query.filter_by(is_deleted=True, uploader_username=current_user.username)
    
    # Sort by deletion date (newest first)
    query = query.order_by(File.deleted_at.desc())
    
    # Paginate the results
    pagination = query.paginate(page=page, per_page=10, error_out=False)
    files = pagination.items
    
    # Calculate days remaining before permanent deletion for each file
    for file in files:
        if file.deleted_at:
            expiry_date = file.deleted_at + timedelta(days=15)
            days_remaining = (expiry_date - datetime.utcnow()).days
            file.days_remaining = max(0, days_remaining)
        else:
            file.days_remaining = 'Unknown'
    
    return render_template('recycle_bin.html', files=files, pagination=pagination)


@app.route('/restore/<int:file_id>', methods=['POST'])
@login_required
def restore_file(file_id):
    """Restore a file from the recycle bin"""
    file = File.query.get_or_404(file_id)
    
    # Check if the current user has permission to restore this file
    if current_user.username != file.uploader_username:
        flash('You do not have permission to restore this file.', 'danger')
        return redirect(url_for('recycle_bin'))
    
    # Restore the file
    file.is_deleted = False
    file.deleted_at = None
    db.session.commit()
    
    flash('File restored successfully.', 'success')
    return redirect(url_for('recycle_bin'))


@app.route('/permanent-delete/<int:file_id>', methods=['POST'])
@login_required
def permanent_delete_file(file_id):
    """Permanently delete a file"""
    file = File.query.get_or_404(file_id)
    
    # Check if the current user has permission to delete this file
    if current_user.username != file.uploader_username:
        flash('You do not have permission to delete this file.', 'danger')
        return redirect(url_for('recycle_bin'))
    
    # Delete the file from the filesystem
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.storage_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete the file from the database
    db.session.delete(file)
    db.session.commit()
    
    flash('File permanently deleted.', 'success')
    return redirect(url_for('recycle_bin'))


# ===============================
# User Account Routes
# ===============================

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    """User account settings and profile management"""
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not all([first_name, last_name, email]):
            flash('First name, last name, and email are required', 'error')
            return redirect(url_for('account'))
        
        # Check if email is already in use by another user
        existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            flash('Email is already in use by another account', 'error')
            return redirect(url_for('account'))
        
        # Update user profile
        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.email = email
        
        # Change password if requested
        if current_password and new_password and confirm_password:
            if not check_password_hash(current_user.password_hash, current_password):
                flash('Current password is incorrect', 'error')
                return redirect(url_for('account'))
            
            if new_password != confirm_password:
                flash('New passwords do not match', 'error')
                return redirect(url_for('account'))
            
            current_user.password_hash = generate_password_hash(new_password)
            flash('Password updated successfully', 'success')
        
        try:
            db.session.commit()
            flash('Profile updated successfully', 'success')
            logger.info(f"User profile updated: {current_user.username}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Profile update error: {str(e)}")
            flash('An error occurred while updating your profile', 'error')
    
    # Get system-wide storage statistics
    import shutil
    import os
    
    # Calculate total storage used by all files in the system
    all_files = File.query.all()
    total_system_storage = sum(file.file_size for file in all_files if file.file_size)
    
    # Get disk space information for the drive where uploads are stored
    upload_drive = os.path.splitdrive(app.config['UPLOAD_FOLDER'])[0] or os.path.abspath(app.config['UPLOAD_FOLDER'])
    total, used, free = shutil.disk_usage(upload_drive)
    
    # Format storage sizes
    def format_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    formatted_system_storage = format_size(total_system_storage)
    formatted_total_space = format_size(total)
    formatted_used_space = format_size(used)
    formatted_free_space = format_size(free)
    
    # Calculate usage percentage
    usage_percentage = (used / total) * 100
    system_usage_percentage = (total_system_storage / total) * 100 if total > 0 else 0
    
    return render_template('edit_profile.html',
                           user=current_user,
                           system_storage=formatted_system_storage,
                           total_space=formatted_total_space,
                           used_space=formatted_used_space,
                           free_space=formatted_free_space,
                           usage_percentage=usage_percentage,
                           system_usage_percentage=system_usage_percentage)


@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account"""
    password = request.form.get('password')
    
    if not password:
        flash('Password is required to delete your account', 'error')
        return redirect(url_for('account'))
    
    if not check_password_hash(current_user.password_hash, password):
        flash('Password is incorrect', 'error')
        return redirect(url_for('account'))
    
    try:
        # Get user files
        user_files = File.query.filter_by(user_id=current_user.id).all()
        
        # Delete files from filesystem
        for file in user_files:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.storage_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Delete user and their files from database
        username = current_user.username
        db.session.delete(current_user)
        db.session.commit()
        
        logout_user()
        logger.info(f"User account deleted: {username}")
        flash('Your account has been deleted', 'info')
        return redirect(url_for('login'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Account deletion error: {str(e)}")
        flash('An error occurred while deleting your account', 'error')
        return redirect(url_for('account'))


# ===============================
# Category Management Routes
# ===============================

@app.route('/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    """Interface for managing document categories"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name')
            description = request.form.get('description', '')
            
            if not name:
                flash('Category name is required', 'error')
                return redirect(url_for('manage_categories'))
            
            # Check if category already exists
            existing_category = Category.query.filter_by(name=name).first()
            if existing_category:
                flash('Category already exists', 'error')
                return redirect(url_for('manage_categories'))
            
            try:
                new_category = Category(name=name, description=description)
                db.session.add(new_category)
                db.session.commit()
                logger.info(f"Category added: {name} by {current_user.username}")
                
                flash('Category added successfully', 'success')
            except Exception as e:
                logger.error(f"Category creation error: {str(e)}")
                flash('Error creating category', 'error')
                db.session.rollback()
            
            return redirect(url_for('manage_categories'))
        
        elif action == 'edit':
            category_id = request.form.get('category_id')
            name = request.form.get('name')
            description = request.form.get('description', '')
            
            if not category_id or not name:
                flash('Category ID and name are required', 'error')
                return redirect(url_for('manage_categories'))
            
            try:
                category = Category.query.get_or_404(category_id)
                
                # Check if name is already used by another category
                existing_category = Category.query.filter(Category.name == name, Category.id != category.id).first()
                if existing_category:
                    flash('Category name already exists', 'error')
                    return redirect(url_for('manage_categories'))
                
                category.name = name
                category.description = description
                db.session.commit()
                logger.info(f"Category updated: {name} by {current_user.username}")
                
                flash('Category updated successfully', 'success')
            except Exception as e:
                logger.error(f"Category update error: {str(e)}")
                flash('Error updating category', 'error')
                db.session.rollback()
            
            return redirect(url_for('manage_categories'))
        
        elif action == 'delete':
            category_id = request.form.get('category_id')
            
            if not category_id:
                flash('Category ID is required', 'error')
                return redirect(url_for('manage_categories'))
            
            try:
                # Get category
                category = Category.query.get_or_404(category_id)
                
                # Check if category has files
                files = File.query.filter_by(category_id=category.id).all()
                if files:
                    # Update files to remove category association
                    for file in files:
                        file.category_id = None
                    db.session.commit()
                    logger.info(f"Removed category association from {len(files)} files")
                
                db.session.delete(category)
                db.session.commit()
                logger.info(f"Category deleted: {category.name} by {current_user.username}")
                
                flash('Category deleted successfully', 'success')
            except Exception as e:
                logger.error(f"Category deletion error: {str(e)}")
                flash('Error deleting category', 'error')
                db.session.rollback()
            
            return redirect(url_for('manage_categories'))
    
    categories = Category.query.all()
    
    return render_template('manage_categories.html', categories=categories)


# ===============================
# Application Entry Point
# ===============================

def cleanup_old_deleted_files():
    """Background task to permanently delete files that have been in the recycle bin for more than 15 days"""
    while True:
        with app.app_context():
            try:
                # Calculate the cutoff date (15 days ago)
                cutoff_date = datetime.utcnow() - timedelta(days=15)
                
                # Find files that were deleted more than 15 days ago
                old_files = File.query.filter(File.is_deleted == True, File.deleted_at <= cutoff_date).all()
                
                for file in old_files:
                    # Delete the file from the filesystem
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.storage_path)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    # Delete the file from the database
                    db.session.delete(file)
                
                db.session.commit()
                print(f"Cleanup task: Removed {len(old_files)} expired files from recycle bin")
            except Exception as e:
                print(f"Error in cleanup task: {str(e)}")
            
            # Run once a day
            time.sleep(86400)  # 24 hours in seconds


if __name__ == '__main__':
    # Start the cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_old_deleted_files, daemon=True)
    cleanup_thread.start()
    
    logger.info("Starting application server")
    app.run(host='0.0.0.0', port=5000, debug=True)
