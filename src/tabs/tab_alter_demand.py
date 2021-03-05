import dash
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc 
import dash_core_components as dcc
import dash_table
import dash_html_components as html
from app import app
import pandas as pd
from alerts import alerts
from utils import config
import os
from database import transforms
from planner import baseline
import logging

snp_list = transforms.snp_list
material_list = transforms.material_list

alter_demand_table = transforms.alter_demand_table

shift_data = pd.read_csv(os.path.join(config.INPUT_LEVER_DIR , config.SHIFT_LEVER_FILE))

alter_demand_lever = pd.read_csv(os.path.join(config.INPUT_LEVER_DIR, 'alter_demand_lever.csv'))


logging.basicConfig(filename='output.log')

layout = html.Div([
    dbc.Row([
        dbc.Col([html.B('Edit The following to alter demand for a material or SNP portfolio')])
    ]),
    dbc.Row([
        dcc.Dropdown(
                id='select-level',
                options=[{'label': i, 'value': i} for i in ['SNPPL01', 'Material']], 
                value='SNPPL01',                               
                style=dict(
                    width='100px'                    
                )
            ),
        dcc.Dropdown(
                id='select-item',
                options=[{'label': str(i), 'value': i} for i in alter_demand_table.SNPPL01.unique()],                
                placeholder="Select Item",
                style=dict(
                    width='400px'                    
                ),
                multi=True
            ),
        dcc.Dropdown(
                id='select-period',
                options=[{'label': i, 'value': i} for i in shift_data.Year_Period.unique()],                
                style=dict(
                    width='200px'                    
                )
            ),
        dcc.Input(
            id="increment",
            type="number",
            placeholder="Increment by",
            style=dict(
                    width='200px'                    
                )
        ),
        dcc.Dropdown(
                id='select-increase-type',
                options=[{'label': i, 'value': i} for i in ['Absolute', 'Percentage']],
                value='Percentage',                
                style=dict(
                    width='200px'                    
                )
            ), 
        html.Button('Add Demand', id='add-demand', n_clicks=0)
        
    ]),
    dbc.Row([
        html.Button('Apply Updates', id='apply-alter-demand', n_clicks=0)
        ,html.Button('Clear Lever', id='clear-lever', n_clicks=0)
    ]),
    dbc.Row([
        html.Div([
           dash_table.DataTable(
                id='alter-demand-preview',
                columns=[
                    {'name': i.replace("_", " "), 'id': i} for i in alter_demand_lever[alter_demand_lever.columns]            
                ],
                data=alter_demand_lever.to_dict('records'),
                editable=False,
                #row_deletable=True,
                style_header={
                    'minWidth': '0px', 'maxWidth': '100px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                }
            )
        ])        
    ]),
    dbc.Row([        
        dcc.Loading(
            id="loading-3",
            type="default",
            children=html.Div(id='alter-demand-short-summary', children='')
        ) 
    ]),
    dbc.Row([        
        dcc.Loading(
            id="loading-1",
            type="default",
            children=html.Div(id='alter-demand-summary', children='')
        ) 
    ]),
    dbc.Row([        
        dcc.Loading(
            id="loading-2",
            type="default",
            children=html.Div(id='alter-demand-update', children='')
        ) 
    ])
       
])


def get_line_loading_plan():
    line_loading = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.SUPPLY_PLAN_INHOUSE_LINELOADING_PICKLE))    
    line_loading.Site_SAP = line_loading.Site_SAP.astype(str) 
    line_loading = line_loading.loc[line_loading.KeyField.isin(['Capacity', 'Consumed', 'SpareHours'])].drop(['Material','Line_Portfolio','Uom'], axis=1)
    line_loading = pd.pivot_table(line_loading, values='Value', index=['Site_SAP', 'Line', 'Year_Period'],
                                        columns='KeyField', aggfunc=sum).reset_index()
    line_loading['Site_Line_Period'] = line_loading[['Site_SAP', 'Line', 'Year_Period']].agg(' - '.join, axis=1)

    return line_loading

def get_inhouse_prod_plan():
    inhouse_production = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.SUPPLY_PLAN_INHOUSE_PICKLE))  
    inhouse_production.Site_SAP = inhouse_production.Site_SAP.astype(str) 
    inhouse_production['Site_Line_Period'] = inhouse_production[['Site_SAP', 'Line', 'Year_Period']].agg(' - '.join, axis=1) 

    return inhouse_production


#' Callbacks

@app.callback(Output('select-item', 'options'),
              [Input('select-level', 'value')]              
            )
def update_material_list(selected_level):    
    
    if selected_level == 'SNPPL01':
        item_list = transforms.alter_demand_table.SNPPL01.unique()
    else:
        item_list = transforms.alter_demand_table.Material_Desc.unique()    
    
    return [{'label': str(i), 'value': i.split(' - ')[0]} for i in item_list]
    



@app.callback(
    Output('alter-demand-preview', 'data'),
    [Input('alter-demand-preview', 'data_timestamp')],
    [Input('add-demand', 'n_clicks')],
    [Input('clear-lever', 'n_clicks')],
    [State('select-level', 'value')],
    [State('select-item', 'value')],
    [State('select-period', 'value')],
    [State('increment', 'value')],
    [State('select-increase-type', 'value')],
    [State('alter-demand-preview', 'data')]
    )
def update_columns(timestamp, n_clicks, n_clicks2, level, items, period, increment, inc_type, rows):

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    #' if clear clicked then clear the lever data
    if 'clear-lever' in changed_id:
        alter_demand_lever_full = pd.read_csv(os.path.join(config.INPUT_LEVER_DIR, 'alter_demand_lever_full.csv'))
        alter_demand_lever = pd.read_csv(os.path.join(config.INPUT_LEVER_DIR, 'alter_demand_lever.csv'))
        
        alter_demand_lever_full = alter_demand_lever_full.head(0)
        alter_demand_lever = alter_demand_lever.head(0)

        alter_demand_lever_full.to_csv(os.path.join(config.INPUT_LEVER_DIR, 'alter_demand_lever_full.csv'), index=False)
        alter_demand_lever.to_csv(os.path.join(config.INPUT_LEVER_DIR, 'alter_demand_lever.csv'), index=False)
   
    
        return alter_demand_lever.to_dict('rows')

    #' Apply updates clicked for every row in lever apply changes
    elif 'add-demand' in changed_id:
        alter_demand_lever_full = pd.read_csv(os.path.join(config.INPUT_LEVER_DIR, 'alter_demand_lever_full.csv'))
        
        if increment is None:            
            return

        if n_clicks == 1:
            #' remove existing lever data on first click            
            alter_demand_lever_full = alter_demand_lever_full.head(0)                        

        alter_demand_table = transforms.alter_demand_table
        alter_demand_table = alter_demand_table.loc[(alter_demand_table.Uom=='ZUC') & (alter_demand_table.KeyField=='Total') & (alter_demand_table.Year_Period==period)]
        
                
        material_list = items
        if level=='SNPPL01':            
            selected_snp = alter_demand_table.loc[alter_demand_table.SNPPL01.isin(items)]
            material_list = selected_snp.Material.tolist()       
              
        
        alter_demand_table = alter_demand_table.loc[alter_demand_table.Material.astype(str).isin(material_list)]        

        if inc_type == 'Percentage':
            inc_percent = increment/100
        else:
            total_value = sum(alter_demand_table.Value)
            inc_percent = increment / total_value

        alter_demand_table['Value'] = alter_demand_table['Value'].astype(float)
        alter_demand_table['NewValue'] = round(alter_demand_table['Value'] + alter_demand_table['Value']*inc_percent,0)   
        alter_demand_table['Units_Required'] = alter_demand_table['NewValue'] - alter_demand_table['Value']

        
        to_add = alter_demand_table[['SNPPL01', 'Material', 'MaterialDescription', 'Year_Period', 'Value', 'NewValue', 'Units_Required']]
        to_add = to_add.groupby(['SNPPL01', 'Material', 'MaterialDescription', 'Year_Period']).sum().reset_index()        
        
        alter_demand_lever_full = alter_demand_lever_full.append(
                                        alter_demand_table[['Site_SAP','Year_Period','Summary_Portfolio','Material', 'MaterialDescription', 'KeyField','Uom','Value','NewValue', 'Units_Required']],
                                        ignore_index=True
                                    )
                                    
        alter_demand_lever_full = alter_demand_lever_full.round()
        alter_demand_lever_full.to_csv(os.path.join(config.INPUT_LEVER_DIR, 'alter_demand_lever_full.csv'), index=False)

        alter_demand_lever = pd.DataFrame.from_dict(rows)       

        alter_demand_lever = alter_demand_lever.append(to_add, ignore_index=True)
        alter_demand_lever = alter_demand_lever.round()


        alter_demand_lever.to_csv(os.path.join(config.INPUT_LEVER_DIR, 'alter_demand_lever.csv'), index=False)       

        return alter_demand_lever.to_dict('rows')
        

@app.callback([Output('alter-demand-update', "children"),
              Output('alter-demand-summary', "children"),
              Output('alter-demand-short-summary', "children")],
    [Input('apply-alter-demand', 'n_clicks')],
    [State('alter-demand-preview', 'data')]
)  
def update_output(n_clicks, rows):  
    
    if(n_clicks > 0):      

        result_list = ['Following updates:',  html.Br()]    
        logging.info('Following updates:')                
        summary_table = pd.DataFrame(columns=['Period', 'Demand_Site', 'Supply_Site', 'Line', 'Units_Made', 'TimeAvailable', 'Time_Used', 'TimeRemaining', 'Trucks'])

        try:            
            alter_demand_lever_full = pd.read_csv(os.path.join(config.INPUT_LEVER_DIR, 'alter_demand_lever_full.csv'))

            for index, row in alter_demand_lever_full.iterrows():               

                result_list.extend([f"------------------------ {index+1} -----------------------------", html.Br()])
                logging.info(f"------------------------ {index+1} -----------------------------")

                demand_site = str(row['Site_SAP'])
                material = str(row['Material'])
                demand_period = row['Year_Period']
                units_required = row['Units_Required']

                #'update the Total demand required at this site
                baseline.update_demand(demand_site,  demand_period, material, units_required, keyfield='Total')

                result_list.extend([f''' Lever Row Period: {demand_site} Material: {material} Current Demand {row['Value']} 
                                     NewDemand {row['NewValue']} Additional Units {units_required}''', html.Br()])      
                logging.info(f''' Lever Row Period: {demand_site} Material: {material} Current Demand {row['Value']} 
                                     NewDemand {row['NewValue']} Additional Units {units_required}''')          
                
                #' read line_loading and inhouse production as these might have been updated in the last iteration
                line_loading = get_line_loading_plan()
                inhouse_production = get_inhouse_prod_plan()                              

                #' We will produce item in P-1 and P to satisfy demand in P
                periods_to_produce = transforms.get_previous_n_periods(demand_period, 1)                
                
                # for each available period make units
                for period in periods_to_produce:                 
                    
                    if units_required == 0:
                            break

                    result_list.extend([f'trying in period {period}', html.Br()])
                    logging.info(f'trying in period {period}')

                    #' Get Lines where this product is being manufactured 
                    this_inhouse_production = inhouse_production[(inhouse_production.Material == material) & (inhouse_production.Year_Period == period)].drop_duplicates(subset=["Site_Line_Period"])                                                                  
                    result_list.extend([f''' {len(this_inhouse_production)} Sites: {", ".join(this_inhouse_production.Site_Line_Period.tolist())} can make {material} in {period} ''', html.Br()])                  

                    line_loading = get_line_loading_plan()
                    this_line_loading = pd.merge(line_loading, this_inhouse_production.drop(['Site_SAP', 'Line', 'Year_Period'] , axis=1),
                                                 on="Site_Line_Period", how='inner')                      
                    
                                        
                    for index, line_row in this_line_loading.iterrows():

                        if (units_required < 1) & (units_required > -1):
                            break
                        #' get available hours on line
                        available_hours =  round(line_row['Capacity'] - line_row['Consumed'],2)
                        supply_site = line_row['Site_SAP']
                        supply_line = line_row['Line']

                        result_list.extend([f''' BEFORE: Line Loading at {supply_site} - {supply_line}: Capacity: {line_row['Capacity'] } 
                                                Consumed: {line_row['Consumed']} Spare: {round(line_row['SpareHours'])} ''', html.Br()])
                        logging.info(f''' BEFORE: Line Loading at {supply_site} - {supply_line}: Capacity: {line_row['Capacity'] } 
                                                Consumed: {line_row['Consumed']} Spare: {round(line_row['SpareHours'])} ''')

                        result_list.extend([f" {available_hours} hours are available at {supply_site} - {supply_line}", html.Br()])
                        logging.info(f" {available_hours} hours are available at {supply_site} - {supply_line}")
                                                
                        if (available_hours > 1) & (units_required > 1):
                            #' if there is some capacity then make units at this line
                            try:
                                units_made, time_remaining, time_used, line_loading_update, inhouse_prod_update = baseline.make_units(available_hours, units_required, 
                                                                                                                material, supply_site, 
                                                                                                                supply_line, period)     
                                                                
                                result_list.extend([inhouse_prod_update, f'Time Used: {time_used} Time_Remaining: {time_remaining} ' , html.Br(), 
                                                    'AFTER:', line_loading_update, html.Br()])
                                logging.info(inhouse_prod_update)
                                logging.info(f'Time Used: {time_used} Time_Remaining: {time_remaining} ')
                                logging.info(line_loading_update)

                                
                                # update the inventory and movement plan if the demand and supply site are different                                
                                units_update, trucks, movement_update = baseline.update_units_and_movements('INVENTORY', demand_site, supply_site, period, 
                                                                                                        material, units_made, inventory_key=['ZUC_ClosingStock', 'ZUC_ClosingStockTarget', 'ZUC_StockVsTarget'])

                                result_list.extend([units_update, html.Br(), movement_update, html.Br()])
                                logging.info(units_update)
                                logging.info(movement_update)

                                units_required = units_required - units_made

                                summary_table = summary_table.append({'Period': period, 'Demand_Site': demand_site, 'Supply_Site': supply_site,
                                                                        'Line': supply_line, 'Units_Made': units_made, 'TimeAvailable': available_hours , 
                                                                        'Time_Used': time_used, 'TimeRemaining': time_remaining, 'Trucks': trucks}
                                                                        , ignore_index=True)
                                

                            except Exception as e:                                
                                result_list.extend([str(e), html.Br()])
                            
                result_list.extend([f"---------------------------------------------------------", html.Br()])
                

                #' Update the alter demand table
                alter_demand_table = transforms.get_alter_demand_table()
                transforms.alter_demand_table = alter_demand_table

                summary_table = summary_table.round(2)
                summary_output = html.Div(                                
                                [
                                    html.B('Detailed Summary'), html.Br(),
                                    dash_table.DataTable(
                                                        id='summary-tab',
                                                        columns=[
                                                            {'name': i, 'id': i, 'deletable': False} for i in summary_table.columns if i != 'id'
                                                        ],
                                                        data=summary_table.to_dict('records')                            
                                                    )
                                ])

                short_summary = summary_table[['Period', 'Line', 'Units_Made', 'Time_Used', 'Trucks']]
                short_summary['Units_Made'] = short_summary['Units_Made'].astype('int32')

                short_summary = short_summary.groupby(['Period', 'Line']).sum().reset_index()
                short_summary = short_summary.round(2)

                short_summary_output = html.Div(                                                
                                                [   html.B('Short Summary'), html.Br(),
                                                    dash_table.DataTable(
                                                                        id='summary-tab',
                                                                        columns=[
                                                                            {'name': i, 'id': i, 'deletable': False} for i in short_summary.columns if i != 'id'
                                                                        ],
                                                                        data=short_summary.to_dict('records')                            
                                                                    )
                                                ]
                                            )

                total_units_made = short_summary.Units_Made.sum()
                total_units_reqd = alter_demand_lever_full.Units_Required.sum()
                unfulfilled = total_units_reqd - total_units_made
                return_string = ''
                if unfulfilled > 0:
                    return_string = f' {unfulfilled} units unfulfilled'

        except Exception as e:
            print(f"Exception Occurred while doing updates {e}")
            result_list.extend([str(e), html.Br()])           
       
       

        return return_string, summary_output, short_summary_output

    else:
        return '', '', ''


