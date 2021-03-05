import pandas as pd
import numpy as np
import os
from utils import config
from database import transforms

DEMAND_SHORTFALL_TRESHOLD = 10
INVENTORY_SHORTFALL_THRESHOLD = 5

def get_demand_alerts():
    dP_siteSummarised = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'dP_siteSummarised')).round(2)
    dP_siteSummarised['Value'] = dP_siteSummarised['Value'].astype(float)
    
    # Demand Shortfalls
    demand_plan = dP_siteSummarised.loc[dP_siteSummarised.Uom == 'ZUC'].pivot(index=['Level2Region','Site_SAP','Year_Period','Summary_Portfolio', 'Material', 'Uom'], \
                                        columns='KeyField')['Value'].reset_index()     

    
    demand_plan['demand_short_fall'] = -1*(demand_plan['Available'] - demand_plan['Total'])
    demand_plan['demand_short_fall_pct'] = round((demand_plan['Available'] - demand_plan['Total'])*-100/ (demand_plan['Available']) )

    demand_shortfalls = demand_plan.loc[demand_plan.demand_short_fall_pct > DEMAND_SHORTFALL_TRESHOLD] 

    if len(demand_shortfalls) > 0:
        demand_shortfalls = demand_shortfalls[['Site_SAP', 'Summary_Portfolio', 'Material', 'Year_Period', 'demand_short_fall']]

        demand_shortfalls.Material = demand_shortfalls.Material.astype(str)
        demand_shortfalls.Site_SAP = demand_shortfalls.Site_SAP.astype(str)

        materials = demand_shortfalls.Material.str.cat(sep="','")
        mh = transforms.get_datatable_from_db(table_name=config.MATERIAL_HEADER_TABLE, where_string=f"WHERE Material in ('{materials}') ")
        demand_shortfalls = pd.merge(demand_shortfalls, mh[['Material', 'MaterialDescription']], on='Material', how='inner')        

        demand_shortfalls.columns = ['Demand_Site', 'Portfolio', 'Demand_Material', 'Year_Period', 'Additional_Units_Required', 'MaterialDescription']


    else:
        demand_shortfalls = pd.DataFrame(columns=['Demand_Site', 'Portfolio', 'Demand_Material', 'Year_Period', 'Additional_Units_Required', 'MaterialDescription'])


    demand_shortfalls = demand_shortfalls.astype(str)
    demand_shortfalls.Additional_Units_Required = demand_shortfalls.Additional_Units_Required.astype(float).astype(int)

    return demand_shortfalls


def get_inventory_alerts():
    # Inventory Shortfalls
    pivot_cols = ['KeyField']
    pivot_rows = ['Site_SAP', 'Summary_Portfolio', 'Material', 'Year_Period']
    value_col = ['Value']
    agg_func = np.sum
    filter_by = {'Uom': 'ZUC'}

    iP_Summarised = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'iP_Summarised')).round(2)
    iP_Summarised['Value'] = iP_Summarised['Value'].astype(float)

    df = iP_Summarised[iP_Summarised.KeyField.isin(['ZUC_ClosingStockTarget', 'ZUC_StockVsTarget'])]

    inventory_shortfalls = pd.pivot_table(df, values=value_col, index=pivot_rows, columns=pivot_cols, aggfunc=agg_func)

    inventory_shortfalls = pd.DataFrame(inventory_shortfalls.to_records())

    inventory_shortfalls.columns = [hdr.replace("('Value', '", "").replace("')", "") for hdr in inventory_shortfalls.columns]
    
    inventory_shortfalls['inventory_shortfall_pct'] = round(inventory_shortfalls['ZUC_StockVsTarget']*-100 / inventory_shortfalls['ZUC_ClosingStockTarget'], 2)

    inventory_shortfalls['inventory_shortfall'] = -1*inventory_shortfalls['ZUC_StockVsTarget']

    inventory_shortfalls = inventory_shortfalls.loc[inventory_shortfalls.inventory_shortfall_pct > INVENTORY_SHORTFALL_THRESHOLD]

    inventory_shortfalls = inventory_shortfalls[['Site_SAP', 'Summary_Portfolio', 'Material', 'Year_Period', 'inventory_shortfall']]

    inventory_shortfalls.Material = inventory_shortfalls.Material.astype(str)
    inventory_shortfalls.Site_SAP = inventory_shortfalls.Site_SAP.astype(str)

    materials = inventory_shortfalls.Material.str.cat(sep="','")
    mh = transforms.get_datatable_from_db(table_name=config.MATERIAL_HEADER_TABLE, where_string=f"WHERE Material in ('{materials}') ")

    inventory_shortfalls = pd.merge(inventory_shortfalls, mh[['Material', 'MaterialDescription']], on='Material', how='inner')

    inventory_shortfalls.columns = ['Inventory_Site', 'Portfolio', 'Inventory_Material', 'Year_Period', 'Inventory_Units_Required', 'MaterialDescription']

    inventory_shortfalls = inventory_shortfalls.astype(str)
    inventory_shortfalls.Inventory_Units_Required = inventory_shortfalls.Inventory_Units_Required.astype(float).astype(int)


    return inventory_shortfalls



# def get_next_period(this_period) :
#     this_month = int(this_period.split('_')[1])
#     this_year = int(this_period.split('_')[0])        
    
#     next_year = this_year
#     if this_month==12:
#         next_year = this_year+1
#         next_month = 1
#     else:
#         next_month = this_month+1
   
#     return f"{next_year}_{next_month:02d}"



def get_inventory_excess():
    # Inventory Shortfalls
    pivot_cols = ['KeyField']
    pivot_rows = ['Site_SAP', 'Summary_Portfolio', 'Material', 'Year_Period']
    value_col = ['Value']
    agg_func = np.sum
    filter_by = {'Uom': 'ZUC'}

    iP_Summarised = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'iP_Summarised')).round(2)
    iP_Summarised['Value'] = iP_Summarised['Value'].astype(float)
    
    df = iP_Summarised[iP_Summarised.KeyField.isin(['ZUC_StockVsTarget'])]

    inventory_excess = pd.pivot_table(df, values=value_col, index=pivot_rows, columns=pivot_cols, aggfunc=agg_func)

    inventory_excess = pd.DataFrame(inventory_excess.to_records())

    inventory_excess.columns = [hdr.replace("('Value', '", "").replace("')", "") for hdr in inventory_excess.columns]

    num = inventory_excess._get_numeric_data()
    num[num < 0] = 0

    # shift period by 1 as excess inventory in this period will be supply in next period
    inventory_excess['Next_Period'] = [ transforms.get_next_period(x) for x in  inventory_excess.Year_Period ]

    inventory_excess.rename(columns={'ZUC_StockVsTarget':'Excess_Inventory', 
                                     'Year_Period':'Excess_in_Period',
                                     'Site_SAP': 'Excess_Site'
                                     }, inplace=True)
    
    return inventory_excess



