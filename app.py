import dash
from dash import dcc, html, Input, Output, dash_table
import dash_leaflet as dl
import pandas as pd
import geopandas as gpd
import plotly.express as px
import json

# =============================
#   Mortalidad en Antioquia – Dash
# =============================

# 1. Lectura de datos
ruta_dataset = "data/Mortalidad_General_en_el_departamento_de_Antioquia_desde_2005_20250915.csv"
ruta_shapefile = "data/MGN_MPIO_POLITICO.shp"

dataset = pd.read_csv(
    ruta_dataset,
    dtype={"CodigoMunicipio": str}
)

# Shapefile de Antioquia
dataset_shapefile = gpd.read_file(ruta_shapefile)
dataset_shapefile = dataset_shapefile[dataset_shapefile["DPTO_CCDGO"] == "05"]
dataset_shapefile = dataset_shapefile[["MPIO_CDPMP", "MPIO_CNMBR", "geometry"]].to_crs(epsg=4326)

# Arreglar geometrías inválidas
dataset_shapefile["geometry"] = dataset_shapefile["geometry"].buffer(0)

dataset_final = dataset[["NombreMunicipio", "CodigoMunicipio", "NombreRegion", "Año", "NumeroCasos", "TasaXMilHabitantes"]]
dataset_final.loc[:, "CodigoMunicipio"] = dataset_final["CodigoMunicipio"].astype(str)
dataset_shapefile["MPIO_CDPMP"] = dataset_shapefile["MPIO_CDPMP"].astype(str)

df_merge = dataset_shapefile.merge(dataset_final, left_on="MPIO_CDPMP", right_on="CodigoMunicipio")

lista_anios = ["Todos los años"] + sorted(df_merge["Año"].unique().tolist())

# =============================
#   App Dash
# =============================
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    dcc.Tabs([

        # ----- Contexto -----
        dcc.Tab(label="Contexto", children=[
            html.H2("Contexto del proyecto"),
            html.P("Este proyecto realiza un análisis georreferenciado de la mortalidad en Antioquia, "
                   "a partir de registros municipales de defunciones entre 2005 y 2021."),
            html.H3("Objetivo del análisis"),
            html.Ul([
                html.Li("Visualizar la distribución espacial de la mortalidad."),
                html.Li("Identificar patrones territoriales de salud y acceso a servicios."),
                html.Li("Generar mapas coropléticos y gráficas para facilitar la comprensión.")
            ]),
            html.H3("Fuente del dataset"),
            html.A("Datos Abiertos de Colombia",
                   href="https://www.datos.gov.co/Salud-y-Protecci-n-Social/Mortalidad-General-en-el-departamento-de-Antioquia/fuc4-tvui/about_data",
                   target="_blank"),
            html.H5("Autor: Johan David Diaz Lopez")
        ]),

        # ----- Tabla de Datos -----
        dcc.Tab(label="Tabla de Datos", children=[
            dash_table.DataTable(
                id="tabla_merge",
                data=df_merge.drop(columns="geometry").to_dict("records"),
                columns=[{"name": i, "id": i} for i in df_merge.drop(columns="geometry").columns],
                page_size=15,
                style_table={"overflowX": "auto"},
            )
        ]),

        # ----- Estadísticas -----
        dcc.Tab(label="Estadísticas descriptivas", children=[
            dash_table.DataTable(
                id="tabla_summary",
                columns=[{"name": "Variable", "id": "Variable"},
                         {"name": "Estadístico", "id": "Estadistico"},
                         {"name": "Valor", "id": "Valor"}],
                style_table={"overflowX": "auto"},
                style_cell={"fontSize": 12}
            )
        ]),

        # ----- Tasa -----
        dcc.Tab(label="Tasa de mortalidad", children=[
            html.Label("Seleccione un año:"),
            dcc.Dropdown(id="anio_tasa", options=[{"label": i, "value": i} for i in lista_anios],
                         value="Todos los años"),
            html.Div(id="mapa_tasa")
        ]),

        # ----- Defunciones -----
        dcc.Tab(label="Número de defunciones", children=[
            html.Label("Seleccione un año:"),
            dcc.Dropdown(id="anio_casos", options=[{"label": i, "value": i} for i in lista_anios],
                         value="Todos los años"),
            html.Div(id="mapa_casos")
        ])
    ])
])

# =============================
#   Callbacks
# =============================

@app.callback(
    Output("tabla_summary", "data"),
    Input("tabla_summary", "id")
)
def update_summary(_):
    def resumen(x):
        return {
            "Mínimo": x.min(),
            "1er Cuartil": x.quantile(0.25),
            "Mediana": x.median(),
            "Media": x.mean(),
            "3er Cuartil": x.quantile(0.75),
            "Máximo": x.max()
        }

    df = []
    for col in ["NumeroCasos", "TasaXMilHabitantes"]:
        stats = resumen(df_merge[col])
        for k, v in stats.items():
            df.append({"Variable": col, "Estadistico": k, "Valor": round(v, 2)})
    return df


# ---- Mapa simple Antioquia (Tasa) ----
@app.callback(
    Output("mapa_tasa", "children"),
    Input("anio_tasa", "value")
)
def update_mapa_tasa(anio):
    df = dataset_shapefile.copy()
    geojson = json.loads(df.to_json())
    return dl.Map(
        children=[
            dl.TileLayer(),
            dl.GeoJSON(
                data=geojson,
                id="geojson_tasa",
                zoomToBounds=True,
                style={"color": "blue", "weight": 2, "fillOpacity": 0}
            )
        ],
        style={"width": "100%", "height": "600px"},
        center=[6.5, -75.5], zoom=7
    )


# ---- Mapa simple Antioquia (Defunciones) ----
@app.callback(
    Output("mapa_casos", "children"),
    Input("anio_casos", "value")
)
def update_mapa_casos(anio):
    df = dataset_shapefile.copy()
    geojson = json.loads(df.to_json())
    return dl.Map(
        children=[
            dl.TileLayer(),
            dl.GeoJSON(
                data=geojson,
                id="geojson_casos",
                zoomToBounds=True,
                style={"color": "blue", "weight": 2, "fillOpacity": 0}
            )
        ],
        style={"width": "100%", "height": "600px"},
        center=[6.5, -75.5], zoom=7
    )


# =============================
#   Lanzar app
# =============================
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
