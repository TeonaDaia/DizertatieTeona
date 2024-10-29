import pystac_client
import planetary_computer
import geopandas
import rich.table
import stackstac
import rasterio
import rioxarray
import sys
import os
import pyproj
import numpy



# Obiect de tip STAC
catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",
                                     modifier=planetary_computer.sign_inplace,)



time_range = "2022-07-01/2022-07-30"
bbox = [18.817924, 68.323238, 19.200386, 68.390350]
search = catalog.search(collections=["landsat-c2-l2"],
                        bbox=bbox,
                        datetime=time_range,
                        query={"eo:cloud_cover": {"lt": 5}}
                        )
items = search.get_all_items()
len(items)

#TODO - genereaza items_final prin filtrarea item-urile din items in baza datei de achizitie a fiecarei imagini
#Exemplu: items_final = []
#for item in items:
#citeste data de achizitie
#daca data este in interiorul lunilor mari - septembrie
#atunci adauga item la items_final



df = geopandas.GeoDataFrame.from_features(items.to_dict(), crs="epsg:4326")
df



bands_tif = ["atran.tif", "blue.tif", "cdist.tif", "coastal.tif", "drad.tif", "emis.tif", "emsd.tif", "green.tif", "lwir11.tif", "nir08.tif",
          "qa.tif", "qa_aerosol.tif", "qa_pixel.tif", "qa_radsat.tif", "red.tif", "swir16.tif", "swir22.tif", "trad.tif", "urad.tif"]
bands = []
for b in bands_tif:
    name_file, ext_file = os.path.splitext(b)
    bands.append(name_file)

# bands2 = [os.path.splitext(file)[0] for file in bands_tif]
# bands2


transformer = pyproj.Transformer.from_crs("EPSG:4326","EPSG:32624", always_xy=True)
bbox_32624 = transformer.transform_bounds(bbox[0], bbox[1], bbox[2], bbox[3])
print(bbox, bbox_32624)

scene_ids = df['landsat:scene_id'].values

data_temp = None
for scene_id in scene_ids:
    folder = os.path.join(r"C:\Dizertatie\Out", scene_id)
    os.makedirs(folder, exist_ok=True)
    print(f"{scene_id}")

    for item in items[:1]:
        print(item.id)
        # Pentru fiecare ID se creeaza un folder; se verifica daca folder exista inainte sa fie creat
        # pentru fiecare banda se salveaza un fisier cu numele benzii; salvarea se face in folderul aferent benzii respective
        data = (stackstac.stack([item],
                                assets=bands,
                                epsg=32634,
                                resolution=30,
                                bounds_latlon=bbox,
                                # bounds_latlon=bbox, #taie imaginea fix pe bbox
                                chunksize=4096).where(lambda x: x > 0, other=numpy.nan))

        qa_pixel = data.sel(band="qa_pixel")
        qa_radsat = data.sel(band='qa_radsat')

        cloud_bitmask = da.from_array(np.array(1 << 5), chunks=qa_pixel.data.chunks)
        shadow_bitmask = da.from_array(np.array(1 << 3), chunks=qa_pixel.data.chunks)
        snow_bitmask = da.from_array(np.array(1 << 4), chunks=qa_pixel.data.chunks)

        data.compute()
        data.where(cloud_bitmask)

        for band in bands:

            try:
                print(f"Se descarca banda {band} din {scene_id}")
                bnd_data = data.sel(band=band)
                bnd_data.rio.write_crs("EPSG:32634", inplace=True)
                #     # a se verofoca daca exista si se sterge daca exista
                #     # a se utiliza cod try except pentru a prinde erorile
                out_bnd = r"C:\Dizertatie\Out\{}\{}.tif".format(scene_id, band)

                if os.path.exists(out_bnd):
                    os.unlink(out_bnd)
                bnd_data.rio.to_raster(out_bnd)

            except Exception as e:
                print(f"Eroare la salvarea benzii {band} din {scene_id}", e)
                pass
