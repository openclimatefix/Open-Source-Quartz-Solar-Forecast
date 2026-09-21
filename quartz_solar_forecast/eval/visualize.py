"""
Geographic visualization for solar forecast evaluation results.
"""

import os
import urllib.request
import zipfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import xarray as xr
from tqdm import tqdm
from PIL import Image


def download_dem_file():
    """Download and extract DEM file if not present."""
    dem_file = 'ETOPO2v2c_f4.nc'
    
    if os.path.exists(dem_file):
        return dem_file
    
    url = 'https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO2/ETOPO2v2-2006/ETOPO2v2c/netCDF/ETOPO2v2c_f4_netCDF.zip'
    zip_file = 'ETOPO2v2c_f4_netCDF.zip'
    
    print(f"Downloading DEM file from {url}")
    urllib.request.urlretrieve(url, zip_file)
    
    print(f"Extracting {zip_file}")
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall('.')
    
    os.remove(zip_file)
    print(f"DEM file ready: {dem_file}")
    
    return dem_file


def create_elevation_map(dem_file, lon_begin, lon_end, lat_begin, lat_end, output_file):
    """Create elevation map for specified region."""
    ds = xr.open_dataset(dem_file)

    x_unique = np.sort(np.unique(ds['x'].values))
    y_unique = np.sort(np.unique(ds['y'].values))

    lon = x_unique
    lat = y_unique
    dem_full = ds['z'].values

    lon_begin_index = np.argmax(lon > lon_begin)
    lon_end_index = np.argmax(lon > lon_end)
    lat_begin_index = np.argmax(lat > lat_begin)
    lat_end_index = np.argmax(lat > lat_end)

    lon_new = lon[lon_begin_index:lon_end_index]
    lat_new = lat[lat_begin_index:lat_end_index]

    lon_grid, lat_grid = np.meshgrid(lon_new, lat_new)
    dem = dem_full[lat_begin_index:lat_end_index, lon_begin_index:lon_end_index]

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300,
                           subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent([lon_begin, lon_end, lat_begin, lat_end], crs=ccrs.PlateCarree())

    levels = [-8000, -6000, -4000, -2000, -1000, -200, -50, 0, 50, 200, 500,
              1000, 1500, 2000, 3000, 4000, 5000, 6000, 7000, 8000]

    colors = ['#084594', '#2171b5', '#4292c6', '#6baed6', '#9ecae1',
              '#c6dbef', '#deebf7', '#006837', '#31a354', '#78c679',
              '#addd8e', '#d9f0a3', '#f7fcb9', '#c9bc87', '#a69165',
              '#856b49', '#664830', '#ad9591', '#d7ccca']

    ax.contourf(lon_grid, lat_grid, dem, levels=levels[5:-5],
                extend='both', colors=colors[5:-5], transform=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)

    plt.savefig(output_file, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.close()

    return output_file


def create_pv_heatmap(results_df, pv_metadata, lon_begin, lon_end, 
                      lat_begin, lat_end, output_file, grid_resolution=50):
    """Create PV forecast heatmap."""
    merged_df = pd.merge(results_df, pv_metadata, on="pv_id")

    site_avg = merged_df.groupby(['pv_id', 'latitude', 'longitude']).agg({
        'forecast_power': 'mean'
    }).reset_index()

    lon_grid_1d = np.linspace(lon_begin, lon_end, grid_resolution)
    lat_grid_1d = np.linspace(lat_begin, lat_end, grid_resolution)
    lon_grid, lat_grid = np.meshgrid(lon_grid_1d, lat_grid_1d)

    pv_array = np.zeros((grid_resolution, grid_resolution))

    for i in tqdm(range(grid_resolution), desc="Creating PV heatmap"):
        for j in range(grid_resolution):
            lat_point = lat_grid[i, j]
            lon_point = lon_grid[i, j]

            distances = np.sqrt(
                (site_avg['latitude'] - lat_point)**2 + 
                (site_avg['longitude'] - lon_point)**2
            )

            mask = distances < 2.0
            if mask.any():
                weights = 1.0 / (distances[mask] + 0.01)
                weights = weights / weights.sum()
                pv_array[i, j] = (site_avg.loc[mask, 'forecast_power'] * weights).sum()

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300,
                           subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent([lon_begin, lon_end, lat_begin, lat_end], crs=ccrs.PlateCarree())

    ax.contourf(lon_grid, lat_grid, pv_array, levels=15, cmap='hot', alpha=0.8,
                transform=ccrs.PlateCarree())
    ax.scatter(site_avg['longitude'].values, site_avg['latitude'].values,
               c='white', s=20, edgecolors='black', linewidths=0.5, zorder=5,
               transform=ccrs.PlateCarree())

    ax.axis('off')
    plt.savefig(output_file, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.close()

    return output_file


def create_overlay_map(elevation_file, pv_file, output_file, alpha=0.6):
    """Create overlay of elevation and PV heatmap."""
    img1 = Image.open(elevation_file)
    img2 = Image.open(pv_file)

    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)

    img1_rgba = img1.convert('RGBA')
    img2_rgba = img2.convert('RGBA')

    overlay = Image.blend(img1_rgba, img2_rgba, alpha=alpha)
    overlay.convert('RGB').save(output_file, quality=95)

    return output_file


def visualize_results(results_df, pv_metadata):
    """Create all visualization outputs."""
    output_dir = "images"
    os.makedirs(output_dir, exist_ok=True)
    
    bounds_padding = 0.5
    lon_begin = pv_metadata['longitude'].min() - bounds_padding
    lon_end = pv_metadata['longitude'].max() + bounds_padding
    lat_begin = pv_metadata['latitude'].min() - bounds_padding
    lat_end = pv_metadata['latitude'].max() + bounds_padding
    
    dem_file = download_dem_file()
    
    elevation_file = os.path.join(output_dir, "elevation.jpg")
    create_elevation_map(dem_file, lon_begin, lon_end, lat_begin, lat_end, elevation_file)

    pv_file = os.path.join(output_dir, "pv_heatmap.jpg")
    create_pv_heatmap(results_df, pv_metadata, lon_begin, lon_end, lat_begin, lat_end, pv_file)

    overlay_file = os.path.join(output_dir, "overlay.jpg")
    create_overlay_map(elevation_file, pv_file, overlay_file)