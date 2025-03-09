import requests
from bs4 import BeautifulSoup
from urllib.request import urlopen
from recipe_scrapers import scrape_html

url = 'https://cooking.nytimes.com/article/cheap-healthy-dinner-ideas'
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Set to store unique recipe URLs
recipe_links = set()

# Collect URLs that contain /recipes/
for a in soup.find_all('a', href=True):
    href = a['href']
    if '/recipes/' in href:
        if href.startswith('https://'):
            full_url = href
        else:
            full_url = 'https://cooking.nytimes.com' + href
        recipe_links.add(full_url)

# Write the unique URLs to a file
with open('recipe_urls.txt', 'w') as file:
    for link in recipe_links:
        file.write(link + '\n')

def get_recipe_nutrients(scraper):
    try:
        nutrients = scraper.nutrients()
        return {
            "carbs": int(nutrients['carbohydrateContent'].split()[0]),
            "protein": int(nutrients['proteinContent'].split()[0]),
            "fat": int(nutrients['fatContent'].split()[0]),
            "calories": int(nutrients['calories'])
        }
    except Exception as e:
        print(f'Failed to extract nutrients: {e}')
        return None

recipe_macros = []

# Open the file with URLs
with open('recipe_urls.txt', 'r') as file:
    for line in file:
        url = line.strip()  # Get the URL from the line and remove any extra whitespace/newlines
        
        try:
            # Retrieve the HTML of the recipe page
            html = urlopen(url).read().decode("utf-8")
            scraper = scrape_html(html, org_url=url)
            
            # Extract nutrients and store in list
            macro_info = get_recipe_nutrients(scraper)
            if macro_info:
                recipe_macros.append((url, macro_info))
        except Exception as e:
            # Handle exceptions (e.g., network issues, parsing errors)
            print(f"An error occurred while processing {url}: {e}")

desired_macros = {
    "carbs_percentage": (0.40, 0.50),  # 40% to 50%
    "protein_percentage": (0.30, 0.45), # 30% to 45%
    "fat_percentage": (0.15, 0.25),     # 15% to 25%
}

def calculate_macro_distribution(total_cals, carbs, protein, fat):
    return {
        "carbs_percentage": (carbs * 4 / total_cals),
        "protein_percentage": (protein * 4 / total_cals),
        "fat_percentage": (fat * 9 / total_cals),
    }

def matches_macros(macro_dist, desired):
    return (desired['carbs_percentage'][0] <= macro_dist['carbs_percentage'] <= desired['carbs_percentage'][1] and
            desired['protein_percentage'][0] <= macro_dist['protein_percentage'] <= desired['protein_percentage'][1] and
            desired['fat_percentage'][0] <= macro_dist['fat_percentage'] <= desired['fat_percentage'][1])

def plan_meal(recipes):
    for breakfast in recipes:
        for lunch in recipes:
            for dinner in recipes:
                total_cals = breakfast[1]['calories'] + lunch[1]['calories'] + dinner[1]['calories']
                carbs = breakfast[1]['carbs'] + lunch[1]['carbs'] + dinner[1]['carbs']
                protein = breakfast[1]['protein'] + lunch[1]['protein'] + dinner[1]['protein']
                fat = breakfast[1]['fat'] + lunch[1]['fat'] + dinner[1]['fat']

                macro_distribution = calculate_macro_distribution(total_cals, carbs, protein, fat)

                if matches_macros(macro_distribution, desired_macros):
                    print(f"Meal Plan:\nBreakfast: {breakfast[0]}\nLunch: {lunch[0]}\nDinner: {dinner[0]}\n")
                    print(f"Total Calories: {total_cals}")
                    print(f"Total Carbs: {carbs} grams ({macro_distribution['carbs_percentage']*100:.2f}%)")
                    print(f"Total Protein: {protein} grams ({macro_distribution['protein_percentage']*100:.2f}%)")
                    print(f"Total Fat: {fat} grams ({macro_distribution['fat_percentage']*100:.2f}%)\n")
                    return  # Stop once we find one valid combination; remove for multiple plans

# Print macro content for each recipe
for recipe in recipe_macros:
    print(f"Recipe URL: {recipe[0]}")
    print(f"Calories: {recipe[1]['calories']}")
    print(f"Carbs: {recipe[1]['carbs']} grams")
    print(f"Protein: {recipe[1]['protein']} grams")
    print(f"Fat: {recipe[1]['fat']} grams\n")

plan_meal(recipe_macros)
