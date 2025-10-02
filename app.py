import dash
from dash import Dash, dcc, html, Input, Output, dash_table
import pandas as pd
import geopandas as gpd
import plotly.express as px
import folium
from dash.dependencies import Input, Output
import dash_leaflet as dl

# -----------------------------------------------------------
# 1. Lectura de datos
# -----------------------------------------------------------
ruta_dataset = "data/Mortalidad_General_en_el_departamento_de_Antioquia_desde_2005_20250915.csv"
ruta_shapefile = "data/MGN_MPIO_POLITICO.shp"

dataset = pd.read_csv(ruta_dataset, dtype={"CodigoMunicipio": str})

dataset_shapefile = gpd.read_file(ruta_shapefile)
dataset_shapefile = dataset_shapefile[dataset_shapefile["DPTO_CCDGO"] == "05"]
dataset_shapefile = dataset_shapefile[["MPIO_CDPMP", "MPIO_CNMBR", "geometry"]].to_crs(4326)

dataset_final = dataset[["NombreMunicipio", "CodigoMunicipio", "NombreRegion", "Año", "NumeroCasos", "TasaXMilHabitantes"]]
dataset_final["CodigoMunicipio"] = dataset_final["CodigoMunicipio"].astype(str)
dataset_shapefile["MPIO_CDPMP"] = dataset_shapefile["MPIO_CDPMP"].astype(str)

df_merge = dataset_shapefile.merge(dataset_final, left_on="MPIO_CDPMP", right_on="CodigoMunicipio")

lista_anios = ["Todos los años"] + sorted(df_merge["Año"].unique().tolist())

# -----------------------------------------------------------
# 2. Inicializar Dash
# -----------------------------------------------------------
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

app.title = "Mortalidad en Antioquia"

# -----------------------------------------------------------
# 3. Layout con pestañas
# -----------------------------------------------------------
app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label="Contexto", children=[
            html.H2("Contexto del proyecto"),
            html.P("Este proyecto realiza un análisis georreferenciado de la mortalidad en el departamento de Antioquia..."),
            html.H3("Objetivo del análisis"),
            html.Ul([
                html.Li("Visualizar la distribución espacial de la mortalidad."),
                html.Li("Identificar patrones territoriales."),
                html.Li("Generar mapas y gráficas para la comprensión del fenómeno.")
            ]),
            html.H3("Fuente del dataset"),
            html.A("Datos Abiertos de Colombia",
                   href="https://www.datos.gov.co/Salud-y-Protecci-n-Social/Mortalidad-General-en-el-departamento-de-Antioquia/fuc4-tvui/about_data",
                   target="_blank"),
            html.H5("Autor: Johan David Diaz Lopez")
        ]),

        dcc.Tab(label="Tabla de Datos", children=[
            html.H2("Tabla completa del dataset con geometría unida"),
            dash_table.DataTable(
                id="tabla_merge",
                columns=[{"name": i, "id": i} for i in df_merge.drop(columns="geometry").columns],
                data=df_merge.drop(columns="geometry").to_dict("records"),
                page_size=20,
                style_table={"overflowX": "auto"},
                style_cell={"fontSize": 12, "textAlign": "left"}
            )
        ]),

        dcc.Tab(label="Estadísticas descriptivas", children=[
            html.H2("Estadística descriptiva"),
            dash_table.DataTable(
                id="tabla_summary",
                columns=[
                    {"name": "Variable", "id": "Variable"},
                    {"name": "Estadístico", "id": "Estadistico"},
                    {"name": "Valor", "id": "Valor"}
                ],
                data=pd.concat([
                    df_merge["NumeroCasos"].describe().rename_axis("Estadistico").reset_index().assign(Variable="NumeroCasos"),
                    df_merge["TasaXMilHabitantes"].describe().rename_axis("Estadistico").reset_index().assign(Variable="TasaXMilHabitantes")
                ])[["Variable", "Estadistico", "Valor"]].to_dict("records"),
                style_table={"overflowX": "auto"},
                style_cell={"fontSize": 12}
            )
        ]),

        dcc.Tab(label="Tasa de mortalidad", children=[
            dcc.Dropdown(id="anio_tasa", options=[{"label": i, "value": i} for i in lista_anios], value="Todos los años"),
            dcc.Graph(id="mapa_tasa"),
            dcc.Dropdown(id="anio_top_tasa", options=[{"label": i, "value": i} for i in lista_anios], value="Todos los años"),
            dcc.Graph(id="plot_top10_tasa")
        ]),

        dcc.Tab(label="Número de defunciones", children=[
            dcc.Dropdown(id="anio_casos", options=[{"label": i, "value": i} for i in lista_anios], value="Todos los años"),
            dcc.Graph(id="mapa_casos"),
            dcc.Dropdown(id="anio_top_casos", options=[{"label": i, "value": i} for i in lista_anios], value="Todos los años"),
            dcc.Graph(id="plot_top10_casos")
        ])
    ])
])

# -----------------------------------------------------------
# 4. Callbacks
# -----------------------------------------------------------
@app.callback(
    Output("mapa_tasa", "figure"),
    Input("anio_tasa", "value")
)
def update_mapa_tasa(anio):
    if anio == "Todos los años":
        data = df_merge.groupby(["NombreMunicipio"]).TasaXMilHabitantes.mean().reset_index()
    else:
        data = df_merge[df_merge["Año"] == anio]
    fig = px.choropleth(df_merge,
                        geojson=df_merge.set_index("NombreMunicipio").geometry.__geo_interface__,
                        locations="NombreMunicipio",
                        color="TasaXMilHabitantes",
                        projection="mercator",
                        title="Mapa Tasa de Mortalidad")
    fig.update_geos(fitbounds="locations", visible=False)
    return fig

@app.callback(
    Output("plot_top10_tasa", "figure"),
    Input("anio_top_tasa", "value")
)
def update_top10_tasa(anio):
    if anio == "Todos los años":
        data = df_merge.groupby("NombreMunicipio").TasaXMilHabitantes.mean().reset_index()
    else:
        data = df_merge[df_merge["Año"] == anio].groupby("NombreMunicipio").TasaXMilHabitantes.mean().reset_index()
    data = data.sort_values("TasaXMilHabitantes", ascending=False).head(10)
    fig = px.bar(data, x="TasaXMilHabitantes", y="NombreMunicipio", orientation="h", title="Top 10 Tasa")
    return fig

@app.callback(
    Output("mapa_casos", "figure"),
    Input("anio_casos", "value")
)
def update_mapa_casos(anio):
    if anio == "Todos los años":
        data = df_merge.groupby(["NombreMunicipio"]).NumeroCasos.sum().reset_index()
    else:
        data = df_merge[df_merge["Año"] == anio]
    fig = px.choropleth(df_merge,
                        geojson=df_merge.set_index("NombreMunicipio").geometry.__geo_interface__,
                        locations="NombreMunicipio",
                        color="NumeroCasos",
                        projection="mercator",
                        title="Mapa Número de Casos")
    fig.update_geos(fitbounds="locations", visible=False)
    return fig

@app.callback(
    Output("plot_top10_casos", "figure"),
    Input("anio_top_casos", "value")
)
def update_top10_casos(anio):
    if anio == "Todos los años":
        data = df_merge.groupby("NombreMunicipio").NumeroCasos.sum().reset_index()
    else:
        data = df_merge[df_merge["Año"] == anio].groupby("NombreMunicipio").NumeroCasos.sum().reset_index()
    data = data.sort_values("NumeroCasos", ascending=False).head(10)
    fig = px.bar(data, x="NumeroCasos", y="NombreMunicipio", orientation="h", title="Top 10 Casos")
    return fig

# -----------------------------------------------------------
# 5. Ejecutar
# -----------------------------------------------------------
if __name__ == "__main__":
    app.run_server(debug=True)
