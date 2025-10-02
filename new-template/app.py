from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

#test

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/group_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.secret_key = "testsecretkey"

# MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    cash_balance = db.Column(db.Float, default=0.0)
    portfolios = db.relationship('Portfolio', backref='owner', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_name = db.Column(db.String(100), nullable=False)
    ticker = db.Column(db.String(10), unique=True, nullable=False)
    initial_price = db.Column(db.Float, nullable=False)
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

# Routes
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    message = None
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        full_name = request.form.get("full_name")
        password = request.form.get("password")
        existing = User.query.filter((User.username==username)|(User.email==email)).first()
        if existing:
            message = "User already exists!"
        else:
            new_user = User(
                username=username,
                email=email,
                full_name=full_name,
                password=password,
                cash_balance=15000.00
            )
            db.session.add(new_user)
            db.session.commit()
            message = "User created successfully!"
            return redirect(url_for("login", message=message))
    return render_template("register.html", message=message)

@app.route("/login", methods=["GET", "POST"])
def login():
    message = request.args.get("message")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["user_id"] = user.id
            return redirect(url_for("portfolio", message="Login successful!"))
        else:
            message = "Invalid username or password"
    return render_template("login.html", message=message)

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login", message="Logout successful!"))

@app.route("/portfolio")
def portfolio():
    message = request.args.get("message")
    user = User.query.get(session.get("user_id"))
    portfolio = Portfolio.query.filter_by(user_id=user.id).all() if user else []
    return render_template("portfolio.html", message=message, portfolio=portfolio)

@app.route("/trade", methods=["GET", "POST"])
def trade():
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect(url_for("login", message="Please log in first."))

    stocks = Stock.query.all()
    portfolio = Portfolio.query.filter_by(user_id=user.id).all()
    message = None

    if request.method == "POST":
        action = request.form.get("action")
        stock_id = int(request.form.get("stock_id"))
        qty = int(request.form.get("quantity"))
        stock = Stock.query.get(stock_id)
        existing = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()

        if action == "buy":
            cost = stock.initial_price * qty
            if user.cash_balance >= cost:
                user.cash_balance -= cost
                if existing:
                    existing.quantity += qty
                else:
                    db.session.add(Portfolio(user_id=user.id, stock_id=stock.id, quantity=qty, average_price=stock.initial_price))
                db.session.add(Transaction(user_id=user.id, stock_id=stock.id, order_type="buy", quantity=qty, price=stock.initial_price))
                db.session.commit()
                message = f"Bought {qty} shares of {stock.ticker}"
            else:
                message = "Not enough cash to buy."

        elif action == "sell":
            if existing and existing.quantity >= qty:
                existing.quantity -= qty
                user.cash_balance += stock.initial_price * qty
                if existing.quantity == 0:
                    db.session.delete(existing)
                db.session.add(Transaction(user_id=user.id, stock_id=stock.id, order_type="sell", quantity=qty, price=stock.initial_price))
                db.session.commit()
                message = f"Sold {qty} shares of {stock.ticker}"
            else:
                message = "Not enough shares to sell."

        return redirect(url_for("trade", message=message))

    return render_template("trade.html", stocks=stocks, portfolio=portfolio, message=request.args.get("message"))

@app.route("/order_history")
def order_history():
    user = User.query.get(session.get("user_id"))
    transactions = Transaction.query.filter_by(user_id=user.id).all() if user else []
    return render_template("order_history.html", transactions=transactions)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        pass
    return render_template("contact.html")

if __name__ == "__main__":
    app.run(debug=True)