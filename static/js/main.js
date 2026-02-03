document.addEventListener('DOMContentLoaded', () => {
    const getRecipesBtn = document.getElementById('get-recipes-btn');
    const restrictionInput = document.getElementById('restriction-input');
    const ingredientsInput = document.getElementById('ingredients-input');
    const resultsSection = document.getElementById('results-section');
    const loadingSpinner = document.getElementById('loading-spinner');

    // Validation Elements
    const warningModal = document.getElementById('warning-modal');
    const warningMessage = document.getElementById('warning-message');
    const closeModalBtn = document.getElementById('close-modal-btn');

    // Recipe Modal Elements
    const recipeModal = document.getElementById('recipe-modal');
    const closeRecipeModalBtn = document.getElementById('close-recipe-modal-btn');
    const modalRecipeTitle = document.getElementById('modal-recipe-title');
    const modalRecipeIngredients = document.getElementById('modal-recipe-ingredients');
    const modalRecipeInstructions = document.getElementById('modal-recipe-instructions');

    // Forbidden Ingredients Map
    const restrictionMap = {
        "Lactose Intolerant": ["milk", "cheese", "cream", "yogurt", "butter", "whey", "ghee", "casein"],
        "Gluten Free": ["wheat", "flour", "bread", "pasta", "barley", "rye", "soy sauce", "malt"],
        "Vegan": ["meat", "chicken", "beef", "pork", "egg", "milk", "cheese", "honey", "fish"],
        "Vegetarian": ["meat", "chicken", "beef", "pork", "fish", "tuna", "salmon"],
        "Nut Free": ["peanut", "almond", "walnut", "cashew", "pecan", "hazelnut", "nut"]
    };

    closeModalBtn.addEventListener('click', () => {
        warningModal.classList.add('hidden');
    });

    // Close modal on outside click (Warning Modal)
    warningModal.addEventListener('click', (e) => {
        if (e.target === warningModal) {
            warningModal.classList.add('hidden');
        }
    });

    // Close Recipe Modal
    const closeRecipeModal = () => {
        recipeModal.classList.add('hidden');
    };

    closeRecipeModalBtn.addEventListener('click', closeRecipeModal);

    recipeModal.addEventListener('click', (e) => {
        if (e.target === recipeModal) {
            closeRecipeModal();
        }
    });

    getRecipesBtn.addEventListener('click', async () => {
        // Validation
        const ingredientsVal = ingredientsInput.value.trim().toLowerCase();
        const restriction = restrictionInput.value;

        if (!ingredientsVal) {
            alert("Please enter at least one ingredient!");
            return;
        }

        // FEATURE: Validation for Restrictions
        if (restriction && restriction !== "None" && restrictionMap[restriction]) {
            const forbiddenItems = restrictionMap[restriction];
            // Check if any forbidden item is in the input string
            const foundConflicts = forbiddenItems.filter(item => ingredientsVal.includes(item));

            if (foundConflicts.length > 0) {
                warningMessage.innerHTML = `You have selected <strong>${restriction}</strong>, but your pantry contains: <br><br> <span style="color:#FF6B6B; font-weight:bold;">${foundConflicts.join(", ")}</span>. <br><br>Please remove these items to get safe recommendations.`;
                warningModal.classList.remove('hidden');
                return; // Stop execution
            }
        }

        // Show Loading
        loadingSpinner.classList.remove('hidden');
        resultsSection.innerHTML = ''; // Clear previous

        try {
            const response = await fetch('/api/recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ingredients: ingredientsInput.value.trim(),
                    restriction: restriction
                })
            });

            const data = await response.json();

            // Artificial delay to show off the fancy spinner (Optional 500ms)
            setTimeout(() => {
                displayResults(data.results);
                loadingSpinner.classList.add('hidden');
            }, 600);

        } catch (error) {
            console.error('Error:', error);
            alert("Something went wrong. Please try again.");
            loadingSpinner.classList.add('hidden');
        }
    });

    function displayResults(recipes) {
        if (!recipes || recipes.length === 0) {
            resultsSection.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 2rem;">
                    <h3>No matching recipes found 😕</h3>
                    <p>Try adding more ingredients or changing your restrictions.</p>
                </div>
            `;
            return;
        }

        recipes.forEach((recipe, index) => {
            const card = document.createElement('div');
            card.className = 'recipe-card';
            card.style.animationDelay = `${index * 100}ms`; // Stagger animation

            // Truncate instruction for preview
            const previewText = recipe.instructions.length > 100
                ? recipe.instructions.substring(0, 100) + '...'
                : recipe.instructions;

            // Truncate ingredients for preview
            const allIngredients = recipe.ingredients.split(',').map(i => i.trim());
            const previewIngredients = allIngredients.length > 6
                ? allIngredients.slice(0, 6).join(', ') + '...'
                : recipe.ingredients;

            card.innerHTML = `
                <div class="card-header">
                    <h3>${recipe.name}</h3>
                    <span class="match-score">${recipe.score} Ingredient Match${recipe.score > 1 ? 'es' : ''}</span>
                </div>
                <div class="card-body">
                    <h4>Ingredients Used</h4>
                    <p>${previewIngredients}</p>
                    
                    <h4>Instructions</h4>
                    <p>${previewText}</p>
                </div>
                <div class="card-footer">
                    <button class="read-more-btn">
                        Read More <ion-icon name="arrow-forward-outline"></ion-icon>
                    </button>
                </div>
            `;

            // Add click listener to the 'Read More' button
            const readMoreBtn = card.querySelector('.read-more-btn');
            readMoreBtn.addEventListener('click', () => {
                openRecipeModal(recipe);
            });

            resultsSection.appendChild(card);
        });
    }

    function openRecipeModal(recipe) {
        modalRecipeTitle.innerText = recipe.name;

        // Handle Ingredients: Split by comma if it's a string to make a list
        modalRecipeIngredients.innerHTML = '';
        const ingreds = recipe.ingredients.split(',').map(i => i.trim());
        ingreds.forEach(ing => {
            const li = document.createElement('li');
            li.textContent = ing;
            modalRecipeIngredients.appendChild(li);
        });

        // Handle Instructions
        modalRecipeInstructions.innerText = recipe.instructions;

        recipeModal.classList.remove('hidden');
    }
});
