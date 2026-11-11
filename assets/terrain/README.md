# Reference elevation data

`reference-terrarium.png` is an unmodified 256×256 elevation-data tile downloaded
on 2026-11-09 from:
https://s3.amazonaws.com/elevation-tiles-prod/terrarium/13/6763/3081.png

It is data encoded in RGB, not an illustration or generated image.
Encoding: elevation in metres = R × 256 + G + B / 256 − 32768.
Source documentation: https://github.com/tilezen/joerd/blob/master/docs/formats.md

SRTM data courtesy of the U.S. Geological Survey. Terrain Tiles by Mapzen/Tilezen,
hosted on AWS Open Data: https://registry.opendata.aws/terrain-tiles/
Attribution and public-domain source notes:
https://github.com/tilezen/joerd/blob/master/docs/attribution.md

The decoded local `frontend/public/academy/great-wall/spatial-v1/terrain-dem.json`
records the source URL, hash, dimensions and 208–477 m source range. At runtime,
elevations are rescaled and blended with an invented road ridge. This is a
stylized learning world, not a geographic reconstruction or a navigation map.
No external terrain API is contacted when students use the page.
