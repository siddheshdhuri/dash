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
from database import transforms
from planner import baseline
import os

#shift_lever = transforms.get_shift_lever(pd.read_csv('input/levers/shift_lever.csv'))

layout = html.Div([
    dbc.Row([
        dbc.Col([html.B('Edit The followiing Lever to Change Shift, Overtime, Downtime, Safety Hours')])
    ]),
    html.Div([            
            html.Button('Apply Updates', id='apply-time-updates', n_clicks=0) ,
            html.Button('Refresh', id='refresh-shift-lever', n_clicks=0)  
        ]),
    dbc.Row([

        dbc.Col( 

            dcc.Loading(
                id="loading-2",
                type="default",
                children=html.Div([
                dash_table.DataTable(
                    id='shift-lever',
                    columns=[
                        {'name': i.replace("_", " "), 'id': i} for i in transforms.get_shift_lever(pd.read_csv('input/levers/shift_lever.csv')).columns  
                    ],
                    data=transforms.get_shift_lever(pd.read_csv('input/levers/shift_lever.csv')).to_dict('records'),
                    editable=True,
                    page_size=20,
                    filter_action='native',
                    style_header={
                        'minWidth': '0px', 'maxWidth': '60px',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                    },
                    style_data_conditional=[                    
                        {
                            'if': {                            
                                'column_id': 'Material_Site_DemandShortfall'
                            },
                            'minWidth': '0px', 'maxWidth': '150px',
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
                        {
                            'if': {                            
                                'column_id': 'Material_Site_InventoryShortfall'
                            },
                            'minWidth': '0px', 'maxWidth': '150px',
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
                        {
                            'if': {
                                'filter_query': '{Additional_Hours} > 0'
                            },
                            'backgroundColor': '#c5e1a5',
                            'color': 'black'
                        },
                        {
                            'if': {
                                'filter_query': '{Additional_Hours} < 0'
                            },
                            'backgroundColor': '#fbf38c',
                            'color': 'black'
                        }  
                    ]
                    
                )
            ])
            )
            
            , width=8)        
        
    ]),
    dbc.Row([
        #html.Div(id='add-time-updates', children='')
        dcc.Loading(
            id="loading-1",
            type="default",
            children=html.Div(id="add-time-updates")
        ) 
    ])
])

@app.callback(
    Output('shift-lever', 'data'),
    [Input('shift-lever', 'data_timestamp'),    
    Input('refresh-shift-lever', 'n_clicks')],    
    [State('shift-lever', 'data')])
def update_columns(timestamp,  n_clicks, rows):    
   
    shift_lever = pd.DataFrame.from_dict(rows)

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'refresh-shift-lever' in changed_id:        
        shift_lever = transforms.get_shift_lever(pd.read_csv('input/levers/shift_lever.csv'))

    elif 'shift-lever' in changed_id:

        for row in rows:
            try:      

                if int(row['Shift_Length']) > 24:
                    row['Shift_Length'] = 24
                
                if int(row['Shift_Days']) > int(row['Weeks_In_Period'])*7:
                    row['Shift_Days'] = int(row['Weeks_In_Period'])*7

                row['Hours_Crew'] = float(row['Shift_Length'])*float(row['Shift_Days']) + float(row['Hours_Overtime'])   

                row['Hours_Sched_PDT'] = round((float(row['Hours_Crew']) - float(row['Hours_Down_Time']))*float(row['Loss_Factor']),2)

                #print(f" SHIFT LENGTH: {row['Shift_Length']} * SHIFT DAYS {row['Shift_Days']} HOURS OVERTIME {row['Hours_Overtime']} = HOURS CREW {row['Hours_Crew']} ")         

                row['Hours_Total_Available_Calc'] = round((float(row['Hours_Crew']) - float(row['Hours_Down_Time']) - float(row['Hours_Sched_PDT']))*float(row['Safety_Hours']),2)

                #print(f" Hours_Total_Available_Calc {row['Hours_Total_Available_Calc']} = ( Hours_Crew {row['Hours_Crew']} - Hours_Down_Time {row['Hours_Down_Time']} - Hours_Sched_PDT {row['Hours_Sched_PDT']} ) * Safety_Hours {row['Safety_Hours']} ")
                            
                additional_hours = round(row['Hours_Total_Available_Calc'] - row['Hours_Total_Available'])        
                
                #print(f"Additional houts {additional_hours} ")

                row['Additional_Hours'] = round(additional_hours - float(row['Additional_Hours_Used']))
                
                
            except Exception as e:            
                print(e)                        

        shift_lever = pd.DataFrame.from_dict(rows)        
        shift_lever = shift_lever.round(2)
        shift_lever.to_csv('input/levers/shift_lever.csv', index=False)


    return shift_lever.to_dict("rows")


@app.callback(Output('add-time-updates', "children"),
    [Input('apply-time-updates', 'n_clicks')]  
)  
def update_output(n_clicks):  
    print("******************************** - INSIDE UPDATE OUTPUT")
    if(n_clicks > 0):

        try:            
            shift_lever = transforms.get_shift_lever(pd.read_csv('input/levers/shift_lever.csv'))          
            shift_lever.Material_Site_DemandShortfall = shift_lever.Material_Site_DemandShortfall.fillna('')                       
            shift_lever.Material_Site_InventoryShortfall = shift_lever.Material_Site_InventoryShortfall.fillna('')

            result_list = ['Updates Completed',  html.Br()]
            time_remaining = 0
            for index, row in shift_lever.loc[shift_lever.Additional_Hours > 0].iterrows():   

                if row['Additional_Hours'] <= 0:
                    # If row has no additional hours, move to next row in shift lever
                    continue
                
                # This row has additional hours added and we need to add these hours to capacity
                supply_site=str(int(row['Site_SAP']))
                supply_line=row['Line']
                period = row['Year_Period']                
                demand_shortfall_list = row['Material_Site_DemandShortfall'].split(' ')
                demand_shortfall_list.remove('')
                inventory_shortfall_list = row['Material_Site_InventoryShortfall'].split(' ')
                inventory_shortfall_list.remove('')
                additional_hours = row['Additional_Hours']        
                additional_hours_used = row['Additional_Hours_Used']     

                #' First we fulfill demand shortfalls
                time_remaining = (additional_hours - additional_hours_used)

                print(f"START short fall fulfillment {time_remaining} ")
                if len(demand_shortfall_list) > 0:
                    print(f"Fulfilling demand shortfall in period {period}")
                    result_list, time_remaining = baseline.fulfill_shortfall("DEMAND", demand_shortfall_list, time_remaining,
                                                                    supply_site, supply_line, period, result_list )    

                    
                    if  time_remaining > 0:  
                        print("There is still more time, fulfilling demand in next period")                      
                        # get next period demand shortfall list
                        next_period = transforms.get_next_period(period)
                        print(f"Next Period {next_period} ")

                        next_short = shift_lever.loc[(shift_lever.Site_SAP == supply_site)
                                                    & (shift_lever.Line ==  supply_line) 
                                                    & (shift_lever.Year_Period == next_period)]['Material_Site_DemandShortfall'].str.strip()
                                                
                        if len(next_short) > 0: next_short = next_short.values[0]

                        if len(next_short) > 0:
                            next_demand_shortfall_list = next_short.split(' ')
                            print(f"Fulfilling Demand shortfall in next period {period}")
                            result_list, time_remaining = baseline.fulfill_shortfall("DEMAND", next_demand_shortfall_list, time_remaining,
                                                                    supply_site, supply_line, period, result_list )  

                        

                        
                else: 
                                   
                    # get next period demand shortfall list
                    next_period = transforms.get_next_period(period)
                    print(f"No demand shortfall in current period {period}. looking for shortfoall in next period {next_period} ")    

                    next_short = shift_lever.loc[(shift_lever.Site_SAP == supply_site) 
                                                & (shift_lever.Line ==  supply_line) 
                                                & (shift_lever.Year_Period == next_period)]['Material_Site_DemandShortfall'].str.strip()
                    
                    if len(next_short) > 0: next_short = next_short.values[0]
                    
                    if len(next_short) > 0:
                        result_list.append(f"found demand shortfall {next_short}in period {period}")
                        next_demand_shortfall_list = next_short.split(' ')
                        print(f"found demand shortfall {next_short}in period {next_period}")
                        result_list, time_remaining = baseline.fulfill_shortfall("DEMAND", next_demand_shortfall_list, time_remaining,
                                                                supply_site, supply_line, period, result_list )

                    else:
                        result_list.append(f"No Demand shortfall in period {period} or period {next_period}")
                                          
                
                print(f"Time remaining after demand fulfillment {time_remaining} ")

                #' If time remaining we fulfill inventory shortfalls
                if len(inventory_shortfall_list) > 0:

                    if time_remaining > 0:           
                        print(f"Fulfilling inventory shortfall in period {period}")        
                        result_list, time_remaining = baseline.fulfill_shortfall("INVENTORY", inventory_shortfall_list, time_remaining,
                                                                                    supply_site, supply_line, period, result_list )
                        
                        if  time_remaining > 0:
                            # get next period inventory shortfall list
                            next_period = transforms.get_next_n_periods(period, 1)[1]
                            print(f"Next Period {next_period} ")

                            next_inventory_short = shift_lever.loc[(shift_lever.Site_SAP == supply_site) 
                                                                    & (shift_lever.Line ==  supply_line) 
                                                                    & (shift_lever.Year_Period == next_period)]['Material_Site_InventoryShortfall'].str.strip()
                                                        
                            if len(next_inventory_short) > 0: next_inventory_short = next_inventory_short.values[0]

                            if len(next_inventory_short) > 0:                               
                                
                                next_inventory_shortfall_list = next_inventory_short.split(' ')
                                print(f"Fulfilling inventory shortfall {next_inventory_short} in next period {next_period}")
                                result_list, time_remaining = baseline.fulfill_shortfall("INVENTORY", next_inventory_shortfall_list, time_remaining,
                                                                        supply_site, supply_line, period, result_list )  


                else:
                    # get next period inventory shortfall list
                    next_period = transforms.get_next_period(period)
                    print(f"Next Period {next_period} ")
                    print(f"Fulfilling inventory shortfall in next period {next_period}")

                    next_inventory_short = shift_lever.loc[(shift_lever.Site_SAP == supply_site) 
                                                            & (shift_lever.Line ==  supply_line) 
                                                            & (shift_lever.Year_Period == next_period)]['Material_Site_InventoryShortfall'].str.strip()
                    if len(next_inventory_short) > 0: next_inventory_short = next_inventory_short.values[0]

                    if len(next_inventory_short) > 0:                        
                        
                        next_inventory_shortfall_list = next_inventory_short.split(' ')
                        print(f"Fulfilling inventory shortfall {next_inventory_short} in next period {next_period}")
                        result_list, time_remaining = baseline.fulfill_shortfall("INVENTORY", next_inventory_shortfall_list, time_remaining,
                                                                supply_site, supply_line, period, result_list ) 

                    else:
                        result_list.extend([f"No Inventory Shortfall to fullfill in period {period} or period {next_period}", html.Br()])


                # update Shift lever with remaining additional hours                
                shift_lever.loc[index, 'Additional_Hours'] = time_remaining
                shift_lever.loc[index, 'Additional_Hours_Used'] = round(additional_hours - time_remaining,2)

            
            shift_lever = shift_lever[config.SHIFT_LEVER_COLUMNS].to_csv('input/levers/shift_lever.csv', index=False)   
            

        except Exception as e:
            print(f"Exception Occurred while doing updates {e}")
            return f"Exception Occurred while doing updates {e}"
       
        return result_list

    else:
        return ''



# @app.callback(
#     Output('shift-lever', 'data'),
#     [Input('refresh-shift-lever', 'n_clicks')]
# )    
# def update_shift_lever(n_clicks):   
#     shift_lever = pd.read_csv('input/levers/shift_lever.csv')       
#     return shift_lever.to_dict('rows')