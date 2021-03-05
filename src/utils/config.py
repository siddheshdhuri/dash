import yaml
import os

config_file = 'config.yaml'   


with open(config_file, 'r') as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

DATABASE_NAME = cfg['database_name']
SERVER_NAME = cfg['server_name']

DEMAND_TABLE = cfg['demand_table']
INVENTORY_TABLE = cfg['inventory_table']
MOVEMENT_TABLE = cfg['movemment_table']
SUPPLY_PLAN_COFILL_TABLE = cfg['supply_plan_cofill_table']
SUPPLY_PLAN_INHOUSE_TABLE = cfg['supply_plan_inhouse_table']
SUPPLY_PLAN_INHOUSE_LINELOADING_TABLE = cfg['supply_plan_lineloading_table']

DEMAND_PICKLE = cfg['demand_pickle']
INVENTORY_PICKLE = cfg['inventory_pickle']
MOVEMENT_PICKLE = cfg['movement_pickle']
SUPPLY_PLAN_COFILL_PICKLE = cfg['supply_plan_cofill_pickle']
SUPPLY_PLAN_INHOUSE_PICKLE = cfg['supply_plan_inhouse_pickle']
SUPPLY_PLAN_INHOUSE_LINELOADING_PICKLE = cfg['supply_plan_lineloading_pickle']
SHIFT_PLAN_PICKLE = cfg['shift_plan_pickle']
DSI_PICKLE = cfg['dsi_pickle']

SHIFT_DATA_TABLE = cfg['shift_data_table']

CONVERSION_TABLE = cfg['conversion_table']
PRODUCTION_CAPACITY_TABLE = cfg['production_capacity_table']
MATERIAL_HEADER_TABLE = cfg['material_header_table']
SITE_MAPPING_TABLE = cfg['site_mapping_table']
PROJECTED_DEMAND_TABLE = cfg['projected_demand_table']

INPUT_PICKLE_DIR = cfg['input_pickle_dir']
INPUT_LEVER_DIR = cfg['input_lever_dir']
OUTPUT_BASELINE_DIR = cfg['output_baseline_dir']
OUTPUT_VIZ_DATA_DIR = cfg['output_viz_data_dir']
METADATA_DIR = cfg['metadata_dir']

SHIFT_LEVER_COLUMNS = cfg['shift_lever_cols']

PAL_TO_TRUCKS_RATIO = cfg['pal_to_trucks_ratio']

IMPORT_COFILL_HUB = cfg['import_cofill_hub']
IMPORT_HUB = cfg['import_hub']
COFILL_HUB = cfg['cofill_hub']
IMPORT_COFILL_LEVER_FILE = cfg['import_cofill_lever_file']
IMPORT_COFILL_METADATA_FILE = cfg['import_cofill_metadata_file']
SHIFT_LEVER_FILE = cfg['shift_lever_file']
#INPUT_DIR = cfg['input_dir']
#OUTPUT_DIR = cfg['output_dir']

ADD_TIME_REGARDLESS_OF_PERIOD = cfg['add_time_regardless_of_period']