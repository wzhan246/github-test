from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/group_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
    id = db.Column(db.Integer, primary_key=True)
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
    order_type = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

# Create tables
with app.app_context():
    db.create_all()
    stock1 = Stock(id=1, company_name="Apple Inc.", ticker="AAPL", initial_price=100.00)
    stock2 = Stock(id=2, company_name="Tesla Inc.", ticker="TSLA", initial_price=500.00)
    stock3 = Stock(id=3, company_name="Amazon.com Inc.", ticker="AMZN", initial_price=415.00)
    stock4 = Stock(id=4, company_name="Microsoft Corp.", ticker="MSFT", initial_price=50.00)
    stock5 = Stock(id=5, company_name="Google LLC", ticker="GOOGL", initial_price=1400.00)
    db.session.add_all([stock1, stock2, stock3, stock4, stock5])
    db.session.commit()


@app.route("/")
def home():
    return render_template("home.html")

@app.route("/portfolio")
def portfolio():
    return render_template("portfolio.html")

@app.route("/trade", methods=["GET", "POST"])
def trade():
    if request.method == "POST":
        pass
    return render_template("trade.html")

@app.route("/order_history")
def order_history():
    return render_template("order_history.html")

if __name__ == "__main__":
    app.run(debug=True)



