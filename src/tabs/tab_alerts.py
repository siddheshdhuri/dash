import dash
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc 
import dash_core_components as dcc
import dash_table
import dash_html_components as html
from app import app
import pandas as pd
from alerts import alerts

demand_shortfalls = alerts.get_demand_alerts()
# print(demand_shortfalls)
inventory_shortfalls = alerts.get_inventory_alerts()

layout = html.Div([   
    dbc.Row([html.Button('Refresh', id='refresh-alerts', n_clicks=0)]), 
    dbc.Row([html.P("Demand Shortfalls")]),
    dbc.Row([        
        dbc.Col([
           
                dcc.Loading(
                    id="loading-1",
                    type="default",
                    children=html.Div([
                                dash_table.DataTable(
                                    id='demand-alerts',
                                    columns=[
                                        {'name': i, 'id': i} for i in demand_shortfalls.columns            
                                    ],
                                    data=demand_shortfalls.to_dict('records'),
                                    editable=False,
                                    page_size=20
                                    ,style_header={
                                        'minWidth': '0px', 'maxWidth': '50px',
                                        'whiteSpace': 'normal',
                                        'height': 'auto',
                                    }
                                ),
                            ])
                ) 
            
            
        ], width=6)
    ]),
    dbc.Row([html.P("Inventory Shortfalls")]),
    dbc.Row([        
        dbc.Col([
            
            dcc.Loading(
                    id="loading-2",
                    type="default",
                    children=html.Div([
                                dash_table.DataTable(
                                    id='inventory-alerts',
                                    columns=[
                                        {'name': i, 'id': i} for i in alerts.get_inventory_alerts().columns            
                                    ],
                                    data=alerts.get_inventory_alerts().to_dict('records'),
                                    editable=False,
                                    page_size=20
                                    ,style_header={
                                        'minWidth': '0px', 'maxWidth': '50px',
                                        'whiteSpace': 'normal',
                                        'height': 'auto',
                                    }
                                ),
                            ])
                ) 
            
            ], width=6)
    ])
])


@app.callback(
    Output('demand-alerts', 'data'),
    [Input('refresh-alerts', 'n_clicks')],
    [State('demand-alerts', 'data')]
)
def update_demand_alerts(n_clicks, rows):    
    
    demand_alerts = alerts.get_demand_alerts()
    demand_alerts = demand_alerts.to_dict('rows')
    
    return demand_alerts


@app.callback(
    Output('inventory-alerts', 'data'),
    [Input('refresh-alerts', 'n_clicks')],
    [State('inventory-alerts', 'data')]
)
def update_inventory_alerts(n_clicks, rows):      
    
    inventory_alerts = alerts.get_inventory_alerts()
    inventory_alerts = inventory_alerts.to_dict('rows')

    return inventory_alerts
