import requests
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import difflib
import os
import random

class RecipeRecommender:
    def __init__(self, data_file='recipes.csv'):
        self.use_api = True
        self.data_file = data_file
        self.df = None
        self.vectorizer = None
        self.tfidf_matrix = None
        self.all_ingredients = []
        
        # Try to load local dataset
        if os.path.exists(self.data_file):
            try:
                print(f"Loading local dataset: {self.data_file}...")
                self.df = pd.read_csv(self.data_file)
                self._prepare_local_data()
                self.use_api = False
                print("✓ Local NLP Engine Loaded Successfully")
            except Exception as e:
                print(f"⚠ Error loading CSV: {e}. Falling back to API.")
                self.use_api = True
        else:
            print("⚠ 'recipes.csv' not found. Using Web API fallback.")

        # API Setup (Backup)
        self.api_base = "https://www.themealdb.com/api/json/v1/1/"

    def _prepare_local_data(self):
        """
        Prepares the dataframe for NLP tasks.
        """
        # 1. Clean Column Names
        self.df.columns = self.df.columns.str.strip().str.lower()
        
        # 2. Ensure vital columns exist (Mapping common dataset variations)
        # The specific dataset usually has 'Name', 'Ingredients', 'Instructions' (or 'Method')
        col_map = {
            'recipe_name': 'name',
            'receipe_name': 'name', # Common typo in dataset
            'ingredients': 'ingredients',
            'prep_time': 'prep_time',
            'cook_time': 'cook_time',
            'total_time': 'total_time',
            'servings': 'servings',
            'directions': 'instructions',
            'method': 'instructions'
        }
        self.df = self.df.rename(columns=col_map)
        
        # Drop rows with missing values in key columns
        self.df = self.df.dropna(subset=['name', 'ingredients', 'instructions'])
        
        # 3. Create a 'combined_features' column for TF-IDF
        # We process ingredients to remove quantities for better matching (simple heuristic)
        self.df['clean_ingredients'] = self.df['ingredients'].apply(lambda x: x.lower().replace(',', ' '))
        
        # 4. Initialize TF-IDF Vectorizer
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df['clean_ingredients'])
        
        # 5. Extract all unique words for simple spell checking
        self.all_ingredients = list(self.vectorizer.vocabulary_.keys())

    def _correct_typos(self, user_input):
        """
        Uses fuzzy matching to correct typos in user input based on known ingredients.
        e.g., 'meet' -> 'meat', 'chiken' -> 'chicken'
        """
        tokens = user_input.lower().replace(',', ' ').split()
        corrected_tokens = []
        
        for token in tokens:
            # Find closest match in our vocabulary
            matches = difflib.get_close_matches(token, self.all_ingredients, n=1, cutoff=0.8)
            if matches:
                corrected_tokens.append(matches[0])
            else:
                # If no close match, keep original (it might be a new word)
                corrected_tokens.append(token)
                
        return " ".join(corrected_tokens)

    def recommend(self, ingredients_input, restriction):
        if self.use_api:
            return self._recommend_api(ingredients_input, restriction)
        else:
            return self._recommend_local(ingredients_input, restriction)

    # ==========================
    # LOCAL NLP LOGIC
    # ==========================
    def _recommend_local(self, ingredients_input, restriction):
        print(f"Processing (Local): {ingredients_input} | Restriction: {restriction}")
        
        # 1. Correct Typos
        clean_input = self._correct_typos(ingredients_input)
        print(f"Corrected Input: {clean_input}")
        
        # 2. Transform input
        user_vector = self.vectorizer.transform([clean_input])
        
        # 3. Calculate Similarity (Content-Based Filtering)
        similarity_scores = cosine_similarity(user_vector, self.tfidf_matrix).flatten()
        
        # 4. Get Top Candidates (Top 50)
        # We get more than we need so we can filter by restriction
        top_indices = similarity_scores.argsort()[::-1][:100]
        
        recommendations = []
        
        # Definition of Forbidden Keywords
        avoid_keywords = self._get_restriction_keywords(restriction)
        
        for idx in top_indices:
            score = similarity_scores[idx]
            if score < 0.1: # Threshold to ignoring totally irrelevant stuff
                continue
                
            row = self.df.iloc[idx]
            ing_text = str(row['ingredients']).lower()
            
            # 5. Apply Restriction Filter
            is_safe = True
            if avoid_keywords:
                for bad_word in avoid_keywords:
                    # Simple substring match - generally effective
                    if bad_word in ing_text:
                        is_safe = False
                        break
            
            if is_safe:
                recommendations.append({
                    "name": row['name'].title(),
                    "ingredients": row['ingredients'],
                    "instructions": row['instructions'],
                    "score": f"{int(score * 100)}% Match"
                })
                
            if len(recommendations) >= 9:
                break
                
        return recommendations

    # ==========================
    # API FALLBACK LOGIC
    # ==========================
    def _recommend_api(self, ingredients_input, restriction):
        # Extract main ingredient (simple split)
        if not ingredients_input:
            return []
            
        # Manual Typo Map for API Mode (Mapping user terms to TheMealDB specific ingredients)
        typo_map = {
            "meet": "beef",
            "meat": "beef",
            "stake": "beef",
            "steak": "beef",
            "chiken": "chicken",
            "chikn": "chicken",
            "potoato": "potato",
            "tomatoe": "tomato",
            "egs": "eggs",
            "egg": "eggs",
            "milkk": "milk"
        }
            
        # Take the first ingredient as the primary search term
        raw_main = ingredients_input.split(',')[0].strip().lower()
        main_ingredient = typo_map.get(raw_main, raw_main)
        
        # 1. Fetch Candidates
        candidates = self._get_recipes_by_ingredient_api(main_ingredient)
        
        # If no results for first ingredient, try second if exists
        if not candidates and ',' in ingredients_input:
             second_ingredient = ingredients_input.split(',')[1].strip().lower()
             candidates = self._get_recipes_by_ingredient_api(second_ingredient)

        if not candidates:
            return []

        random.shuffle(candidates)
        candidates = candidates[:8]
        
        final_recipes = []
        avoid_keywords = self._get_restriction_keywords(restriction)

        # 2. Get Details & Filter
        for meal in candidates:
            details = self._get_recipe_details_api(meal['idMeal'])
            if not details:
                continue
                
            meal_ingredients = []
            for i in range(1, 21):
                ing = details.get(f'strIngredient{i}')
                if ing and ing.strip():
                    meal_ingredients.append(ing.lower())
            
            # Check restriction
            is_safe = True
            for bad_word in avoid_keywords:
                for ing in meal_ingredients:
                    if bad_word in ing:
                        is_safe = False
                        break
                if not is_safe:
                    break
            
            if is_safe:
                all_ingredients_list = [i.title() for i in meal_ingredients]
                ingredients_str = ", ".join(all_ingredients_list)
                    
                final_recipes.append({
                    "name": details['strMeal'],
                    "ingredients": ingredients_str,
                    "instructions": details['strInstructions'],
                    "score": "Web Match"
                })
        
        return final_recipes

    def _get_restriction_keywords(self, restriction):
        if restriction == "Lactose Intolerant":
            return ['milk', 'cream', 'cheese', 'butter', 'yogurt', 'ghee', 'casein', 'whey']
        elif restriction == "Gluten Free":
            return ['flour', 'bread', 'wheat', 'pasta', 'barley', 'rye', 'soy sauce', 'malt']
        elif restriction == "Vegan":
            return ['chicken', 'beef', 'pork', 'lamb', 'egg', 'cheese', 'milk', 'butter', 'cream', 'honey', 'fish', 'salmon', 'tuna', 'gelatin']
        elif restriction == "Vegetarian":
            return ['chicken', 'beef', 'pork', 'lamb', 'fish', 'tuna', 'salmon', 'bacon', 'ham']
        elif restriction == "Nut Free":
            return ['nut', 'almond', 'cashew', 'pecan', 'walnut', 'peanut']
        return []

    def _get_recipes_by_ingredient_api(self, ingredient):
        try:
            url = f"{self.api_base}filter.php?i={ingredient}"
            response = requests.get(url)
            data = response.json()
            return data.get('meals') or []
        except:
            return []

    def _get_recipe_details_api(self, id_meal):
        try:
            url = f"{self.api_base}lookup.php?i={id_meal}"
            response = requests.get(url)
            data = response.json()
            return data.get('meals')[0] if data.get('meals') else None
        except:
            return None
