from database import transforms

import dash
import plotly
from dash.dependencies import Input, Output
from app import app
from tabs import sidepanel, tab_visualisation, tab_shift_lever, tab_dsi, tab_alerts, tab_import_cofill_lever, tab_alter_demand
import pandas as pd
from pyfladesk import init_gui

app.layout = sidepanel.layout

@app.callback(Output('tabs-content', 'children'),
              [Input('tabs', 'value')])
def render_content(tab):
    if tab == 'tab-visualisation':
        return tab_visualisation.layout
    elif tab == 'tab-shift-lever':
       return tab_shift_lever.layout
    elif tab == 'tab-dsi':
       return tab_dsi.layout
    elif tab == 'tab-alerts':
       return tab_alerts.layout
    elif tab == 'tab-import-cofill':
       return tab_import_cofill_lever.layout
    elif tab == 'tab-alter-demand':
       return tab_alter_demand.layout



if __name__ == '__main__':
    init_gui(app.server)
    #app.run_server(debug = True)