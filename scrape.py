import requests
import json
import csv
import os
from typing import Dict, List, Optional
from serpapi import GoogleSearch


# Converting city name to lat/lon (OpenStreetMap)

def city_to_ll(city: str, zoom: int = 12) -> str:
    response = requests.get(
        'https://nominatim.openstreetmap.org/search',
        params={
            'q': city,
            'format': 'json',
            'limit': 1,
        },
        headers={
            'User-Agent': 'GeoScraper/1.0 (contact: ajaiikumaarappan@gmail.com)',
            'Accept-Language': 'en',
        },
        timeout=10,
    )
    
    data = response.json()
    
    if not data or len(data) == 0:
        raise ValueError(f"City not found: {city}")
    
    lat = data[0]['lat']
    lon = data[0]['lon']
    return f"@{lat},{lon},{zoom}z"



# Lemlist request options builder

def get_lemlist_options(company_name: str) -> Dict:
    return {
        'headers': {
            'Authorization': 'Basic Ojg2MjY1NTJmYjgyM2NkZWVhZTkyZmE4YThjZGJiYmIw',
            'Content-Type': 'application/json',
        },
        'json': {
            'filters': [
                {'filterId': 'keywordInCompany', 'in': [company_name], 'out': []},
                {'filterId': 'currentCompanyCountry', 'in': ['India'], 'out': []},
                {'filterId': 'currentCompanyLocation', 'in': ['Chennai'], 'out': []},
                {
                    'filterId': 'seniority',
                    'in': [
                        'CxO',
                        'Owner/Partner',
                        'Vice President',
                        'CEO',
                        'COO',
                        'CFO',
                        'CTO',
                    ],
                    'out': [],
                },
                {
                    'filterId': 'department',
                    'in': ['Operations', 'Information Technology', 'Engineering', 'Sales'],
                    'out': [],
                },
            ],
            'page': 1,
            'size': 5,
        },
    }



# JSON → CSV helper

def json_to_csv(data: List[Dict], filename: str) -> None:
    
    if not data or len(data) == 0:
        return
    
    headers = list(data[0].keys())
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)



# Main function to get data from Google Maps and Lemlist

def get_data(query: str, near: str) -> Dict:
    
    if not query or not near:
        raise ValueError('query and near are required')
    
    final_output = []
    linkedin_output = []
    
    # To Get latitude/longitude for the city
    ll = city_to_ll(near)
    
    # Searching Google Maps using SerpAPI
    search = GoogleSearch({
        'engine': 'google_maps',
        'q': query,
        'll': ll,
        'type': 'search',
        'hl': 'en',
        'gl': 'in',
        'api_key': '5399d6ce05afd2d31b445d5ca7884babec722b4084377071fee0187c168389c9',
    })
    
    maps_data = search.get_dict()
    
    if 'error' in maps_data:
        raise Exception(maps_data['error'])
    
    # Processing Google Maps results
    local_results = maps_data.get('local_results', [])
    
    for item in local_results:
        final_output.append({
            'name': item.get('title'),
            'type': item.get('type'),
            'address': item.get('address'),
            'openstate': item.get('hours'),
            'phone': item.get('phone'),
            'website': item.get('website'),
            'lemlistData': None,
        })
    
    # To Enrich with Lemlist data
    for company in final_output:
        print(f"Searching Lemlist for: {company['name']}")
        
        try:
            options = get_lemlist_options(company['name'])
            response = requests.post(
                'https://api.lemlist.com/api/database/people',
                headers=options['headers'],
                json=options['json'],
            )
            
            data = response.json()
            company['lemlistData'] = data
            
            if 'results' in data and data['results']:
                for person in data['results']:
                    linkedin_output.append({
                        'name': person.get('full_name'),
                        'company': person.get('current_exp_company_name'),
                        'seniority': person.get('seniority'),
                        'linkedin': person.get('lead_linkedin_url'),
                        'headline': person.get('headline'),
                        'department': person.get('department'),
                        'companyIndustry': person.get('current_exp_cmpany_subindustry'),
                    })
        
        except Exception as err:
            print(f"Lemlist error for {company['name']}: {str(err)}")
            company['lemlistData'] = {'error': str(err)}
    
    
    # SAVING OUTPUT FILES
    
    output_dir = './output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Saving JSON
    with open(os.path.join(output_dir, 'linkedin_output.json'), 'w', encoding='utf-8') as f:
        json.dump(linkedin_output, f, indent=2, ensure_ascii=False)
    
    # Saving CSV
    json_to_csv(linkedin_output, os.path.join(output_dir, 'linkedin_output.csv'))
    
    print('linkedin_output.json & linkedin_output.csv saved')
    
    return {
        'totalCompanies': len(final_output),
        'companies': final_output,
        'linkedinProfiles': linkedin_output,
    }


# Example usage

if __name__ == '__main__':
    try:
        result = get_data('software companies', 'Chennai')
        print('\n FINAL RESULT:\n')
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as err:
        print(f'Error: {str(err)}')