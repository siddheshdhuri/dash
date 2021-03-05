import pandas as pd
import numpy as np
import os
from database import transforms
import dash_html_components as html
from utils import config


# Function to update the line loading data and save to disk
def update_line_loading(site, line, period, units_made=None, additional_hours=None, used_hours=None):

    try:
    
        line_loading_plan = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.SUPPLY_PLAN_INHOUSE_LINELOADING_PICKLE)).round(2)        
        
        # Evaluate base conditions to filter data
        base_condition = ((line_loading_plan.Site_SAP.astype(str) == str(site)) \
                        & (line_loading_plan.Uom == 'Hours') \
                        & (line_loading_plan.Line == line) \
                        & (line_loading_plan.Year_Period == period) 
                        )
        
        if used_hours is None:
            # add hours to consumed and capacity
            condition = base_condition & (line_loading_plan.KeyField.isin(['Capacity', 'SpareHours']))        

            line_loading_plan.loc[condition, 'Value'] = line_loading_plan.loc[condition]['Value'] + additional_hours    

            result_string = f''' Line Loading update: {additional_hours} added to Capacity and Spare {site} {line} in period {period} '''     
            
        elif additional_hours is None:
            # Update line_loading_plan with used time to consumed and spare hours
            condition_capacity = base_condition & (line_loading_plan.KeyField.isin(['Capacity']))
            conditions_consumed = base_condition & (line_loading_plan.KeyField.isin(['Consumed']))         
            conditions_spare = base_condition &(line_loading_plan.KeyField.isin(['SpareHours']))   
            conditions_available_vol = base_condition &(line_loading_plan.KeyField.isin(['EstimatedUnconsumedCapacity']))               

            line_loading_plan.loc[conditions_consumed, 'Value'] = line_loading_plan.loc[conditions_consumed]['Value'] + used_hours
            
            line_loading_plan.loc[conditions_spare, 'Value'] = line_loading_plan.loc[conditions_spare]['Value'] - used_hours

            line_loading_plan.loc[conditions_available_vol, 'Value'] = line_loading_plan.loc[conditions_available_vol]['Value'] - units_made         

            result_string = f'''Line Loading update: Time remaining at {site} {line} 
                capacity: {round(line_loading_plan.loc[condition_capacity].Value.values[0],2)} 
                consumed {round(line_loading_plan.loc[conditions_consumed].Value.values[0],2)} 
                spare {round(line_loading_plan.loc[conditions_spare].Value.values[0],2)}
                '''   
            

        #' Write changes to disk
        line_loading_plan.to_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.SUPPLY_PLAN_INHOUSE_LINELOADING_PICKLE))

        return result_string

    except Exception as e:
        raise Exception(f"Exceptiion While updating line loading {e}")


# function to update inhouse production and save to disk
def update_inhouse_production(site, line, material, period, units_made):

    try:
    
        inhouse_production = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'sP_portSummarisedIH')).round(2)        

        # Evaluate base conditions to filter data
        base_condition = ((inhouse_production.Site_SAP.astype(str) == str(site)) & (inhouse_production.Line == line) \
                        & (inhouse_production.Year_Period == period) \
                        & (inhouse_production.Material.astype(str) == str(material)) \
                        )

        uom_list = list(inhouse_production.Uom.unique())
        # for each uom update the units produced        
        for uom in uom_list:   
            conversion_ratio = transforms.get_conversion_ratio(material, 'ZUC', uom)                        
            this_units = units_made*conversion_ratio                         
            condition = base_condition & (inhouse_production.Uom == uom)           
            
            inhouse_production.loc[condition, 'Value'] = inhouse_production.loc[condition, 'Value']  + this_units  
    

        # write to disk
        inhouse_production.to_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'sP_portSummarisedIH'))

        return f"Inhouse Production update: {units_made} units of {material} made at site: {site} line: {line} in period {period} "

    except Exception as e:
        raise Exception(f"Exceptiion While updating inhouse production {e}")


# Function to calculate the time required to manufacture required material units at a given site line.    
def get_time_required(site, line, material, additional_units_required):    
    
    try:
        # get material runrate from production capacity file
        material_runrate = transforms.production_capacity
        
        material_runrate = material_runrate.drop_duplicates(subset=['Plant', 'Line', 'Material'])
        
        #Time Required to manufacture shortfall         
        this_runrate = material_runrate.loc[(material_runrate.Plant == str(site))\
                            & (material_runrate.Material == str(material)) \
                            & (material_runrate.Line == line)
                            ]['BaseUnitsPerHour']
        
        if len(this_runrate) <= 0:
            raise Exception(f"No record found for SITE: {site} MATERIAL: {material} LINE: {line} in Production Capacity data")
       
        # Calcuate time required in hours
        time_required_hours = float(round(additional_units_required / this_runrate, 4))
    except Exception as e:
        raise Exception(f"Exception while calcuating Time Required {e}")

    return time_required_hours, this_runrate

# Function to update demand data and save to disk
def update_demand(demand_site,  period, material, units_made, keyfield='Available'):
    
    # read pickle file
    dP_siteSummarised = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.DEMAND_PICKLE))   

    # Filter condistions 
    conditions_demand = ( (dP_siteSummarised.Site_SAP.astype(str) == str(demand_site)) \
                            &(dP_siteSummarised.Year_Period.astype(str) == period) \
                            &(dP_siteSummarised.KeyField==keyfield) & (dP_siteSummarised.Material.astype(str) == str(material))
                        )
    
    uom_list = list(dP_siteSummarised.Uom.unique())
    # for every unit of measure update the number of units field
    for uom in list(uom_list):   
        conversion_ratio = transforms.get_conversion_ratio(material, 'ZUC', uom)    
        
        this_units = units_made*conversion_ratio  
        
        condition = conditions_demand & (dP_siteSummarised.Uom == uom)           
        print(f" UPDATING DEMAND OLD VALUE  SITE {str(demand_site)} PERIOD {period} MATERIAL {str(material)} UNITS = {dP_siteSummarised.loc[condition, 'Value'].values[0]} - {uom} " )
        dP_siteSummarised.loc[condition, 'Value'] = dP_siteSummarised.loc[condition, 'Value']  + this_units
        print(f" UPDATED DEMAND NEW VALUE = {dP_siteSummarised.loc[condition, 'Value'].values[0]} - {uom} ")
        
    # write to disk    
    dP_siteSummarised.to_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'dP_siteSummarised'))

    result_string = f" {units_made} units added to {keyfield} Demand at Site {demand_site} in period {period}"
    
    return result_string

# Function to update inventory data and save to disk
def update_inventory(inventory_site, period, material, units_made, keyfields=['ZUC_ClosingStock', 'ZUC_StockVsTarget']):

    iP_Summarised = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'iP_Summarised'))  
    # Filter Conidtions  
    print(f"INVENTORY SITE {inventory_site}")
    conditions_inventory = ( (iP_Summarised.Site_SAP.str.startswith(str(inventory_site))) \
                            & (iP_Summarised.Year_Period == period) \
                            & (iP_Summarised.Material.astype(str) == material)
                        )                      
    
    uom_list = list(iP_Summarised.Uom.unique())    
    uom_list.remove('GBP')
    
    for uom in uom_list:   
        conversion_ratio = transforms.get_conversion_ratio(material, 'ZUC', uom)
        print(f" Conversion ratio for {material} {uom} = {conversion_ratio} old units = {units_made} new units = {units_made*conversion_ratio } ")                        
        units = units_made*conversion_ratio 
        print(f"=========================================================== UOM = {uom} ")
        for keyfield in keyfields:
            condition = conditions_inventory & (iP_Summarised.KeyField == keyfield) & (iP_Summarised.Uom == uom) 
            print(f" LEN of inventory df {iP_Summarised.loc[condition].KeyField.unique()} ")
            if len(iP_Summarised.loc[condition]) > 0:
                
                print(f" UPDATING INVENTORY {keyfield} OLD VALUE SITE {str(inventory_site)} PERIOD {period} MATERIAL {str(material)} adding {units} #UNITS = {iP_Summarised.loc[condition, 'Value'].values[0]}")
                iP_Summarised.loc[condition, 'Value'] = iP_Summarised.loc[condition, 'Value']  + units
                print(f" UPDATED INVENTORY {keyfield} NEW VALUE = {iP_Summarised.loc[condition, 'Value'].values[0]}")            
       
    
    iP_Summarised.to_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.INVENTORY_PICKLE))
    
    # Update DSI tables with new ClosingStock
    update_dsi_table(inventory_site, period, material, units_made)

    if units_made < 0:
        result_string = f" {units_made} units removed from Site {inventory_site} in period {period}"
    else:
        result_string = f" {units_made} units added to Site {inventory_site} in period {period}"

    return result_string


#Function to update DSI table
def update_dsi_table(inventory_site, period, material, units_made, keyfields=['ClosingStock', 'ClosingStock_Target']):
    #' read pickle file
    dsi_pickle = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.DSI_PICKLE))
    dsi_pickle.fillna(0)
    dsi_pickle['ZUC_ClosingStock'] = dsi_pickle['ZUC_ClosingStock'].astype(float)
    dsi_pickle['ZUC_ClosingStock_Target'] = dsi_pickle['ZUC_ClosingStock_Target'].astype(float)
    dsi_pickle['ZRW_ClosingStock'] = dsi_pickle['ZRW_ClosingStock'].astype(float)
    dsi_pickle['ZRW_ClosingStock_Target'] = dsi_pickle['ZRW_ClosingStock_Target'].astype(float)
    dsi_pickle = dsi_pickle.round()
    
    print(f"INVENTORY SITE {inventory_site}")
    # update closing stock and ClosingStock_Target for ZUC
    conditions_dsi = ( (dsi_pickle.Site_SAP.str.startswith(str(inventory_site))) \
                            & (dsi_pickle.Year_Period == period) \
                            & (dsi_pickle.Material.astype(str) == material)
                        )
    
    dsi_pickle.loc[conditions_dsi, 'ZUC_ClosingStock'] = dsi_pickle.loc[conditions_dsi, 'ZUC_ClosingStock']  + units_made
    dsi_pickle.loc[conditions_dsi, 'ZUC_ClosingStock_Target'] = dsi_pickle.loc[conditions_dsi, 'ZUC_ClosingStock']  + units_made
    
    # update closing stock and ClosingStock_Target for ZRW

    conversion_ratio = transforms.get_conversion_ratio(material, 'ZUC', 'ZRW')       
    zrw_units = units_made*conversion_ratio 
    
    dsi_pickle.loc[conditions_dsi, 'ZRW_ClosingStock'] = dsi_pickle.loc[conditions_dsi, 'ZRW_ClosingStock']  + zrw_units
    dsi_pickle.loc[conditions_dsi, 'ZRW_ClosingStock_Target'] = dsi_pickle.loc[conditions_dsi, 'ZRW_ClosingStock']  + zrw_units
    
    # save to disk
    dsi_pickle.to_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.DSI_PICKLE))

    print("DSI TABLE UPDATED")
    
    


# Function to update truck movements from site to site and save to disk
def update_movements(demand_site, supply_site, period, material, units_made, save=True):
    movement_string = 'Nothing to move'
    units = 0

    #' get summary portfolio for material
    dp = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.DEMAND_PICKLE))
    try:
        summary_portfolio = dp.loc[dp.Material.astype(str) == material].Summary_Portfolio.values[0]
    except:
        summary_portfolio = ''

    if demand_site != supply_site:
        # update Movement Plan        
        mP_Summarised = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'mP_Summarised')).round(2)
        
        print(f' Supply site: {supply_site} Demand Site {demand_site} period {period} Material {material} ')                          
        conditions_movement = ((mP_Summarised.Site_SAP_From.astype(str) == str(supply_site)) \
                                & (mP_Summarised.Site_SAP_To.astype(str) == str(demand_site)) \
                                & (mP_Summarised.Year_Period.astype(str) == period) \
                                & (mP_Summarised.Material.astype(str) == str(material))
                                )

        uom_list = list(mP_Summarised.Uom.unique())
        uom_list.remove('GBP')
        for uom in uom_list:               
            conversion_ratio = transforms.get_conversion_ratio(material, 'ZUC', uom)
            
            units = round(units_made*conversion_ratio, 2)                         
            condition = conditions_movement & (mP_Summarised.Uom == uom)  
            
            if len(mP_Summarised.loc[condition]) == 0:
                # no existing movement from site to sitein period for material                
                new_row = {'FromCountry':'', 'ToCountry':'', 'SiteCountry':'', 'From_GeoRegion':'', 'To_GeoRegion':'',
                            'Site_SAP_From': supply_site, 'Site_SAP_To': demand_site, 'Year_Period': period, 'Summary_Portfolio': summary_portfolio, 
                            'Material': material,'KeyField':uom, 'Value':0, 'Uom':uom, 'ToRepack_Flag':0
                            }
                
                #append row to the dataframe
                mP_Summarised = mP_Summarised.append(new_row, ignore_index=True)             
                
                #recalculate condition on new index
                conditions_movement = ((mP_Summarised.Site_SAP_From.astype(str) == supply_site) \
                                    & (mP_Summarised.Site_SAP_To.astype(str) == demand_site) \
                                    & (mP_Summarised.Year_Period.astype(str) == period) \
                                    & (mP_Summarised.Material.astype(str) == material)
                                    )
                condition = conditions_movement & (mP_Summarised.Uom == uom)                       
                        
            mP_Summarised.loc[condition, 'Value'] = mP_Summarised.loc[condition, 'Value']  + units                                       
            
            if uom == 'Trucks':
                movement_string = f" {units} Trucks moved from {supply_site} to {demand_site}"
        
        if save:
            mP_Summarised.to_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'mP_Summarised'))        

    return units, movement_string


# Function to update units manufactured to demand / inventory plan and truck movements data
def update_units_and_movements(plan, demand_site, supply_site, period, material, units_made, 
                                demand_key='Available', inventory_key=['ZUC_ClosingStock', 'ZUC_StockVsTarget']):  
    
    # Update Demand      
    try:         
        
        if plan == "DEMAND":
            units_update = update_demand(demand_site, period, material, units_made, demand_key)
            
        else:
            units_update = update_inventory(demand_site, period, material, units_made, inventory_key)
                                                
    except Exception as e:
        print(f"Exception while updating Demand / Inventory Plan {e}")

    trucks, movement_update = update_movements(demand_site, supply_site, period, material, units_made)    
    

    return units_update, trucks, movement_update




# Functin to manufactre requied material units using production hours at a give site / line
def make_units(time_available, units_required, material, supply_site, supply_line, period):

    #Time Required to manufacture shortfall      
    time_required_hours, runrate = get_time_required(supply_site, supply_line, material, units_required)       

    print(f"Time required in hours: {time_required_hours} at the runrate of {runrate}")

    # Check if additional hours are enough
    if time_required_hours < time_available:
        time_to_use = time_required_hours 
        time_remaining = time_available - time_required_hours
    else:
        time_to_use = time_available
        time_required_hours = time_required_hours - time_available
        time_remaining = 0   

    # Update Demand / Movement plans    
    units_made = round(float(runrate * time_to_use))

    # Update line_loading_plan with used time to consumed and spare hours
    line_loading_update = update_line_loading(supply_site, supply_line, period, units_made, used_hours=time_to_use)       
    print(f"Updating line loading {runrate} time to use {time_to_use} ")    

    #Update Inhouse production plan
    inhouse_prod_update = update_inhouse_production(supply_site, supply_line, material, period, units_made)

    return units_made, time_remaining, time_to_use, line_loading_update, inhouse_prod_update
    
    
# function to update all the plans one user has altered a lever and more units are manufacutured
def update_plans(plan, additional_hours_added, additional_units_required, demand_site, 
                 material, supply_site, supply_line, period):
    
    # Update Line Loading with additional hours to capacity and spare
    if plan == 'DEMAND' :
        update_line_loading(supply_site, supply_line, period, units_made=None, additional_hours=additional_hours_added)    
    
    # With the additional hours added to capacity, make additional units consuming required hours
    units_made, time_remaining, _, line_loading_update, inhouse_prod_update = make_units(time_available = additional_hours_added, 
                                                                                        units_required = additional_units_required, 
                                                                                        material=material,
                                                                                        supply_site=supply_site, supply_line=supply_line, 
                                                                                        period=period)    

    # update the demand and movement plan if the demand and supply site are different
    _ ,_, movement_update = update_units_and_movements(plan, demand_site, supply_site, period, material, units_made)
    print("DEMAND AND MOVEMENT UPDATED")
    return units_made, time_remaining, movement_update, line_loading_update, inhouse_prod_update


# Function to fullfill a demand / inventory shortfall
def fulfill_shortfall(requirement, shortfall_list, time_remaining,
                      supply_site, supply_line, period, result_list ):

    for i in range(len(shortfall_list)):        
        material = shortfall_list[i].split('_')[0]        
        required_site = shortfall_list[i].split('_')[1]         
        required_units = float(shortfall_list[i].split('_')[2])   

        if (required_units > 0) & (time_remaining > 0):     

            units_made, time_remaining, movement_string, _, _ = update_plans(requirement, time_remaining, required_units, required_site,                                                                 
                                                                                            material, supply_site, supply_line, period)                                                                                         
            print(f"fulfilling SHORT FALL: {shortfall_list[i]}")
            print(f" Site {supply_site} made {units_made} units for {required_site} time remaining {time_remaining} and {movement_string} ")

            result_list.extend(['------------------------:', html.Br(), 
                            f'{round(units_made,0)} Additional Units Made at {supply_site} line {supply_line}', html.Br(), 
                            f'{round(time_remaining,2)} Hours Remaining after demand fulfillment', html.Br(),                                    
                            movement_string, html.Br(),    
                            ])

            

    return result_list, time_remaining


