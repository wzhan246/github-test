from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/group_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.secret_key = "testsecretkey"

# login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Simple random float generator for stock prices
seed = 42
def random_float(min_value, max_value):
    global seed
    seed = (seed * 9301 + 49297) % 233280
    return round(min_value + (max_value - min_value) * (seed / 233280.0), 2)

# MODELS
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    role = db.Column(db.String(50), default="user", nullable=False)  # "user" or "admin"
    cash_balance = db.Column(db.Float, default=0.0)
    portfolios = db.relationship('Portfolio', backref='owner', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_name = db.Column(db.String(100), nullable=False)
    ticker = db.Column(db.String(10), unique=True, nullable=False)
    initial_price = db.Column(db.Float, nullable=False)  # static price in DB
    portfolios = db.relationship('Portfolio', backref='stock', lazy=True)
    transactions = db.relationship('Transaction', backref='stock', lazy=True)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    average_price = db.Column(db.Float, nullable=False, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    order_type = db.Column(db.String(10), nullable=False)  # "buy" or "sell"
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

# Initialize DB
with app.app_context():
    db.create_all()
    if Stock.query.count() == 0:
        demo_stocks = [
            Stock(company_name="Apple Inc.", ticker="AAPL", initial_price=100.00),
            Stock(company_name="Tesla Inc.", ticker="TSLA", initial_price=500.00),
            Stock(company_name="Amazon.com Inc.", ticker="AMZN", initial_price=415.00),
            Stock(company_name="Microsoft Corp.", ticker="MSFT", initial_price=50.00),
            Stock(company_name="Google LLC", ticker="GOOGL", initial_price=1400.00),
        ]
        db.session.add_all(demo_stocks)
        db.session.commit()
with app.app_context():
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            password=generate_password_hash("admin123"),
            full_name="Administrator",
            email="admin@example.com",
            role="admin",
            cash_balance=15000.00
        )
        db.session.add(admin)
        db.session.commit()


# ROLE-BASED ACCESS CONTROL DECORATOR
def role_required(role):
    def decorator(f):
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role != role:
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ROUTES
@app.route("/register", methods=["GET", "POST"])
def register():
    message = None
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        full_name = request.form.get("full_name")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password)
        existing = User.query.filter((User.username==username)|(User.email==email)).first()
        if existing:
            message = "User already exists!"
        else:
            new_user = User(
                username=username,
                email=email,
                full_name=full_name,
                password=hashed_password,
                cash_balance=15000.00
            )
            db.session.add(new_user)
            db.session.commit()
            message = "User created successfully!"
            return redirect(url_for("login", message=message))
    return render_template("register.html", message=message)

@app.route("/")
@login_required # Restricts access to authenticated users only
def home():
    return render_template("home.html")

# update login with flask-login function.
@app.route("/login", methods=["GET", "POST"])
def login():
    message = request.args.get("message")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            # Before update: session["user_id"] = user.id
            login_user(user)  # Use Flask-Login to log in the user
            return redirect(url_for("portfolio", message="Login successful!"))
        else:
            message = "Invalid username or password"
    return render_template("login.html", message=message)

@app.route("/logout")
@login_required # Use Flask-Login to ensure user is logged in
def logout():
    logout_user()  # Use Flask-Login to log out the user
    return redirect(url_for("login", message="Logout successful!"))

@app.route("/portfolio")
@login_required # update to use Flask-Login
def portfolio():
    #user_id = session.get("user_id")
    #if not user_id:
        #return redirect(url_for("login", message="Please log in first."))
    #user = User.query.get(user_id)
    #if not user:
       # session.pop("user_id", None)
        #return redirect(url_for("login", message="User not found. Please log in again."))
   
    user = current_user  # Use Flask-Login to get the current user
    portfolio = Portfolio.query.filter_by(user_id=user.id).all()
    stocks = Stock.query.all()
    market_prices = {stock.id: random_float(1.0, 5000.0) for stock in stocks}
    return render_template(
        "portfolio.html",
        message=request.args.get("message"),
        portfolio=portfolio,
        user=user,
        market_prices=market_prices
    )

@app.route("/trade", methods=["GET", "POST"])
@login_required # update to use Flask-Login 
def trade():
    #user = User.query.get(session.get("user_id"))
    #if not user:
        #return redirect(url_for("login", message="Please log in first."))
    
    user = current_user  # Use Flask-Login to get the current user  
    stocks = Stock.query.all()
    display_prices = {stock.id: random_float(1.0, 5000.0) for stock in stocks}
    portfolio = Portfolio.query.filter_by(user_id=user.id).all()
    message = request.args.get("message")

    if request.method == "POST":
        action = request.form.get("action")
        stock_id = int(request.form.get("stock_id"))
        qty = int(request.form.get("quantity"))
        stock = Stock.query.get(stock_id)
        price = display_prices[stock.id]
        existing = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()

        if action == "buy":
            cost = price * qty
            if user.cash_balance >= cost:
                user.cash_balance -= cost
                if existing:
                    total_cost = existing.average_price * existing.quantity + price * qty
                    existing.quantity += qty
                    existing.average_price = total_cost / existing.quantity
                else:
                    db.session.add(Portfolio(user_id=user.id, stock_id=stock.id, quantity=qty, average_price=price))
                db.session.add(Transaction(user_id=user.id, stock_id=stock.id, order_type="buy", quantity=qty, price=price))
                db.session.commit()
                message = f"Bought {qty} shares of {stock.ticker} at ${price}"

        elif action == "sell":
            if existing and existing.quantity >= qty:
                existing.quantity -= qty
                user.cash_balance += price * qty
                if existing.quantity == 0:
                    db.session.delete(existing)
                db.session.add(Transaction(user_id=user.id, stock_id=stock.id, order_type="sell", quantity=qty, price=price))
                db.session.commit()
                message = f"Sold {qty} shares of {stock.ticker} at ${price}"

        return redirect(url_for("trade", message=message))

    return render_template("trade.html", stocks=stocks, portfolio=portfolio, display_prices=display_prices, message=message)

@app.route("/order_history")
@login_required # update to use Flask-Login 
def order_history():
    #user = User.query.get(session.get("user_id"))
    user = current_user  # Use Flask-Login to get the current user
    transactions = Transaction.query.filter_by(user_id=user.id).all() if user else []
    return render_template("order_history.html", transactions=transactions)

@app.route("/admin") # admin dashboard
@login_required
@role_required("admin")
def admin_dashboard():
    users = User.query.all()
    stocks = Stock.query.all()
    return render_template("admin_dashboard.html", users=users)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        pass
    return render_template("contact.html")

if __name__ == "__main__":
    app.run(debug=True)
