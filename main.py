import asyncio
import secrets

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status

from config import MAPBOX_TOKEN

app = FastAPI()
security = HTTPBasic()

postcode_lookup = dict()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "eatouthelpout")
    correct_password = secrets.compare_digest(credentials.password, "eatouthelpout")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/")
def index(request: Request, username: str = Depends(get_current_username)):
    return templates.TemplateResponse('index.html', {'request': request})


async def geocode(session: httpx.AsyncClient, address):
    endpoint = 'mapbox.places'
    url = f'https://api.mapbox.com/geocoding/v5/{endpoint}/{address}.json?country=GB&access_token={MAPBOX_TOKEN}'
    return await session.get(url)


@app.get('/restaurants')
async def restaurants(postcode: str, username: str = Depends(get_current_username)):
    if postcode is None or postcode == '':
        return 'bad request'

    if postcode in postcode_lookup:
        return postcode_lookup[postcode]

    async with httpx.AsyncClient() as client:
        response = await client.get(f'https://www.tax.service.gov.uk/eat-out-to-help-out/find-a-restaurant/results?postcode={postcode}')

    soup = BeautifulSoup(response.content, features="html.parser")
    restaurants_list = []
    for result_item in soup.find_all('li', {'class': 'govuk-results-list-item'}):
        restaurants_list.append({
            'name': result_item.find('h3').text.strip(),
            'distance': result_item.find('p', {'class': 'govuk-results-miles'}).text.strip(),
            'address': result_item.find('p', {'class': 'govuk-results-address'}).text.strip(),
        })

    session = httpx.AsyncClient()
    geocode_results = await asyncio.gather(*[geocode(session, restaurant['address']) for restaurant in restaurants_list])
    await session.aclose()

    num_success = 0
    for geocode_result, restaurant in zip(geocode_results, restaurants_list):
        try:
            lng_lat = geocode_result.json()['features'][0]['center']
            restaurant.update(dict(lng=lng_lat[0], lat=lng_lat[1]))
            num_success += 1
        except:
            pass

    print(f'Completed parsing result. Success ratio: {num_success / len(restaurants_list)}')
    postcode_lookup[postcode] = restaurants_list
    return restaurants_list
