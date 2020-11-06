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

#Get French hospital data
with urlopen('https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-bfd1-f1b3ee1cabd7') as file:
    covid = pd.read_csv(file, sep= ';')
    
    
#Cleaning and engineering the data
covid.dropna(inplace= True) #Dropping Nan

def format_date(date_str):
    if '-' in date_str:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        return datetime.strptime(date_str, '%d/%m/%Y').date()


covid['jour'] = covid['jour'].apply(format_date) #Solving date formatting issues
covid = covid[covid['dep'].apply(lambda x : len(x) == 2)] #Removing DOM-TOM (length of dep code is not 2)

di = {0: 'all', 1: 'male', 2: 'female'}
covid['sexe'].replace(di, inplace= True)

france_total = covid.groupby(['jour', 'sexe']).sum()
france_total.reset_index(inplace=  True)

code_dict = {elm['properties']['code']: elm['properties']['nom'] for elm in france['features']}
covid['dep_name'] = covid['dep'].apply(lambda x : code_dict[x]) #Adding departments names

#Change column names for UI
covid.columns = ['dep', 'sex', 'day', 'hospitalised', 'intensive care', 'discharged', 'deaths', 'dep_name']
france_total.columns = ['day', 'sex', 'hospitalised', 'intensive care', 'discharged', 'deaths']


# Define usual masks
pop = covid['sex'] == 'all'

days = list(covid['day'].unique())

first_day = days[0]
last_day = days[-1]


#Initialize the app
app = dash.Dash(__name__)
server = app.server

#app options
app.title= "Covid France"

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
                        searchable= False,
                        clearable=False,
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
                        display_format = 'DD-MM-YYYY',
                        clearable= False
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
    	data_frame = covid[pop & (covid['day'] ==  datetime.strptime(date_picker, '%Y-%m-%d').date())],
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
            covid[(covid['dep'] == dep) & (covid['sex'] != 'all')],
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
