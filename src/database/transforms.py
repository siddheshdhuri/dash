import pandas as pd
import numpy as np
import seaborn as sns
import sqlite3
import os
import pyodbc 
from utils import config
import logging

"""
Simple module that monkey patches pkg_resources.get_distribution used by dash
to determine the version of Flask-Compress which is not available with a
flask_compress.__version__ attribute. Known to work with dash==1.16.3 and
PyInstaller==3.6.
"""

import sys
from collections import namedtuple

import pkg_resources


logging.basicConfig(filename='output.log')

df_dict = {}

IS_FROZEN = hasattr(sys, '_MEIPASS')

# backup true function
_true_get_distribution = pkg_resources.get_distribution
# create small placeholder for the dash call
# _flask_compress_version = parse_version(get_distribution("flask-compress").version)
_Dist = namedtuple('_Dist', ['version'])

def _get_distribution(dist):
    if IS_FROZEN and dist == 'flask-compress':
        return _Dist('1.5.0')
    else:
        return _true_get_distribution(dist)

# monkey patch the function so it can work once frozen and pkg_resources is of
# no help
pkg_resources.get_distribution = _get_distribution

# Return Float of value or return 0
def FloatOrZero(value):
    try:
        return float(value)
    except:
        return 0.0

# Function to fill NA values in dataframe
def fill_na_by_type(df, str_na='', float_na=0, int_na=0, bool_na=False):
    float_cols = df.select_dtypes(include=['float64']).columns
    str_cols = df.select_dtypes(include=['object']).columns

    df.loc[:, float_cols] = df.loc[:, float_cols].fillna(float_na)
    df.loc[:, str_cols] = df.loc[:, str_cols].fillna(str_na)

    return df

# Function to trim all string columns in a dataframe
def trim_strings_df(df):
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    return df

#' function to get the conversion ratio to convert between different Uom (Unit of Measures)
def get_conversion_ratio(material, from_uom, to_uom):
    try:

        if to_uom == 'Trucks':
            to_uom = 'PAL'

        # get connection to database
        conn = pyodbc.connect('Driver={SQL Server};'
                            f'Server={config.SERVER_NAME};'
                            f'Database={config.DATABASE_NAME};'
                            'Trusted_Connection=yes;')
        
        # create SQL query
        sql = f'''SELECT [CombinedConversion]
                    FROM [{config.DATABASE_NAME}].{config.CONVERSION_TABLE}
                    WHERE [Material] = '{material}'
                    AND [From_Uom] = '{from_uom}'
                    AND [To_Uom] = '{to_uom}'
                    '''
        
        data = pd.read_sql(sql,conn)       

        conv_ratio = np.nan
        if len(data) > 0:
            conv_ratio = round(data.CombinedConversion.values[0],4)

            if to_uom == 'Trucks':            
                conv_ratio = round(conv_ratio / config.PAL_TO_TRUCKS_RATIO, 2)                
        
        conn.close()
    except Exception as e:        
        raise Exception(f"Database error: Unable to get conversion ration from {sql} Exception {e}")

    return conv_ratio

#' Function to get Next n periods from this period
def get_next_n_periods(this_period, n) :
    this_month = int(this_period.split('_')[1])
    this_year = int(this_period.split('_')[0])
    
    period_list = [this_period]
    
    # For requested n next periods generate next period strings
    for i in range(n):    
        next_year = this_year    
        if this_month==12:
            next_year = this_year+1
            next_month = 1
        else:
            next_month = this_month+1
        
        period_list.append(f"{next_year}_{next_month:02d}")
        
        this_year=next_year
        this_month=next_month
    
    return period_list

#' Function to get Previous n periods from this period
def get_previous_n_periods(this_period, n) :
    this_month = int(this_period.split('_')[1])
    this_year = int(this_period.split('_')[0])
    
    period_list = [this_period]
    
    # For requested n next periods generate pervious period strings
    for i in range(n):    
        prev_year = this_year    
        if this_month==1:
            prev_year = this_year-1
            prev_month = 12
        else:
            prev_month = this_month-1
        
        period_list.append(f"{prev_year}_{prev_month:02d}")
        
        this_year=prev_year
        this_month=prev_month
    
    period_list.reverse()
    
    return period_list


# Function to get data from the database for a given table
def get_datatable_from_db(table_name, where_string=''):
    logging.info(f'Fetching data for {table_name}')
    try:
        conn = pyodbc.connect('Driver={SQL Server};'
                            f'Server={config.SERVER_NAME};'
                            f'Database={config.DATABASE_NAME};'
                            'Trusted_Connection=yes;')

        sql = f''' SELECT * FROM [{config.DATABASE_NAME}].{table_name} {where_string} '''

        data = pd.read_sql(sql,conn)

        data = trim_strings_df(data)
        data = fill_na_by_type(data)

        conn.close()
    except Exception as e:
        raise Exception(f"Database Error: Unable to fetch data for [{config.DATABASE_NAME}].{table_name} Exception {e}")

    return data


# Function to get import lever from movement datatable in database
def get_import_lever(config):
    logging.info(f'Fetching movement data from databse ')

    conn = pyodbc.connect('Driver={SQL Server};'
                        f'Server={config.SERVER_NAME};'
                        f'Database={config.DATABASE_NAME};'
                        'Trusted_Connection=yes;')

    query_string = '''
                    DECLARE @cols AS NVARCHAR(MAX),
                        @query  AS NVARCHAR(MAX);

                    select @cols = STUFF((SELECT distinct ',' + QUOTENAME(c.Year_Period) 
                                FROM [PACSQL_MTP].[dbo].[temp_mP_Summarised_materiallevel] c
                                FOR XML PATH(''), TYPE
                                ).value('.', 'NVARCHAR(MAX)') 
                            ,1,1,'')

                    set @query = 'SELECT [FromCountry], [ToCountry], [Material], ' + @cols + ' from 
                                (
                                    select [FromCountry], [ToCountry], [Material], Year_Period, Value
                                    from [PACSQL_MTP].[dbo].[temp_mP_Summarised_materiallevel]
                                    where [FromCountry] <> ''GB''
                                    and [ToRepack_Flag] = 0
                            ) x
                                pivot 
                                (
                                    sum(Value)
                                    for Year_Period in (' + @cols + ')
                                ) p '


                    execute(@query)
                '''

    data = pd.read_sql(query_string, conn)
    data = data.round(2)
    data = trim_strings_df(data)
    data = fill_na_by_type(data)

    conn.close()

    return data


#' Function to read all the differend Transformed APO logs from the database and saves to Pickle files.
#' Alteryx workflows transform APO logs and update data in SQL database (Alteryx WFs developed by Stephen Wooliscroft)
def get_data_from_db(input_pickle_dir):

    # read Demand Plan summarised data
    dP_siteSummarised = get_datatable_from_db(table_name=config.DEMAND_TABLE)   
    dP_siteSummarised['Value'] = dP_siteSummarised['Value'].apply(FloatOrZero) 
    dP_siteSummarised.to_pickle(os.path.join(input_pickle_dir, 'dP_siteSummarised'))

    # read Inventory Plan summarised data
    iP_Summarised = get_datatable_from_db(table_name=config.INVENTORY_TABLE)
    iP_Summarised['Value'] = iP_Summarised['Value'].apply(FloatOrZero)
    iP_Summarised.to_pickle(os.path.join(input_pickle_dir, 'iP_Summarised'))

    # read Movement Plan summarised data
    mP_Summarised = get_datatable_from_db(table_name=config.MOVEMENT_TABLE)
    mP_Summarised['Value'] = mP_Summarised['Value'].apply(FloatOrZero)
    mP_Summarised.to_pickle(os.path.join(input_pickle_dir, 'mP_Summarised'))

    # read Shift Plan data
    get_shift_data()       
    
    # read Supply PLan Cofill summarised data
    sP_portSummarisedCofill = get_datatable_from_db(table_name=config.SUPPLY_PLAN_COFILL_TABLE)
    sP_portSummarisedCofill['Value'] = sP_portSummarisedCofill['Value'].apply(FloatOrZero)
    sP_portSummarisedCofill.to_pickle(os.path.join(input_pickle_dir, 'sP_portSummarisedCofill'))

    # read Supply plan inhouse summarised data
    sP_portSummarisedIH = get_datatable_from_db(table_name=config.SUPPLY_PLAN_INHOUSE_TABLE) 
    sP_portSummarisedIH['Value'] = sP_portSummarisedIH['Value'].apply(FloatOrZero)   
    sP_portSummarisedIH.to_pickle(os.path.join(input_pickle_dir, 'sP_portSummarisedIH'))

    # read Supply PLan In House Lineloading summarised data
    sP_portSummarisedIHLineLoading = get_datatable_from_db(table_name=config.SUPPLY_PLAN_INHOUSE_LINELOADING_TABLE)    
    sP_portSummarisedIHLineLoading['Value'] = sP_portSummarisedIHLineLoading['Value'].apply(FloatOrZero)   
    sP_portSummarisedIHLineLoading.to_pickle(os.path.join(input_pickle_dir, 'sP_portSummarisedIHLineLoading'))    

    # get conversion table that has conversion rations between different Unit of Measures (UoM)
    conversion_table = get_datatable_from_db(table_name=config.CONVERSION_TABLE,
                                        where_string = "Where From_Uom in ('PAL', 'ZRW','ZUC') AND To_Uom in ('PAL', 'ZRW','ZUC')")
    conversion_table['CombinedConversion'] = conversion_table['CombinedConversion'].apply(FloatOrZero)
    conversion_table.to_pickle(os.path.join(input_pickle_dir, 'conversion_table'))

    # read production capacity data
    production_capacity = get_datatable_from_db(table_name=config.PRODUCTION_CAPACITY_TABLE, where_string='WHERE GETDATE() BETWEEN [ValidFrom] AND [ValidTo]')
    production_capacity['BaseUnitsPerHour'] = production_capacity['BaseUnitsPerHour'].apply(FloatOrZero)
    production_capacity.to_pickle(os.path.join(input_pickle_dir, 'production_capacity'))

    # read DSI table for ZUC and ZRW
    zuc_dsi = get_dsi_table()
    zrw_dsi = get_dsi_table(uom='ZRW')
    dsi_pickle = pd.merge(zuc_dsi, zrw_dsi, on=['Site_SAP', 'Level2Region', 'Summary_Portfolio', 
                                    'Material', 'Year_Period', 'BucketsInPeriod'], how='inner')

    dsi_pickle.to_pickle(os.path.join(input_pickle_dir, config.DSI_PICKLE))



#' Function to summarise dataframe for visualisation purpose.
def summarise_df_for_visualisation(df):
    unwanted_cols = ['Material', 'Value']
    cols = [ele for ele in df.columns.tolist() if ele not in unwanted_cols] 
    
    df['Value'] = df['Value'].fillna(0)
    df[cols] = df[cols].fillna('') 
        
    df = df[cols+['Value']].groupby(cols).sum().round().reset_index()    

    return df


#' Function to get the demand plan from the Demand pickle file.
def get_demand_plan(level='Summary_Portfolio', uom='ZUC'):
    pivot_cols = ['KeyField']
    pivot_rows = [level, 'Year_Period']
    value_col = ['Value']
    agg_func = np.sum
    filter_by = {'Uom':uom}

    # read deamand pickle file
    df = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.DEMAND_PICKLE))

    # summaris demand plan for visualisation
    df = summarise_df_for_visualisation(df)

    # Filter df by the filter cliteria
    df = df.loc[(df[list(filter_by)] == pd.Series(filter_by)).all(axis=1)]

    # Create a pivot table that will be used to plot data
    plot_df = pd.pivot_table(df, values=value_col, index=pivot_rows,
                        columns=pivot_cols, aggfunc=agg_func)

    # Flatten pivot table dataframe
    demand_plan = pd.DataFrame(plot_df.to_records())
    demand_plan.columns = [hdr.replace("('Value', '", "").replace("')", "") \
                        for hdr in demand_plan.columns]

    #Calcuate fields
    demand_plan['Stock_Availability'] = (demand_plan['Available']*100 / demand_plan['Total']).astype(int)

    demand_plan = demand_plan.fillna(0)

    return demand_plan



#' Function to get the Movement plan from the Demand pickle file.
def get_movement_plan(level='Summary_Portfolio', uom='ZUC'):

    pivot_cols = ['Move_Type']
    pivot_rows = [level, 'Year_Period']
    value_col = ['Value']
    agg_func = np.sum
    filter_by = {'Uom': uom}

    # Read pickle file and summarise dataframe
    df = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.MOVEMENT_PICKLE))    
    df = summarise_df_for_visualisation(df)
    df['ToRepack_Flag'] = df['ToRepack_Flag'].astype(str)
    
    # Conditional categories used to categorise a column into categories    
    cofill_sites = import_cofill_metadata.loc[import_cofill_metadata.Import_Cofill == 'Cofill']['Site_SAP_From'].tolist()
    cofill_sites = [x.split('_')[0] for x in cofill_sites]    

    import_sites = import_cofill_metadata.loc[import_cofill_metadata.Import_Cofill == 'Import']['Site_SAP_From'].tolist()

    # Specify conditions list
    conditions = [
        (df['FromCountry'] == 'GB') & (df['ToCountry'] != 'GB'),
        (df['Site_SAP_From'].isin(cofill_sites) | df['Site_SAP_To'].str.contains('Cofill')),
        (df['Site_SAP_From'].isin(import_sites) | df['Site_SAP_To'].str.contains('Import')),
        (df['FromCountry'] == 'GB') & (df['ToCountry'] == 'GB') & (df['ToRepack_Flag'] == 'True'),
        (df['FromCountry'] == 'GB') & (df['ToCountry'] == 'GB') & (df['ToRepack_Flag'] == 'False')
        ]
    choices = ['Export', 'Cofill_Movement', 'Import', 'Domestic Repack', 'IBT']

    
    df['Move_Type'] = np.select(conditions, choices, default='Move_Other')
   
    logging.info(df['Move_Type'].value_counts(dropna=False))

    df = df.loc[(df[list(filter_by)] == pd.Series(filter_by)).all(axis=1)]

    plot_df = pd.pivot_table(df, values=value_col, index=pivot_rows,
                        columns=pivot_cols, aggfunc=agg_func)

    movement_plan = pd.DataFrame(plot_df.to_records())

    movement_plan.columns = [hdr.replace("('Value', '", "").replace("')", "") for hdr in movement_plan.columns]

    movement_plan = movement_plan.fillna(0)

    return movement_plan


# Production Plan In House
def get_production_inhouse_plan(level='Summary_Portfolio', uom='ZUC'):
    pivot_cols = ['Uom']
    pivot_rows = [level, 'Year_Period']
    value_col = ['Value']
    agg_func = np.sum
    filter_by = {'Uom': uom}

    df = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.SUPPLY_PLAN_INHOUSE_PICKLE))
    df = summarise_df_for_visualisation(df)
    df = df.loc[(df[list(filter_by)] == pd.Series(filter_by)).all(axis=1)]

    plot_df = pd.pivot_table(df, values=value_col, index=pivot_rows,
                        columns=pivot_cols, aggfunc=agg_func)

    prod_plan_inhouse = pd.DataFrame(plot_df.to_records())

    prod_plan_inhouse.columns = [hdr.replace("('Value', '", "").replace(f"{uom}')", "Production") \
                     for hdr in prod_plan_inhouse.columns]


    prod_plan_inhouse = prod_plan_inhouse.fillna(0)

    return prod_plan_inhouse


# Production Plan  Cofill
def get_production_cofill_plan(level='Summary_Portfolio', uom='ZUC'):

    pivot_cols = ['Uom']
    pivot_rows = [level, 'Year_Period']
    value_col = ['Value']
    agg_func = np.sum
    filter_by = {'Uom': uom}

    df = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.SUPPLY_PLAN_COFILL_PICKLE))
    df = summarise_df_for_visualisation(df)
    df = df.loc[(df[list(filter_by)] == pd.Series(filter_by)).all(axis=1)]

    plot_df = pd.pivot_table(df, values=value_col, index=pivot_rows,
                        columns=pivot_cols, aggfunc=agg_func)

    prod_plan_cofill = pd.DataFrame(plot_df.to_records())

    prod_plan_cofill.columns = [hdr.replace("('Value', '", "").replace(f"{uom}')", "Cofill") \
                     for hdr in prod_plan_cofill.columns]


    prod_plan_cofill = prod_plan_cofill.fillna(0)

    return prod_plan_cofill


# Inventory Plan 
def get_inventory_plan(level='Summary_Portfolio', uom='ZUC'):
    pivot_cols = ['Inventory_Type']
    pivot_rows = [level, 'Year_Period']
    value_col = ['Value']
    agg_func = np.sum
    filter_by = {'Uom': uom}

    df = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.INVENTORY_PICKLE))
    df = summarise_df_for_visualisation(df)

    # Conditional categories
    conditions = [
        df.KeyField.str.endswith('ClosingStock'),
        df.KeyField.str.contains('StockVsTarget', case=False)
        ]
    choices = ['Inventory_Closing','Inventory_National_Target']

    df['Inventory_Type'] = np.select(conditions, choices, default='Inventory_Other')

    df = df.loc[(df[list(filter_by)] == pd.Series(filter_by)).all(axis=1)]

    plot_df = pd.pivot_table(df, values=value_col, index=pivot_rows,
                        columns=pivot_cols, aggfunc=agg_func)

    inventory_plan = pd.DataFrame(plot_df.to_records())

    inventory_plan.columns = [hdr.replace("('Value', '", "").replace("')", "") for hdr in inventory_plan.columns]

    inventory_plan = inventory_plan.fillna(0)

    return inventory_plan


# Days of Stock Inventory Plan - Projected stock holding 
def get_dsi_plan(level='Line_Portfolio', uom='ZUC'):
    pivot_cols = ['DSI_Type']
    pivot_rows = [level, 'Year_Period']
    value_col = ['Value']
    agg_func = np.sum
    filter_by = {}

    df = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.INVENTORY_PICKLE))
    df = summarise_df_for_visualisation(df)

    # Conditional categories
    conditions = [
        (df.KeyField == 'Days_DSI_National_LinePortfolio'),
        (df.KeyField == 'Days_DSI_Regional_LinePortfolio') & (df.Level2Region == 'North'),
        (df.KeyField == 'Days_DSI_Regional_LinePortfolio') & (df.Level2Region == 'South'),
        (df.KeyField == 'Days_DSI_Regional_LinePortfolio') & (df.Level2Region == 'Scotland'),
        (df.KeyField == 'Days_ClosingStockTarget_National_LinePortfolio')
        ]
    choices = ['DSI_National','DSI_North', 'DSI_South', 'DSI_Scotland', 'DSI_Target_National']

    df['DSI_Type'] = np.select(conditions, choices, default='DSI_Other')

    df = df.loc[(df[list(filter_by)] == pd.Series(filter_by)).all(axis=1)]

    plot_df = pd.pivot_table(df, values=value_col, index=pivot_rows,
                        columns=pivot_cols, aggfunc=agg_func)

    dsi_plan = pd.DataFrame(plot_df.to_records())

    dsi_plan.columns = [hdr.replace("('Value', '", "").replace("')", "") for hdr in dsi_plan.columns]

    dsi_plan = dsi_plan.fillna(0)

    return dsi_plan


# Merge all the demand / supply plan DFs into one dataframe
def get_comined_long_and_wide_df(wide_df_name='wide_df', long_df_name='long_df', level='Summary_Portfolio', uom='ZUC'):    
    demand_plan = get_demand_plan(level, uom)
    movement_plan = get_movement_plan(level, uom)
    prod_plan_inhouse = get_production_inhouse_plan(level, uom)    
    inventory_plan = get_inventory_plan(level, uom)
    prod_plan_cofill = get_production_cofill_plan(level, uom)

    dfs = [demand_plan, movement_plan, prod_plan_inhouse, prod_plan_cofill, inventory_plan]    
    dfs = [df.set_index(['Summary_Portfolio', 'Year_Period']) for df in dfs]
    
    wide_df = dfs[0].join(dfs[1:]).reset_index()
    wide_df =wide_df.fillna(0)       

    wide_df.to_pickle(os.path.join(config.INPUT_PICKLE_DIR, wide_df_name))

    key_cols = ['Summary_Portfolio', 'Year_Period']
    value_cols = list(set(wide_df.columns) - set(key_cols))

    #' Wide to Long DF
    long_df = wide_df.melt(id_vars=key_cols, 
                value_vars=value_cols,
                var_name='Category', value_name='Value')

    long_df['Parent_Category'] = ['Demand' if x in ['Total','Domestic Repack', 'Export'] \
                                       else 'Supply' if x in ['Production','Import', 'Cofill', 'Cofill_Movement'] \
                              else '' for x in long_df.Category]

    long_df.to_pickle(os.path.join(config.INPUT_PICKLE_DIR, long_df_name))

    return wide_df, long_df
    

# Production Line Plan

def get_production_line_plan(level='Line_Portfolio', uom='Hours'):
    pivot_cols = ['KeyField']
    pivot_rows = [level, 'Site_SAP', 'Line', 'Year_Period']
    value_col = ['Value']
    agg_func = np.sum
    filter_by = {'Uom': uom}

    df = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.SUPPLY_PLAN_INHOUSE_LINELOADING_PICKLE))
    
    df = summarise_df_for_visualisation(df)

    wide_df = pd.pivot_table(df, values=value_col, index=pivot_rows,
                        columns=pivot_cols, aggfunc=agg_func)

    production_line_plan = pd.DataFrame(wide_df.to_records())

    production_line_plan.columns = [hdr.replace("('Value', '", "").replace("')", "") \
                        for hdr in production_line_plan.columns]

    production_line_plan['Consumed'] = production_line_plan['Consumed'].astype(float)
    production_line_plan['Capacity'] = production_line_plan['Capacity'].astype(float)

    #Calcuated fields
    production_line_plan['Capacity_Utilisation'] = production_line_plan['Consumed']*100 / production_line_plan['Capacity']

    production_line_plan['Available_Vol'] = production_line_plan['EstimatedUnconsumedCapacity']
    production_line_plan['Available_Vol_with_Safety_Hours'] = production_line_plan['EstimatedUnconsumedCapacity'] + production_line_plan['EstimatedHoursSpareCapacity']


    production_line_plan = production_line_plan.fillna(0)

    return production_line_plan



# Shift Data
def get_shift_plan(input_pickle_dir, pickle_file_name='MTP_WF003_05_Visualise Baseline Plan_ShiftData'):
    pivot_cols = ['Hours_Type']
    pivot_rows = ['Site_SAP', 'Line', 'Year_Period']
    value_col = ['Value']
    agg_func = np.sum
    filter_by = {}

    df = pd.read_pickle(os.path.join(input_pickle_dir, pickle_file_name))

    # Conditional categories
    conditions = [
        df.KeyField == 'Hours_Spare',
        df.KeyField == 'Hours_DownTime', 
        df.KeyField == 'Hours_SchedPDT',
        df.KeyField == 'Hours_UnCrewed',
        ]
    choices = ['Spare_Hours','Planned_Downtime', 'Loss_Factor', 'Uncrewed']

    df['Hours_Type'] = np.select(conditions, choices, default='Hours_Other')

    #'Filter'
    df = df.loc[(df[list(filter_by)] == pd.Series(filter_by)).all(axis=1)]

    # pivot
    wide_df = pd.pivot_table(df, values=value_col, index=pivot_rows,
                        columns=pivot_cols, aggfunc=agg_func)


    shift_plan = pd.DataFrame(wide_df.to_records())

    shift_plan.columns = [hdr.replace("('Value', '", "").replace("')", "") \
                        for hdr in shift_plan.columns]

    shift_plan = shift_plan.fillna(0)

    return shift_plan



# Freight plan data showing movement of trucks between sites
def get_freight_plan(level='Summary_Portfolio', uom='Trucks', portfolio='LPET'):
    pivot_cols = ['Year_Period']
    pivot_rows = [level, 'To_GeoRegion', 'From_GeoRegion']
    value_col = ['Value']
    agg_func = np.sum

    if portfolio == 'Total_GB':
        filter_by = {'Uom':uom}
    else:
        filter_by = {'Uom':uom, 'Summary_Portfolio':portfolio}

    df = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.MOVEMENT_PICKLE))
    df = summarise_df_for_visualisation(df)

    df = df.loc[ ~df.To_GeoRegion.isna() & ~df.From_GeoRegion.isna() ]
    df[pivot_rows] = df[pivot_rows].fillna('NA')
    df[value_col] = df[value_col].fillna(0)

    df['From_GeoRegion'] = pd.Categorical(df['From_GeoRegion'], ["North", "South", "Scotland"])
    df['To_GeoRegion'] = pd.Categorical(df['To_GeoRegion'], ["North", "South", "Scotland"])


    df = df.loc[(df[list(filter_by)] == pd.Series(filter_by)).all(axis=1)]


    wide_df = pd.pivot_table(df, values=value_col, index=pivot_rows,
                        columns=pivot_cols, aggfunc=agg_func)

    wide_df = wide_df.fillna(0)

    wide_df = wide_df.round(0).astype(int)    

    freight_df = pd.concat([
                        d.append(d.sum().rename((k, 'Total')))
                        for k, d in wide_df.groupby(level=1)
                    ]).append(wide_df.sum().rename(('Grand', 'Total')))

    freight_df = pd.DataFrame(freight_df.to_records())

    freight_df.columns = [hdr.replace("('Value', '", "").replace("')", "") for hdr in freight_df.columns] 

    return freight_df


# Function to get the Days of Stock Inventory Heatmap by Summary Portfolio for every period
def get_dsi_heatmap(level='Summary_Portfolio', uom='ZUC'):    

    conn = pyodbc.connect('Driver={SQL Server};'
                            f'Server={config.SERVER_NAME};'
                            f'Database={config.DATABASE_NAME};'
                            'Trusted_Connection=yes;')
      

    sql = f'''
            WITH DSI_TABLE AS (
                SELECT	  
                    CASE PD.[Site_SAP]
                            WHEN 'P67' THEN '5567'
                            WHEN 'P69' THEN '5569'
                            WHEN 'P14' THEN '5504'
                            ELSE PD.[Site_SAP]
                        END AS Site_SAP
                    ,CASE PD.[Site_SAP]
                            WHEN 'P67' THEN 'North'
                            WHEN 'P69' THEN 'North'
                            WHEN 'P14' THEN 'South'
                            ELSE PD.[Level2Region]
                        END AS Level2Region
                    ,PD.[Summary_Portfolio] 
                    ,PD.[Material]
                    ,CONCAT([Year],'_',format (CAST(PD.[CCEP_Period] AS INT), '0#')) AS Year_Period
                    ,CASE WHEN PD.[CCEP_Period] IN ('3','6','9','12') THEN 5 ELSE 4 END AS BucketsInPeriod
                    ,ROUND(convert(float,PD.[Value]),0) AS TotalDemand
                    ,ROUND(convert(float, PD.[Value],0) / ((CASE WHEN PD.[CCEP_Period] IN ('3','6','9','12') THEN 5 ELSE 4 END)*7),2) AS PeriodDailyDemand
                    ,ROUND(convert(float, IP.[Value]),0) AS ClosingStock
                    ,ROUND(convert(float,IP_target.[Value]),0) AS ClosingStock_Target
                FROM [PACSQL_MTP].{config.PROJECTED_DEMAND_TABLE} PD
                INNER JOIN [PACSQL_MTP].{config.INVENTORY_TABLE} IP
                    ON IP.Year_Period = CONCAT(PD.[Year],'_',format (CAST(PD.[CCEP_Period] AS INT), '0#'))
                    AND IP.Material = PD.[Material]
                    AND IP.Site_SAP = PD.Site_SAP
                INNER JOIN [PACSQL_MTP].{config.INVENTORY_TABLE} IP_target
                    ON IP_target.Year_Period = CONCAT(PD.[Year],'_',format (CAST(PD.[CCEP_Period] AS INT), '0#'))
                    AND IP_target.Material = PD.[Material]
                    AND IP_target.Site_SAP = PD.Site_SAP
                WHERE 1=1
                    AND PD.[Table] = 'Demand_Site_Material'
                    AND PD.[KeyField] = '{uom}_TotalDemand'
                    AND IP.[KeyField] = '{uom}_ClosingStock'
                    AND IP_target.[KeyField] = '{uom}_ClosingStockTarget'
            ),
            DSI_GROUPED AS (
                select Summary_Portfolio, Year_Period 
                        ,SUM(TotalDemand) AS Total_Demand 
                        ,SUM(PeriodDailyDemand) AS PeriodDailyDemand 
                        ,SUM(ClosingStock) AS ClosingStock
                        ,SUM(ClosingStock_Target) AS ClosingStock_Target
                        ,ROUND(SUM(ClosingStock) / SUM(PeriodDailyDemand), 2) AS DSI_Planned
                        ,ROUND(SUM(ClosingStock_Target) / SUM(PeriodDailyDemand), 2) AS DSI_Target			
                FROM DSI_TABLE
                GROUP BY Summary_Portfolio, Year_Period
            )
            SELECT Summary_Portfolio
            ,Year_Period
            ,Total_Demand
            ,PeriodDailyDemand
            ,ClosingStock
            ,ClosingStock_Target
            ,DSI_Planned
            ,DSI_Target
            ,ROUND((DSI_Target - DSI_Planned) *100 / DSI_Target, 2) AS DSI_Under_Target_Percent
            FROM DSI_GROUPED    
    '''

    data = pd.read_sql(sql,conn) 

    planned_dsi = pd.pivot(data, values=['DSI_Planned'], index=['Summary_Portfolio'], columns=['Year_Period'])
    planned_dsi = pd.DataFrame(planned_dsi.to_records())    
    planned_dsi.columns = [hdr.replace("('DSI_Planned', '", "").replace("')", "") for hdr in planned_dsi.columns]
    
    target_dsi = pd.pivot(data, values=['DSI_Target'], index=['Summary_Portfolio'], columns=['Year_Period'])
    target_dsi = pd.DataFrame(target_dsi.to_records())
    target_dsi.columns = [hdr.replace("('DSI_Target', '", "").replace("')", "") for hdr in target_dsi.columns]

    diff_df = pd.pivot(data, values=['DSI_Under_Target_Percent'], index=['Summary_Portfolio'], columns=['Year_Period'])
    diff_df = pd.DataFrame(diff_df.to_records())
    diff_df.columns = [hdr.replace("('DSI_Under_Target_Percent', '", "").replace("')", "") for hdr in diff_df.columns]

    return planned_dsi, target_dsi, diff_df


# Function to create a shift lever that user will use to add time to production lines
def get_shift_lever(shift_lever):
    shift_lever = shift_lever[config.SHIFT_LEVER_COLUMNS]
    shift_lever = shift_lever.drop_duplicates(subset=['Site_SAP','Line','Year_Period'])
    shift_lever['Site_SAP'] = shift_lever['Site_SAP'].fillna(0).astype(int).astype(str)

    production_capability = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'production_capacity'))
    production_capability = production_capability[['Plant', 'Line', 'Material']].drop_duplicates()
    production_capability.columns = ['Site_SAP', 'Line', 'Material']
    production_capability.Site_SAP = production_capability.Site_SAP.astype(str)

    shift_lever = pd.merge(shift_lever, production_capability, on=['Site_SAP', 'Line'])
    
    from alerts import alerts
    demand_shortfalls = alerts.get_demand_alerts()
    demand_shortfalls.drop_duplicates()
    demand_shortfalls = demand_shortfalls.drop(['MaterialDescription'], axis=1)
    inventory_shortfalls = alerts.get_inventory_alerts()
    inventory_shortfalls.drop_duplicates()
    inventory_shortfalls = inventory_shortfalls.drop(['MaterialDescription'], axis=1)
    
    
    shift_lever = pd.merge(shift_lever, demand_shortfalls.drop('Portfolio', axis=1), 
                        left_on=['Material','Year_Period'], right_on=['Demand_Material','Year_Period'], 
                        how='left')        
    shift_lever = pd.merge(shift_lever, inventory_shortfalls.drop('Portfolio', axis=1), 
                            left_on=['Material','Year_Period'], right_on=['Inventory_Material','Year_Period'], 
                            how='left')
 
    
    
    shift_lever = shift_lever.drop("Material", axis=1)
    shift_lever = shift_lever.fillna("")
    shortfall_cols = ['Demand_Site', 'Demand_Material', 'Additional_Units_Required', 
                      'Inventory_Site', 'Inventory_Material', 'Inventory_Units_Required']

    for col in shortfall_cols:
            shift_lever[col] = shift_lever[col].astype(str)

    shift_lever['Material_Site_DemandShortfall'] = shift_lever[['Demand_Material', 'Demand_Site', 'Additional_Units_Required']].agg('_'.join, axis=1)
    shift_lever['Material_Site_InventoryShortfall'] = shift_lever[['Inventory_Material', 'Inventory_Site', 'Inventory_Units_Required']].agg('_'.join, axis=1)
    shift_lever = shift_lever.replace('__','')
    shift_lever = shift_lever.drop(shortfall_cols, axis=1)    

    agg_cols = ['Material_Site_DemandShortfall', 'Material_Site_InventoryShortfall']

    for col in agg_cols:
        shift_lever[col] = shift_lever[col].astype(str)
        shift_lever[col] = shift_lever.groupby(config.SHIFT_LEVER_COLUMNS)[col].transform(lambda x : ' '.join(set(x))) 


    shift_lever = shift_lever.drop_duplicates()    

    return shift_lever

# Function to get the list of distinct SNP codes for all materials
def get_snp_list():
    try:      

        conn = pyodbc.connect('Driver={SQL Server};'
                            f'Server={config.SERVER_NAME};'
                            f'Database={config.DATABASE_NAME};'
                            'Trusted_Connection=yes;')
        
        sql = f'''SELECT DISTINCT SNPPL01 FROM [{config.DATABASE_NAME}].{config.MATERIAL_HEADER_TABLE} '''

        data = pd.read_sql(sql,conn)   

        data.to_csv(os.path.join(config.INPUT_PICKLE_DIR, 'SNPPL01_LIST'))
        
        conn.close()
    except Exception as e:        
        logging.info(f"Database error: Unable to get Material information from [{config.DATABASE_NAME}].{config.MATERIAL_HEADER_TABLE} Exception {e}")
        data = pd.read_csv(os.path.join(config.INPUT_PICKLE_DIR, 'SNPPL01_LIST'))

    return data

# Function to get SNPPL01 and material list for selected SNPPL01 code or Material code.
def get_material_list(SNPPL01=None, material=None):
    try:      

        conn = pyodbc.connect('Driver={SQL Server};'
                            f'Server={config.SERVER_NAME};'
                            f'Database={config.DATABASE_NAME};'
                            'Trusted_Connection=yes;')
        if SNPPL01:
            sql = f'''SELECT DISTINCT Material, SNPPL01 
                      FROM [{config.DATABASE_NAME}].{config.MATERIAL_HEADER_TABLE} 
                      WHERE SNPPL01 = '{SNPPL01}'
                      '''
        elif material:
            sql = f'''SELECT DISTINCT Material, SNPPL01 
                      FROM [{config.DATABASE_NAME}].{config.MATERIAL_HEADER_TABLE} 
                      WHERE Material = '{material}'
                      '''
        else:
            sql = f'''SELECT DISTINCT Material, SNPPL01 FROM [{config.DATABASE_NAME}].{config.MATERIAL_HEADER_TABLE} '''

        data = pd.read_sql(sql,conn)   
        data['Material_Desc']  =  data[['Material', 'SNPPL01']].agg(' - '.join, axis=1)
        
        conn.close()
    except Exception as e:        
        raise Exception(f"Database error: Unable to get Material information from [{config.DATABASE_NAME}].{config.PRODUCTION_CAPACITY_TABLE} Exception {e}")

    return data

# Function to get shift data from the database
def get_shift_data():
    try:      

        conn = pyodbc.connect('Driver={SQL Server};'
                            f'Server={config.SERVER_NAME};'
                            f'Database={config.DATABASE_NAME};'
                            'Trusted_Connection=yes;')
        
        sql = f'''
                WITH SHIFT_DATA AS (
                    SELECT Site_SAP, Line, [Year], CCEP_Period, sum(AvailHours) as AvailHours, sum(SchedPDT) as SchedPDT, sum(DownTime) as DownTime, 
                    sum(ProdTimeH) as ProdTimeH, sum(Spare) as Spare, sum(ShiftDays) as ShiftDays, sum(AvailHours) / sum(ShiftDays) as Avg_AvailHours,
                    AVG(LossFactor) as LossFactor, AVG(SafetyHours) as SafetyHours
                    FROM [{config.DATABASE_NAME}].{config.SHIFT_DATA_TABLE}  	  
                    group by  Site_SAP, Line, [Year], CCEP_Period
                )
                SELECT 
                    SD.[Site_SAP]
                    ,SD.[Line]
                    ,CONCAT(SD.[Year],'_',format (CAST(SD.[CCEP_Period] AS INT), '0#')) AS Year_Period  
                    ,CASE CAST(SD.[CCEP_Period] AS INT) % 3 WHEN 0 THEN 5 ELSE 4 END AS Weeks_In_Period
                    ,SD.[ShiftDays] as Shift_Days      
                    ,SD.[Avg_AvailHours] AS Shift_Length
                    ,0 AS Hours_Overtime
                    ,AvailHours AS Hours_Crew	
                    ,SD.[LossFactor] AS Loss_Factor
                    ,SD.[DownTime] AS Hours_Down_Time
                    ,ROUND(SD.[SchedPDT],2) AS Hours_Sched_PDT
                    ,SD.[SafetyHours] AS Safety_Hours	
                    ,ROUND(((AvailHours - SD.[DownTime] - ROUND(SD.[SchedPDT],2))*SD.[SafetyHours]),2)  as Hours_Total_Available	
                FROM SHIFT_DATA SD 

         '''
       
        
        data = pd.read_sql(sql,conn)                          
         
        data['Additional_Hours_Used'] = data['Hours_Total_Available_Calc'] = data['Hours_UnCrewed'] = data['Additional_Hours'] = 0

        data['Hours_Crew'] = data['Shift_Length'].astype(float) * data['Shift_Days'].astype(float) + data['Hours_Overtime'].astype(float)

        data.to_csv(os.path.join(config.INPUT_LEVER_DIR , config.SHIFT_LEVER_FILE), index=False)

        conn.close()
    except Exception as e:        
        raise Exception(f"Database error: Unable to get Material information from [{config.DATABASE_NAME}].{config.SHIFT_DATA_TABLE} Exception {e}")

    return data

# Function to get Site to region mapping
def get_site_region_mapping(config):
    try:      

        conn = pyodbc.connect('Driver={SQL Server};'
                            f'Server={config.SERVER_NAME};'
                            f'Database={config.DATABASE_NAME};'
                            'Trusted_Connection=yes;')
        
        sql = f'''
                SELECT DISTINCT
                        TRIM([ToCountry]) as country   
                        ,TRIM([To_GeoRegion]) as region   
                        ,TRIM([Site_SAP_To]) as site
                FROM [{config.DATABASE_NAME}].{config.MOVEMENT_TABLE}
                UNION
                SELECT DISTINCT
                        TRIM([FromCountry]) as country   
                        ,TRIM([From_GeoRegion]) as region
                        ,TRIM([Site_SAP_From]) as site
                FROM [{config.DATABASE_NAME}].{config.MOVEMENT_TABLE}
                '''
        
        data = pd.read_sql(sql,conn)           
        
        conn.close()
    except Exception as e:        
        raise Exception(f"Database error: Unable to get Site Region mapping from [{config.DATABASE_NAME}].{config.MOVEMENT_TABLE} Exception {e}")

    return data

# Function to read import and confill metadata from the input csv file
def get_import_cofill_metadata():

    import_lever_metadata = pd.read_csv(os.path.join(config.METADATA_DIR, config.IMPORT_COFILL_METADATA_FILE))
    import_lever_metadata = import_lever_metadata.fillna('')
    import_lever_metadata['Site_SAP_From'] = import_lever_metadata['Site_SAP_From'].astype(str).str.strip()

    import_lever_metadata = import_lever_metadata.loc[import_lever_metadata.Import_Cofill.isin(['Import', 'Cofill'])]
    import_lever_metadata['Site'] = import_lever_metadata[['Site_SAP_From', 'Site_Name']].agg(' - '.join, axis=1)

    return import_lever_metadata

# Function to get site mapping from database.
def get_site_mapping():
    try:      

        conn = pyodbc.connect('Driver={SQL Server};'
                            f'Server={config.SERVER_NAME};'
                            f'Database={config.DATABASE_NAME};'
                            'Trusted_Connection=yes;')
        
        sql = f'''SELECT * FROM [{config.DATABASE_NAME}].{config.SITE_MAPPING_TABLE} '''
        
        data = pd.read_sql(sql,conn)           
        
        conn.close()
    except Exception as e:        
        raise Exception(f"Database error: Unable to get Material information from [{config.DATABASE_NAME}].{config.SHIFT_DATA_TABLE} Exception {e}")

    return data


# Function to get days stock inventory from the database.
def get_dsi_table(uom='ZUC'):
    try:      

        conn = pyodbc.connect('Driver={SQL Server};'
                            f'Server={config.SERVER_NAME};'
                            f'Database={config.DATABASE_NAME};'
                            'Trusted_Connection=yes;')        
        
        sql = f'''
                SELECT	  
                    CASE PD.[Site_SAP]
                            WHEN 'P67' THEN '5567'
                            WHEN 'P69' THEN '5569'
                            WHEN 'P14' THEN '5504'
                            ELSE PD.[Site_SAP]
                        END AS Site_SAP
                    ,CASE PD.[Site_SAP]
                            WHEN 'P67' THEN 'North'
                            WHEN 'P69' THEN 'North'
                            WHEN 'P14' THEN 'South'
                            ELSE PD.[Level2Region]
                        END AS Level2Region
                    ,PD.[Summary_Portfolio] 
                    ,PD.[Material]
                    ,CONCAT([Year],'_',format (CAST(convert(float,PD.[CCEP_Period],0) AS INT), '0#')) AS Year_Period
                    ,CASE CAST(convert(float,PD.[CCEP_Period],0) AS INT) % 3 WHEN 0 THEN 5 ELSE 4 END AS BucketsInPeriod
                    ,PD.[Value] AS {uom}_TotalDemand
                    ,ROUND(convert(float,PD.[Value],0) / ((CASE CAST(convert(float,PD.[CCEP_Period],0) AS INT) % 3 WHEN 0 THEN 5 ELSE 4 END)*7),2) AS {uom}_PeriodDailyDemand
                    ,IP.[Value] AS {uom}_ClosingStock
                    ,IP_target.[Value] AS {uom}_ClosingStock_Target                    
                FROM [PACSQL_MTP].{config.PROJECTED_DEMAND_TABLE} PD
                INNER JOIN [PACSQL_MTP].{config.INVENTORY_TABLE} IP
                    ON IP.Year_Period = CONCAT(PD.[Year],'_',format (CAST(convert(float,PD.[CCEP_Period],0) AS INT), '0#'))
                    AND IP.Material = PD.[Material]
                    AND IP.Site_SAP = PD.Site_SAP
                INNER JOIN [PACSQL_MTP].{config.INVENTORY_TABLE} IP_target
                    ON IP_target.Year_Period = CONCAT(PD.[Year],'_',format (CAST(convert(float,PD.[CCEP_Period],0) AS INT), '0#'))
                    AND IP_target.Material = PD.[Material]
                    AND IP_target.Site_SAP = PD.Site_SAP
                WHERE 1=1
                    AND PD.[Table] = 'Demand_Site_Material'
                    AND PD.[KeyField] = '{uom}_TotalDemand'
                    AND IP.[KeyField] = '{uom}_ClosingStock'
                    AND IP_target.[KeyField] = '{uom}_ClosingStockTarget'
        '''

        dsi_table = pd.read_sql(sql,conn)  
        
        conn.close()
    except Exception as e:        
        raise Exception(f"Database error: Unable to get DSI information from [{config.DATABASE_NAME}].{config.PROJECTED_DEMAND_TABLE} and {config.INVENTORY_TABLE} Exception {e}")

    return dsi_table

# function to create demand table for the alter demand lever
def get_alter_demand_table():
    dp = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.DEMAND_PICKLE))
    mh = get_datatable_from_db(table_name=config.MATERIAL_HEADER_TABLE, where_string="WHERE SNPPL01 LIKE '%(IH)%' ")

    dp.Material = dp.Material.astype(str)
    mh.Material = mh.Material.astype(str)

    dp = pd.merge(dp, mh[['SNPPL01', 'Material', 'FLAVOR', 'MaterialDescription']], on='Material')
    dp['Material_Desc'] = dp[['Material', 'MaterialDescription']].agg(' - '.join, axis=1)

    return dp

#' function to get the production plan from database.
def get_inhouse_production_plan():
    try:      

        conn = pyodbc.connect('Driver={SQL Server};'
                            f'Server={config.SERVER_NAME};'
                            f'Database={config.DATABASE_NAME};'
                            'Trusted_Connection=yes;')

        sql = f'''
                SELECT   
                    IH.[Site_SAP]
                    ,IH.[Line]
                    ,IH.[Year_Period]
                    ,IH.[Summary_Portfolio]
                    ,IH.[Material]
                    ,IH.[Uom]
                    ,IH.[Value]
                    ,PC.[BaseUnitsPerHour]
                    ,ROUND(IH.[Value] / PC.[BaseUnitsPerHour], 2) AS ConsumedHours
                FROM [PACSQL_MTP].{config.SUPPLY_PLAN_INHOUSE_TABLE} IH
                INNER JOIN [PACSQL_MTP].{config.PRODUCTION_CAPACITY_TABLE} PC
                    ON IH.Site_SAP = PC.Plant
                    AND IH.Line = PC.Line
                    AND IH.Material = PC.Material
                    WHERE 1=1
                    AND GETDATE() BETWEEN PC.ValidFrom AND PC.ValidTo
                    AND IH.Uom = 'ZUC'
            '''      
        
        data = pd.read_sql(sql,conn)           
        
        conn.close()
    except Exception as e:        
        raise Exception(f"Database error: Unable to get DSI information from [{config.DATABASE_NAME}].{config.PROJECTED_DEMAND_TABLE} and {config.INVENTORY_TABLE} Exception {e}")

    return data

# Function to get the data for the DSI plot 
def get_dsi_plot(summary_portfolio, uom='ZUC'):
    
    dsi_table = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.DSI_PICKLE ))

    if summary_portfolio == 'Total_GB':
        dsi_table.Summary_Portfolio = 'Total_GB'

    dsi_table = dsi_table.loc[dsi_table.Summary_Portfolio == summary_portfolio]

    dsi_table[f'{uom}_ClosingStock'] = dsi_table[f'{uom}_ClosingStock'].astype(float)
    dsi_table[f'{uom}_ClosingStock_Target'] = dsi_table[f'{uom}_ClosingStock_Target'].astype(float)
    dsi_group = dsi_table[['Summary_Portfolio', 'Level2Region', 'Year_Period', 
            f'{uom}_PeriodDailyDemand', f'{uom}_ClosingStock', 
            f'{uom}_ClosingStock_Target']].groupby(['Summary_Portfolio', 'Level2Region', 'Year_Period']).sum().reset_index()

    # This periods closing stock is used as inventory for next period so we shift period by -1
    dsi_north = dsi_group[dsi_group.Level2Region == 'North']
    dsi_north['Days_DSI'] = dsi_north[f'{uom}_ClosingStock'] / dsi_north[f'{uom}_PeriodDailyDemand'].shift(-1)
    dsi_north['Days_DSI_Target'] = dsi_north[f'{uom}_ClosingStock_Target'] / dsi_north[f'{uom}_PeriodDailyDemand'].shift(-1)

    dsi_south = dsi_group[dsi_group.Level2Region == 'South']
    dsi_south['Days_DSI'] = dsi_south[f'{uom}_ClosingStock'] / dsi_south[f'{uom}_PeriodDailyDemand'].shift(-1)
    dsi_south['Days_DSI_Target'] = dsi_south[f'{uom}_ClosingStock_Target'] / dsi_south[f'{uom}_PeriodDailyDemand'].shift(-1)

    dsi_scotland = dsi_group[dsi_group.Level2Region == 'Scotland']
    dsi_scotland['Days_DSI'] = dsi_scotland[f'{uom}_ClosingStock'] / dsi_scotland[f'{uom}_PeriodDailyDemand'].shift(-1)
    dsi_scotland['Days_DSI_Target'] = dsi_scotland[f'{uom}_ClosingStock_Target'] / dsi_scotland[f'{uom}_PeriodDailyDemand'].shift(-1)

    dsi_group = pd.concat([dsi_north, dsi_south, dsi_scotland])

    dsi_regional = pd.pivot(dsi_group, 
            values=['Days_DSI', 'Days_DSI_Target'],
            index=[ 'Summary_Portfolio', 'Year_Period'],
            columns=['Level2Region']
            )

    dsi_regional = pd.DataFrame(dsi_regional.to_records())
    dsi_regional.columns = [hdr.replace("('Days_DSI_Target', '", "Target_").replace("('Days_DSI', '", "Planned_").replace("')", "") for hdr in dsi_regional.columns]

    #' DSI National
    dsi_national = dsi_table[['Summary_Portfolio', 'Year_Period', 
            f'{uom}_PeriodDailyDemand', f'{uom}_ClosingStock', 
            f'{uom}_ClosingStock_Target']].groupby(['Summary_Portfolio', 'Year_Period']).sum().reset_index()

    dsi_national['Planned_National'] = dsi_national[f'{uom}_ClosingStock'] / dsi_national[f'{uom}_PeriodDailyDemand'].shift(-1)
    dsi_national['Target_National'] = dsi_national[f'{uom}_ClosingStock_Target'] / dsi_national[f'{uom}_PeriodDailyDemand'].shift(-1)

    dsi_national = dsi_national[['Summary_Portfolio', 'Year_Period', 'Planned_National', 'Target_National']]

    dsi_plot = pd.merge(dsi_regional, dsi_national, on=['Summary_Portfolio', 'Year_Period'], how='inner')    

    dsi_plot = dsi_plot.dropna()

    return dsi_plot


# Function to get next period from this period
def get_next_period(this_period) :
    this_month = int(this_period.split('_')[1])
    this_year = int(this_period.split('_')[0])        
    
    next_year = this_year
    if this_month==12:
        next_year = this_year+1
        next_month = 1
    else:
        next_month = this_month+1
   
    return f"{next_year}_{next_month:02d}"


def get_material_header():
    return None



import_cofill_metadata = get_import_cofill_metadata()
snp_list = get_snp_list()
material_list = get_material_list()
site_mapping = get_site_mapping()
production_capacity = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, 'production_capacity'))


line_loading = pd.read_pickle(os.path.join(config.INPUT_PICKLE_DIR, config.SUPPLY_PLAN_INHOUSE_LINELOADING_PICKLE))

inhouse_production = get_inhouse_production_plan()

alter_demand_table = get_alter_demand_table()


combined_df, long_df = get_comined_long_and_wide_df()

#' DSI Heat map
planned_dsi, target_dsi, diff_df = get_dsi_heatmap()





