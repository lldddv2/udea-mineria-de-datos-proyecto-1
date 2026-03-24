import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import LogFormatterMathtext
from matplotlib.patches import Ellipse
from scipy.optimize import curve_fit

# --------------- Obtención de datos ---------------
conexion = sqlite3.connect('datos_mision.db')
consulta = "SELECT * FROM exoplanetas ORDER BY id ASC;"
df = pd.read_sql_query(consulta, conexion, index_col='id')
conexion.close()
# -------------------------------------------------

# --------------- Análisis de datos ---------------
# segun  https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html
# Las unidades son en masas terrestres (M_Earth) y radios terrestres (R_Earth)
masas = df['pl_bmasse']
radios = df['pl_rade']
densidades = masas / (4/3*np.pi*radios**3)

N_densidades = 300  # Mayor resolución para una transición más suave

# Usar logspace para que el muestreo sea uniforme en escala logarítmica
masas_logspace = np.logspace(
    np.log10(masas.min()),
    np.log10(masas.max()),
    N_densidades
)
radios_logspace = np.logspace(
    np.log10(radios.min()),
    np.log10(radios.max()),
    N_densidades
)

Masas_grid, Radios_grid = np.meshgrid(masas_logspace, radios_logspace, indexing='ij')
# Densidad relativa terrestre: rho/rho_earth = (M/M_earth)/(R/R_earth)^3
densidades_grid = np.divide(
    Masas_grid,
    Radios_grid**3,
    out=np.full_like(Masas_grid, np.nan, dtype=float),
    where=Radios_grid > 0,
)
# -------------------------------------------------

# --------------- Gráfica -------------------------
fig, ax = plt.subplots()

Z = np.ma.masked_invalid(densidades_grid)
Z = np.ma.masked_less_equal(Z, 0)
dens_min = Z.compressed().min()
dens_max = Z.compressed().max()
decada_min = int(np.floor(np.log10(dens_min)))
decada_max = int(np.ceil(np.log10(dens_max)))
limites_decadas = 10.0 ** np.arange(decada_min, decada_max + 1)
dens_cmap = plt.get_cmap('Pastel2', len(limites_decadas) - 1)
norm_decadas = BoundaryNorm(limites_decadas, ncolors=len(limites_decadas) - 1, clip=True)

# El extent ahora está en log10 (coordenadas del espacio log)
im = ax.imshow(
    Z,
    extent=[
        np.log10(radios_logspace.min()),
        np.log10(radios_logspace.max()),
        np.log10(masas_logspace.min()),
        np.log10(masas_logspace.max()),
    ],
    origin='lower',
    aspect='auto',
    cmap=dens_cmap,
    norm=norm_decadas,
    zorder=0,
)
plt.colorbar(
    im,
    ticks=limites_decadas,
    format=LogFormatterMathtext(base=10),
    label=r'$\rho / \rho_{\oplus}$ (bandas por orden de magnitud)',
)

# Scatter también en log10 para coincidir con el extent
mask = (masas > 0) & (radios > 0)
ax.plot(np.log10(radios[mask]), np.log10(masas[mask]), '.k', markersize=1, zorder=2)

# Referencias del Sistema Solar en unidades terrestres (R_E, M_E)
tierra_radio, tierra_masa = 1.0, 1.0
jupiter_radio, jupiter_masa = 11.2, 317.8

ax.scatter(
    [np.log10(tierra_radio), np.log10(jupiter_radio)],
    [np.log10(tierra_masa), np.log10(jupiter_masa)],
    c='red',
    s=40,
    zorder=4,
)
ax.annotate(
    'Tierra',
    (np.log10(tierra_radio), np.log10(tierra_masa)),
    textcoords='offset points',
    xytext=(-30, -25),
    color='red',
    fontsize=12,
    ha='left',
    va='bottom',
    zorder=6,
    bbox=dict(boxstyle="round,pad=0.3", facecolor=(1,1,1,0.7), edgecolor='none')
)
ax.annotate(
    'Jupiter',
    (np.log10(jupiter_radio), np.log10(jupiter_masa)),
    textcoords='offset points',
    xytext=(-30, -25),
    color='red',
    fontsize=12,
    ha='left',
    va='bottom',
    zorder=6,
    bbox=dict(boxstyle="round,pad=0.3", facecolor=(1,1,1,0.7), edgecolor='none')
)

# Ticks manuales que imitan escala log
x_ticks = [-1, 0, 1]          # 0.1, 1, 10 R_E
y_ticks = [-1, 0, 1, 2, 3, 4] # 0.1, 1, 10, 100, 1000, 10000 M_E
ax.set_xticks(x_ticks)
ax.set_xticklabels([f'$10^{{{t}}}$' for t in x_ticks])
ax.set_yticks(y_ticks)
ax.set_yticklabels([f'$10^{{{t}}}$' for t in y_ticks])
ax.set_xlabel(r'$\log_{10}(R / R_{\oplus})$')
ax.set_ylabel(r'$\log_{10}(M / M_{\oplus})$')
ax.set_title('Exoplanetas')

ax.set_xlim(np.log10(radios.min()), np.log10(radios.max()))
ax.set_ylim(np.log10(masas.min()), np.log10(masas.max()))

# Función auxiliar para el ajuste bimodal (suma de dos gaussianas)
def _bimodal(x, mu1, s1, A1, mu2, s2, A2):
    return A1 * np.exp(-0.5 * ((x - mu1) / s1) ** 2) + A2 * np.exp(-0.5 * ((x - mu2) / s2) ** 2)

log_r = np.log10(radios[mask])
log_m = np.log10(masas[mask])
popt_r = popt_m = None

# Histogramas marginales dentro del ax
# Distribución de radios a lo largo del eje x (franja inferior, 10% de altura)
ax_hx = ax.inset_axes([0, 0, 1, 0.10])
counts_r, edges_r, _ = ax_hx.hist(log_r, bins=50, color='steelblue', alpha=0.5, linewidth=0, density=True)
ax_hx.set_xlim(ax.get_xlim())
ax_hx.axis('off')
ax_hx.text(0.01, 0.97, r'Distribución $R$', transform=ax_hx.transAxes,
           fontsize=7, va='top', ha='left', color='steelblue')
# Ajuste bimodal radios
xc_r = 0.5 * (edges_r[:-1] + edges_r[1:])
med_r = np.median(log_r)
p0_r = [med_r - 0.4, 0.3, counts_r.max() * 0.6, med_r + 0.4, 0.3, counts_r.max() * 0.6]
try:
    popt_r, _ = curve_fit(_bimodal, xc_r, counts_r, p0=p0_r, maxfev=8000)
    x_fit_r = np.linspace(log_r.min(), log_r.max(), 400)
    ax_hx.plot(x_fit_r, _bimodal(x_fit_r, *popt_r), color='navy', linewidth=1.2, zorder=3)
except RuntimeError:
    pass

# Distribución de masas a lo largo del eje y (franja izquierda, 10% de ancho)
ax_hy = ax.inset_axes([0, 0, 0.10, 1])
counts_m, edges_m, _ = ax_hy.hist(log_m, bins=50, orientation='horizontal',
                                   color='steelblue', alpha=0.5, linewidth=0, density=True)
ax_hy.set_ylim(ax.get_ylim())
ax_hy.axis('off')
ax_hy.text(0.97, 0.99, r'Distribución $M$', transform=ax_hy.transAxes,
           fontsize=7, va='top', ha='right', color='steelblue', rotation=270)
# Ajuste bimodal masas
yc_m = 0.5 * (edges_m[:-1] + edges_m[1:])
med_m = np.median(log_m)
p0_m = [med_m - 1.0, 0.8, counts_m.max() * 0.6, med_m + 1.0, 0.8, counts_m.max() * 0.6]
try:
    popt_m, _ = curve_fit(_bimodal, yc_m, counts_m, p0=p0_m, maxfev=8000)
    y_fit_m = np.linspace(log_m.min(), log_m.max(), 400)
    ax_hy.plot(_bimodal(y_fit_m, *popt_m), y_fit_m, color='navy', linewidth=1.2, zorder=3)
except RuntimeError:
    pass

# Elipses de 2-sigma para los dos grupos identificados por el ajuste bimodal
# Grupo 1: 1ª moda de masas (bajas) + 2ª moda de radios (grandes)  → gigantes gaseosos
# Grupo 2: 2ª moda de masas (altas) + 1ª moda de radios (pequeños) → rocosos/supertierra
if popt_r is not None and popt_m is not None:
    modes_r = sorted([(popt_r[0], abs(popt_r[1])), (popt_r[3], abs(popt_r[4]))], key=lambda x: x[0])
    modes_m = sorted([(popt_m[0], abs(popt_m[1])), (popt_m[3], abs(popt_m[4]))], key=lambda x: x[0])
    grupos = [
        (modes_r[0][0], modes_m[0][0], modes_r[0][1], modes_m[0][1]),
        (modes_r[1][0], modes_m[1][0], modes_r[1][1], modes_m[1][1]),
    ]
    etiquetas = ['Rocosos / supertierras', 'Gigantes gaseosos']
    colores_elipse = ['darkorange', 'forestgreen']
    for (cx, cy, sr, sm), label, color in zip(grupos, etiquetas, colores_elipse):
        ax.add_patch(Ellipse(
            xy=(cx, cy),
            width=4 * sr,   # diámetro = 2 × 2σ
            height=4 * sm,
            edgecolor=color,
            facecolor='none',
            linewidth=1.5,
            linestyle='--',
            zorder=5,
            label=label,
        ))
    ax.legend(loc='upper left', fontsize=8, framealpha=0.7)

    # Contorno de decisión: puntos donde P(grupo 0) = P(grupo 1)
    # Se extraen las componentes gaussianas (mu, sigma, amplitud) ordenadas por mu
    comps_r = sorted(
        [(popt_r[0], abs(popt_r[1]), popt_r[2]), (popt_r[3], abs(popt_r[4]), popt_r[5])],
        key=lambda c: c[0],
    )
    comps_m = sorted(
        [(popt_m[0], abs(popt_m[1]), popt_m[2]), (popt_m[3], abs(popt_m[4]), popt_m[5])],
        key=lambda c: c[0],
    )

    xg = np.linspace(*ax.get_xlim(), 500)
    yg = np.linspace(*ax.get_ylim(), 500)
    XG, YG = np.meshgrid(xg, yg)

    # Distancia de Mahalanobis al centroide de cada grupo (sin amplitudes para evitar
    # que las colas se distorsionen por diferencias en el número de planetas de cada grupo)
    # d²_k(x,y) = ((x-mu_r_k)/s_r_k)² + ((y-mu_m_k)/s_m_k)²
    # Frontera: d²_0 = d²_1  →  log_ratio = d²_1 - d²_0 = 0
    d2_rocky = ((XG - comps_r[0][0]) / comps_r[0][1])**2 + ((YG - comps_m[0][0]) / comps_m[0][1])**2
    d2_gas   = ((XG - comps_r[1][0]) / comps_r[1][1])**2 + ((YG - comps_m[1][0]) / comps_m[1][1])**2
    log_ratio = d2_gas - d2_rocky  # > 0 → más cerca del grupo rocoso

    cs = ax.contour(XG, YG, log_ratio, levels=[0], colors=['black'], linewidths=1.2,
                    linestyles=['--'], zorder=6)
    from matplotlib.lines import Line2D
    handles, labels = ax.get_legend_handles_labels()
    handles.append(Line2D([0], [0], color='black', linewidth=1.2, linestyle='--'))
    labels.append('Frontera de decisión')
    ax.legend(handles=handles, labels=labels, loc='upper left', fontsize=8, framealpha=0.7)

plt.tight_layout()
plt.savefig('resultado.png', dpi=300)
# -------------------------------------------------