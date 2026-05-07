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
            alert(window.langData.val_empty);
            return;
        }

        // --- Client side generic check removed, relying on Server API for detailed conflict check ---

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

            setTimeout(() => {
                loadingSpinner.classList.add('hidden');

                if (data.status === 'conflict') {
                    // SERVER DETECTED CONFLICT

                    // 1. Get the Localized Name of the restriction (from the UI dropdown)
                    const restrictionSelect = document.getElementById('restriction-input');
                    const selectedText = restrictionSelect.options[restrictionSelect.selectedIndex].text;

                    // 2. Use format string replacement
                    let msg = window.langData.val_conflict_msg
                        .replace('{0}', selectedText)
                        .replace('{1}', data.conflict_item); // Item returned by server (now translated)

                    warningMessage.innerHTML = msg;
                    warningModal.classList.remove('hidden');
                } else if (data.status === 'ok') {
                    // SUCCESS
                    displayResults(data.data);
                } else if (data.status === 'error') {
                    if (data.message === 'login_required') {
                        alert(window.langData.err_login_required || "You must be logged in.");
                        window.location.href = '/login';
                    } else if (data.message === 'limit_reached') {
                        warningMessage.innerHTML = (window.langData.err_limit_reached || "Limit reached.") + '<br><br><a href="/upgrade" class="glow-button" style="text-decoration:none; display:inline-block; margin-top:10px;">' + (window.langData.btn_upgrade || "Upgrade") + '</a>';
                        warningModal.classList.remove('hidden');
                    } else {
                        alert(data.message);
                    }
                } else {
                    // Error or unknown state
                    console.error("Unknown Server Status:", data);
                    alert(window.langData.err_generic);
                }
            }, 600);

        } catch (error) {
            console.error('Error:', error);
            alert(window.langData.err_generic);
            loadingSpinner.classList.add('hidden');
        }
    });

    function displayResults(recipes) {
        if (!recipes || recipes.length === 0) {
            resultsSection.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 2rem;">
                    <h3>${window.langData.msg_no_recipes}</h3>
                    <p>${window.langData.msg_try_adjust}</p>
                </div>
            `;
            return;
        }

        recipes.forEach((recipe, index) => {
            const card = document.createElement('div');
            card.className = 'recipe-card';
            card.style.animationDelay = `${index * 100}ms`;

            // Generate Safety Badges based on restrictions
            const restriction = document.getElementById('restriction-input').value;
            let badgesHTML = '';
            
            if (restriction === 'Lactose Intolerant') {
                badgesHTML += `<span class="safety-badge no-lactose"><ion-icon name="water-outline"></ion-icon> No Lactose</span>`;
            }
            if (restriction === 'Gluten Free') {
                badgesHTML += `<span class="safety-badge no-gluten"><ion-icon name="shield-checkmark-outline"></ion-icon> Gluten Free</span>`;
            }
            if (restriction === 'Vegan') {
                badgesHTML += `<span class="safety-badge vegan"><ion-icon name="leaf-outline"></ion-icon> Vegan</span>`;
            }
            if (restriction === 'Nut Free') {
                badgesHTML += `<span class="safety-badge no-soy"><ion-icon name="alert-circle-outline"></ion-icon> Nut Free</span>`;
            }

            // Generate description from instructions
            let descriptionPreview = recipe.instructions.split('.')[0] + '.';
            if(descriptionPreview.length < 20 && recipe.instructions.split('.').length > 1) {
                descriptionPreview += ' ' + recipe.instructions.split('.')[1] + '.';
            }
            if(descriptionPreview.length > 120) {
                descriptionPreview = descriptionPreview.substring(0, 120) + '...';
            }

            // Fallback image if API doesn't provide one
            const recipeImage = recipe.image || 'https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&q=80&w=800';

            card.style.display = 'flex';
            card.style.flexDirection = 'column';

            card.innerHTML = `
                <div style="position: relative;">
                    <img src="${recipeImage}" alt="${recipe.name}" style="width: 100%; height: 220px; object-fit: cover; display: block;">
                    <div style="position: absolute; top: 10px; right: 10px; background: var(--card-bg); width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <ion-icon name="restaurant-outline" style="color: var(--sage-green); font-size: 1.2rem;"></ion-icon>
                    </div>
                </div>
                <div class="card-body" style="padding: 1.5rem; flex: 1; display: flex; flex-direction: column;">
                    <h3 style="font-family: var(--font-heading); font-size: 1.3rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.5rem; line-height: 1.3;">${recipe.name}</h3>
                    <p style="color: #9ca3af; line-height: 1.5; font-size: 0.95rem; margin-bottom: 1rem; flex: 1;">${descriptionPreview}</p>
                    
                    ${badgesHTML ? `<div class="safety-badges" style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.5rem;">${badgesHTML}</div>` : ''}
                    
                    <div class="card-footer" style="display: flex; flex-direction: column; gap: 0.75rem; margin-top: auto;">
                        <button class="read-more-btn" style="width: 100%; padding: 0.75rem; background: var(--sage-green); color: white; border: none; border-radius: 8px; font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: background 0.2s; display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                            Read More <ion-icon name="arrow-forward-outline"></ion-icon>
                        </button>
                        <button class="grocery-list-btn" data-ingredients="${recipe.ingredients}" style="width: 100%; padding: 0.75rem; background: transparent; color: var(--text-primary); border: 1px solid var(--glass-border); border-radius: 8px; font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                            Grocery List <ion-icon name="cart-outline"></ion-icon>
                        </button>
                    </div>
                </div>
            `;

            // Add click listener to the 'Read More' button
            const readMoreBtn = card.querySelector('.read-more-btn');
            readMoreBtn.addEventListener('click', () => {
                openRecipeModal(recipe);
            });

            // Add grocery list functionality
            const groceryBtn = card.querySelector('.grocery-list-btn');
            groceryBtn.addEventListener('click', (e) => {
                const ingredients = e.currentTarget.dataset.ingredients;
                exportGroceryList(ingredients);
            });

            resultsSection.appendChild(card);
        });
    }

    let currentGroceryIngredients = '';

    // Grocery List Export - Digital Receipt Style inside App
    function exportGroceryList(ingredients) {
        currentGroceryIngredients = ingredients;
        const ingredientList = ingredients.split(',').map(i => i.trim());
        
        const listItemsContainer = document.getElementById('grocery-list-items');
        if(!listItemsContainer) return;
        
        listItemsContainer.innerHTML = '';
        
        ingredientList.forEach(ing => {
            const li = document.createElement('li');
            li.style.cssText = 'padding: 0.75rem 0; border-bottom: 1px dashed rgba(255,255,255,0.1); color: #e5e7eb; display: flex; align-items: center; gap: 10px;';
            li.innerHTML = `<input type="checkbox" style="accent-color: #8FA98B; width: 18px; height: 18px;"> <span>${ing}</span>`;
            listItemsContainer.appendChild(li);
        });

        const groceryModal = document.getElementById('grocery-modal');
        if(groceryModal) {
            groceryModal.classList.remove('hidden');
        }
    }

    // Share & Download Buttons Logic
    const shareBtn = document.getElementById('share-grocery-btn');
    const downloadBtn = document.getElementById('download-grocery-btn');

    if(shareBtn) {
        shareBtn.addEventListener('click', async () => {
            const textToShare = "🛒 Grocery List from NutriDish AI:\n\n" + currentGroceryIngredients.split(',').map(i => "- " + i.trim()).join('\n');
            if (navigator.share) {
                try {
                    await navigator.share({
                        title: 'NutriDish Grocery List',
                        text: textToShare,
                    });
                } catch (err) {
                    console.log('Error sharing:', err);
                }
            } else {
                // Fallback to clipboard
                navigator.clipboard.writeText(textToShare).then(() => {
                    alert('Grocery list copied to clipboard!');
                });
            }
        });
    }

    if(downloadBtn) {
        downloadBtn.addEventListener('click', () => {
            const textToSave = "🛒 Grocery List from NutriDish AI:\n\n" + currentGroceryIngredients.split(',').map(i => "- " + i.trim()).join('\n');
            const blob = new Blob([textToSave], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'nutridish-grocery-list.txt';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    }

    let currentRecipeData = null; // Track currently viewed recipe
    const saveRecipeBtn = document.getElementById('save-recipe-btn');

    function openRecipeModal(recipe) {
        currentRecipeData = recipe; // Store for saving

        modalRecipeTitle.innerText = recipe.name;
        
        // ETM Layout Updates
        const modalBreadcrumb = document.getElementById('modal-breadcrumb-name');
        if(modalBreadcrumb) modalBreadcrumb.innerText = recipe.name;
        
        const modalImage = document.getElementById('modal-recipe-image');
        if(modalImage) {
            modalImage.src = recipe.image || 'https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&q=80&w=800';
            modalImage.alt = recipe.name;
        }

        // Reset Save Button State
        const saveIcon = saveRecipeBtn.querySelector('ion-icon');
        saveIcon.setAttribute('name', 'bookmark-outline');
        saveRecipeBtn.style.transform = 'scale(1)';

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

    // Save Button Logic
    if (saveRecipeBtn) {
        saveRecipeBtn.addEventListener('click', async () => {
            if (!window.userLoggedIn) {
                // Not logged in -> Redirect logic
                window.location.href = '/login';
                return;
            }

            if (!currentRecipeData) return;

            // Animate
            const saveIcon = saveRecipeBtn.querySelector('ion-icon');
            saveIcon.setAttribute('name', 'bookmark'); // Fill
            saveRecipeBtn.style.transform = 'scale(1.2)';
            setTimeout(() => saveRecipeBtn.style.transform = 'scale(1)', 200);

            try {
                const response = await fetch('/api/save_recipe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: currentRecipeData.name,
                        ingredients: currentRecipeData.ingredients,
                        instructions: currentRecipeData.instructions,
                        image: currentRecipeData.image
                    })
                });

                const data = await response.json();
                if (data.status === 'success') {
                    // Saved!
                } else if (data.status === 'exists') {
                    // Already saved
                }
            } catch (e) {
                console.error("Save failed:", e);
                // Revert icon if failed?
                saveIcon.setAttribute('name', 'bookmark-outline');
            }
        });
    }
});
