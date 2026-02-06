from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from ai_engine import RecipeRecommender
from translations import translations
from models import db, User, SavedRecipe
import os

app = Flask(__name__)
# Config
app.config['SECRET_KEY'] = 'your-secret-key-change-this' # Simple secret key for MVP
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nutridish_v2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Init extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

recommender = RecipeRecommender()

# Create DB
with app.app_context():
    db.create_all()

def get_t():
    lang = request.cookies.get('lang', 'en')
    return translations.get(lang, translations['en'])

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_conf_var():
    # Detect language from cookie, default to 'en'
    lang = request.cookies.get('lang', 'en')
    if lang not in translations:
        lang = 'en'
    return dict(t=translations[lang], lang=lang, user=current_user)

@app.route('/')
def home():
    return render_template('index.html')

# --- AUTH ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash(get_t().get('flash_invalid_cred'))
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        
        # Validation
        if not first_name.isalpha() or not last_name.isalpha():
            flash(get_t().get('flash_name_alpha'))
            return render_template('signup.html')
            
        if len(password) < 8 or len(password) > 20:
             flash(get_t().get('flash_pass_len'))
             return render_template('signup.html')

        if User.query.filter_by(username=username).first():
            flash(get_t().get('flash_user_exist'))
        elif User.query.filter_by(email=email).first():
            flash(get_t().get('flash_email_exist'))
        else:
            new_user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('home'))
            
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate current password
    if not current_user.check_password(current_password):
        flash(get_t().get('flash_pass_wrong'))
        return redirect(url_for('profile'))
    
    # Check if new passwords match
    if new_password != confirm_password:
        flash(get_t().get('flash_pass_mismatch'))
        return redirect(url_for('profile'))
    
    # Validate password length
    if len(new_password) < 8 or len(new_password) > 20:
        flash(get_t().get('flash_pass_len'))
        return redirect(url_for('profile'))
    
    # Update password
    current_user.set_password(new_password)
    db.session.commit()
    flash(get_t().get('flash_pass_changed'))
    return redirect(url_for('profile'))

@app.route('/profile')
@login_required
def profile():
    saved_refs = current_user.saved_recipes
    
    # Check language
    lang = request.cookies.get('lang', 'en')
    if lang not in translations:
        lang = 'en'
    
    print(f"DEBUG: Profile - Language is '{lang}', saved recipes count: {len(saved_refs)}")
    
    # Prepare recipes list
    recipes = []
    for r in saved_refs:
        recipes.append({
            'name': r.recipe_name,
            'ingredients': r.recipe_ingredients,
            'instructions': r.recipe_instructions,
            'id': r.id
        })
    
    print(f"DEBUG: Before translation - {len(recipes)} recipes")
        
    # Translate if needed
    if lang != 'en' and recipes:
        print(f"DEBUG: Translating to {lang}...")
        try:
            recipes = recommender._translate_results(recipes, lang)
            print(f"DEBUG: Translation complete")
        except Exception as e:
            print(f"Profile Translation Error: {e}")
            import traceback
            traceback.print_exc()
            
    return render_template('profile.html', recipes=recipes)

@app.route('/api/save_recipe', methods=['POST'])
@login_required
def save_recipe():
    from deep_translator import GoogleTranslator
    
    data = request.json
    name = data.get('name')
    ingredients = data.get('ingredients')
    instructions = data.get('instructions')
    
    # Get current language
    lang = request.cookies.get('lang', 'en')
    
    # If not English, translate back to English before saving
    if lang != 'en':
        try:
            translator = GoogleTranslator(source=lang, target='en')
            name = translator.translate(name)
            ingredients = translator.translate(ingredients)
            instructions = translator.translate(instructions[:4500])
        except Exception as e:
            print(f"Error translating to English before save: {e}")
    
    # Check if already saved
    existing = SavedRecipe.query.filter_by(user_id=current_user.id, recipe_name=name).first()
    if existing:
        return jsonify({'status': 'exists', 'message': 'Recipe already saved'})
        
    new_save = SavedRecipe(
        user_id=current_user.id,
        recipe_name=name,
        recipe_ingredients=ingredients,
        recipe_instructions=instructions
    )
    db.session.add(new_save)
    db.session.commit()
    
    return jsonify({'status': 'success'})

@app.route('/set_lang/<lang_code>')
def set_language(lang_code):
    if lang_code not in translations:
        lang_code = 'en'
    # Redirect to referrer or home
    resp = make_response(redirect(request.referrer or url_for('home')))
    resp.set_cookie('lang', lang_code, max_age=30*24*60*60) # 30 days
    return resp

@app.route('/api/recommend', methods=['POST'])
def recommend():
    try:
        data = request.json
        ingredients = data.get('ingredients', '')
        restriction = data.get('restriction', '')
        
        # Get language from cookie to help with translation
        lang = request.cookies.get('lang', 'en')
        
        result = recommender.recommend(ingredients, restriction, lang=lang)
        
        return jsonify(result)
    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
