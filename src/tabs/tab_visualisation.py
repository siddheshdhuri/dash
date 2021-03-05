import warnings
warnings.filterwarnings("ignore")

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc 
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import matplotlib
from dash.dependencies import Input, Output
import dash_table
from app import app
from database import transforms
from alerts import alerts
from planner import baseline
import seaborn as sns
import os
import math
from utils import config


layout = html.Div([
    dbc.Row([
        html.Button('Refresh Visuals', id='refresh-visuals', n_clicks=0)  
    ]),
    dbc.Row([        
        dbc.Col([
            dcc.Loading(
            id="loading-demand-supply",
            type="default",
            children=html.Div(id="demand-supply-chart", className="five columns")
        )])                     
    ]),
    dbc.Row([                
        dcc.Dropdown(
            id='exclude-cofill-movements',
            options=[
                    {'label': 'Exclude Cofill Movements', 'value': 'True'},
                    {'label': 'Include Cofill Movements', 'value': 'False'}                    
                ],
            value='False',
            style=dict(
                    width='250px'                                       
                )
        )],
        align="end",
    ),
    dbc.Row([               
        dbc.Col([
            dcc.Loading(
            id="loading-inventory",
            type="default",
            children=html.Div(id='inventory-chart', className="five columns"))
        ]),        
        dbc.Col([
            dcc.Loading(
            id="loading-production",
            type="default",
            children=html.Div(id='production-chart', className="five columns"))                    
        ])
    ]),
    dbc.Row([html.P("Line Utilisation")]),
    dbc.Row([        
        dbc.Col([html.Div(id='line-utilisation-chart', className="five columns")])
    ]),
    dbc.Row([html.P("Freight & Deliveries")]),
    dbc.Row([        
        dbc.Col([html.Div(id='freight-chart', className="five columns")])
    ])
])

# Demand Supply Chart
@app.callback(Output('demand-supply-chart', "children"),
[Input('summary-portfolio', 'value')],
[Input('uom', 'value')],
[Input('refresh-visuals', 'n_clicks')],
[Input('exclude-cofill-movements', 'value')]
)
def update_demand_supply(summary_portfolio, uom, n_clicks, exclude_cofill_movements):        
    
    pd.options.display.float_format = '{:,.2f}'.format

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
           

    if ('uom' in changed_id) |( 'refresh-visuals' in changed_id):
        # for uom and refresh recalculate data
        combined_df, long_df = transforms.get_comined_long_and_wide_df(uom=uom)
        transforms.combined_df = combined_df
        transforms.lonf_df = long_df
    else:
        combined_df = transforms.combined_df
        long_df = transforms.long_df


    demand_supply_df = long_df.loc[long_df.Parent_Category.isin(['Demand', 'Supply'])]
    inventory_df =  combined_df[['Summary_Portfolio','Year_Period', 'Inventory_Closing','Inventory_National_Target','Inventory_Other']]

    plot_df = pd.merge(demand_supply_df, inventory_df, on=['Summary_Portfolio','Year_Period'], how='inner')

    
    if summary_portfolio == 'Total_GB':
        plot_df = plot_df.groupby(['Year_Period', 'Parent_Category', 'Category']).sum().reset_index()
    else:
        plot_df = plot_df[plot_df.Summary_Portfolio == summary_portfolio]   

    plot_df = plot_df.round(0)    

    fig = go.Figure()
    
    fig.update_layout(
        template="simple_white",
        xaxis=dict(title_text="Year Period"),
        yaxis=dict(title_text="Units", tickformat=".2s", showgrid= True),
        barmode="stack",
        #bargap=0.1,
        bargroupgap = 0.5       
    )

    colors = sns.color_palette("rocket").as_hex()

    if exclude_cofill_movements == "True":
        plot_df = plot_df.loc[plot_df.Category != 'Cofill_Movement']
        labels={"Import": "Supply_Imports", 
        "Production": "Supply_Production",
        "Cofill": "Supply_Cofill",             
        "Total": "Demand_Domestic_Sales",
        "Domestic Repack": "Demand_Domestic_Repack",
        "Export": "Demand_Export"}

    else:
        labels={"Import": "Supply_Imports", 
            "Production": "Supply_Production",
            "Cofill": "Supply_Cofill",     
            "Cofill_Movement": "Supply_Cofill_Movement",  
            "Total": "Demand_Domestic_Sales",
            "Domestic Repack": "Demand_Domestic_Repack",
            "Export": "Demand_Export"}

    plot_df.Category = [labels[x] for x in plot_df.Category]    

    categories = plot_df.Category.unique().tolist()
    categories.sort()

    for r, c in zip(categories, colors):   
        this_df = plot_df[plot_df.Category == r]
        
        fig.add_trace(
            go.Bar(x=[this_df.Year_Period, this_df.Parent_Category], y=this_df.Value, name=r, marker_color=c),
        )    

    transforms.df_dict['Demand_Supply'] = plot_df

    inv_df = plot_df.sort_values(by=['Year_Period', 'Parent_Category'])        
    
    fig.add_trace(
            go.Scatter(x=[inv_df.Year_Period, inv_df.Parent_Category] ,y=inv_df.Inventory_Closing, name='Inventory_Closing')
    )   
    
    return html.Div([
        dcc.Graph(
            id='demand-supply-fig'
            , figure=fig
        )
    ])


# Inventory Chart
# Inventory Chart
@app.callback(Output('inventory-chart', "children"),
[Input('summary-portfolio', 'value')
, Input('uom', 'value')
, Input('refresh-visuals', 'n_clicks')
])
def update_inventory(summary_portfolio, uom, n_clicks):    

    pd.options.display.float_format = '{:,.0f}'.format

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    
    plot_df = transforms.get_dsi_plot(summary_portfolio, uom)


    if summary_portfolio == 'Total_GB':
        plot_df = plot_df.groupby(['Year_Period']).sum().reset_index()
        
    else:
        plot_df = plot_df.loc[plot_df.Summary_Portfolio == summary_portfolio]    

    plot_df = plot_df.fillna(0)
    plot_df = plot_df.round(0)
    
    fig = go.Figure()
    fig = go.FigureWidget(fig)



    fig.update_layout(
        template="simple_white",
        xaxis=dict(title_text="Year Period"),
        yaxis=dict(title_text="Days", showgrid= True)    
    )

    bar_cols = ['Planned_North', 'Planned_South', 'Planned_Scotland', 'Planned_National']
    colors = sns.color_palette("Oranges_r").as_hex()

    for column, color in zip(bar_cols, colors):       
        fig.add_trace(
            go.Bar(x=plot_df['Year_Period'], y=plot_df[column], name=column, marker_color=color),
        )
        
    fig.add_trace(
            go.Scatter(x=plot_df.Year_Period ,y=plot_df.Target_National, name='Target_National')
    ) 
     
    transforms.df_dict['Inventory'] = plot_df

    return html.Div([
        dcc.Graph(
            id='inventory-fig'
            , figure=fig
        )
    ])




#Production Chart
@app.callback(Output('production-chart', "children"),
[Input('summary-portfolio', 'value')
, Input('uom', 'value')
, Input('refresh-visuals', 'n_clicks')
])
def update_production_chart(summary_portfolio, uom, n_clicks):    

    pd.options.display.float_format = '{:,.0f}'.format

    index_cols = ['Year_Period']
    bar_cols = ['Consumed','Unused','SpareHours','Planned_Downtime', 'Loss_Factor', 'Uncrewed']
    line_cols = []

    production_line_plan = transforms.get_production_line_plan()
    shift_lever = pd.read_csv('input/levers/shift_lever.csv')

    production_line_plan.Site_SAP = production_line_plan.Site_SAP.astype(str)
    shift_lever.Site_SAP = shift_lever.Site_SAP.astype(str)

    plot_df = pd.merge(production_line_plan, shift_lever, on=['Site_SAP', 'Line', 'Year_Period'], how='inner')

    plot_df = plot_df[['Line_Portfolio', 'Site_SAP', 'Line', 'Year_Period', 
            'Capacity', 'Consumed', 'SpareHours', 'Hours_Down_Time', 'Hours_Sched_PDT', 
            'Hours_Crew', 'Weeks_In_Period'
            ]]

    plot_df.columns = ['Line_Portfolio', 'Site_SAP', 'Line', 'Year_Period', 
                    'Capacity', 'Consumed', 'SpareHours', 'Planned_Downtime', 'Loss_Factor',
                    'Hours_Crew', 'Weeks_In_Period'
                    ]
    plot_df['Uncrewed'] = plot_df['Weeks_In_Period']*168 - plot_df['Hours_Crew']

    #plot_df = production_hours.copy()

    if summary_portfolio == 'Total_GB':
        
        plot_df = plot_df.groupby(['Year_Period']).sum().reset_index()
        
    else:
        if summary_portfolio.startswith('Cans'):
            summary_portfolio = 'Cans'

        plot_df = plot_df.loc[plot_df.Line_Portfolio == summary_portfolio]

    
    plot_df = plot_df.groupby(['Year_Period']).sum().reset_index()    

    plot_df['Percent_Consumed'] = round(plot_df['Consumed']*100 / plot_df['Capacity'],0).fillna(0)
    plot_df['Unused'] = plot_df['Capacity'] - plot_df['Consumed']

    plot_df = plot_df[index_cols + bar_cols + line_cols + ['Percent_Consumed']]     
    
    
    fig = go.Figure()

    fig.update_layout(
        template="simple_white",
        xaxis=dict(title_text="Year Period"),
        yaxis=dict(title_text="Hours", showgrid= True),
        #yaxis=dict(title_text="Hours", tickformat='.1s', showgrid= True),
        barmode="stack",
    )

    colors = sns.color_palette("Blues_r").as_hex()[:2] + \
            sns.color_palette("gray").as_hex()[5:6] + \
            sns.color_palette("YlOrRd").as_hex()[:2] + \
            sns.color_palette("Greens").as_hex()[:1]


    for column, color in zip(bar_cols, colors): 
        if column == 'Consumed':            

            fig.add_trace(
                go.Bar(x=plot_df['Year_Period'], y=plot_df[column], name=column, marker_color=color, 
                customdata=plot_df['Percent_Consumed'].astype(int).astype(str)+'%',
                texttemplate="%{customdata}",
                textposition="inside",
                textangle=0,
                textfont_color="white"                
                )
            )
        else:
            fig.add_trace(
                go.Bar(x=plot_df['Year_Period'], y=plot_df[column], name=column, marker_color=color),
            )

    colors = sns.color_palette("rocket").as_hex()
    for column, color in zip(line_cols, colors):       
        fig.add_trace(
            go.Scatter(x=plot_df['Year_Period'], y=plot_df[column], name=column, marker_color=color),
        )       
             
    transforms.df_dict['ProductionHours'] = plot_df

    return html.Div([
        dcc.Graph(
            id='production-fig'
            , figure=fig
        )
    ])



#Line Utilisation Chart
@app.callback(Output('line-utilisation-chart', "children"),
        [Input('summary-portfolio', 'value')
        , Input('uom', 'value')
        , Input('include-safety-hours', 'value')
        , Input('refresh-visuals', 'n_clicks')         
        ])
def update_line_utilisation(summary_portfolio, uom, include_safety_hours, n_clicks):    

    pd.options.display.float_format = '{:,.0f}'.format

    production_line_plan = transforms.get_production_line_plan()
    shift_lever = pd.read_csv('input/levers/shift_lever.csv')

    production_line_plan.Site_SAP = production_line_plan.Site_SAP.astype(str)
    shift_lever.Site_SAP = shift_lever.Site_SAP.astype(str)

    plot_df = pd.merge(production_line_plan, shift_lever, on=['Site_SAP', 'Line', 'Year_Period'], how='inner')

    if summary_portfolio == 'Total_GB':        
        plot_df = plot_df.groupby(['Site_SAP','Line','Year_Period']).sum().reset_index()
        
    else:        
        plot_df = plot_df[plot_df.Line_Portfolio == summary_portfolio]


    key_cols = ['Site_SAP','Line', 'Year_Period']
    if include_safety_hours == 'True':
        value_cols = ['Capacity_Utilisation', 'Available_Vol_with_Safety_Hours']
        vol_col = 'Available_Vol_with_Safety_Hours'
    else:
        value_cols = ['Capacity_Utilisation', 'Available_Vol']
        vol_col = 'Available_Vol'

    # Totals df
    totals = plot_df[['Year_Period', vol_col, 'Capacity', 'Consumed']]
    totals = totals.groupby('Year_Period').sum()
    totals['Capacity_Utilisation'] = round(totals['Consumed']*100 / totals['Capacity'], 2)
    totals = totals[value_cols]
    totals.columns = ['Total_'+s  for s in value_cols]
    totals = totals[['Total_'+s  for s in value_cols]].T
    totals.reset_index(inplace=True)
    totals.rename(columns = {"index": "Line_Utilisation"}, inplace = True) 

    totals['Site_SAP'] = 'All Sites'
    totals['Line'] = 'All Lines'


    long_df = plot_df.melt(id_vars=key_cols, 
    value_vars=value_cols,
    var_name='Line_Utilisation', value_name='Value')

    pivot_cols = ['Year_Period']
    pivot_rows = ['Site_SAP','Line', 'Line_Utilisation']
    value_col = ['Value']
    agg_func = np.sum

    line_util = pd.pivot_table(long_df, values=value_col, index=pivot_rows,
                                columns=pivot_cols, aggfunc=agg_func)   

    line_util = line_util.fillna(0)    
    line_util = line_util.round(0).astype(int)

    if len(line_util) <= 0:
        return html.Div([html.B("NO LINES")])

    line_util = pd.DataFrame(line_util.to_records())

    line_util.columns = [hdr.replace("('Value', '", "").replace("')", "") for hdr in line_util.columns] 

    # Column totals
    line_util_totals = line_util.drop(['Site_SAP', 'Line'], axis=1).groupby(['Line_Utilisation']).sum().reset_index()
    line_util_totals['Site_SAP'] = 'All Sites'
    line_util_totals['Line'] = 'All Lines'

    line_util = pd.concat([line_util, totals])


    #' format numbers in table
    line_util_avail = line_util.loc[line_util.Line_Utilisation.str.contains('Available')]
    for col in line_util_avail.columns.tolist():
        if col.startswith('20'):
            line_util_avail[col] = line_util_avail.apply(lambda x: "{:,}".format(x[col]), axis=1)

    

    line_util_capacity = line_util.loc[line_util.Line_Utilisation.str.contains('Capacity')]
    for col in line_util_capacity.columns.tolist():
        if col.startswith('20'):
            line_util_capacity[col] = line_util_capacity.apply(lambda x: "{0:.0f}%".format(x[col]), axis=1)

    

    line_util = pd.concat([line_util_avail, line_util_capacity])

    line_util = line_util.sort_values(['Site_SAP', 'Line'])

    transforms.df_dict['LineUtilisation'] = plot_df

    return html.Div([
        dash_table.DataTable(
                            id='line-utilisation-tab',
                            columns=[
                                {'name': i, 'id': i, 'deletable': True} for i in line_util[line_util.columns]
                            ],
                            data=line_util.to_dict('records'),
                            style_table={
                                    'overflowY': 'scroll'
                                },
                            style_data = {'text-align': 'center'},
                            style_data_conditional=[
                                {
                                    'if': {
                                        'filter_query': '{Line} contains "All"'
                                    },
                                    'backgroundColor': '#33A7F8',
                                    'color': 'white'
                                }                            

                            ]
                            
                        )
    ])  


#Freight Chart
@app.callback(Output('freight-chart', "children"),
        [Input('summary-portfolio', 'value')
        , Input('uom', 'value')
        , Input('refresh-visuals', 'n_clicks')
        ])
def update_freight(summary_portfolio, uom, n_clicks):       

    freight_df = transforms.get_freight_plan(level='Summary_Portfolio', uom='Trucks', portfolio=summary_portfolio)

    if len(freight_df) <= 0:
        return html.Div([html.B("NO FREIGHT DATA FOUND")])


    transforms.df_dict['Freight'] = freight_df

    return html.Div([
        dash_table.DataTable(
                            id='freight-tab',
                            columns=[
                                {'name': i, 'id': i, 'deletable': True} for i in freight_df[freight_df.columns]
                            ],
                            data=freight_df.to_dict('records'),
                            style_data = {'text-align': 'center'},
                            style_data_conditional=[
                                {
                                    'if': {
                                        'filter_query': '{index} contains "Grand"'
                                    },
                                    'backgroundColor': '#33A7F8',
                                    'color': 'white'
                                },
                                {
                                    'if': {
                                        'filter_query': '{index} contains "Total"'
                                    },
                                    'backgroundColor': '#CDE7F9',
                                    'color': 'black'
                                }                                

                            ]
                        )
    ])  



    
   





