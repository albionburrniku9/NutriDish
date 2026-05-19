from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone

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

class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    user = db.relationship('User', backref='password_reset_tokens', lazy=True)

    def is_valid(self):
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return self.used_at is None and expires_at > datetime.now(timezone.utc)
