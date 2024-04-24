from flask import Flask, render_template, request, redirect, url_for , jsonify , session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime , timedelta
import random 
from werkzeug.utils import secure_filename
import os
import secrets
from flask_login import current_user
from flask_login import login_required
from sqlalchemy import Date

app = Flask(__name__ , static_url_path='/static')
app.secret_key = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'uploads'  # Configure the upload folder
db = SQLAlchemy(app)

@app.template_filter('string_to_datetime')
def string_to_datetime(s):
    return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')

class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)
    
    # Define the one-to-many relationship with Book
    books = db.relationship('Book', backref='section', lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)
    issue_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    poster = db.Column(db.String(200))  # Assuming poster link will be stored as string
    price = db.Column(db.Float)
    # Add a column to store PDF files
    pdf_file = db.Column(db.String(100))  # Assuming PDF will be stored as binary data
    
    
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    
class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    # name = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    # confirm_password = db.Column(db.String(120), nullable=False)
    
class UserBookAccess(db.Model):
    # __tablename__ = 'user_book_access'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    access_type = db.Column(db.String(50), nullable=False)  # Define the type of access (e.g., read, write, etc.)
    days = db.Column(db.Integer, nullable=False)  # Number of days the access is granted for
    book_name = db.Column(db.String(100))  # Add column for book name
    user_name = db.Column(db.String(80))   # Add column for user name
    # request_date = db.Column(db.DateTime, nullable=False , default=datetime.utcnow)  # Column for request date
    request_date = db.Column(Date, nullable=False, default=datetime.utcnow)
    # Define the relationship with User and Book tables
    user = db.relationship('User', backref=db.backref('book_access', cascade='all, delete-orphan'))
    book = db.relationship('Book', backref=db.backref('user_access', cascade='all, delete-orphan'))


@app.route("/")
def hello():
    return render_template("index.html")


@app.route("/collections/<int:user_id>")
def Collection(user_id):
    allSections = Section.query.all()
    random_colors = ['#'+('%06x' % random.randint(0,256**3-1)) for _ in range(len(allSections))]
    
    active_user = User.query.get(user_id)
    
    if active_user:
        # Save the user ID in the session for future use
        session['user_id'] = user_id
        session['username'] = active_user.username
        return render_template("collection.html", alltodo=allSections, random_colors=random_colors, active_user=active_user , username=active_user.username)
    else:
        return "User not found", 404

@app.route("/admin")
def admin():
    BookCount = Book.query.count()
    sectionCOunt = Section.query.count()
    allSections = Section.query.all()
    return render_template("admin.html"  , alltodo = allSections , sectionCOunt=sectionCOunt , BookCount=BookCount)

@app.route('/login')
def user():
    return render_template('login.html')

@app.route('/user_authentication', methods=['POST'])
def user_authentication():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            # return redirect('/collections')
            return redirect(f'/collections/{user.user_id}')
        else:
            message = "Invalid username or password. Please try again."
            return render_template('login.html', message=message)
 
@app.route('/user_register', methods=['GET','POST'])
def user_register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            message = "Username already exists. Please choose another username."
            return render_template('user_register.html', message=message)
  
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        message = "Registration successful. You can now log in."
        return render_template('user_register.html', message=message)

    return render_template('user_register.html')   
  
@app.route('/admin_login')
def manager():
    return render_template('admin_login.html')

VALID_USERNAME='manager'
VALID_PASSWORD='123'

@app.route('/admin_authentication', methods=['POST'])
def admin_authentication():
    username = request.form.get('username')
    password = request.form.get('password')

    if username==VALID_USERNAME and password == VALID_PASSWORD:
        return redirect('/admin')
    else:
        message = "Please check your credentials."
        return render_template('admin_login.html', message=message)


@app.route('/search_books' , methods = ["GET"])
def search_books():
    search_query = request.args.get('search_query')
    
    books = Book.query.all()
    user_id = request.args.get('user_id')
    username = request.args.get('username')
    
    if search_query:
        books = Book.query.filter(
            (Book.name.ilike(f'%{search_query}%')) | (Book.author.ilike(f'%{search_query}%'))
        ).all()

    return render_template('search.html', books=books, search_query=search_query ,  current_user=user_id, username=username)      

@app.route('/search_section' , methods = ["GET"])
def search_section():
    search_query = request.args.get('search_query')
    
    section = Section.query.all()
    
    if search_query:
        section = Section.query.filter(
            (Section.name.ilike(f'%{search_query}%')) 
        ).all()

    return render_template('search_section.html', section=section, search_query=search_query)   

@app.route('/search_user_section', methods=["GET"])
def search_user_section():
    search_query = request.args.get('search_query')
    
    sections = []
    if search_query:
        # Search for sections based on the provided search query
        sections = Section.query.filter(
            Section.name.ilike(f'%{search_query}%')
        ).all()

    active_user = None
    if 'user_id' in session:
        user_id = session['user_id']
        active_user = User.query.get(user_id)

    random_colors = ['#'+('%06x' % random.randint(0,256**3-1)) for _ in range(len(sections))]

    return render_template('collection.html', alltodo=sections, random_colors=random_colors, active_user=active_user , username=active_user.username if active_user else None)    

@app.route("/add_section", methods=["GET", "POST"])
def add_section():
    if request.method == "POST":
        
        name = request.form["sectionName"]
        description = request.form["sectionDescription"]
        
        new_section = Section(
            name=name, 
            description=description
            )
        db.session.add(new_section)
        db.session.commit()
        
        allSections = Section.query.all()
        
        print("New section added successfully:", new_section)  # Debugging statement
        return redirect(url_for('admin'))
   
    return render_template("add_section.html" )

@app.route("/update_section/<int:id>" , methods=["GET" , "POST"])
def update_section(id):
    if(request.method == "POST"):
        name = request.form["sectionName"]
        description = request.form["sectionDescription"]
        
        section_to_update = Section.query.get(id)
        
        section_to_update.name = name
        section_to_update.description = description
        
        db.session.add(section_to_update)
        db.session.commit()
        return redirect(url_for('admin'))
    
    section_to_update = Section.query.get(id)
    print(section_to_update.id)
    return render_template("update_section.html" , section_to_update=section_to_update)

@app.route("/add_books")
def add_books():
    allSections = Section.query.all()
    return render_template("add_books.html" , alltodo = allSections)
    
@app.route("/delete_section/<int:id>")
def delete_section(id):
    section_to_delete = Section.query.get(id)
    print("printing section that is deleted:", section_to_delete)
    try:
        Book.query.filter_by(section_id=id).delete()
        db.session.delete(section_to_delete)
        db.session.commit()
        return redirect(url_for("admin"))
    except Exception as e:
        print("Error deleting section:", e)
        return "Error deleting section"
    
@app.route("/adding_books/<int:id>")
def adding_books(id):
    section_id = id
    return render_template("books_registering.html" , section_id = section_id )

@app.route("/update_boook/<int:id>" , methods = ["GET" , "POST"])
def update_book(id):
    if request.method == "POST":
        name = request.form["name"]
        content = request.form["content"]
        author = request.form["author"]
        issue_date_str = request.form["issue_date"]
        issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d")
        poster = request.form["poster"]
        price = request.form["price"]
        book_to_update = Book.query.get(id)
        
        book_to_update.name = name
        book_to_update.content = content
        book_to_update.author = author
        book_to_update.issue_date = issue_date
        book_to_update.poster = poster
        book_to_update.price = price
        
        
        db.session.add(book_to_update)
        db.session.commit()
        return redirect(url_for('exploring_books', id=book_to_update.section_id))        
        
    book_to_update = Book.query.get(id)
    print(book_to_update.name)
    return render_template("update_book.html" , book_to_update = book_to_update)


@app.route("/exploreBooks/<int:id>")
# @login_required
def exploring_books(id):
    print(id)
    # allBooks = Book.query.all()
    # allBooks = Book.query.filter_by(id=section_id).all()
    user_id = request.args.get('user_id')
    username = request.args.get('username')
    allBooks = Book.query.filter_by(section_id=id).all()
    print(allBooks)
    return render_template("explorebook.html" , allBooks = allBooks , current_user=user_id , username=username)

@app.route("/add_registring_books", methods=["POST"])
def add_registring_books():
    if request.method == "POST":
        section_id = request.form["section_id"]
        section = Section.query.get(section_id)
        
        if section:
            name = request.form["name"]
            content = request.form["content"]
            author = request.form["author"]
            issue_date_str = request.form["issue_date"]
            issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d")
            poster = request.form["poster"]
            price = request.form["price"]
           

            new_book = Book(
                name=name,
                content=content,
                author=author,
                issue_date=issue_date,
                poster=poster,
                price = price,
                # pdf_filename=pdf_filename,
                section=section,
                pdf_file = "static\pdf_folder\python certificate.pdf"
            )
            
            db.session.add(new_book)
            db.session.commit()
            
            allBooks = Book.query.all()
            # print(allBooks[-1].section_id)
            return redirect(url_for("delete_books" , id = allBooks[-1].section_id ))
        else:
            return "Invalid Section"
        
@app.route("/pdf_viewer", methods=['GET'])
def pdf():
 
    return render_template("pdf_viwer.html")

@app.route("/delete_books/<int:id>")
def delete_books(id):
    allBooks = Book.query.filter_by(section_id=id).all()
    print(allBooks)
    return render_template("remove_book.html" , allBooks = allBooks)

@app.route("/delte_boook/<int:id>/<int:sid>")
def delted(id,sid):
    allBooks = Book.query.filter_by(section_id=id).all()

    book_to_delete = Book.query.get(id)
    try:
        
        db.session.delete(book_to_delete)
        db.session.commit()
        return redirect(url_for("delete_books" ,  id = sid) )

    except Exception as e:
        print("Error deleting book:", e)
        return "Error deleting book"
    

@app.route("/requestAccess")
def RequestAccess():
    requestAccess = UserBookAccess.query.all()
    return render_template("RequestAcess.html" , requestAccess=requestAccess)


@app.route("/user_dashboard/<int:user_id>")
def user_dashboard(user_id):
    user = User.query.get(user_id)
    if user:
        requestAccess = UserBookAccess.query.filter_by(user_id=user_id).all()
        
        for book in requestAccess:
            book.return_date = book.request_date + timedelta(days=book.days)

        return render_template("user_dashboard.html", user=user , requestAccess=requestAccess , timedelta=timedelta)
    else:
        return "User not found", 404

    
@app.route("/payment" )
def payment():
    # if request.method == "POST":
        
    return render_template("payment.html")


@app.route('/request_access', methods=['POST'])
def request_access():
    if request.method == 'POST':
        # Get data from the request
        user_id = request.json.get('user_id')
        book_id = request.json.get('book_id')
        access_type = request.json.get('access_type')  # You can modify this as needed
        days = request.json.get('days')
        book_name = request.json.get('bookName')  # New column
        user_name = request.json.get('username')  # New column
        # Check if all required data is provided
        
        user_access_count = UserBookAccess.query.filter_by(user_id=user_id).count()
        if user_access_count >= 5:
            return jsonify({'message': 'You have already accessed the maximum number of books'}), 400
        
        user_access = UserBookAccess.query.filter_by(user_id=user_id, book_id=book_id).first()
        if user_access:
            print("myuser has already accessed ",user_access)
        # User has already accessed the book, show access denied page with message
            return jsonify({'message': 'Book already requested'}), 400    
        
        if not book_id or not days or not access_type:
            return jsonify({'message': 'Missing data'}), 400

        # Create a new UserBookAccess instance
        user_book_access = UserBookAccess(
            user_id=user_id,
            book_id=book_id,
            access_type=access_type,
            days=days,
            book_name=book_name,
            user_name=user_name
        )

        # Add the instance to the session and commit changes to the database
        db.session.add(user_book_access)
        db.session.commit()
        
        requestAccess = UserBookAccess.query.all()

        return jsonify({'message': 'Access requested successfully'}), 200


@app.route('/update_access', methods=['POST'])
def update_access():
    if request.method == 'POST':
        # Get data from the request
        book_id = request.json.get('book_id')
        user_id = request.json.get('user_id')  # Add user_id parameter
        access_type = request.json.get('access_type')

        # Update the access_type in the database for the specified book and user
        user_book_access = UserBookAccess.query.filter_by(book_id=book_id, user_id=user_id).first()
        if user_book_access:
            user_book_access.access_type = access_type
            db.session.commit()
            return jsonify({'message': 'Access updated successfully'}), 200
        else:
            return jsonify({'message': 'Book not found for the user'}), 404


@app.route('/revoke_access', methods=['POST'])
def revoke_access():
    if request.method == 'POST':
        # Get data from the request
        book_id = request.json.get('book_id')
        user_id = request.json.get('user_id')  # Add user_id parameter
        access_type = request.json.get('access_type')
        # Check if the book_id is provided
        # if not book_id:
        #     return jsonify({'message': 'Missing book ID'}), 400

        # Find the requested access in the database
        user_book_access = UserBookAccess.query.filter_by(book_id=book_id, user_id=user_id).first()
        if user_book_access:
            user_book_access.access_type = access_type
            db.session.commit()
            return jsonify({'message': 'Denied updated successfully'}), 200
        else:
            return jsonify({'message': 'Book not found for the user'}), 404

def has_access(user_id, book_id):
    print("inside has_access")
    user_access = UserBookAccess.query.filter_by(user_id=user_id, book_id=book_id, access_type='accepted').first()
    print("after useracces")
    print(user_access)
    if user_access:
        print("Inside if")
        # Convert user_access.request_date to datetime object
        request_date = datetime.combine(user_access.request_date, datetime.min.time())
        # Calculate the expiration date based on the access start date and number of days
        expiration_date = request_date + timedelta(days=user_access.days)
        print("checking")
        # Check if the current date is before the expiration date
        if datetime.utcnow() < expiration_date:
            print("condition chl pyi")
            return True
    return False



@app.route('/view_book/<int:book_id>/<int:user_id>', methods=['GET'])
def view_book(book_id, user_id):
    # Fetch the book object from the database
    book = Book.query.get(book_id)
    
    if has_access(user_id, book_id):
        return render_template('view_book.html', book=book)
    else:
            # Access denied page
        return render_template('access_denied.html', message="You do not have access to view this book.")


# Route to download the book (disabled for users with limited access)

@app.route('/download_book/<int:book_id>', methods=['GET'])
def download_book(book_id):
    # Check if the user has access to the book
    if has_access(current_user.id, book_id):
        # Download the book (code to download the book)
        return send_file('path_to_pdf_file', as_attachment=True)
    else:
        # Access denied page
        return render_template('access_denied.html')

              
if __name__ == "__main__":
    app.run(debug=True)
