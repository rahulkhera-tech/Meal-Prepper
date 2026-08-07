# Meal Prepper

A lightweight, mobile-friendly weekly meal planner designed to make choosing meals and building a grocery list quick and simple.

Meal suggestions are based on **RecipeTin Eats**, prioritising meals that are easy to cook, suitable for weeknights, and generally take less than an hour.

## Features

### Weekly Meal Suggestions

Browse a curated selection of meals for the week, including:

* Chicken
* Pork
* Fish
* Lamb
* Vegetarian meals
* No beef meals

Meals can be filtered by protein and cooking time.

### Recipe Selection

Select any combination of meals for the week.

Selected meals:

* Are visually highlighted
* Display a ✓ indicator
* Change the selection button to **Unselect**
* Automatically contribute their ingredients to the shopping list

Unselecting a meal removes its ingredients from the shopping list.

### Consolidated Shopping List

Ingredients from all selected recipes are automatically combined into one grocery list.

Where multiple recipes use the same ingredient, quantities are consolidated.

For example:

```text
Recipe 1: 3 garlic cloves
Recipe 2: 2 garlic cloves

Shopping list: 5 garlic cloves
```

### Woolworths AI Olive

The consolidated ingredient list can be copied directly to the clipboard using **Copy ingredients**.

The output is kept simple so it can be pasted into **Woolworths AI Olive** to help find and add grocery items.

Example:

```text
800 g Chicken thighs
600 g Risoni
5 Garlic cloves
550 g Cherry tomatoes
300 g Feta
220 g Baby spinach
2 Lemon
```

## Recipe Sources

Recipes are primarily sourced from [RecipeTin Eats](https://www.recipetineats.com/).

Each meal card includes a direct link to the original recipe where available.

## Design Principles

Meal Prepper is designed around a few simple rules:

* Prioritise easy meals
* Keep cooking time generally under 1 hour
* Use readily available Australian supermarket ingredients
* Avoid unnecessary one-off ingredients where possible
* Make leftovers useful for lunches
* Avoid beef meals
* Keep grocery planning simple

## Technology

The site is intentionally lightweight:

* HTML
* CSS
* Vanilla JavaScript
* No framework
* No database
* No account required

This allows the entire application to run as a static website and be hosted for free using GitHub Pages.

## Running Locally

Download `index.html` and open it in any modern browser.

No installation or build process is required.

## GitHub Pages

The site is intended to be hosted using GitHub Pages from the `main` branch.

Once Pages is enabled, the website can be opened directly from a phone and added to the home screen for app-like access.

## Future Improvements

Potential additions include:

* Automatically generate new weekly meal suggestions
* Improved RecipeTin Eats recipe library
* Serving-size adjustment
* Pantry-item exclusion
* Better unit conversion when consolidating ingredients
* Woolworths-friendly product quantities
* Save selected meals between sessions
* Meal history to avoid repeating meals too frequently
* Favourite meals
* Mobile-first shopping mode
* Ingredient categories such as produce, meat, dairy and pantry
