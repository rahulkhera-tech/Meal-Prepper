#!/usr/bin/env python3
import json
import re
import time
import hashlib
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://www.recipetineats.com"
MAX_RECIPES = 1000
MAX_ARCHIVE_PAGES = 100
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.10

HEADERS = {
    "User-Agent": "MealPrepper/2.0 (+personal meal-planning cache)"
}

ARCHIVE_PATTERNS = [
    "/category/main-dishes/page/{page}/",
    "/category/chicken-recipes/page/{page}/",
    "/category/pork-recipes/page/{page}/",
    "/category/fish-recipes/page/{page}/",
    "/category/lamb-recipes/page/{page}/",
    "/category/vegetarian-recipes/page/{page}/",
    "/blog/page/{page}/",
]

DESSERT = re.compile(
    r"\b("
    r"cake|cookie|cookies|brownie|brownies|dessert|pudding|muffin|muffins|"
    r"cupcake|cupcakes|cheesecake|tart|tarts|ice cream|sorbet|frosting|icing|"
    r"donut|doughnut|macaron|meringue|trifle|fudge|pavlova|crumble|sweet slice|"
    r"caramel slice|chocolate slice|biscuit|biscuits"
    r")\b",
    re.I,
)

BEEF = re.compile(r"\b(beef|veal)\b", re.I)

SKIP_PATH_PARTS = (
    "/category/",
    "/tag/",
    "/about",
    "/contact",
    "/privacy",
    "/terms",
    "/shop",
    "/cookbook",
    "/blog/",
    "/recipes/",
    "/wp-",
)

def get(url, tries=3):
    last = None
    for attempt in range(tries):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response
        except Exception as exc:
            last = exc
            if attempt < tries - 1:
                time.sleep(2 * (attempt + 1))
    raise last


def canonical_recipe_url(href):
    if not href:
        return None

    href = urljoin(BASE, href).split("#")[0]
    parsed = urlparse(href)

    if parsed.scheme not in ("http", "https"):
        return None
    if parsed.netloc not in ("www.recipetineats.com", "recipetineats.com"):
        return None

    path = parsed.path or "/"
    low = path.lower()

    if path == "/":
        return None
    if any(part in low for part in SKIP_PATH_PARTS):
        return None
    if low.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf")):
        return None

    return f"https://www.recipetineats.com{path.rstrip('/')}/"


def discover_recipe_links():
    seen = set()
    discovered = []

    for pattern in ARCHIVE_PATTERNS:
        empty_pages = 0

        for page in range(1, MAX_ARCHIVE_PAGES + 1):
            url = BASE + pattern.format(page=page)

            try:
                response = get(url)
            except requests.HTTPError as exc:
                status = getattr(exc.response, "status_code", None)
                if status in (404, 410):
                    break
                print(f"archive error {url}: {exc}")
                break
            except Exception as exc:
                print(f"archive error {url}: {exc}")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            page_links = []

            selectors = [
                "main article a[href]",
                ".site-main article a[href]",
                ".entry-title a[href]",
                "h2 a[href]",
                "h3 a[href]",
            ]

            for selector in selectors:
                for anchor in soup.select(selector):
                    candidate = canonical_recipe_url(anchor.get("href"))
                    if candidate and candidate not in seen:
                        page_links.append(candidate)

            page_links = list(dict.fromkeys(page_links))

            if not page_links:
                empty_pages += 1
                if empty_pages >= 2:
                    break
            else:
                empty_pages = 0

            for link in page_links:
                seen.add(link)
                discovered.append(link)

            print(
                f"discovered {len(discovered)} unique candidate URLs "
                f"after {url}"
            )

            time.sleep(REQUEST_DELAY)

    return discovered


def find_recipe_json_ld(html):
    soup = BeautifulSoup(html, "html.parser")
    found = []

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        stack = data if isinstance(data, list) else [data]

        while stack:
            item = stack.pop()

            if isinstance(item, dict):
                recipe_type = item.get("@type")

                if recipe_type == "Recipe" or (
                    isinstance(recipe_type, list)
                    and "Recipe" in recipe_type
                ):
                    found.append(item)

                for value in item.values():
                    if isinstance(value, (dict, list)):
                        stack.append(value)

            elif isinstance(item, list):
                stack.extend(item)

    return found


def duration_minutes(value):
    if not value:
        return None

    match = re.match(
        r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?",
        str(value),
    )
    if not match:
        return None

    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)

    return days * 1440 + hours * 60 + minutes


def classify_protein(title, ingredients, categories):
    title_text = title.lower()
    ingredient_text = " ".join(ingredients).lower()
    category_text = " ".join(categories).lower()
    combined = f"{title_text} {ingredient_text} {category_text}"

    if BEEF.search(combined):
        return None

    rules = {
        "chicken": ["chicken", "turkey"],
        "pork": [
            "pork",
            "bacon",
            "ham",
            "prosciutto",
            "chorizo",
            "sausage",
        ],
        "fish": [
            "fish",
            "salmon",
            "tuna",
            "cod",
            "barramundi",
            "snapper",
            "trout",
            "prawn",
            "shrimp",
            "seafood",
            "squid",
            "calamari",
        ],
        "lamb": ["lamb", "mutton"],
    }

    for protein, terms in rules.items():
        if any(term in combined for term in terms):
            return protein

    # Anything without a meat/fish match is treated as vegetarian only when
    # its title/category/ingredients show a plausible meat-free main.
    vegetarian_terms = [
        "vegetarian",
        "veggie",
        "tofu",
        "lentil",
        "chickpea",
        "halloumi",
        "ricotta",
        "mushroom",
        "eggplant",
        "aubergine",
        "zucchini",
        "courgette",
        "cauliflower",
        "broccoli",
        "bean",
        "beans",
        "pumpkin",
        "sweet potato",
        "spinach",
        "paneer",
        "falafel",
    ]

    if any(term in combined for term in vegetarian_terms):
        return "vegetarian"

    return None


def parse_recipe(url):
    response = get(url)
    recipes = find_recipe_json_ld(response.text)

    if not recipes:
        return None

    recipe = recipes[0]

    title = str(recipe.get("name") or "").strip()
    ingredients = [
        str(item).strip()
        for item in (recipe.get("recipeIngredient") or [])
        if str(item).strip()
    ]

    categories = recipe.get("recipeCategory") or []
    if isinstance(categories, str):
        categories = [categories]

    cuisine = recipe.get("recipeCuisine") or []
    if isinstance(cuisine, str):
        cuisine = [cuisine]

    if not title or len(ingredients) < 3:
        return None

    # Dessert filtering is intentionally restricted to title/categories.
    # Related post text and navigation are ignored.
    dessert_text = f"{title} {' '.join(categories)}"
    if DESSERT.search(dessert_text):
        return None

    protein = classify_protein(
        title=title,
        ingredients=ingredients,
        categories=categories,
    )
    if not protein:
        return None

    aggregate = recipe.get("aggregateRating") or {}

    try:
        rating = (
            float(aggregate.get("ratingValue"))
            if aggregate.get("ratingValue") is not None
            else None
        )
    except Exception:
        rating = None

    try:
        votes = (
            int(float(aggregate.get("ratingCount")))
            if aggregate.get("ratingCount") is not None
            else 0
        )
    except Exception:
        votes = 0

    total_minutes = duration_minutes(recipe.get("totalTime"))

    return {
        "id": hashlib.sha1(url.encode("utf-8")).hexdigest()[:12],
        "title": title,
        "url": url,
        "protein": protein,
        "rating": rating,
        "votes": votes,
        "time": total_minutes,
        "categories": categories,
        "cuisine": cuisine,
        "ingredients": ingredients,
    }


def ranking_score(recipe):
    # Primary signal: rating.
    # Secondary signal: rating-count confidence/popularity.
    rating = recipe["rating"] or 0
    votes = min(recipe["votes"] or 0, 10000)
    return rating * 100000 + votes * 5


def main():
    links = discover_recipe_links()
    print(f"candidate URLs discovered: {len(links)}")

    rows = []
    seen_recipe_ids = set()

    for index, url in enumerate(links, 1):
        try:
            recipe = parse_recipe(url)

            if recipe and recipe["id"] not in seen_recipe_ids:
                seen_recipe_ids.add(recipe["id"])
                rows.append(recipe)

        except Exception as exc:
            print(f"skip {url}: {exc}")

        if index % 25 == 0:
            print(
                f"{index} URLs scanned; "
                f"{len(rows)} verified meal recipes retained"
            )

        time.sleep(REQUEST_DELAY)

    rows.sort(key=ranking_score, reverse=True)
    rows = rows[:MAX_RECIPES]

    if not rows:
        raise SystemExit(
            "No verified meal recipes were found. "
            "Refusing to write an empty database."
        )

    with open("recipes.json", "w", encoding="utf-8") as file:
        json.dump(rows, file, ensure_ascii=False, indent=2)

    print(
        f"wrote {len(rows)} verified meal recipes "
        f"(maximum requested: {MAX_RECIPES})"
    )


if __name__ == "__main__":
    main()
