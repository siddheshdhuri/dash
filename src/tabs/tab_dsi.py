import dash
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc 
import dash_core_components as dcc
import dash_table
import dash_html_components as html
from app import app
import pandas as pd
from database import transforms

layout = html.Div([
    dbc.Row([
        dbc.Col([html.B('Target DSI')])
    ]),
    dbc.Row([        
        dcc.Loading(
            id="loading-2",
            type="default",
            children=html.Div(id='dsi-target-heatmap', className="five columns") 
        ) 
    ]),   
    dbc.Row([
        dbc.Col([html.B('Planned DSI')])
    ]),
    dbc.Row([        
        dcc.Loading(
            id="loading-1",
            type="default",
            children=html.Div(id='dsi-planned-heatmap', className="five columns") 
        ) 
    ])   
    ,dbc.Row([
        dbc.Col([html.B('Diff DSI')])
    ])
    ,dbc.Row([        
        dcc.Loading(
            id="loading-3",
            type="default",
            children=html.Div(id='dsi-diff-heatmap', className="five columns") 
        ) 
    ]) 
    
])


@app.callback(Output('dsi-planned-heatmap', "children"),
        [Input('summary-portfolio', 'value')
        , Input('uom', 'value')
        ])
def update_dsi_planned_heatmap(summary_portfolio, uom):   

    planned_dsi = transforms.planned_dsi

    transforms.df_dict['PlannedDSI'] = planned_dsi

    return html.Div([
        dash_table.DataTable(
                            id='dsi-planned-heat-tab',
                            columns=[
                                {'name': i, 'id': i, 'deletable': False} for i in planned_dsi.columns if i != 'id'
                            ],
                            data=planned_dsi.to_dict('records')                            
                        )
    ])  
    


@app.callback(Output('dsi-target-heatmap', "children"),
        [Input('summary-portfolio', 'value')
        , Input('uom', 'value')
        ])
def update_dsi_target_heatmap(summary_portfolio, uom):   

    target_dsi = transforms.target_dsi

    return html.Div([
        dash_table.DataTable(
                            id='dsi-diff-heat-tab',
                            columns=[
                                {'name': i, 'id': i, 'deletable': False} for i in target_dsi.columns if i != 'id'
                            ],
                            data=target_dsi.to_dict('records')                            
                        )
    ])  




@app.callback(Output('dsi-diff-heatmap', "children"),
        [Input('summary-portfolio', 'value')
        , Input('uom', 'value')
        ])
def update_dsi_diff_heatmap(summary_portfolio, uom):   

    diff_df = transforms.diff_df

    return html.Div([
        dash_table.DataTable(
                            id='dsi-heat-tab',
                            columns=[
                                {'name': i, 'id': i, 'deletable': False} for i in diff_df.columns if i != 'id'
                            ],
                            data=diff_df.to_dict('records')                            
                        )
    ])  



# @app.callback(Output('dsi-heatmap', "children"),
#         [Input('summary-portfolio', 'value')
#         , Input('inventory-vol-uom', 'value')
#         ])
# def update_dsi_heatmap(summary_portfolio, uom):       

#     # Configure Trigger

#     dsi_heatmap_df = transforms.dsi_heatmap_df


#     def style_row_by_top_values(df, nlargest=2):
#         numeric_columns = df.select_dtypes('number').drop(['id'], axis=1).columns
#         styles = []
#         for i in range(len(df)):
#             if df.iloc[i].DSI_Type == 'Percent_Diff':
#                 row = df.loc[i, numeric_columns]                
#                 for j in range(len(numeric_columns)):
#                     if(row[j] >= 20):                        
#                         styles.append({
#                             'if': {
#                                 'filter_query': '{{id}} = {}'.format(i),
#                                 'column_id': row.keys()[j]
#                             },
#                             'backgroundColor': 'yellow',
#                             'color': 'black',
#                             'format': "{:.2f}%",
#                         })
#                     elif(row[j] <= -5):
#                         styles.append({
#                             'if': {
#                                 'filter_query': '{{id}} = {}'.format(i),
#                                 'column_id': row.keys()[j]
#                             },
#                             'backgroundColor': 'red',
#                             'color': 'white'
#                         })
#                     else:
#                         styles.append({
#                             'if': {
#                                 'filter_query': '{{id}} = {}'.format(i),
#                                 'column_id': row.keys()[j]
#                             },
#                             'backgroundColor': '#808080',
#                             'color': 'white'
#                         })
#         return styles 
    

#     dsi_heatmap_df['id'] = dsi_heatmap_df.index

#     return html.Div([
#         dash_table.DataTable(
#                             id='dsi-heat-tab',
#                             columns=[
#                                 {'name': i, 'id': i, 'deletable': True} for i in dsi_heatmap_df.columns if i != 'id'
#                             ],
#                             data=dsi_heatmap_df.to_dict('records'),
#                             style_data_conditional=style_row_by_top_values(dsi_heatmap_df)
#                         )
#     ])  

# @app.callback(
#     Output('computed-table', 'data'),
#     [Input('computed-table', 'data_timestamp')],
#     [State('computed-table', 'data')])
# def update_columns(timestamp, rows):
#     for row in rows:
#         try:            
#             row['Hours_Crew'] = int(row['Weeks_WeeksInPeriod'])*int(row['Shift_Length'])*int(row['Shifts_In_Day'])*int(row['Shift_Days_In_Week']) + float(row['Hours_Overtime'])
            
#             row['Hours_UnCrewed'] = int(row['Weeks_WeeksInPeriod'])*168 - float(row['Hours_Crew'])
            
#             row['Hours_SchedPDT'] = (float(row['Hours_Crew']) - float(row['Hours_DownTime']))*float(row['LossFactor'])
            
#             row['Hours_TotalAvailable'] = (float(row['Hours_Crew']) - float(row['Hours_DownTime']) - float(row['Hours_SchedPDT']))*float(row['SafetyHours'])
            
#         except Exception as e:
#             print("Error Occurred")
#             print(e)
#             print(type(row['Shifts_In_Day']))
#             print(f" @@@@@@@@@ SITE: {row['Site_SAP']} LINE {row['Line']} PERIOD {row['Period']}")
#     return rows
