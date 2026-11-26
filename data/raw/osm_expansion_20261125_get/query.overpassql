[out:json][timeout:50];
rel(3289417);map_to_area->.ouhai;
nwr(area.ouhai)["name"]["leisure"="park"];out tags center 55;
nwr(area.ouhai)["name"]["tourism"~"^(attraction|viewpoint)$"];out tags center 55;
nwr(area.ouhai)["name"]["tourism"="museum"];out tags center 18;
nwr(area.ouhai)["name"]["amenity"="library"];out tags center 18;
