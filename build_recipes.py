#!/usr/bin/env python3
import json, re, time, hashlib
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE='https://www.recipetineats.com'
TARGET=1000
HEADERS={'User-Agent':'MealPrepper/1.0 (+personal meal-planning cache)'}
DESSERT=re.compile(r'\b(cake|cookie|cookies|brownie|brownies|dessert|pudding|muffin|muffins|cupcake|cupcakes|cheesecake|tart|tarts|ice cream|sorbet|frosting|icing|donut|doughnut|macaron|meringue|trifle|fudge|pavlova|crumble|sweet slice)\b',re.I)
BEEF=re.compile(r'\b(beef|veal)\b',re.I)

def get(url, tries=3):
    last=None
    for n in range(tries):
        try:
            r=requests.get(url,headers=HEADERS,timeout=30)
            r.raise_for_status(); return r
        except Exception as e:
            last=e; time.sleep(2*(n+1))
    raise last

def recipe_links():
    seen=set(); out=[]
    page=1
    while len(out)<1500 and page<=100:
        url=f'{BASE}/recipes/page/{page}/'
        r=get(url)
        s=BeautifulSoup(r.text,'html.parser')
        found=0
        for a in s.select('main a[href], article a[href], .site-main a[href]'):
            href=a.get('href','')
            if not href.startswith(BASE+'/'): continue
            if '/category/' in href or '/tag/' in href or '/recipes/' in href or '/about' in href: continue
            href=href.split('#')[0].rstrip('/')+'/'
            txt=' '.join(a.stripped_strings)
            if href not in seen and txt:
                seen.add(href); out.append(href); found+=1
        if found==0 and page>5: break
        page+=1
    return out

def ld_recipes(html):
    s=BeautifulSoup(html,'html.parser')
    found=[]
    for sc in s.find_all('script',type='application/ld+json'):
        try: data=json.loads(sc.string or sc.get_text() or '{}')
        except Exception: continue
        stack=data if isinstance(data,list) else [data]
        while stack:
            x=stack.pop()
            if isinstance(x,dict):
                typ=x.get('@type')
                if typ=='Recipe' or (isinstance(typ,list) and 'Recipe' in typ): found.append(x)
                for v in x.values():
                    if isinstance(v,(dict,list)): stack.append(v)
            elif isinstance(x,list): stack.extend(x)
    return found

def minutes(v):
    if not v:return None
    m=re.match(r'P(?:\d+D)?T(?:(\d+)H)?(?:(\d+)M)?',str(v))
    if not m:return None
    return (int(m.group(1) or 0)*60)+(int(m.group(2) or 0))

def classify(title, ingredients, cats):
    text=' '.join([title,' '.join(ingredients),' '.join(cats)]).lower()
    if BEEF.search(text): return None
    rules={
      'chicken':['chicken','turkey'],
      'pork':['pork','bacon','ham','prosciutto','chorizo','sausage'],
      'fish':['fish','salmon','tuna','cod','barramundi','snapper','trout','prawn','shrimp','seafood','squid'],
      'lamb':['lamb','mutton'],
    }
    for p,terms in rules.items():
        if any(t in text for t in terms): return p
    return 'vegetarian'

def parse(url):
    r=get(url); data=ld_recipes(r.text)
    if not data:return None
    x=data[0]
    title=str(x.get('name') or '').strip()
    cats=x.get('recipeCategory') or []
    if isinstance(cats,str): cats=[cats]
    cuisine=x.get('recipeCuisine') or []
    if isinstance(cuisine,str): cuisine=[cuisine]
    ingredients=[str(i).strip() for i in (x.get('recipeIngredient') or []) if str(i).strip()]
    if not title or len(ingredients)<3:return None
    filter_text=' '.join([title,' '.join(cats)])
    if DESSERT.search(filter_text):return None
    protein=classify(title,ingredients,cats)
    if not protein:return None
    agg=x.get('aggregateRating') or {}
    try: rating=float(agg.get('ratingValue')) if agg.get('ratingValue') is not None else None
    except: rating=None
    try: votes=int(float(agg.get('ratingCount'))) if agg.get('ratingCount') is not None else 0
    except: votes=0
    return {
      'id':hashlib.sha1(url.encode()).hexdigest()[:12],
      'title':title,
      'url':url,
      'protein':protein,
      'rating':rating,
      'votes':votes,
      'time':minutes(x.get('totalTime')),
      'categories':cats,
      'cuisine':cuisine,
      'ingredients':ingredients,
    }

def score(r):
    return ((r['rating'] or 0)*100000)+(min(r['votes'],10000)*5)

links=recipe_links()
print('candidate links',len(links))
rows=[]
for i,url in enumerate(links,1):
    try:
        row=parse(url)
        if row: rows.append(row)
    except Exception as e:
        print('skip',url,e)
    if i%25==0: print(i,'scanned',len(rows),'qualified')
    if len(rows)>=1300: break
    time.sleep(0.08)

# Prefer genuinely rated recipes, then popularity. Keep a broad mix.
rows.sort(key=score,reverse=True)
rows=rows[:TARGET]
if len(rows)<TARGET:
    raise SystemExit(f'Only found {len(rows)} qualified meal recipes; refusing to fabricate records.')

with open('recipes.json','w',encoding='utf-8') as f:
    json.dump(rows,f,ensure_ascii=False,indent=2)
print('wrote',len(rows),'recipes')
