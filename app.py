import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import geopandas as gpd
import pandas as pd
import json
import branca.colormap as cm

# =============================
#   Mortalidad en Antioquia – Dash
# =============================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# -----------------------------------------------------------
# Lectura de datos (igual que en tu código original)
# -----------------------------------------------------------
# Dataset de mortalidad
dataset_final = pd.read_csv("datos/Mortalidad_General_en_el_departamento_de_Antioquia.csv")

# Convertir el código de municipio a string para merge
dataset_final["CodigoMunicipio"] = dataset_final["CodigoMunicipio"].astype(str)

# Shapefile de municipios
shapefile = gpd.read_file("datos/MGN2021_MPIO_POLITICO/MGN_MPIO_POLITICO.shp")

# Hacer merge con geopandas
df_merge = shapefile.merge(
    dataset_final,
    left_on="MPIO_CCDGO",
    right_on="CodigoMunicipio",
    how="left"
)

# Asegurar que es un GeoDataFrame válido
df_merge = gpd.GeoDataFrame(df_merge, geometry="geometry", crs="EPSG:4326")

# -----------------------------------------------------------
# Layout
# -----------------------------------------------------------
app.layout = dbc.Container([
    html.H1("Mortalidad en Antioquia", className="text-center my-4"),

    dbc.Row([
        dbc.Col([
            html.Label("Seleccione el año (Tasa por mil)"),
            dcc.Dropdown(
                id="anio_tasa",
                options=[{"label": str(anio), "value": anio} for anio in sorted(dataset_final["Año"].unique())] +
                        [{"label": "Todos los años", "value": "Todos los años"}],
                value="Todos los años"
            ),
            html.Div(id="mapa_tasa")
        ], md=6),

        dbc.Col([
            html.Label("Seleccione el año (Número de casos)"),
            dcc.Dropdown(
                id="anio_casos",
                options=[{"label": str(anio), "value": anio} for anio in sorted(dataset_final["Año"].unique())] +
                        [{"label": "Todos los años", "value": "Todos los años"}],
                value="Todos los años"
            ),
            html.Div(id="mapa_casos")
        ], md=6)
    ])
], fluid=True)

# -----------------------------------------------------------
# Callback: mapa de Tasa
# -----------------------------------------------------------
@app.callback(
    Output("mapa_tasa", "children"),
    Input("anio_tasa", "value")
)
def update_mapa_tasa(anio):
    if anio == "Todos los años":
        df = df_merge.groupby(
            ["NombreMunicipio", "CodigoMunicipio", "NombreRegion", "geometry"]
        ).agg({"TasaXMilHabitantes": "mean"}).reset_index()
    else:
        df = df_merge[df_merge["Año"] == anio]

    df = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    geojson = json.loads(df.to_json())

    values = df["TasaXMilHabitantes"]
    min_val, max_val = values.min(), values.max()
    cmap = cm.linear.YlOrRd_09.scale(min_val, max_val)

    def style_function(feature):
        valor = feature["properties"].get("TasaXMilHabitantes")
        return {
            "fillColor": cmap(valor) if valor is not None else "transparent",
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.7,
        }

    def on_each_feature(feature, layer):
        municipio = feature["properties"].get("NombreMunicipio", "")
        valor = feature["properties"].get("TasaXMilHabitantes", "")
        layer.bindTooltip(f"{municipio}: {round(valor, 2)}")

    choropleth = dl.GeoJSON(
        data=geojson,
        id="geojson_tasa",
        zoomToBounds=True,
        options=dict(style=style_function),
        hoverStyle={"weight": 3, "color": "red", "fillOpacity": 0.9},
        onEachFeature=on_each_feature,
    )

    return dl.Map(
        children=[
            dl.TileLayer(),
            choropleth,
            cmap.to_step(index=[min_val, max_val], caption="Tasa por mil", width=20, height=150),
        ],
        style={"width": "100%", "height": "600px"},
        center=[6.5, -75.5],
        zoom=7,
    )

# -----------------------------------------------------------
# Callback: mapa de Casos
# -----------------------------------------------------------
@app.callback(
    Output("mapa_casos", "children"),
    Input("anio_casos", "value")
)
def update_mapa_casos(anio):
    if anio == "Todos los años":
        df = df_merge.groupby(
            ["NombreMunicipio", "CodigoMunicipio", "NombreRegion", "geometry"]
        ).agg({"NumeroCasos": "sum"}).reset_index()
    else:
        df = df_merge[df_merge["Año"] == anio]

    df = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    geojson = json.loads(df.to_json())

    values = df["NumeroCasos"]
    min_val, max_val = values.min(), values.max()
    cmap = cm.linear.OrRd_09.scale(min_val, max_val)

    def style_function(feature):
        valor = feature["properties"].get("NumeroCasos")
        return {
            "fillColor": cmap(valor) if valor is not None else "transparent",
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.7,
        }

    def on_each_feature(feature, layer):
        municipio = feature["properties"].get("NombreMunicipio", "")
        valor = feature["properties"].get("NumeroCasos", "")
        layer.bindTooltip(f"{municipio}: {valor}")

    choropleth = dl.GeoJSON(
        data=geojson,
        id="geojson_casos",
        zoomToBounds=True,
        options=dict(style=style_function),
        hoverStyle={"weight": 3, "color": "blue", "fillOpacity": 0.9},
        onEachFeature=on_each_feature,
    )

    return dl.Map(
        children=[
            dl.TileLayer(),
            choropleth,
            cmap.to_step(index=[min_val, max_val], caption="Número de casos", width=20, height=150),
        ],
        style={"width": "100%", "height": "600px"},
        center=[6.5, -75.5],
        zoom=7,
    )

# -----------------------------------------------------------
# Run
# -----------------------------------------------------------
if __name__ == "__main__":
    app.run_server(debug=True)

