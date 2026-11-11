# Great Wall realism assets — 2026-11-10

Generated with the built-in `image_gen` tool using the imagegen skill. New
versioned assets; original project illustrations remain unchanged. Original
PNGs are retained here; runtime WebPs and SHA-256 provenance are beside them in
`frontend/public/academy/great-wall/realistic-v1/`. PNG-to-WebP conversion only;
no repainting, compositing or background substitutions. Pine alpha is retained.

## masonry-source.png

Tool: transparent_background=false. Exact prompt:

> Create one production-ready physically realistic seamless tileable 3D game material base-color texture, square 1024 x 1024. Subject: aged Great Wall of China masonry: thin rectangular grey beige sandstone bricks in irregular staggered horizontal courses, weathered pale warm grey faces, tiny chips, subtle darker hairline mortar, naturally varying blocks, occasional restrained dry moss in crevices. Orthographic perfectly flat frontal material scan, even diffuse overcast light, NO directional shadows or dramatic lighting, NO perspective, NO border, NO lettering, NO drawing or cartoon style. Small real Chinese wall masonry bricks, believable micrograin, neutral slightly warm low saturation stone, no orange or ochre yellow. Texture is intended to repeat seamlessly on actual 3D wall meshes. Fill every pixel with masonry.

## pines-source.png

Tool: transparent_background=true. Exact prompt:

> Production 3D landscape cutout atlas, fully TRANSPARENT background including empty space between trees. Wide horizontal composition of three distinct realistic mature Chinese mountain pine trees, one in each equal-width third, all fully visible from roots to crown, upright, NO overlapping between thirds. Each tree centered horizontally in its own equal cell, root at 95% image height, crown at 6% image height. 1st tree slender windswept mountain pine, 2nd broader ancient rugged branching pine, 3rd dense umbrella-canopy pine. Believable botanical structure: fine individual dark forest-green needles, exposed irregular grey-brown bark, many fine twig branches and layered canopies, natural muted greens, avoid bright yellow/chartreuse tips. Realistic photographic game environment asset with soft neutral daylight, whole tree silhouettes rooted at equal baseline; no people, rocks, ground, scenery, labels, shadows on background, or cartoon illustration. Tree height about 85% of canvas, width within each cell with clear transparent padding. Preserve alpha at fine needles. Atlas aspect ratio 3:1.

Actual atlas: 2172×724 RGBA. Root x anchors derived from alpha >128 in the
bottom 10% of each cell: .349 / .453 / .510. The ordinary faint alpha-edge
pixels are rejected by the renderer's alpha test.

## paving-source.png

Tool: transparent_background=false. Exact prompt:

> Square 1024 x 1024 seamless tileable photorealistic base-color material texture for the walking surface of the Great Wall of China. Worn flat grey-beige sandstone paving slabs, rectangular large flagstones arranged in quiet staggered horizontal rows. Fine natural stone grains, subtle chipped bevels, thin dark dry mortar seams, understated age, slight realistic variation of neutral warm grey and pale limestone. Perfect orthographic overhead view, completely flat, even shadowless diffuse daylight, no perspective, NO steps, no architecture, no people, no illustration, no graphic effects, no letters or borders. A physically believable 3D game albedo map that repeats on actual stone stair treads. Not orange, not golden, not brown, not glossy. Fill entire frame with stone paving.

Both stone outputs are 1254×1254 RGB. The request size is part of the prompt;
actual output dimensions are recorded rather than claimed to be 1024px.
