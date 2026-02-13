import requests

url = "https://www.themealdb.com/api/json/v1/1/filter.php?i=chicken"
r = requests.get(url)
print(r.json())
