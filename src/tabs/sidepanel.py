import dash
import plotly
import dash_core_components as dcc
import dash_html_components as html 
import dash_bootstrap_components as dbc 
import dash_table
import pandas as pd
from dash.dependencies import Input, Output
from utils import config
from app import app
import os
from tabs import tab_visualisation, tab_shift_lever, tab_dsi, tab_alerts, tab_import_cofill_lever, tab_alter_demand
import io
import flask
import pandas as pd
from database import transforms

combined_df = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'combined_df')) 

min_p=10
max_p=20

layout = html.Div([
    #dbc.Row([ html.H1('Mid Term Planning') ]),
    dbc.Row([dbc.Col(
        html.Div([
         html.Img(src='https://1000logos.net/wp-content/uploads/2016/11/Coca-Cola-Logo.png', width="200", height="200")
        
        ,html.Div([html.P('Summary Portfolio')
            ,dcc.Dropdown(
                id='summary-portfolio',
                options= [{'label':'Total GB', 'value':'Total_GB'}] + [{'label': i, 'value': i} for i in combined_df.Summary_Portfolio.unique()],
                value='LPET'
            )
            ,html.Hr()
        ])        
        ,html.Div([html.P('UOM')
            ,dcc.Dropdown(
                id='uom',
                options=[
                    {'label': 'ZUC', 'value': 'ZUC'},
                    {'label': 'ZRW', 'value': 'ZRW'}                    
                ],
                value='ZUC'
            )
            ,html.Hr()
        ])               
        ,html.Div([
            html.P('Include Safety Hours in Available Volume calculation?')
            ,dcc.Dropdown(
                id='include-safety-hours',
                options=[
                    {'label': 'Include Safety Hours', 'value': 'True'},
                    {'label': 'Exclude Safety Hours', 'value': 'False'}                    
                ],
                value='False'
            ) 
            ,html.Hr()  
        ])
        ,html.Div([            
            html.Button('Reset Data', id='reset-data', n_clicks=0)  
            ,dcc.ConfirmDialog(
                id='confirm-reset',
                message='This will reload data from database. Are you sure you want to continue?',
            )            
        ])
        ,html.Div([            
            html.Button('Export Baseline Data', id='export-baseline-data', n_clicks=0)   
            ,html.Button('Export Vizualisation Data', id='export-viz-data', n_clicks=0)  
        ])
        # ,html.Div(children=[
        #         html.A("Download Viz Data", href="/download_viz_data/"),
        #     ])        
        ,dcc.Loading(
            id="loading-1",
            type="default",
            children=html.Div(id="data-refresh-status")
        )   
        ,dcc.Loading(
            id="loading-2",
            type="default",
            children=html.Div(id="data-export-status")
        ) 
        ,dcc.Loading(
            id="loading-3",
            type="default",
            children=html.Div(id="viz-data-export-status")
        )       
    ]
    , style={'marginBottom': 50, 'marginTop': 25, 'marginLeft':15, 'marginRight':15})
    , width=2)

    ,dbc.Col(html.Div([
            dcc.Tabs(id="tabs", value='tab-visualisation', children=[
                    dcc.Tab(label='Visuals', value='tab-visualisation')
                    ,dcc.Tab(label='DSI Heatmap', value='tab-dsi')
                    ,dcc.Tab(label='Alerts', value='tab-alerts')
                    ,dcc.Tab(label='Shift Lever', value='tab-shift-lever') 
                    ,dcc.Tab(label='Import Cofill Lever', value='tab-import-cofill')
                    ,dcc.Tab(label='Alter Demand', value='tab-alter-demand')
                ])
            , html.Div(id='tabs-content')
        ]), width=10)])
    
    ])


@app.callback(Output('confirm-reset', 'displayed'),
              Input('reset-data', 'n_clicks'))
def display_confirm(n_clicks):
    if n_clicks > 0:
        return True
    return False


@app.callback(
    Output('data-refresh-status', 'children'),    
    [Input('confirm-reset', 'submit_n_clicks')]
    )
def update_refresh(submit_n_clicks):  
    
    from database import transforms
    message = ''
    if submit_n_clicks:
        #message = 'Feature still to be tested'
        print("inside refresh data")
        try:
            transforms.get_data_from_db(config.INPUT_PICKLE_DIR)
            message = "Data refreshed"
        except Exception as e:
            message = f"Exception occured while loading data from database: {e}"

    return message



# @app.server.route('/download_viz_data/')
# def download_viz_data():

#     df_dict = transforms.df_dict   

#     #Convert DF
#     strIO = io.BytesIO()
#     excel_writer = pd.ExcelWriter(strIO, engine="xlsxwriter")

#     for key, value in df_dict.items():   
#         value.to_excel(excel_writer, sheet_name=key)
    
#     excel_writer.save()
#     excel_data = strIO.getvalue()
#     strIO.seek(0)

#     return flask.send_file(strIO,
#                      attachment_filename='visualisation_data.xlsx',
#                      as_attachment=True)


@app.callback(
    Output('viz-data-export-status', 'children'),    
    [Input('export-viz-data', 'n_clicks')]
    )
def download_viz_data(n_clicks):

    if n_clicks > 0:

        df_dict = transforms.df_dict   

        if not os.path.exists(config.OUTPUT_VIZ_DATA_DIR):
            os.makedirs(config.OUTPUT_VIZ_DATA_DIR)

        path_to_file = os.path.join(config.OUTPUT_VIZ_DATA_DIR, 'visualisation_data.xlsx')

        with pd.ExcelWriter(path_to_file) as writer:
            for key, value in df_dict.items():   
                value.to_excel(writer, sheet_name=key)


        return f"Data downloaded to {config.OUTPUT_VIZ_DATA_DIR}"
    
    return ""



@app.callback(
    Output('data-export-status', 'children'),    
    [Input('export-baseline-data', 'n_clicks')]
    )
def download_baseline_data(n_clicks):

    if n_clicks > 0:

        baseline_list = [config.DEMAND_PICKLE, config.INVENTORY_PICKLE, config.MOVEMENT_PICKLE, config.SUPPLY_PLAN_COFILL_PICKLE, 
                            config.SUPPLY_PLAN_INHOUSE_PICKLE, config.SUPPLY_PLAN_INHOUSE_LINELOADING_PICKLE]

        if not os.path.exists(config.OUTPUT_BASELINE_DIR):
            os.makedirs(config.OUTPUT_BASELINE_DIR)                         

        for item in baseline_list: 
            df = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, item))
            df.to_csv(os.path.join(config.OUTPUT_BASELINE_DIR, f"{item}.csv"))


        import shutil
        shutil.copy2(os.path.join(config.INPUT_LEVER_DIR , config.SHIFT_LEVER_FILE), config.OUTPUT_BASELINE_DIR)


        return f"Data downloaded to {config.OUTPUT_BASELINE_DIR}"
    
    return ""

   