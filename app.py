from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from translations import translations
from models import db, User, SavedRecipe
import os
import re

app = Flask(__name__)
# Config
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-this')

database_url = os.getenv('DATABASE_URL') or os.getenv('LOCAL_DATABASE_URL') or 'sqlite:///nutridish_v2.db'
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Init extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

recommender = None

def get_recommender():
    global recommender
    if recommender is None:
        from ai_engine import RecipeRecommender
        recommender = RecipeRecommender()
    return recommender

if os.getenv('AUTO_CREATE_TABLES') == '1':
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

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/api/health/db')
def db_health():
    try:
        from sqlalchemy import inspect, text

        with db.engine.connect() as connection:
            connection.execute(text('SELECT 1'))

        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        required_tables = {'users', 'saved_recipes', 'dietary_profiles'}
        missing_tables = sorted(required_tables - tables)

        return jsonify({
            'success': not missing_tables,
            'database_connected': True,
            'missing_tables': missing_tables
        }), 200 if not missing_tables else 503
    except Exception as e:
        print(f"DB Health Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'database_connected': False,
            'message': str(e.__class__.__name__)
        }), 500

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
        # Safe fallback redirect if submitted normally by older cached browsers
        return redirect(url_for('signup'))
    return render_template('signup.html')

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Payload jo valid."}), 400
            
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({
                "success": False, 
                "message": "Ju lutem plotësoni të gjitha fushat."
            }), 400
            
        # Support login with either username or email
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User.query.filter_by(email=username).first()
            
        if user and user.check_password(password):
            login_user(user)
            return jsonify({
                "success": True,
                "message": "Hyrja u krye me sukses."
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Të dhënat e hyrjes janë të pasakta."
            }), 401
    except Exception as e:
        print(f"Login API Error: {e}")
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "Diçka shkoi keq. Provo përsëri."
        }), 500

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Invalid JSON payload."
            }), 400
            
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        phone_number = data.get('phone_number', '').strip()

        errors = {}

        # First name required
        if not first_name:
            errors['first_name'] = "Emri është i detyrueshëm."
            
        # Last name required
        if not last_name:
            errors['last_name'] = "Mbiemri është i detyrueshëm."

        # Username required & minimum 3 characters
        if not username:
            errors['username'] = "Përdoruesi është i detyrueshëm."
        elif len(username) < 3:
            errors['username'] = "Përdoruesi duhet të ketë të paktën 3 karaktere."

        # Email required & valid format
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not email:
            errors['email'] = "Email është i detyrueshëm."
        elif not re.match(email_regex, email):
            errors['email'] = "Email nuk është valid."

        # Password required, 8-20 chars, letter + number
        if not password:
            errors['password'] = "Fjalëkalimi është i detyrueshëm."
        elif len(password) < 8 or len(password) > 20:
            errors['password'] = "Fjalëkalimi duhet të ketë 8–20 karaktere."
        elif not re.search(r'[a-zA-Z]', password) or not re.search(r'[0-9]', password):
            errors['password'] = "Fjalëkalimi duhet të përmbajë të paktën një shkronjë dhe një numër."

        # Confirm password match
        if confirm_password != password:
            errors['confirm_password'] = "Fjalëkalimet nuk përputhen."

        # Phone optional but validate if provided
        if phone_number:
            if not re.match(r'^[0-9+ ]+$', phone_number):
                errors['phone_number'] = "Numri i telefonit nuk është valid."

        if errors:
            return jsonify({
                "success": False,
                "message": "Please fix the validation errors.",
                "errors": errors
            }), 400

        # Check duplicate user/email
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            return jsonify({
                "success": False,
                "message": "Ky email ose përdorues ekziston tashmë."
            }), 409

        # Create user
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

        return jsonify({
            "success": True,
            "message": "Llogaria u krijua me sukses."
        }), 201

    except Exception as e:
        print(f"Signup API Error: {e}")
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "Diçka shkoi keq. Provo përsëri."
        }), 500

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

@app.route('/saved')
@login_required
def saved():
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
            'id': r.id,
            'image': r.image_url
        })
    
    print(f"DEBUG: Before translation - {len(recipes)} recipes")
        
    # Translate if needed
    if lang != 'en' and recipes:
        print(f"DEBUG: Translating to {lang}...")
        try:
            recipes = get_recommender()._translate_results(recipes, lang)
            print(f"DEBUG: Translation complete")
        except Exception as e:
            print(f"Profile Translation Error: {e}")
            import traceback
            traceback.print_exc()
            
    return render_template('saved_recipes.html', recipes=recipes)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/api/update_profile_image', methods=['POST'])
@login_required
def update_profile_image():
    try:
        data = request.json
        image_data = data.get('image')
        
        # If image_data is empty string or None, we set to None (remove image)
        if not image_data:
            current_user.profile_image = None
        else:
            current_user.profile_image = image_data
            
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error updating profile image: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/save_recipe', methods=['POST'])
@login_required
def save_recipe():
    from deep_translator import GoogleTranslator
    
    data = request.json
    name = data.get('name')
    ingredients = data.get('ingredients')
    instructions = data.get('instructions')
    image_url = data.get('image')
    
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
    
    # Check limit BEFORE checking if already saved (optional, but good practice)
    if not current_user.is_pro:
        saved_count = SavedRecipe.query.filter_by(user_id=current_user.id).count()
        if saved_count >= 3:
            return jsonify({'status': 'error', 'message': 'limit_reached', 'detail': 'You can only save up to 3 recipes on the free plan.'})

    # Check if already saved
    existing = SavedRecipe.query.filter_by(user_id=current_user.id, recipe_name=name).first()
    if existing:
        return jsonify({'status': 'exists', 'message': 'Recipe already saved'})
        
    new_save = SavedRecipe(
        user_id=current_user.id,
        recipe_name=name,
        recipe_ingredients=ingredients,
        recipe_instructions=instructions,
        image_url=image_url
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
        # Enforce Login
        if not current_user.is_authenticated:
            return jsonify({'status': 'error', 'message': 'login_required'}), 403
            
        # Optional: We could limit generations, but requirements state limits on SAVING recipes.
        # Removing generation limit to allow users to freely search/generate.
        # if not current_user.is_pro and current_user.generations_used >= 3:
        #     return jsonify({'status': 'error', 'message': 'limit_reached'}), 403
            
        data = request.json
        ingredients = data.get('ingredients', '')
        restriction = data.get('restriction', '')
        
        # Get language from cookie to help with translation
        lang = request.cookies.get('lang', 'en')
        
        result = get_recommender().recommend(ingredients, restriction, lang=lang)
        
        # Increment usage if successful
        if result.get('status') == 'success':
            current_user.generations_used += 1
            db.session.commit()
            
        return jsonify(result)
    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

import stripe

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_1234567890') # Replace with actual test key
DOMAIN = 'http://localhost:5000' # Update based on environment

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': 900, # $9.00
                        'product_data': {
                            'name': 'NutriDish Pro Unlimited',
                            'description': 'Unlock unlimited recipe saves forever.',
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=DOMAIN + '/upgrade?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=DOMAIN + '/upgrade',
            client_reference_id=str(current_user.id)
        )
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 403

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '') # Set your webhook secret
    
    event = None
    
    try:
        if endpoint_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        else:
            # Fallback for dev if no secret configured
            import json
            event = json.loads(payload)
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400
        
    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('client_reference_id')
        if user_id:
            user = User.query.get(int(user_id))
            if user:
                user.is_pro = True
                db.session.commit()
                print(f"User {user.username} upgraded to Pro via Webhook!")

    return 'Success', 200

@app.route('/upgrade', methods=['GET', 'POST'])
@login_required
def upgrade():
    # If returned from Stripe checkout with success
    session_id = request.args.get('session_id')
    if session_id:
        current_user.is_pro = True
        db.session.commit()
        flash(get_t().get('flash_upgraded', 'Successfully upgraded to Pro!'))
        return redirect(url_for('profile'))
        
    return render_template('upgrade.html')

@app.route('/react')
def react_app():
    return render_template('react_app.html')

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG') == '1')
