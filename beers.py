#!/usr/bin/python

import glob
import re
import markdown
import os.path
import StringIO
import string
from collections import namedtuple

import shutil
import codecs

OUT_FOLDER = "out"

top_html = """
<!DOCTYPE html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" type="text/css" href="pure-min.css">
    <link rel="stylesheet" type="text/css" href="beers.css">
    <title>{0}</title>
  </head>
  <body>
    <div id="content">
"""

bottom_html = """
    </div>
  </body>
</html>
"""

Ingredient = namedtuple("Ingredient", "name description")
Page = namedtuple("Page", "id title content")

def get_ingredient_html_path(ingredient):
    return "ingredient_{0}.html".format(ingredient)

def get_beer_html_path(beer):
    return "beer_{0}.html".format(beer["id"])

def get_page_html_path(page):
    return "{0}.html".format(page.id)

def get_anchor_name(name):
    return name.replace(' ', '')

def parse_header(header):
    match = re.match("([^:]*):\s*(.*)", header)
    name = match.group(1).lower()
    value = match.group(2)
    if name in ['hops', 'malts', 'additives']:
        value = [v.strip() for v in value.split(',')] 
    return (name, value)

def read_beer(filename, template = dict()):
    beer = dict(template)
    beer['id'] = os.path.splitext(os.path.basename(filename))[0]
    with codecs.open(filename, encoding='utf-8') as f:
        while True:
            line = f.readline()
            if line.strip() == '':
                break
            header = parse_header(line)
            beer[header[0]] = header[1]
        beer['content'] = markdown.markdown(''.join(f.readlines()))
        f.close()

    return beer

def read_beers():
    files = glob.glob('beers/*.md')
    template_filename = 'beers/_template.md'
    template = read_beer(template_filename)
    return [read_beer(beer_file, template) for beer_file in files if beer_file != template_filename]

def read_page(filename):
    id = os.path.splitext(os.path.basename(filename))[0]
    if id == "index":
        title = "Home"
    else:
        title = id.title()
    string_file = StringIO.StringIO()
    markdown.markdownFromFile(input=filename, output=string_file)
    content =  string_file.getvalue()
    return Page(id, title, content)

def read_pages():
    files = ['pages/index.md'] + [page for page in glob.glob('pages/*.md') if page != 'pages/index.md']
    return [read_page(page_file) for page_file in files]

def get_beers_by_hop_link(name = ""):
    if name:
        target = get_anchor_name(name)
        text = name
    else:
        target = ""
        text = "Beers by hop"

    return '<a href="ingredient_hop.html#{0}">{1}</a>'.format(target, text)

def get_beer_link(beer, name = None):
    if name == None:
        name = beer["name"]
    return '<a href="{0}">{1}</a>'.format(get_beer_html_path(beer), name)


def get_page_formatted_hops(beer):
    if not "hops" in beer:
        return "No hops"
    return ", ".join([get_beers_by_hop_link(hop) for hop in beer["hops"]])

def get_beers_by_malt_link(name = ""):
    if name:
        target = get_anchor_name(name)
        text = name
    else:
        target = ""
        text = "Beers by malt"

    return '<a href="ingredient_malt.html#{0}">{1}</a>'.format(target, text)

def get_page_formatted_malts(beer):
    if not "malts" in beer:
        return "No malts"
    return ", ".join([get_beers_by_malt_link(malt) for malt in beer["malts"]])

def get_beers_by_ingredient_link(ingredient, name):
    if name:
        target = get_anchor_name(name)
        text = name
    else:
        target = ""
        text = "Beers by " + ingredient

    return '<a href="ingredient_{0}.html#{1}">{2}</a>'.format(ingredient, target, name)

def get_beers_by_yeast_link(name = ""):
    return get_beers_by_ingredient_link("yeast", name)

def get_page_formatted_yeast(beer):
    if not "yeast" in beer:
        return "No yeast"
    return get_beers_by_yeast_link(beer['yeast'])

def create_beer_page_content(beer):
    values = dict()
    for key in ["name", "date", "ibu", "abv", "content", "style", "recipeurl", "label"]:
        values[key] = beer.get(key, "")
    values["malts_formatted"] = get_page_formatted_malts(beer)
    values["hops_formatted"] = get_page_formatted_hops(beer)
    values["yeast_formatted"] = get_page_formatted_yeast(beer)
    template = '''
<h1>$name</h1>
<div class="beer-details">
<span class="beer-label">ABV: </span> $abv%<br/>
<span class="beer-label">Style: </span>$style<br/>
<span class="beer-label">IBU: </span>$ibu<br/>
<span class="beer-label">Label: </span>$label<br/>
<span class="beer-label">Brewed: </span>$date<br/>
<details class="beer-details-ingredients">
<summary>Ingredients</summary>
<div><span class="beer-label">Malts: </span>$malts_formatted</div>
<div><span class="beer-label">Hops: </span>$hops_formatted</div>
<div><span class="beer-label">Yeast: </span>$yeast_formatted</div>
<a class="beer-recipe-link" href="$recipeurl" target="_blank">Full recipe</a>
</details>
</div>

$content
'''
    return string.Template(template).substitute(values)



def read_ingredient(ingredient_filename):
    ingredients = list()
    with open(ingredient_filename) as ingredient_file:
        for line in ingredient_file.readlines():
            match = re.match("([^:]*):\s*(.*)", line)
            name = match.group(1)
            description = match.group(2)
            ingredients.append(Ingredient(name, description))
    return ingredients


def read_ingredients():
    ingredients = dict()
    ingredient_filenames = glob.glob('ingredients/*.def')
    for ingredient_filename in ingredient_filenames:
        name = os.path.splitext(os.path.basename(ingredient_filename))[0]
        ingredients[name] = read_ingredient(ingredient_filename)
    return ingredients

def fuzzy_match_ingredient(type, a, b):
    a_lower = a.lower()
    b_lower = b.lower()
    if type == "yeast":
        if len(a_lower) < len(b_lower):
            return b_lower.startswith(a_lower)
        else:
            return a_lower.startswith(b_lower)
    else:
        return a_lower == b_lower


def create_ingredient_page_content(type, items):
    global beers
    html = ["<h1>{0}</h2>".format(type.title())]
    ingredient_key = type + "s"
    for item in items:
        beers_with_ingredient = list()
        for beer in beers:
            if type == "yeast":
                if "yeast" in beer and item.name.lower().startswith(beer["yeast"].lower()):
                    beers_with_ingredient.append(beer)
            else:
                for beer_ingredient in beer.get(ingredient_key, []):
                    if beer_ingredient.lower() == item.name.lower():
                        beers_with_ingredient.append(beer)
                        break
        html.append('<h2>{0}</h2><div>{1}</div>'.format(item.name, item.description))
        if beers_with_ingredient:
            html.append('<div>Used in: ')
            html.append(', '.join([get_beer_link(beer) for beer in beers_with_ingredient]))
            html.append('</div>')

    return "".join(html) 


def find_beer_by_name(name):
    for beer in beers:
        if beer["name"] == name:
            return beer
    return None

def reference_expander(match):
    whitespace = match.groups()[0]
    type = match.groups()[1]
    value = match.groups()[2]
    text = value
    if type == "beer":
        beer = find_beer_by_name(value)
        if beer:
            text = get_beer_link(beer)
    return whitespace + text

def expand_references(content):
    return re.sub("([ .])@([^\(]*)\(([^\)]*)\)", reference_expander, content)

def render_content(filename, content, sub_title = None):
    expanded_content = expand_references(content)
    out_filename = os.path.join(OUT_FOLDER, filename)
    title = "Petter brewing"
    if sub_title:
        title = title + " - " + sub_title

    with codecs.open(out_filename, encoding='utf-8', mode='w') as file:
        file.write(top_html.format(title))
        file.write(menu_html)
        file.write('<div id="inner-content">')
        file.write(expanded_content)
        file.write('</div>')
        file.write(bottom_html)
        file.close()

def format_menu_item(title, url):
    return '<li class="pure-menu-item"><a class="pure-menu-link" href="{1}">{0}</a></li>'.format(title, url)

def generate_menu_html():
    html = []
    html.append('<div id="menu" class="pure-menu pure-menu-horizontal"><ul class="pure-menu-list">')
    for page in pages:
        if page.id == 'ingredients':
            html.append('<li class="pure-menu-item pure-menu-has-children pure-menu-allow-hover">')
            html.append('<a href="#" class="pure-menu-link">Ingredients</a>')
            html.append('<ul class="pure-menu-children">')
            for ingredient in ingredients:
                html.append(format_menu_item(ingredient.title(), get_ingredient_html_path(ingredient)))
            html.append('</ul>')
            html.append('</li>')
        else:
            html.append(format_menu_item(page.title, get_page_html_path(page)))
    html.append('</ul></div>');
    return ''.join(html)


def generate_beer_page_sorted_table(field, reverse = False):
    content_html = []
    id_attribute = ''
    id_attribute = "id=by-{}".format(field)

    content_html.append('''
    <table {} class="pure-table pure-table-horizontal beer-table">
       <thead>
         <tr>
           <th>Date</th>
           <th>Name</th>
           <th>Label</th>
           <th>Style</th>
           <th>ABV%</th>
         </tr>
       </thead>
       <tbody>
    '''.format(id_attribute))
    
    for beer in sorted(beers, key=lambda b: b[field], reverse = reverse):
        content_html.append('<tr>')
        content_html.append('<td>')
        content_html.append(beer["date"])
        content_html.append('</td>')
        content_html.append('<td>')
        content_html.append(get_beer_link(beer))
        content_html.append('</td>')
        content_html.append('<td>')
        content_html.append(beer["label"])
        content_html.append('</td>')
        content_html.append('<td>')
        content_html.append(beer["style"])
        content_html.append('</td>')
        content_html.append('<td>')
        content_html.append(beer["abv"])
        content_html.append('</td>')
        content_html.append('</tr>')

    content_html.append('''
      </tbody>
    </table>
    ''')

    return ''.join(content_html)



def generate_beer_page():
    id = "beers"
    title = "Beers"
    content_html = ['<table class="pure-table pure-table-horizontal">']

    content_html.append('''
    <p>
      These are all my wonderful, and not so wonderful, brewes throug the years. Enjoy :)
    </p>
    <p>
    Sort by:
    <a class="beer-sort" href="#">Date</a>
    <a class="beer-sort" href="#by-name">Name</a>
    <a class="beer-sort" href="#by-style">Style</a>
    <a class="beer-sort" href="#by-abv">Abv</a>
    </p>
    ''')

    for field in ["name", "style", "abv", "date"]:
        content_html.append(generate_beer_page_sorted_table(field, field == "date"))

    content = ''.join(content_html)

    return Page(id, title, content)

def generate_ingredient_page():
    id = 'ingredients'
    title = 'Ingredients'

    content_html = ['<ul>']
    for ingredient in ingredients:
        content_html.append('<li><a href="{}">'.format(get_ingredient_html_path(ingredient)))
        content_html.append(ingredient.title())
        content_html.append('</a></li>')

    content_html.append('</ul>')

    content = ''.join(content_html)

    return Page(id, title, content)

beers = read_beers()
pages = read_pages()
ingredients = read_ingredients()

pages.append(generate_beer_page())
pages.append(generate_ingredient_page())

shutil.rmtree(OUT_FOLDER, True)
shutil.copytree("htdocs/", OUT_FOLDER)

menu_html = generate_menu_html()

for ingredient in ingredients:
    content = create_ingredient_page_content(ingredient, ingredients.get(ingredient))
    render_content(get_ingredient_html_path(ingredient), content)

for beer in beers:
    content = create_beer_page_content(beer)
    render_content(get_beer_html_path(beer), content, beer["name"])

for page in pages:
    content = markdown.markdown(page.content)
    render_content(get_page_html_path(page), content)
