
from flask import Flask, session, render_template, jsonify, request, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests


app = Flask(__name__)


# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine("postgres://nwxnjdwochgocs:83ebb2ae24471f7872b0b2213e81e590187bffe71a7fccf2b7b8e62ae638207a@ec2-34-232-147-86.compute-1.amazonaws.com:5432/d6f019qvcptvf7")
db = scoped_session(sessionmaker(bind=engine))

# Redirecting
@app.route("/")
def index():
    return redirect(url_for('login'))

# Login
@app.route("/login", methods=["POST", "GET"])
def login():
    message = ""
    disableBackground = False

    if checkLogin(False) == False:
        return redirect(url_for('home'))

    if request.form.get("command") == "LOGIN":
        username = request.form.get("username")
        password = request.form.get("password")

        users = db.execute("SELECT * FROM customers WHERE password=:password AND username=:username", {"password": password, "username": username}).fetchall()

        if len(users) == 0:
            message = "Incorrect password or username, try again."
        else:
            session["isLoggedIn"] = True
            session["loggedInUser"] = users[0]
            return redirect(url_for('home'))
         
    return render_template("index.html", disableBackground=disableBackground, message=message)

# Dashboard
@app.route("/home")
def home():

    # disable background
    disableBackground = True

    # Check the site is protected or not
    if checkLogin(True) == False:
        return redirect(url_for('login'))
   
   # Check the session is avaliable or not

    loggedInUser = session.get("loggedInUser")

    # Disable background 
    disableBackground = True
    return render_template("home.html", disableBackground=disableBackground, loggedInUser=loggedInUser)



# Signup
@app.route("/signup", methods=["POST", "GET"])
def signup():

    # Check the site is protected or not

    if checkLogin(False) == False:
        return redirect(url_for('home'))

    # Message var
    message=""

    # Disable the normal background
    disableBackground = True

    # Taking infos from input fields
    if request.form.get("sCommand") == "SIGN UP":
        password = request.form.get('signupPassword')
        username = request.form.get('signupUsername')
        email = request.form.get('signupEmail')

        trackUser = db.execute("SELECT * FROM customers WHERE username=:username AND password=:password", {"username":username, "password":password}).rowcount

        if trackUser > 0:
            message = "You already have an account!"
        else:
            createUser = db.execute("INSERT INTO customers (username, password, email) VALUES (:username, :password, :email)", {"username":username, "password": password, "email":email})
            db.commit()
            message = "You have been registered."
            return redirect(url_for('login'))
            
    return render_template("signup.html", message=message ,disableBackground=disableBackground,)

# Logout
@app.route("/logout")
def logout():

    # Check wether the site is protected or not

    if checkLogin(True) == False:
        return redirect(url_for('home'))

    session["isLoggedIn"] = None
    session["loggedInUser"]=None
    return redirect(url_for('login'))


# Search for Books
@app.route("/search", methods=["POST", "GET"])
def search():

    # Check the site is protected or not
    if checkLogin(True) == False:
        return redirect(url_for("login"))

    # disable the normal background
    disableBackground = True
    # Get the session to display on navbar
    loggedInUser = session.get("loggedInUser")

    # Initialize var searchResult
    searchResult = [] 

    # Take the value of input fields, and seperate them by categories (ISBN, author, title, year)
    # Is not case-sensitive (WITH ILIKE KEYWOARD)

    if request.form.get("searchBy") == "ISBN":
        if request.form.get("command") == "Search":
            getIsbn = request.form.get("bookDetail")
            searchResult = db.execute("SELECT * FROM bookdetails WHERE isbn ILIKE :isbn", {"isbn":'%'+getIsbn+'%'}).fetchall()

    if request.form.get("searchBy") == "Author":
        if request.form.get("command") == "Search":
            getAuthor = request.form.get("bookDetail")
            searchResult = db.execute("SELECT * FROM bookdetails WHERE author ILIKE :author", {"author": ('%'+getAuthor+'%')}).fetchall()

    if request.form.get("searchBy") == "Title":
        if request.form.get("command") == "Search":
            getName = request.form.get("bookDetail")
            searchResult = db.execute("SELECT * FROM bookdetails WHERE title ILIKE :title", {"title":('%'+getName+'%')}).fetchall()

    if request.form.get("searchBy") == "Year":
        if request.form.get("command") == "Search":
            getYear = request.form.get("bookDetail")
            searchResult = db.execute("SELECT * FROM bookdetails WHERE year LIKE :year", {"year":'%'+getYear+'%'}).fetchall()

    return render_template("search.html", disableBackground=disableBackground, loggedInUser=loggedInUser, searchResult=searchResult)



# Book page
@app.route("/book_detail/<int:book_id>", methods=["POST", "GET"])
def bookpage(book_id):

    # Check the page is protected
    if checkLogin(True) == False:
        return redirect(url_for("login"))

    # session name and message for error and navbar
    loggedInUser = session.get("loggedInUser")
    message="Book couldn't found. Check the id of the book."

    # Make sure the book id exists
    checkBooks = db.execute("SELECT * FROM bookdetails WHERE id = :id", {"id":book_id}).fetchone()
    
    storeInfo = []
    # if it is not:
    if checkBooks is None:
        return render_template("error.html", message=message)
    else:
        # Select all the information about that particular id that a book has
        books = db.execute("SELECT * FROM bookdetails WHERE id = :id", {"id": book_id}).fetchall()

        # Getting the reviews from Goodreads with API
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "qHVOaMnw8ecYJUs6wONWDA", "isbns": books[0][1]})

        if res.status_code != 200:
            raise Exception("ERROR: API request unsuccessful.")
        else:
            data = res.json()
            rate = data["books"]
            countRatings = rate[0]['work_ratings_count']
            averageRating = rate[0]['average_rating']
                
        # Check if a user has commented more than once:
        checkTwiceReview = db.execute("SELECT customer_id FROM reviews WHERE customer_id = :customer_id AND books_id = :books_id", {"customer_id":loggedInUser[0], "books_id": book_id}).rowcount

        # Neccessary if statement for checking
        if checkTwiceReview > 0:
            message = "A user cannot make more than one reviews."
        else:
            # If a user has submitted a review:
            if request.form.get("command") == "submit_review":
                reviewText = request.form.get("reviewDetail")
                rating = request.form.get("reviewBy")
                reviewResult = db.execute("INSERT INTO reviews (review, rating, customer_id, books_id) VALUES (:review, :rating, :customer_id, :books_id)", {"review": reviewText, "rating":rating, "customer_id":loggedInUser[0], "books_id": books[0][0]})
                db.commit()
                message="Your review has been submitted!"
        # storeReviews = db.execute("SELECT review FROM reviews WHERE books_id = :books_id", {"books_id":book_id}).fetchall()
        # storeRatings = db.execute("SELECT rating FROM reviews WHERE books_id = :books_id", {"books_id": book_id}).fetchall()

        storeInfo = db.execute("SELECT * FROM reviews INNER JOIN customers ON reviews.customer_id=customers.id WHERE books_id = :book_id", {"book_id": book_id}).fetchall()


        # Allow normal background
        disableBackground = False

        return render_template("books.html", books=books, message=message, loggedInUser=loggedInUser, disableBackground=disableBackground, countRatings=countRatings, averageRating=averageRating, storeInfo=storeInfo) 


@app.route("/api/<isbn_number>", methods=["GET"])
def api(isbn_number):

    # Background disable
    disableBackground = True

    # Check the page is protected
    if checkLogin(True) == False:
        return redirect(url_for("login"))

    # Make sure the isbn exists:
    checkIsbn = db.execute("SELECT * FROM bookdetails WHERE isbn=:isbn", {"isbn":isbn_number}).fetchone()

    # if it is not:
    if checkIsbn is None:
        return jsonify({"Error":"invalid ISBN number"}), 404
    else:
        # Get all of the information that a particular book has with ISBN
        allInfo = db.execute("SELECT * FROM bookdetails WHERE isbn=:isbn", {"isbn": str(isbn_number)}).fetchall()

        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "qHVOaMnw8ecYJUs6wONWDA", "isbns": allInfo[0][1]})
        data = res.json()
        rate = data["books"]
        numberRatings = rate[0]['work_ratings_count']
        averageRatings = rate[0]['average_rating']


        return jsonify({
            "title": allInfo[0][2],
            "author": allInfo[0][3],
            "year": allInfo[0][4],
            "isbn": allInfo[0][1],
            "review_count": numberRatings,
            "average_score": averageRatings,
        })




# Check if user has been logged in
def checkLogin(isProtected):
    if isProtected == True:
        isLoggedIn = session.get("isLoggedIn")
        if isLoggedIn is None:
            return False
    else:
        isLoggedIn = session.get("isLoggedIn")
        if isLoggedIn is not None:
            return False



