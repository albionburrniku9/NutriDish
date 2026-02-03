from flask import Flask, render_template, request, jsonify
from ai_engine import RecipeRecommender

app = Flask(__name__)
recommender = RecipeRecommender()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.json
    ingredients = data.get('ingredients', '')
    restriction = data.get('restriction', '')
    
    recommendations = recommender.recommend(ingredients, restriction)
    
    return jsonify({'results': recommendations})

if __name__ == '__main__':
    app.run(debug=True)
