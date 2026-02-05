from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for
from ai_engine import RecipeRecommender
from translations import translations

app = Flask(__name__)
recommender = RecipeRecommender()

@app.context_processor
def inject_conf_var():
    # Detect language from cookie, default to 'en'
    lang = request.cookies.get('lang', 'en')
    if lang not in translations:
        lang = 'en'
    return dict(t=translations[lang], lang=lang)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/set_lang/<lang_code>')
def set_language(lang_code):
    if lang_code not in translations:
        lang_code = 'en'
    # KEY FIX: Redirect to home so the next request picks up the NEW cookie
    resp = make_response(redirect(url_for('home')))
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
