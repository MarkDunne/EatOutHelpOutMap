import numpy as np
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.security import HTTPBasic
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
security = HTTPBasic()

postcode_lookup = dict()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

restaurant_data = pd.read_csv('data/restaurants.processed.csv')


def haversine_vectorize(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    haver_formula = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2

    dist = 2 * np.arcsin(np.sqrt(haver_formula))
    km = 6367 * dist  # 6367 for distance in KM for miles use 3958
    return km


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.get('/restaurants')
async def restaurants(longitude: float, latitude: float):
    nearby_restaurants = (restaurant_data
        .assign(distance=haversine_vectorize(longitude, latitude, restaurant_data['lng'], restaurant_data['lat']))
        .sort_values('distance')
        .loc[lambda df: df['distance'] < 2]).head(100)

    return nearby_restaurants.drop('distance', axis=1).to_dict(orient='records')
