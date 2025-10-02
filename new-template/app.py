from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/group_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)
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


#Initialize DB
with app.app_context():
    db.create_all()

    # If empty
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

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        return redirect(url_for("portfolio", message="Login successful!"))
    message = request.args.get("message")
    return render_template("login.html", message=message)

@app.route("/logout")
def logout():
    return redirect(url_for("login", message="Logout successful!"))

@app.route("/portfolio")
def portfolio():
    message = request.args.get("message")
    return render_template("portfolio.html", message=message)

@app.route("/trade", methods=["GET", "POST"])
def trade():
    stocks = Stock.query.all()
    portfolio = []
    if request.method == "POST":
        action = request.form.get("action")
        stock_id = request.form.get("stock_id")
        qty = request.form.get("quantity")
    return render_template("trade.html", stocks=stocks, portfolio=portfolio)

@app.route("/order_history")
def order_history():
    return render_template("order_history.html")

if __name__ == "__main__":
    app.run(debug=True)
