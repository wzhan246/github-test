from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from datetime import datetime, time
from functools import wraps

# -------------------------
# HOLIDAY LIST (MM-DD format, for 2026)
# -------------------------
HOLIDAYS = {
    "01-01",  # 🎉 New Year's Day
    "01-19",  # 🕊️ Martin Luther King Jr. Day
    "07-03",  # 🇺🇸 Independence Day (observed)
    "09-07",  # 💪 Labor Day
    "12-25",  # 🎄 Christmas Day
}


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/group_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "testsecretkey"
db = SQLAlchemy(app)

# -------------------------
# LOGIN MANAGER
# -------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------
# RANDOM PRICE GENERATOR
# -------------------------
seed = 42
def random_float(min_value, max_value):
    global seed
    seed = (seed * 9301 + 49297) % 233280
    return round(min_value + (max_value - min_value) * (seed / 233280.0), 2)

# -------------------------
# MODELS
# -------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    role = db.Column(db.String(50), default="user", nullable=False)
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
    volume = db.Column(db.Integer, nullable=False)

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

class MarketHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    open_time = db.Column(db.Time, nullable=False)
    close_time = db.Column(db.Time, nullable=False)
    is_open = db.Column(db.Boolean, default=False)

class MarketSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Day toggles
    monday = db.Column(db.Boolean, default=True)
    tuesday = db.Column(db.Boolean, default=True)
    wednesday = db.Column(db.Boolean, default=True)
    thursday = db.Column(db.Boolean, default=True)
    friday = db.Column(db.Boolean, default=True)
    saturday = db.Column(db.Boolean, default=False)
    sunday = db.Column(db.Boolean, default=False)

    # Day-specific hours
    monday_open = db.Column(db.Time, default=time(9, 0))
    monday_close = db.Column(db.Time, default=time(16, 0))
    tuesday_open = db.Column(db.Time, default=time(9, 0))
    tuesday_close = db.Column(db.Time, default=time(16, 0))
    wednesday_open = db.Column(db.Time, default=time(9, 0))
    wednesday_close = db.Column(db.Time, default=time(16, 0))
    thursday_open = db.Column(db.Time, default=time(9, 0))
    thursday_close = db.Column(db.Time, default=time(16, 0))
    friday_open = db.Column(db.Time, default=time(9, 0))
    friday_close = db.Column(db.Time, default=time(16, 0))
    saturday_open = db.Column(db.Time, default=time(9, 0))
    saturday_close = db.Column(db.Time, default=time(16, 0))
    sunday_open = db.Column(db.Time, default=time(9, 0))
    sunday_close = db.Column(db.Time, default=time(16, 0))


# -------------------------
# HELPER: CHECK MARKET STATUS
# -------------------------
def is_market_open():
    market = MarketHours.query.first()
    schedule = MarketSchedule.query.first()
    if not schedule:
        return False

    now = datetime.now()
    current_time = now.time()
    weekday = now.strftime("%A").lower()
    today_str = now.strftime("%m-%d")

    if today_str in HOLIDAYS:
        return False
    if not getattr(schedule, weekday):
        return False

    open_time = getattr(schedule, f"{weekday}_open")
    close_time = getattr(schedule, f"{weekday}_close")

    return open_time <= current_time <= close_time


# -------------------------
# INITIALIZE DATABASE
# -------------------------
with app.app_context():
    db.create_all()
    if Stock.query.count() == 0:
        demo_stocks = [
            Stock(company_name="Apple Inc.", ticker="AAPL", initial_price=100.00, volume=500),
            Stock(company_name="Tesla Inc.", ticker="TSLA", initial_price=500.00, volume=560),
            Stock(company_name="Amazon.com Inc.", ticker="AMZN", initial_price=415.00, volume=5000),
            Stock(company_name="Microsoft Corp.", ticker="MSFT", initial_price=50.00, volume=1000),
            Stock(company_name="Google LLC", ticker="GOOGL", initial_price=1400.00, volume=164),
        ]
        db.session.add_all(demo_stocks)
        db.session.commit()

    if not MarketHours.query.first():
        market = MarketHours(open_time=time(9, 0), close_time=time(16, 0), is_open=False)
        db.session.add(market)
        db.session.commit()
        print("Default market hours: 9:00–16:00")

    if not MarketSchedule.query.first():
        schedule = MarketSchedule(
            monday=True, tuesday=True, wednesday=True,
            thursday=True, friday=True, saturday=False, sunday=False
        )
        db.session.add(schedule)
        db.session.commit()
        print("✅ Default market schedule: Mon–Fri open, Sat/Sun closed.")

# -------------------------
# ROLE CONTROL
# -------------------------
def role_required(role):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role != role:
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# -------------------------
# AUTH ROUTES
# -------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    message = None
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        full_name = request.form.get("full_name")
        password = request.form.get("password")

        hashed_password = generate_password_hash(password)
        existing = User.query.filter((User.username == username) | (User.email == email)).first()

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
            return redirect(url_for("login", message="User created successfully!"))
    return render_template("register.html", message=message)

@app.route("/login", methods=["GET", "POST"])
def login():
    message = request.args.get("message")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("portfolio"))
        else:
            message = "Invalid username or password"
    return render_template("login.html", message=message)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login", message="Logout successful!"))

# -------------------------
# USER ROUTES
# -------------------------
@app.route("/")
@login_required
def home():
    return render_template("home.html")

@app.route("/portfolio")
@login_required
def portfolio():
    user = current_user
    portfolio = Portfolio.query.filter_by(user_id=user.id).all()
    stocks = Stock.query.all()
    market_prices = {stock.id: random_float(1.0, 5000.0) for stock in stocks}
    return render_template("portfolio.html",
        portfolio=portfolio,
        user=user,
        market_prices=market_prices,
        message=request.args.get("message"),
        market_is_open=is_market_open(),
        market=MarketHours.query.first(),
        schedule=MarketSchedule.query.first(),
        cash_balance=user.cash_balance
    )

@app.route("/trade", methods=["GET", "POST"])
@login_required
def trade():
    user = current_user
    stocks = Stock.query.all()
    display_prices = {stock.id: random_float(1.0, 5000.0) for stock in stocks}
    portfolio = Portfolio.query.filter_by(user_id=user.id).all()
    message = request.args.get("message")

        # --- Get market info ---
    market = MarketHours.query.first()
    schedule = MarketSchedule.query.first()
    if not schedule:
        schedule = MarketSchedule(
            monday=True, tuesday=True, wednesday=True,
            thursday=True, friday=True, saturday=False, sunday=False
        )
        db.session.add(schedule)
        db.session.commit()

    now = datetime.now()
    today_str = now.strftime("%m-%d")
    weekday_name = now.strftime("%A")
    market_open = is_market_open()

    # --- Determine reason if closed ---
    closed_reason = None
    if today_str in HOLIDAYS:
        closed_reason = "Market closed today for a holiday."
    elif not getattr(schedule, weekday_name.lower(), False):
        closed_reason = f"Market closed today ({weekday_name})."
    elif market and not (market.open_time <= now.time() <= market.close_time):
        closed_reason = f"Market closed. Hours are {market.open_time.strftime('%I:%M %p')}–{market.close_time.strftime('%I:%M %p')}."
    else:
        closed_reason = "Market is currently closed."

    # --- Block trade if market closed ---
    if not market_open:
        return render_template(
            "trade.html",
            stocks=stocks,
            portfolio=portfolio,
            display_prices=display_prices,
            message=closed_reason or "Market is currently closed.",
            market_is_open=False,
            market=market,
            schedule=schedule,
            cash_balance=user.cash_balance
        )

    # --- Handle trade form submission ---
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
                    db.session.add(
                        Portfolio(user_id=user.id, stock_id=stock.id, quantity=qty, average_price=price)
                    )
                db.session.add(
                    Transaction(user_id=user.id, stock_id=stock.id, order_type="buy", quantity=qty, price=price)
                )
                db.session.commit()
                message = f"Bought {qty} shares of {stock.ticker} at ${price}"
            else:
                message = "Not enough balance."
        elif action == "sell":
            if existing and existing.quantity >= qty:
                existing.quantity -= qty
                user.cash_balance += price * qty
                if existing.quantity == 0:
                    db.session.delete(existing)
                db.session.add(
                    Transaction(user_id=user.id, stock_id=stock.id, order_type="sell", quantity=qty, price=price)
                )
                db.session.commit()
                message = f"Sold {qty} shares of {stock.ticker} at ${price}"
            else:
                message = "You don’t have enough shares."
        return redirect(url_for("trade", message=message))

    # --- Render trade page if market open ---
    return render_template(
        "trade.html",
        stocks=stocks,
        portfolio=portfolio,
        display_prices=display_prices,
        message=message,
        market_is_open=True,
        market=market,
        schedule=schedule,
        cash_balance=user.cash_balance
    )


@app.route("/order_history")
@login_required
def order_history():
    user = current_user
    transactions = Transaction.query.filter_by(user_id=user.id).all()
    return render_template("order_history.html", transactions=transactions)

# -------------------------
# ADMIN ROUTES
# -------------------------
@app.route("/admin")
@login_required
@role_required("admin")
def admin_dashboard():
    users = User.query.all()
    transactions = Transaction.query.order_by(Transaction.id.desc()).all()
    return render_template("admin_dashboard.html", users=users, transactions=transactions)

@app.route("/admin/users")
@login_required
@role_required("admin")
def admin_users():
    users = User.query.all()
    return render_template("admin_users.html", users=users)

@app.route("/admin/stocks")
@login_required
@role_required("admin")
def admin_stocks():
    stocks = Stock.query.all()
    return render_template("modify_stocks.html", stocks=stocks, message=request.args.get("message"))

@app.route("/admin/stocks/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_stock():
    message = None
    if request.method == "POST":
        company_name = request.form.get("company_name")
        ticker = request.form.get("ticker")
        initial_price = request.form.get("initial_price")
        volume = int(request.form['volume'])

        if not (company_name and ticker and initial_price):
            message = "All fields are required."
        elif Stock.query.filter_by(ticker=ticker.upper()).first():
            message = "Ticker already exists!"
        else:
            new_stock = Stock(
                company_name=company_name,
                ticker=ticker.upper(),
                initial_price=float(initial_price),
                volume=volume
            )
            db.session.add(new_stock)
            db.session.commit()
            message = "Stock added successfully!"
            return redirect(url_for("admin_stocks", message=message))
    return render_template("add_stock.html", message=message)

@app.route("/admin/stocks/edit/<int:stock_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    if request.method == "POST":
        stock.company_name = request.form.get("company_name")
        stock.ticker = request.form.get("ticker").upper()
        stock.initial_price = float(request.form.get("initial_price"))
        stock.volume = int(request.form.get("volume"))
        db.session.commit()
        return redirect(url_for("admin_stocks", message=f"Stock '{stock.ticker}' updated successfully!"))
    return render_template("edit_stock.html", stock=stock)

@app.route("/admin/stocks/delete/<int:stock_id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    db.session.delete(stock)
    db.session.commit()
    return redirect(url_for("admin_stocks", message=f"Stock '{stock.ticker}' deleted successfully!"))

@app.route("/admin/market-hours", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_market_hours():
    market = MarketHours.query.first()
    if request.method == "POST":
        market.open_time = datetime.strptime(request.form.get("open_time"), "%H:%M").time()
        market.close_time = datetime.strptime(request.form.get("close_time"), "%H:%M").time()
        market.is_open = request.form.get("is_open") == "on"
        db.session.commit()
        return redirect(url_for("admin_market_hours"))
    return render_template("market_hours.html", market=market)

@app.route("/admin/market-days", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_market_days():
    schedule = MarketSchedule.query.first()
    if not schedule:
        schedule = MarketSchedule()
        db.session.add(schedule)
        db.session.commit()

    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    if request.method == "POST":
        for day in days:
            setattr(schedule, day, request.form.get(day) == "on")
            open_field = f"{day}_open"
            close_field = f"{day}_close"
            setattr(schedule, open_field, datetime.strptime(request.form.get(open_field), "%H:%M").time())
            setattr(schedule, close_field, datetime.strptime(request.form.get(close_field), "%H:%M").time())

        db.session.commit()
        return redirect(url_for("admin_market_days"))

    return render_template("market_days.html", schedule=schedule)


# -------------------------# MISC ROUTES

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        pass
    return render_template("contact.html")

@app.route("/cash_balance", methods=["GET", "POST"])
@login_required
def cash_balance():
    user = current_user
    message = None

    if request.method == "POST":
        action = request.form.get("action")
        amount = float(request.form.get("amount", 0))

        if amount <= 0:
            message = "❌ Please enter a positive amount."
        else:
            if action == "deposit":
                user.cash_balance += amount
                message = f"✅ Deposited ${amount:.2f} successfully!"
            elif action == "cashout":
                if user.cash_balance >= amount:
                    user.cash_balance -= amount
                    message = f"💵 Cashed out ${amount:.2f} successfully!"
                else:
                    message = "❌ Insufficient funds for cash out."

            db.session.commit()

    return render_template("cash_balance.html", user=user, message=message)


# -------------------------
# MAIN ENTRY POINT****
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)