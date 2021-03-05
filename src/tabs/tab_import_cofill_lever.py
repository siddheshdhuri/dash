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


mP_Summarised = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'mP_Summarised')).round(2)
# @TODO Material Material desc to add

import_cofill_metadata = transforms.import_cofill_metadata
snp_list = transforms.snp_list
material_list = transforms.material_list

shift_data = pd.read_csv(os.path.join(config.INPUT_LEVER_DIR , config.SHIFT_LEVER_FILE))

import_lever = pd.read_csv(os.path.join(config.INPUT_LEVER_DIR, config.IMPORT_COFILL_LEVER_FILE))

def get_lever():
    print("insude get lever")
    return pd.read_csv(os.path.join(config.INPUT_LEVER_DIR, config.IMPORT_COFILL_LEVER_FILE))


layout = html.Div([
    dbc.Row([
        dbc.Col([html.B('Edit The following to import cofill material')])
    ]),
    dbc.Row([
        dcc.Dropdown(
                id='import-or-cofill',
                options=[{'label': i, 'value': i} for i in ['Import', 'Cofill']], 
                value='Import',                               
                style=dict(
                    width='100px'                    
                )
            ),
        dcc.Dropdown(
                id='from-country',
                options=[{'label': i, 'value': i} for i in import_cofill_metadata.FromCountry.unique()],                
                placeholder="Select From Country",
                style=dict(
                    width='100px'                    
                )
            ),
        dcc.Dropdown(
                id='from-site',
                options=[{'label': i, 'value': i.split(' - ')[0]} for i in import_cofill_metadata.Site.unique()],
                value='',
                placeholder="Select From Site",
                style=dict(
                    width='300px'                    
                )
            ),                
        dcc.Dropdown(
                id='snp-list',
                options=[{'label': i, 'value': i} for i in snp_list.SNPPL01.unique()],
                value='',
                placeholder="Select SNPPL01",
                style=dict(
                    width='200px'                    
                )
            ),
        dcc.Dropdown(
                id='material-list',
                options=[{'label': i, 'value': i.split(' - ')[0]} for i in material_list.Material_Desc.unique()],
                value='',
                placeholder="Select Material",
                style=dict(
                    width='300px'                    
                )
            ),
        dcc.Dropdown(
                id='year_period',
                options=[{'label': i, 'value': i} for i in shift_data.Year_Period.unique()],
                value='',
                placeholder="Select Year Period",
                style=dict(
                    width='100px'                    
                )
            ),
        dcc.Dropdown(
                id='to-site',
                options=[{'label': i, 'value': i} for i in config.IMPORT_COFILL_HUB],
                value='',
                placeholder="Select To Site",
                style=dict(
                    width='100px'                    
                )
            ),
        dcc.Input(
            id="input_number",
            type="number",
            placeholder="ZUC Units",
            style=dict(
                    width='100px'                    
                )
        ),
        html.Button('Add', id='add-to-lever', n_clicks=0)
        
    ]),
    dbc.Row([
        html.Button('Save Lever', id='save-import-cofill-lever', n_clicks=0),
        html.P("                                                          "),
        html.Button('Apply Updates', id='apply-import-cofill', n_clicks=0)
    ]),
    dbc.Row([

        dcc.Loading(
            id="loading-1",
            type="default",
            children=html.Div(id='import-lever-div', children=html.Div([
                dash_table.DataTable(
                    id='import-lever',
                    columns=[
                        {'name': i.replace("_", " "), 'id': i} for i in import_lever.columns            
                    ],
                    data=import_lever.to_dict('records'),
                    editable=False,
                    row_deletable=True,
                    style_header={
                        'minWidth': '0px', 'maxWidth': '100px',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                    }
                )
            ])
            ) 
        )
                
    ]),
    dbc.Row([        
        dcc.Loading(
            id="loading-1",
            type="default",
            children=html.Div(id='import-cofill-update', children='')
        ) 
    ])
    
])


@app.callback(Output('from-country', 'options'),
              [Input('import-or-cofill', 'value')]              
            )
def update_countries(import_or_cofill):   
    import_cofill_metadata = transforms.import_cofill_metadata    
    import_cofill_metadata = import_cofill_metadata.loc[import_cofill_metadata.Import_Cofill == import_or_cofill]        
    
    return [{'label': i, 'value': i} for i in import_cofill_metadata.FromCountry.unique()]


# @app.callback(Output('to-site', 'options'),
#               [Input('import-or-cofill', 'value')]              
#             )
# def update_hub(import_or_cofill):       
#     if import_or_cofill == 'Import':
#         options = config.IMPORT_HUB
#     else:
#         options = config.COFILL_HUB

#     return [{'label': i, 'value': i} for i in options]


@app.callback(Output('from-site', 'options'),
              [Input('from-country', 'value')]              
            )
def update_from_sites(from_country):    
    
    metadata = transforms.import_cofill_metadata
    metadata = metadata.loc[metadata.FromCountry == from_country]
    
    return [{'label': i, 'value': i.split(' - ')[0]} for i in metadata.Site.unique()]



@app.callback(Output('material-list', 'options'),
              [Input('snp-list', 'value')]              
            )
def update_material_list(snp_selected):    
    
    material_list = transforms.material_list
    if snp_selected:
        material_list = material_list.loc[material_list.SNPPL01 == snp_selected]
    
    return [{'label': i, 'value': i.split(' - ')[0]} for i in material_list.Material_Desc.unique()]
    


@app.callback(
    Output('import-lever-div', 'children'),
    [Input('add-to-lever', 'n_clicks'),
    Input('save-import-cofill-lever', 'n_clicks')],
    [State('import-or-cofill', 'value'),
    State('from-country', 'value'),
    State('from-site', 'value'),    
    State('material-list', 'value'),
    State('year_period', 'value'),
    State('input_number', 'value'),
    State('to-site', 'value'),
    State('import-lever', 'data')]
    )
def update_columns(n_clicks, n_clicks2, import_or_cofill, from_country, from_site,                   
                    material, year_period, units, to_site, rows):    

    
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]    

    if 'save-import-cofill-lever' in changed_id:
        import_lever = pd.DataFrame.from_dict(rows)       
        import_lever.to_csv(os.path.join(config.INPUT_LEVER_DIR, config.IMPORT_COFILL_LEVER_FILE), index=False)

    elif 'add-to-lever' in changed_id: 

        if n_clicks > 0:
            print(f" - {from_country} - {from_site} - {to_site} - {material} - {year_period} - {units} ")           
            
            from_site = from_site.split(' - ')[0]             
            material = material.split(' - ')[0]

            # no existing movement from site to sitein period for material                
            new_row = {'Import_Cofill': import_or_cofill, 'FromCountry':from_country, 'ToCountry':'GB', 'Site_SAP_From': from_site, 
                        'Year_Period': year_period, 'Summary_Portfolio':'', 'Material': material,'KeyField':'ZUC', 'Value':units, 
                        'Uom':'ZUC', 'ToRepack_Flag':0, 'To_Site': to_site+import_or_cofill
                        }                         

            import_lever = pd.DataFrame.from_dict(rows)
            import_lever = import_lever.append(new_row, ignore_index=True)
    else:
        import_lever = get_lever()               

            
    return html.Div([
            dash_table.DataTable(
                id='import-lever',
                columns=[
                    {'name': i.replace("_", " "), 'id': i} for i in import_lever.columns            
                ],
                data=import_lever.to_dict('records'),
                editable=False,
                row_deletable=True,
                style_header={
                    'minWidth': '0px', 'maxWidth': '100px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                }
            )
        ])




@app.callback(Output('import-cofill-update', "children"),
    [Input('apply-import-cofill', 'n_clicks')],
    [State('import-lever', 'data')]
)  
def update_output(n_clicks, rows):  

    if(n_clicks > 0):
        result_list = ['Following updates:',  html.Br()]
        try:
            demand_shortfalls = alerts.get_demand_alerts()
            inventory_shortfalls = alerts.get_inventory_alerts()

            for row in rows:
                #import_or_cofill = row['Import_Cofill']
                from_site = row['Site_SAP_From']
                to_site = row['To_Site']
                material = row['Material']
                imported_units = row['Value']
                year_period = row['Year_Period']                

                #Import items from import site to hubsite
                _, result = baseline.update_movements(to_site, from_site, year_period, material, imported_units)
                result_list.extend([result, html.Br()])

                # Add all imported items to to_site
                result = baseline.update_inventory(to_site, year_period, material, imported_units)
                result_list.extend([result, html.Br()])                
                
                periods_to_fulfill = transforms.get_next_n_periods(year_period,1)

                #' fulfill demand shortfalls
                material_shortfall = demand_shortfalls.loc[(demand_shortfalls.Demand_Material == material) 
                                                            & (demand_shortfalls.Year_Period.isin(periods_to_fulfill))]                
                
                if len(material_shortfall) > 0:
                    print("demand shortfalls exists trying to fulfill")
                    for index, short in material_shortfall.iterrows():                    
                        demand_site = short['Demand_Site']
                        year_period = short['Year_Period']
                        material = short['Demand_Material']
                        required_units = short['Additional_Units_Required']
                        required_units = round(required_units)
                    
                        print(f" UNITS REQUIRED AT SITE {demand_site} units: {required_units} and units avaialble {imported_units} ")
                        
                        units_to_add = required_units if imported_units >= required_units else imported_units                        
                        imported_units = imported_units - units_to_add

                        # Reduce items from Hub site
                        result = baseline.update_inventory(to_site, year_period, material, -units_to_add)                    
                        result_list.extend([result, html.Br()])

                        # Add items to demand site
                        #' Add units as available at Demand site
                        print(f"adding {units_to_add} units to site {demand_site}")
                        result = baseline.update_demand(demand_site,  year_period, material, units_to_add)
                        result_list.extend([result, html.Br()])
                        
                        # Add movements from Hub site to demand site
                        _, result = baseline.update_movements(demand_site, to_site, year_period, material, units_to_add)
                        result_list.extend([result, html.Br()])  

                        if imported_units < 1:
                            break

                else:
                    result_list.extend([f"No demand shortfall for Material {material} in period {periods_to_fulfill}", html.Br()]) 

                if imported_units > 0:

                    material_shortfall = inventory_shortfalls.loc[(inventory_shortfalls.Inventory_Material == material)
                                                                  & (inventory_shortfalls.Year_Period.isin(periods_to_fulfill))] 

                    if len(material_shortfall) > 0:

                        for index, short in material_shortfall.iterrows():                    
                            demand_site = short['Inventory_Site']
                            year_period = short['Year_Period']
                            material = short['Inventory_Material']
                            required_units = short['Inventory_Units_Required']
                        
                            units_to_add = required_units if imported_units >= required_units else imported_units                        
                            imported_units = imported_units - units_to_add

                            # Reduce items from Hub site
                            result = baseline.update_inventory(to_site, year_period, material, -units_to_add)                    
                            result_list.extend([result, html.Br()])

                            # Add items to demand site
                            result = baseline.update_inventory(demand_site, year_period, material, units_to_add)
                            result_list.extend([result, html.Br()])
                            
                            
                            # Add movements from Hub site to demand site
                            _, result = baseline.update_movements(demand_site, to_site, year_period, material, units_to_add)
                            result_list.extend([result, html.Br()])  
                    else:
                        result_list.extend([f"No inventory shortfall for Material {material} in period {periods_to_fulfill}", html.Br()])  
                else:
                    print("NO UNITS REMAINING AFTER DEMAND SHHORTS")                         
            
                result_list.extend([f"------------------------------------------", html.Br()])


        except Exception as e:
            print(f"Exception Occurred while doing updates {e}")
            return f"Exception Occurred while doing updates {e}"
       
        return result_list

    else:
        return ''
