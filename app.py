import dash
from dash import Dash, dcc, html, dash_table, Input, Output
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import dash_leaflet.express as dlx
import branca.colormap as cm
import pandas as pd
import geopandas as gpd
from dash.exceptions import PreventUpdate

# =============================
#   Mortalidad en Antioquia – Dash
#   Autor: Johan David Díaz López
#   Fuente: Datos Abiertos de Colombia
# =============================

# Cargar datos
df_final = gpd.read_file("data/df_final.geojson")  # <-- asegúrate que el archivo esté en /data
df_final["Anio"] = df_final["Anio"].astype(int)

# Iniciar app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# --------------------------
# Layout
# --------------------------
app.layout = dbc.Container([
    html.H1("Mortalidad en Antioquia", style={"textAlign": "center"}),
    dcc.Tabs(id="tabs", value="contexto", children=[
        dcc.Tab(label="Contexto", value="contexto"),
        dcc.Tab(label="Tabla de Datos", value="tabla"),
        dcc.Tab(label="Estadísticas descriptivas", value="estadisticas"),
        dcc.Tab(label="Tasa de mortalidad", value="tasa"),
        dcc.Tab(label="Número de defunciones", value="defunciones"),
    ]),
    html.Div(id="tabs-content")
], fluid=True)


# --------------------------
# Callbacks
# --------------------------
@app.callback(Output("tabs-content", "children"),
              Input("tabs", "value"))
def render_content(tab):
    if tab == "contexto":
        return html.Div([
            html.H4("Contexto"),
            html.P("Este tablero muestra estadísticas de mortalidad en los municipios de Antioquia, "
                   "incluyendo tasas por mil habitantes y número de defunciones totales. "
                   "Los datos provienen del portal oficial de Datos Abiertos de Colombia.")
        ])

    elif tab == "tabla":
        return html.Div([
            html.H4("Tabla de Datos"),
            dash_table.DataTable(
                data=df_final.head(20).to_dict("records"),
                columns=[{"name": i, "id": i} for i in df_final.columns],
                page_size=10,
                style_table={"overflowX": "auto"}
            )
        ])

    elif tab == "estadisticas":
        return html.Div([
            html.H4("Estadísticas descriptivas"),
            html.Pre(df_final.describe().to_string())
        ])

    elif tab == "tasa":
        return html.Div([
            dcc.Tabs(id="tabs-tasa", value="mapa-tasa", children=[
                dcc.Tab(label="Mapa interactivo", value="mapa-tasa"),
                dcc.Tab(label="Top 10 más altos", value="top-altos"),
                dcc.Tab(label="Top 10 más bajos", value="top-bajos"),
            ]),
            html.Div(id="content-tasa")
        ])

    elif tab == "defunciones":
        return html.Div([
            dcc.Tabs(id="tabs-casos", value="mapa-casos", children=[
                dcc.Tab(label="Mapa interactivo", value="mapa-casos"),
                dcc.Tab(label="Top 10 más altos", value="top-altos-casos"),
                dcc.Tab(label="Top 10 más bajos", value="top-bajos-casos"),
            ]),
            html.Div(id="content-casos")
        ])


# --------------------------
# Callbacks Tasa Mortalidad
# --------------------------
@app.callback(Output("content-tasa", "children"),
              Input("tabs-tasa", "value"))
def render_tasa(tab):
    if tab == "mapa-tasa":
        return html.Div([
            html.Label("Seleccione un año:"),
            dcc.Dropdown(
                id="anio-tasa",
                options=[{"label": str(a), "value": a} for a in sorted(df_final["Anio"].unique())] +
                        [{"label": "Todos los años", "value": "all"}],
                value="all"
            ),
            html.Div(id="mapa-tasa")
        ])
    elif tab == "top-altos":
        top = df_final.groupby("NombreMunicipio")["TasaMortalidad"].mean().nlargest(10).reset_index()
        return dash_table.DataTable(data=top.to_dict("records"), columns=[{"name": i, "id": i} for i in top.columns])
    elif tab == "top-bajos":
        bottom = df_final.groupby("NombreMunicipio")["TasaMortalidad"].mean().nsmallest(10).reset_index()
        return dash_table.DataTable(data=bottom.to_dict("records"), columns=[{"name": i, "id": i} for i in bottom.columns])


@app.callback(Output("mapa-tasa", "children"),
              Input("anio-tasa", "value"))
def update_mapa_tasa(anio):
    if anio is None:
        raise PreventUpdate

    if anio == "all":
        df = df_final.copy()
    else:
        df = df_final[df_final["Anio"] == anio]

    geojson = dlx.geojson_to_geobuf(df.__geo_interface__)
    colormap = cm.linear.Reds_09.scale(df["TasaMortalidad"].min(), df["TasaMortalidad"].max())
    colormap.caption = "Tasa por mil habitantes"

    return dl.Map(
        center=[7.0, -75.5],
        zoom=7,
        style={'width': '100%', 'height': '600px'},
        children=[
            dl.TileLayer(),
            dl.Choropleth(
                data=geojson,
                id="choropleth-tasa",
                colorProp="TasaMortalidad",
                colorscale=colormap.colors,
                bins=8,
                opacity=0.8,
                weight=1,
                fillOpacity=0.7
            ),
            dl.LayerGroup(children=[dlx.colorbar.create(color=colormap)])
        ]
    )


# --------------------------
# Callbacks Número de Defunciones
# --------------------------
@app.callback(Output("content-casos", "children"),
              Input("tabs-casos", "value"))
def render_casos(tab):
    if tab == "mapa-casos":
        return html.Div([
            html.Label("Seleccione un año:"),
            dcc.Dropdown(
                id="anio-casos",
                options=[{"label": str(a), "value": a} for a in sorted(df_final["Anio"].unique())],
                value=df_final["Anio"].min()
            ),
            html.Div(id="mapa-casos")
        ])
    elif tab == "top-altos-casos":
        top = df_final.groupby("NombreMunicipio")["NumeroCasos"].sum().nlargest(10).reset_index()
        return dash_table.DataTable(data=top.to_dict("records"), columns=[{"name": i, "id": i} for i in top.columns])
    elif tab == "top-bajos-casos":
        bottom = df_final.groupby("NombreMunicipio")["NumeroCasos"].sum().nsmallest(10).reset_index()
        return dash_table.DataTable(data=bottom.to_dict("records"), columns=[{"name": i, "id": i} for i in bottom.columns])


@app.callback(Output("mapa-casos", "children"),
              Input("anio-casos", "value"))
def update_mapa_casos(anio):
    if anio is None:
        raise PreventUpdate

    df = df_final[df_final["Anio"] == anio]
    geojson = dlx.geojson_to_geobuf(df.__geo_interface__)
    colormap = cm.linear.Reds_09.scale(df["NumeroCasos"].min(), df["NumeroCasos"].max())
    colormap.caption = "Número de defunciones"

    return dl.Map(
        center=[7.0, -75.5],
        zoom=7,
        style={'width': '100%', 'height': '600px'},
        children=[
            dl.TileLayer(),
            dl.Choropleth(
                data=geojson,
                id="choropleth-casos",
                colorProp="NumeroCasos",
                colorscale=colormap.colors,
                bins=8,
                opacity=0.8,
                weight=1,
                fillOpacity=0.7
            ),
            dl.LayerGroup(children=[dlx.colorbar.create(color=colormap)])
        ]
    )


# --------------------------
# Run
# --------------------------
if __name__ == "__main__":
    app.run_server(debug=True)

