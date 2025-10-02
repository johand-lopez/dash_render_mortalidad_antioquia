# =============================
#   Mortalidad en Antioquia – Dash (Python)
# =============================

import os
import pandas as pd
import geopandas as gpd
import dash
from dash import Dash, dcc, html, dash_table, Input, Output
import plotly.express as px
import dash_leaflet as dl

# -----------------------------------------------------------
# 1. Lectura de datos
# -----------------------------------------------------------
ruta_dataset = "data/Mortalidad_General_en_el_departamento_de_Antioquia_desde_2005_20250915.csv"
ruta_shapefile = "data/MGN_MPIO_POLITICO.shp"

# Dataset base
dataset = pd.read_csv(ruta_dataset, dtype={"CodigoMunicipio": str})

# Shapefile
gdf = gpd.read_file(ruta_shapefile)
gdf = gdf[gdf["DPTO_CCDGO"] == "05"][["MPIO_CDPMP", "MPIO_CNMBR", "geometry"]]
gdf = gdf.to_crs(epsg=4326)
gdf["MPIO_CDPMP"] = gdf["MPIO_CDPMP"].astype(str)

# Merge
df_merge = gdf.merge(dataset, left_on="MPIO_CDPMP", right_on="CodigoMunicipio")

lista_anios = ["Todos los años"] + sorted(df_merge["Año"].unique().tolist())

# -----------------------------------------------------------
# 2. Inicializar app
# -----------------------------------------------------------
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server  # necesario para Render

# -----------------------------------------------------------
# 3. Layout
# -----------------------------------------------------------
app.layout = dcc.Tabs([
    # ----- Contexto -----
    dcc.Tab(label="Contexto", children=[
        html.H2("Contexto del proyecto"),
        html.P("Este proyecto realiza un análisis georreferenciado de la mortalidad en el departamento de Antioquia, "
               "a partir de registros municipales de defunciones ocurridas entre 2005 y 2021."),
        html.H3("Objetivo del análisis"),
        html.Ul([
            html.Li("Visualizar la distribución espacial de la mortalidad en los municipios de Antioquia."),
            html.Li("Identificar patrones territoriales que reflejen diferencias de salud o acceso a servicios."),
            html.Li("Generar mapas y gráficos que faciliten la comprensión de estas diferencias."),
        ]),
        html.H3("Fuente del dataset"),
        html.A("Datos Abiertos de Colombia",
               href="https://www.datos.gov.co/Salud-y-Protecci-n-Social/Mortalidad-General-en-el-departamento-de-Antioquia/fuc4-tvui/about_data",
               target="_blank"),
        html.H5("Autor: Johan David Diaz Lopez")
    ]),

    # ----- Tabla de Datos -----
    dcc.Tab(label="Tabla de Datos", children=[
        html.H2("Tabla completa del dataset con geometría unida"),
        dash_table.DataTable(
            id="tabla_merge",
            columns=[{"name": c, "id": c} for c in df_merge.drop(columns="geometry").columns],
            data=df_merge.drop(columns="geometry").to_dict("records"),
            page_size=15,
            style_table={"overflowX": "auto"}
        )
    ]),

    # ----- Estadísticas descriptivas -----
    dcc.Tab(label="Estadísticas descriptivas", children=[
        html.H2("Estadística descriptiva"),
        dash_table.DataTable(
            id="tabla_summary",
            page_size=12,
            style_table={"overflowX": "auto"}
        )
    ]),

    # ----- Tasa de mortalidad -----
    dcc.Tab(label="Tasa de mortalidad", children=[
        dcc.Tabs([
            dcc.Tab(label="Mapa interactivo", children=[
                html.Label("Seleccione un año:"),
                dcc.Dropdown(id="anio_tasa", options=[{"label": x, "value": x} for x in lista_anios],
                             value="Todos los años"),
                dcc.Graph(id="mapa_tasa")
            ]),
            dcc.Tab(label="Top 10 más altos", children=[
                dcc.Dropdown(id="anio_top_tasa_alta", options=[{"label": x, "value": x} for x in lista_anios],
                             value="Todos los años"),
                dcc.Graph(id="plot_top10_tasa_alta")
            ]),
            dcc.Tab(label="Top 10 más bajos", children=[
                dcc.Dropdown(id="anio_top_tasa_baja", options=[{"label": x, "value": x} for x in lista_anios],
                             value="Todos los años"),
                dcc.Graph(id="plot_top10_tasa_baja")
            ])
        ])
    ]),

    # ----- Número de defunciones -----
    dcc.Tab(label="Número de defunciones", children=[
        dcc.Tabs([
            dcc.Tab(label="Mapa interactivo", children=[
                html.Label("Seleccione un año:"),
                dcc.Dropdown(id="anio_casos", options=[{"label": x, "value": x} for x in lista_anios],
                             value="Todos los años"),
                dcc.Graph(id="mapa_casos")
            ]),
            dcc.Tab(label="Top 10 más altos", children=[
                dcc.Dropdown(id="anio_top_casos_alto", options=[{"label": x, "value": x} for x in lista_anios],
                             value="Todos los años"),
                dcc.Graph(id="plot_top10_casos_alto")
            ]),
            dcc.Tab(label="Top 10 más bajos", children=[
                dcc.Dropdown(id="anio_top_casos_bajo", options=[{"label": x, "value": x} for x in lista_anios],
                             value="Todos los años"),
                dcc.Graph(id="plot_top10_casos_bajo")
            ])
        ])
    ])
])

# -----------------------------------------------------------
# 4. Callbacks
# -----------------------------------------------------------

# ---- Estadísticas descriptivas ----
@app.callback(
    Output("tabla_summary", "data"),
    Output("tabla_summary", "columns"),
    Input("tabla_summary", "id")
)
def resumen_stats(_):
    def resumen(x):
        return {
            "Mínimo": x.min(),
            "1er Cuartil": x.quantile(0.25),
            "Mediana": x.median(),
            "Media": x.mean(),
            "3er Cuartil": x.quantile(0.75),
            "Máximo": x.max()
        }

    resumen_df = pd.DataFrame([
        {"Variable": "NumeroCasos", **resumen(df_merge["NumeroCasos"])},
        {"Variable": "TasaXMilHabitantes", **resumen(df_merge["TasaXMilHabitantes"])}
    ])
    cols = [{"name": c, "id": c} for c in resumen_df.columns]
    return resumen_df.to_dict("records"), cols

# ---- Mapas ----
@app.callback(
    Output("mapa_tasa", "figure"),
    Input("anio_tasa", "value")
)
def update_mapa_tasa(anio):
    if anio == "Todos los años":
        df = df_merge.groupby(["NombreMunicipio", "geometry"]).agg({"TasaXMilHabitantes": "mean"}).reset_index()
    else:
        df = df_merge[df_merge["Año"] == anio]
    fig = px.choropleth(df,
                        geojson=df.set_index("NombreMunicipio").geometry.__geo_interface__,
                        locations=df.index,
                        color="TasaXMilHabitantes",
                        color_continuous_scale="Reds",
                        labels={"TasaXMilHabitantes": "Tasa"})
    fig.update_geos(fitbounds="locations", visible=False)
    return fig

@app.callback(
    Output("mapa_casos", "figure"),
    Input("anio_casos", "value")
)
def update_mapa_casos(anio):
    if anio == "Todos los años":
        df = df_merge.groupby(["NombreMunicipio", "geometry"]).agg({"NumeroCasos": "sum"}).reset_index()
    else:
        df = df_merge[df_merge["Año"] == anio]
    fig = px.choropleth(df,
                        geojson=df.set_index("NombreMunicipio").geometry.__geo_interface__,
                        locations=df.index,
                        color="NumeroCasos",
                        color_continuous_scale="OrRd",
                        labels={"NumeroCasos": "Casos"})
    fig.update_geos(fitbounds="locations", visible=False)
    return fig

# ---- Top 10 Tasa ----
@app.callback(
    Output("plot_top10_tasa_alta", "figure"),
    Input("anio_top_tasa_alta", "value")
)
def top10_tasa_alta(anio):
    df = df_merge if anio == "Todos los años" else df_merge[df_merge["Año"] == anio]
    df = df.groupby("NombreMunicipio")["TasaXMilHabitantes"].mean().nlargest(10).reset_index()
    return px.bar(df, x="TasaXMilHabitantes", y="NombreMunicipio", orientation="h", color="TasaXMilHabitantes",
                  color_continuous_scale="Reds")

@app.callback(
    Output("plot_top10_tasa_baja", "figure"),
    Input("anio_top_tasa_baja", "value")
)
def top10_tasa_baja(anio):
    df = df_merge if anio == "Todos los años" else df_merge[df_merge["Año"] == anio]
    df = df.groupby("NombreMunicipio")["TasaXMilHabitantes"].mean().nsmallest(10).reset_index()
    return px.bar(df, x="TasaXMilHabitantes", y="NombreMunicipio", orientation="h", color="TasaXMilHabitantes",
                  color_continuous_scale="Blues")

# ---- Top 10 Casos ----
@app.callback(
    Output("plot_top10_casos_alto", "figure"),
    Input("anio_top_casos_alto", "value")
)
def top10_casos_alto(anio):
    df = df_merge if anio == "Todos los años" else df_merge[df_merge["Año"] == anio]
    df = df.groupby("NombreMunicipio")["NumeroCasos"].sum().nlargest(10).reset_index()
    return px.bar(df, x="NumeroCasos", y="NombreMunicipio", orientation="h", color="NumeroCasos",
                  color_continuous_scale="Reds")

@app.callback(
    Output("plot_top10_casos_bajo", "figure"),
    Input("anio_top_casos_bajo", "value")
)
def top10_casos_bajo(anio):
    df = df_merge if anio == "Todos los años" else df_merge[df_merge["Año"] == anio]
    df = df.groupby("NombreMunicipio")["NumeroCasos"].sum().nsmallest(10).reset_index()
    return px.bar(df, x="NumeroCasos", y="NombreMunicipio", orientation="h", color="NumeroCasos",
                  color_continuous_scale="Blues")

# -----------------------------------------------------------
# 5. Lanzar la aplicación
# -----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)

