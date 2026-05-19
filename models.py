from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_pro = db.Column(db.Boolean, default=False)
    generations_used = db.Column(db.Integer, default=0)
    profile_image = db.Column(db.Text, nullable=True)
    saved_recipes = db.relationship('SavedRecipe', backref='user', lazy=True)
    dietary_profile = db.relationship('DietaryProfile', backref='user', uselist=False, lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class DietaryProfile(db.Model):
    __tablename__ = "dietary_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    allergies = db.Column(db.String(200), nullable=True) # Comma separated
    diet_type = db.Column(db.String(50), nullable=True) # e.g., Vegan, Keto
    calorie_goal = db.Column(db.Integer, nullable=True)

class SavedRecipe(db.Model):
    __tablename__ = "saved_recipes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipe_name = db.Column(db.String(200), nullable=False)
    recipe_ingredients = db.Column(db.Text, nullable=True)
    recipe_instructions = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.Text, nullable=True)
