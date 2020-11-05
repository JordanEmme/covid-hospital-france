#Importing libraries
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import plotly.express as px

from datetime import date, datetime

import pandas as pd

import json

from urllib.request import urlopen

#Get JSON for France

with open('geoJson/map.json') as file:
    france = json.load(file)

#get France hospital Data

with urlopen('https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-bfd1-f1b3ee1cabd7') as file:
    covid = pd.read_csv(file, sep= ';')
    
    
#Engineer the data

code_dict = {elm['properties']['code']: elm['properties']['nom'] for elm in france['features']}
    
def format_date(date_str):
    if '-' in date_str:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        return datetime.strptime(date_str, '%d/%m/%Y').date()


def clean_date(data):
    data['jour'] = data['jour'].apply(format_date)
    return data


def remove_dom_tom(data):
    return data[data['dep'].apply(lambda x : len(x) == 2)]


def get_days(data):
    return list(data['jour'].unique())


def add_dep_name(data):
    data['dep_name'] = data['dep'].apply(lambda x : code_dict[x])
    return data


def convert_sexe(data):
    di = {0: 'all', 1: 'male', 2: 'female'}
    data['sexe'].replace(di, inplace= True)
    return data


def get_france_total(data):
    france_total = data.groupby(['jour', 'sexe']).sum()
    france_total.reset_index(inplace=  True)
    return france_total


def make_data(covid):
    data = covid.copy()
    data.dropna(inplace= True)
    data = clean_date(data)
    data = remove_dom_tom(data)
    data = add_dep_name(data)
    france_total = get_france_total(data)
    data = convert_sexe(data)
    france_total = convert_sexe(france_total)
    return data, france_total

data, france_total = make_data(covid)


#Change column names
data.columns = ['dep', 'sex', 'day', 'hospitalised', 'intensive care', 'discharged', 'deaths', 'dep_name']
france_total.columns = ['day', 'sex', 'hospitalised', 'intensive care', 'discharged', 'deaths']


pop = data['sex'] == 'all'

first_day= list(data['day'].unique())[0]
last_day = list(data['day'].unique())[-1]


#Initialize the app

app = dash.Dash(__name__)

server = app.server


#Define app layout

app.layout = html.Div(children = [

	html.Div(className='row',

		children=[

			html.Div(className='four columns div-user-controls', 

				children= [

					html.H1(children='Hospital data on COVID-19 in France'),

					html.P('''Please select what to visualise from the dropdown menu below.'''),

					dcc.Dropdown(
				        id='dropdown_select',
				        options=[
				            {'label': 'Cumulated number of deaths', 'value': 'deaths'},
				            {'label': 'Number of hospitalised people', 'value': 'hospitalised'},
				            {'label': 'Number of people in intensive care', 'value': 'intensive care'},
				            {'label': 'Cumulated number of recoveries', 'value': 'discharged'}
				        ],
				        value='deaths'
				    ),

					html.P(),

				    html.P('''Please select a date to update the map.'''),

				    dcc.DatePickerSingle(
				        id='date_picker',
				        min_date_allowed=first_day,
				        max_date_allowed=last_day,
				        initial_visible_month=last_day,
				        date=last_day,
                        display_format = 'DD-MM-YYYY'
				    ),

				    html.P(),

				    html.P('All data can be found at the following address:'),

				    dcc.Link(href= 'https://www.data.gouv.fr/fr/datasets/donnees-hospitalieres-relatives-a-lepidemie-de-covid-19/')

				]),

			html.Div(className='eight columns div-for-charts bg-grey', 

				children = [

					html.Div([
        
				        dcc.Graph(
				            id='france_map'
				        ),
				        
				        dcc.Graph(
				            id='figure'
				        )    

				    ])
				            
				]
			)
		])
	])




#Define callbacks


#For map

@app.callback(
    Output('france_map', 'figure'),
    [Input('dropdown_select', 'value'),
    Input('date_picker', 'date')])
def update_map(dropdown_select, date_picker):
       
    france_map = px.choropleth(
    	data_frame = data[pop & (data['day'] ==  datetime.strptime(date_picker, '%Y-%m-%d').date())],
        geojson= france,
        color=dropdown_select,
        template = "plotly_dark",
        locations= 'dep',
        hover_name= 'dep_name',
        featureidkey="properties.code",
        projection= 'mercator',
        color_continuous_scale= ['white', 'red', 'black']
        )


    france_map.update_geos(fitbounds="locations", visible=False)

    france_map.update_layout(
    	margin={"r":10,"t":0,"l":0,"b":0},
    	clickmode='event+select'
    	)
    
    return france_map


#For graph

@app.callback(
    Output('figure', 'figure'),
    [Input('dropdown_select', 'value'),
    Input('france_map', 'selectedData')])
def update_figure(dropdown_select, selectedData):
   
    figure =px.bar(
        france_total[france_total['sex'] != 'all'],
        x= 'day',
        y=dropdown_select,
        template = "plotly_dark",
        color = 'sex',
        color_discrete_map={'male': 'blue', 'female': 'red'}
    )

    
    if selectedData:        
        
        dep = selectedData["points"][0]['location']
        figure = px.bar(
            data[(data['dep'] == dep) & (data['sex'] != 'all')],
            x= 'day',
            y=dropdown_select,
            template = "plotly_dark",
            color = 'sex',
            color_discrete_map={'male': 'blue', 'female': 'red'}
        )
        
    
    return figure



#Run the app

if __name__ == '__main__':
    app.run_server(debug=True)
