from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from datetime import datetime
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
import qrcode
from io import BytesIO
import base64
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Database configuration with environment variable support
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///certificates.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload settings
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

db = SQLAlchemy(app)

# QR Code generation function
def generate_qr_code(certificate_id, certificate_data):
    """Generate QR code for birth certificate"""
    
    # Create the QR code data
    qr_string = f"Certificate ID: {certificate_id}\nType: Birth Certificate\nIssued by: Embassy of Afghanistan Berlin\nName: {certificate_data.get('given_name', '')} {certificate_data.get('family_name', '')}\nDOB: {certificate_data.get('date_of_birth', '')}\nVerify at: https://your-embassy-website.com/verify/{certificate_id}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    qr.add_data(qr_string)
    qr.make(fit=True)
    
    # Create QR code image
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 string for embedding in HTML
    buffer = BytesIO()
    qr_image.save(buffer, format='PNG')
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return qr_code_base64

# Barcode generation function
def generate_barcode(certificate_id):
    """Generate barcode for birth certificate"""
    
    try:
        # Create a Code128 barcode with custom options for larger size
        barcode_class = barcode.get_barcode_class('code128')
        
        # Configure writer with larger dimensions
        writer = ImageWriter()
        writer.set_options({
            'module_width': 0.4,    # Width of individual bars (increased from default 0.2)
            'module_height': 8.0,   # Height of bars (increased from default 15.0)
            'quiet_zone': 2.0,      # Reduced quiet zone for more barcode area
            'font_size': 8,         # Font size for text below barcode
            'text_distance': 2.0,   # Distance between barcode and text
            'background': 'white',  # Background color
            'foreground': 'black',  # Barcode color
        })
        
        # Generate barcode with certificate ID
        barcode_instance = barcode_class(certificate_id, writer=writer)
        
        # Create the barcode image
        buffer = BytesIO()
        barcode_instance.write(buffer)
        
        # Convert to base64 string for embedding in HTML
        barcode_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return barcode_base64
        
    except Exception as e:
        print(f"Error generating barcode: {e}")
        return None

# Models
class BirthCertificate(db.Model):
    __tablename__ = 'birth_certificate'
    
    id = db.Column(db.String, primary_key=True)
    family_name = db.Column(db.String, nullable=False)
    given_name = db.Column(db.String, nullable=False)
    previous_name = db.Column(db.String, default='')
    date_of_birth = db.Column(db.String, nullable=False)
    gender = db.Column(db.String)
    place_of_birth = db.Column(db.String)
    passport_number = db.Column(db.String)
    father_name = db.Column(db.String)
    mother_name = db.Column(db.String)
    photo_path = db.Column(db.String)
    id_card_path = db.Column(db.String)
    qr_code_data = db.Column(db.Text)
    barcode_data = db.Column(db.Text)
    status = db.Column(db.String, default='completed')
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    @property
    def birth_image_url(self):
        if self.photo_path:
            return url_for('uploaded_file', filename=self.photo_path)
        return None
    
    @property
    def id_card_url(self):
        if self.id_card_path:
            return url_for('uploaded_file', filename=self.id_card_path)
        return None

class MarriageCertificate(db.Model):
    id = db.Column(db.String, primary_key=True)
    husbandFamilyName = db.Column(db.String, nullable=False)
    husbandGivenName = db.Column(db.String, nullable=False)
    husbandDOB = db.Column(db.String)
    husbandPlaceOfBirth = db.Column(db.String)
    husbandIDNumber = db.Column(db.String)
    wifeFamilyName = db.Column(db.String, nullable=False)
    wifeGivenName = db.Column(db.String, nullable=False)
    wifeDOB = db.Column(db.String)
    wifePlaceOfBirth = db.Column(db.String)
    wifeIDNumber = db.Column(db.String)
    marriageDate = db.Column(db.String)
    marriagePlace = db.Column(db.String)
    status = db.Column(db.String, default='completed')
    created_at = db.Column(db.DateTime, default=datetime.now)

# Database reset function
def reset_database():
    """Reset database with new schema - WARNING: Deletes all data"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database reset complete - all existing data has been deleted")

# Create tables
try:
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")
        print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")
except Exception as e:
    print(f"Error creating tables: {e}")
    print("If you see 'Table already defined' error, delete certificates.db file and restart")

# Celibacy certificates (in-memory)
CELIBACY_CERTIFICATES = [
    {
        'id': 'CC-2024-001',
        'fullName': 'Mohammad Hassan',
        'dateOfBirth': '10.12.1990',
        'nationality': 'Afghan',
        'purpose': 'Immigration',
        'currentAddress': 'Bonn, Germany',
        'passportNumber': 'AF9876543',
        'fatherName': 'Abdul Hassan',
        'status': 'completed',
        'created': '17.09.2025'
    }
]

# Users - can also be moved to environment variables for better security
USERS = {
    'admin@econsulate.gov.af': {
        'name': 'System Administrator', 
        'password': os.environ.get('ADMIN_PASSWORD', 'admin123'), 
        'role': 'admin'
    },
    'user@econsulate.gov.af': {
        'name': 'Regular User', 
        'password': os.environ.get('USER_PASSWORD', 'user123'), 
        'role': 'user'
    }
}

# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user']['role'] != 'admin':
            return "Access denied: Admin privileges required", 403
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
@login_required
def index():
    birth_count = BirthCertificate.query.count()
    marriage_count = MarriageCertificate.query.count()
    celibacy_count = len(CELIBACY_CERTIFICATES)
    return render_template('index.html', birth_count=birth_count,
                           marriage_count=marriage_count,
                           celibacy_count=celibacy_count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email in USERS and USERS[email]['password'] == password:
            session['user'] = {'email': email, 'name': USERS[email]['name'], 'role': USERS[email]['role']}
            return redirect(request.args.get('next') or url_for('index'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/users')
@login_required
def users():
    return render_template('users.html', users=USERS)

# Birth Certificates
@app.route('/birth-certificates')
@login_required
def birth_certificates():
    certificates = BirthCertificate.query.order_by(BirthCertificate.created_at.desc()).all()
    return render_template('birth.html', certificates=certificates)

@app.route('/birth-certificate/create', methods=['GET', 'POST'])
@login_required
def create_birth_certificate():
    if request.method == 'POST':
        certificate_id = f"BC-{datetime.now().year}-{BirthCertificate.query.count()+1:03d}"

        # Handle file uploads
        photo = request.files.get('birthImage')
        id_card = request.files.get('idCard')

        photo_filename = None
        id_card_filename = None

        if photo and photo.filename:
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
            if '.' in photo.filename and photo.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                photo_filename = secure_filename(f"{certificate_id}_photo_{photo.filename}")
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
                photo.save(photo_path)
                
                if not os.path.exists(photo_path):
                    print(f"ERROR: Photo file was not saved to {photo_path}")

        if id_card and id_card.filename:
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
            if '.' in id_card.filename and id_card.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                id_card_filename = secure_filename(f"{certificate_id}_id_{id_card.filename}")
                id_card_path = os.path.join(app.config['UPLOAD_FOLDER'], id_card_filename)
                id_card.save(id_card_path)
                
                if not os.path.exists(id_card_path):
                    print(f"ERROR: ID card file was not saved to {id_card_path}")

        # Generate QR code
        certificate_data = {
            'family_name': request.form['familyName'],
            'given_name': request.form['givenName'],
            'date_of_birth': f"{request.form['birthDay']}.{request.form['birthMonth']}.{request.form['birthYear']}",
        }
        
        try:
            qr_code_base64 = generate_qr_code(certificate_id, certificate_data)
        except Exception as e:
            print(f"Error generating QR code: {e}")
            qr_code_base64 = None

        # Generate barcode
        try:
            barcode_base64 = generate_barcode(certificate_id)
        except Exception as e:
            print(f"Error generating barcode: {e}")
            barcode_base64 = None

        certificate = BirthCertificate(
            id=certificate_id,
            family_name=request.form['familyName'],
            given_name=request.form['givenName'],
            previous_name=request.form.get('previousName', ''),
            date_of_birth=f"{request.form['birthDay']}.{request.form['birthMonth']}.{request.form['birthYear']}",
            gender=request.form.get('gender'),
            place_of_birth=request.form.get('placeOfBirth'),
            passport_number=request.form.get('passportNumber'),
            father_name=request.form.get('fatherName'),
            mother_name=request.form.get('motherName'),
            photo_path=photo_filename,
            id_card_path=id_card_filename,
            qr_code_data=qr_code_base64,
            barcode_data=barcode_base64
        )

        db.session.add(certificate)
        db.session.commit()
        
        print(f"Certificate created with QR code: {qr_code_base64 is not None}")
        print(f"Certificate created with barcode: {barcode_base64 is not None}")
        
        return redirect(url_for('view_birth_certificate', certificate_id=certificate_id))

    return render_template('birth_form.html')

@app.route('/birth-certificate/<certificate_id>')
@login_required
def view_birth_certificate(certificate_id):
    certificate = BirthCertificate.query.get(certificate_id)
    if not certificate:
        return "Certificate not found", 404
    
    print(f"Certificate photo_path: {certificate.photo_path}")
    print(f"Certificate birth_image_url: {certificate.birth_image_url}")
    print(f"Certificate has QR code: {certificate.qr_code_data is not None}")
    print(f"Certificate has barcode: {certificate.barcode_data is not None}")
    
    return render_template('birth_certificate.html', certificate=certificate)

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        else:
            print(f"File not found: {file_path}")
            return "File not found", 404
    except Exception as e:
        print(f"Error serving file {filename}: {e}")
        return "Error serving file", 500

# Verification route
@app.route('/verify/<certificate_id>')
def verify_certificate(certificate_id):
    certificate = BirthCertificate.query.get(certificate_id)
    if certificate:
        return f"Certificate {certificate_id} is VALID.<br>Name: {certificate.given_name} {certificate.family_name}<br>DOB: {certificate.date_of_birth}<br>Issued: {certificate.created_at.strftime('%d.%m.%Y')}"
    else:
        return f"Certificate {certificate_id} is INVALID or not found", 404

# Marriage Certificates
@app.route('/marriage-certificates')
@login_required
def marriage_certificates():
    certificates = MarriageCertificate.query.order_by(MarriageCertificate.created_at.desc()).all()
    return render_template('marriage.html', certificates=certificates)

@app.route('/marriage-certificate/create', methods=['GET', 'POST'])
@login_required
def create_marriage_certificate():
    if request.method == 'POST':
        certificate_id = f"MC-{datetime.now().year}-{MarriageCertificate.query.count()+1:03d}"
        certificate = MarriageCertificate(
            id=certificate_id,
            husbandFamilyName=request.form.get('husbandFamilyName'),
            husbandGivenName=request.form.get('husbandGivenName'),
            husbandDOB=f"{request.form.get('husbandBirthDay')}.{request.form.get('husbandBirthMonth')}.{request.form.get('husbandBirthYear')}",
            husbandPlaceOfBirth=request.form.get('husbandPlaceOfBirth'),
            husbandIDNumber=request.form.get('husbandIDNumber'),
            wifeFamilyName=request.form.get('wifeFamilyName'),
            wifeGivenName=request.form.get('wifeGivenName'),
            wifeDOB=f"{request.form.get('wifeBirthDay')}.{request.form.get('wifeBirthMonth')}.{request.form.get('wifeBirthYear')}",
            wifePlaceOfBirth=request.form.get('wifePlaceOfBirth'),
            wifeIDNumber=request.form.get('wifeIDNumber'),
            marriageDate=request.form.get('marriageDate'),
            marriagePlace=request.form.get('marriagePlace')
        )
        db.session.add(certificate)
        db.session.commit()
        return redirect(url_for('view_marriage_certificate', certificate_id=certificate_id))
    return render_template('marriage_form.html')

@app.route('/marriage-certificate/<certificate_id>')
@login_required
def view_marriage_certificate(certificate_id):
    certificate = MarriageCertificate.query.get(certificate_id)
    if not certificate:
        return "Certificate not found", 404
    return render_template('marriage_certificate.html', certificate=certificate)

# Celibacy Certificates
@app.route('/celibacy-certificates')
@login_required
def celibacy_certificates():
    return render_template('celibacy.html', certificates=CELIBACY_CERTIFICATES)

@app.route('/celibacy-certificate/create')
@login_required
def celibacy_certificate_form():
    return render_template('celibacy_form.html')

# Database reset route (admin only)
@app.route('/reset-database')
@admin_required
def reset_db_route():
    reset_database()
    return "Database reset complete. All data has been deleted and tables recreated."

if __name__ == '__main__':
    # Use environment variables for production settings
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)