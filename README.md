# This is the application for Mid-Term Planning.


## Setting up project from Git

You have an empty repository
To get started you will need to run these commands in your terminal.

New to Git? Learn the basic Git commands
Configure Git for the first time

```
git config --global user.name "Your Name as on BitBucket Account"
git config --global user.email "Email account registered with BitBucket"
```

## Working with your repository

To simply clone this empty repository then run this command in your terminal.

git clone https://git.ccep-dev.com/scm/mtp/mtp.git


## Virtual Environment:

We use python virtual environments using pipenv to maintain clear 
This help is maintaining project dependencies in an effective manner.

When you are running the application for the first time you will have to create
a new virtual environment using the following command. Ensure you are currently in the 
folder wheren you can see the `Pipfile.lock`

`pipenv shell`

once the environment is created you will see the name of your virtual environment as a string as the start of your command prompt.
The environement name will be something link (mtp-P4lxf2bF) this is a unique identifier and it will be different for your environment.
you can now install all the required dependencies using the following command

`pipenv install`

One the environment is created the first time, hence forth you only need to activate the environment before running your programs.
with the same commamnd used to create your environment. Make sure you execure this command in the same directory when your Pipfile.lock 
is created, otherwise it will not detect the existing environment and create a new one.

`pipenv shell`


Jupyter Lab:
JupyterLab is a web-based interactive development environment for Jupyter notebooks, code, and data.
to start Jupyter Lab you just need to execute following command

`jupyter lab`


## To Launch the application:

The application connects to the database PACSQL_MTP on the CVAPWPEQR001. ensure that you are connected to the CCEP VPN.
if you face any database connection isses please reach out to CCEP IT team.

Make sure you are in the project folder named 'mtp', From there you can execute the run command

`mtp> run`

this will start the dash server and launch the application. 


## Configuring the tool

The configution variables such as Database name, input table names, output file locations can be specified in the config.yaml file
Eg: to configure the database connection you would change the following variables in the config.yaml file

`server_name: CVAPWPEQR001`
`database_name: PACSQL_MTP`


## Building a new release of the application

When there are code changes made to the tool, you will need to create a new build of the application codebase.

This process has been made simple with the use of the build script. You just have to run the `build` command and this will
create a new build and copy the release files into the projects /release folder.

`mtp> build`

We also have a video recording of the build process which you can find in the project folder at /docs/how_to_build.mp4


<video width="320" height="240" controls>
  <source src="/docs/how_to_build.mp4" type="video/mp4">
</video>

## Refreshing data in the the tool

The MTP tool connects to the PACSQL_MTP Database on the server CVAPWPEQR001. If new data has been loaded into the database tables and you need
to refresh the data in the tool then

case 1 -  Tables names in the database remain the same as before

As the tables names haven't changed, no changes are needed to configure the tool and the data in the tool can be simply refreshed using the 
Reset Data button on the sidepanel

![Reset Data](/images/reset_data_button.PNG)

Case 2 - Table names in the database have changed, compared to what they were in the last version of the tool

As the table names have now changed we need to tell the tool the new table names, these can be easily configured in the config.yaml file

![Database Tables](/images/database_tables.PNG)

Case 3 - Structure of the tables have changes eg: a column datatype has changed or the name of a column has changed/

This is a major strucutural changes and might require code changes.


## Glossary of terms:

*Summary Portfolio* : CCEP classification of product into a summary category. eg: LPET (Large Pet bottle). This is the highest level of product classification hierarchy

*Material* : Material code of the product. this is the lowest level of product classification hierarchy

*Year_Period* : This is the period that CCEP uses for their mid term planning. each period is either 4 week or 5 week period. they are organised as YYYY_MM codes

*Import* : When material is received from one of the import sites

*Cofill* : When material is received from one of the cofiller sites

*DSI* : Days of Stock Inventory, Number of day of stock available in inventory.

*SNPPL01* : CCEP's internal categorisation of products

*ZUC* : Unit cases a unit of measure of stock

*ZRW* : Raw cases a unit of measure of stock

*PAL* : Pallettes a unit of measure of stock

*Truck* : Truck to move between sites

*run rate* : production capacity of a production line (number of units / per hour)



## INPUT DATA

INPUT DATA	                    DATABASE TABLE NAME
demand_table                    dbo.temp_dP_siteSummarised_materiallevel_REFRESH     -   Datatable with current demand requirements for material at a given site

inventory_table	                dbo.temp_iP_Summarised_materiallevel_REFRESH

movemment_table	                dbo.temp_mP_Summarised_materiallevel_REFRESH

supply_plan_cofill_table	    dbo.temp_sP_portSummarisedCofill_materiallevel_REFRESH

supply_plan_inhouse_table	    dbo.temp_sP_portSummarisedIH_materiallevel_REFRESH

supply_plan_lineloading_table	dbo.temp_sP_portSummarisedIHLineLoading_materiallevel_REFRESH

shift_data_table	            dbo.ProductionShiftFile_FullVersion
	
conversion_table	            Material.Output_ecc_ConversionTable

production_capacity_table	    production.Extract_ecc_ProductionCapability

material_header_table	        material.Model_MaterialHeader_02

site_mapping_table	            dbo.temp_tbl_usermaintained_CPEtoSAPSiteMapping
	
projected_demand_table	        model.MTP_WF003_02_ProjectedDemand_REFRESH

projected_demand_table: 	    model.MTP_WF003_02_ProjectedDemand_REFRESH


### USER INPUT FILES:

When user creates a new lever using the user interface, the lever data is stored into CSV files.
these CSV files are used by the tool to run the respective baseline and what-if scenarios.

import_cofill_metadata - input/metadata/import_cofill_metadata.csv

![Import Cofill Metadata](/images/import_cofill_metadata.PNG)

import_cofill_lever    - input/levers/import_cofill_lever.csv

![Import Cofill Lever](/images/import_cofill_lever_csv.PNG)

Add time lever         - input/levers/shift_lever.csv

![Add time lever](/images/add_time_lever_csv.PNG)

Alter Demand Lever     - input/levers/alter_demand_lever.csv (aggregated by material)
                       - input/levers/alter_demand_lever_full.csv (material requirement per site)

Alter Demand Lever (Aggregated at material level)

![Alter Demand Lever](/images/alter_demand_lever_csv.PNG)

Alter Demand Lever Full (Aggregated at material level)

![Alter Demand Lever Full](/images/alter_demand_lever_full_csv.PNG)


### CODE

The Code it organised into modules in the 'src' folder. 

![code_structure](/images/code_structure.PNG)

The entry point of the application is the file *index.py* which laysput the components of the user interface.

*app.py* is the server that serves the dash application.

The rest of the code is organised into 5 folders

*alerts*
contains the alerts.py file that computes the demand and inventory shortfall alerts that are then displayed on the Alerts tab

*database*
contains the transforms.py file that performs the extraction and transformation of data from the database. Required data tables are read 
from the database and various functions are defined in the transforms.py file to performs required transformations on the raw data.

*hooks* - these are files required by the dash app and not developed by the developer. They contain no business logic.

*planner* - this folder contains the baseline.py file that contains functions for implementing the scenario plannning workflows as listed in
the design doc Mid-Term Planning Levers & Impactv_0.6.pdf

*tabs* - this folder cotains the the files that render the user interface. The various Tabs that you see on the UI are organised as separate tab_xxx.py files
*sidepanel.py*
*tab_alerts.py*
*tab_alter_demand.py*
*tab_dsi.py*
*tab_import_cofill_lever.py*
*tab_shift_lever.py*
*tab_visualisation.py*



*utils*
contains the config.py file that creates the config object from the config.yaml file that is used across the application.






### UI Files:

*sidepanel.py* 
This file contains the UI components of the Sidepanel, the sidepanel has controls for
selecting Summary_Portfolio, Unit of Measure, Include Safety Hours, and Export data.

The various Tabs that you see on the UI are organised as separate tab_xxx.py files


*tab_visualisation.py*
This file is the landing page that is the dashboard displaying all the charts. These visualisation were developed based on the prototype in  docs\GB Midterm Supply Planning Tool_v0.7.xlsx

![Visualisations Tab](/images/visualisations.PNG)


*tab_dsi.py*
This file conta ins functions to display DSI heatmaps, Days of Stock Inventory for each inventory. This table plot a pivot table for each Summary Portfolio agaist Every Yaer_Period 
with each cell showing the number of material units.

![DSI tab](/images/DSI.PNG)


*tab_alerts.py*

This file contains functions to display the demand shortfall and inventory shortfall alerts on the user interface.

![Alerts](/images/alerts.PNG)


*tab_alter_demand.py:*
This file contatins the functions to display the alter deman lever user input, that user can use to change the demand and run a 'What-if' scenario as 
described in the design document.

The Alter demand lever is used to test a What-if scenario. The user can add change the demand for a given material / SNP Portfolio 

![Alter Demand Lever](/images/alter_demand_lever.PNG)


*tab_import_cofill.py*
This file contains functionality to display the import cofill lever user input, User can change add import and cofill items and run the backedn engine
to reflect on the visualisation charts.

User can add Imports or Cofill of material items to increase inventory or required materials in a given period. to fulfill demand / inventory shortfall
in the current or next period.

![Import Cofill Lever](/images/import_cofill_lever.PNG)


*tab_shift_lever.py*
This file contains functions to display the add time lever, users can use this lever to add / remove time on a manufacturing line and take effect on the 
visualisations.

User can change in the table itself parameters such as Hours downtime, Spare Hours, etc.. to add / remove time to a production line
which can then be used to fullfill inventory / demand shortfall in the current or next period.

![Add Time Lever](/images/add_time_lever.PNG)


### Backend Processing Files:

*alerts/alerts.py*
Contains functionality to calculate demand shortfall alerts and inventory short fall alerts.
Demand short falls are when then Available Volume is lower than the Total required demand
and Inventory short falls are when the StockVsTarget is lower than zero
Excess Inventory is when StockVsTarget is greater than zero.

When Demand is higher thatn supply for a given period for a material at a site, you will see an alert for that.
when inventory Stock is lower than target you will see an alert for this on this tab.

*database/transforms.py*
This file contains the database extraction and transformation functions that are used across the application.
The raw data read from the PACSQL_MTP database tables is in long format and for visulisation and analysis need to 
be engineered into required formats

The Transforms.py file contains functions to convert data to wide format / summarise data / create pivot tables / filter data etc..

*planner/baseline.py*
this file contains functions to process the backend scenario planning rules. The logic explained the in lever workflows in the 
PDF file Mid-Term Planning Levers & Impactv_0.6.pdf








