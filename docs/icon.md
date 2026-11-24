# Application icon

The user supplied the original small blue music badge. The high-resolution artwork
was edited with the built-in imagegen tool, preserving the white note and sound waves.

Final image-generation prompt: correct the blue badge to perfect concentric circles,
preserve its musical symbol and colors, render on a square canvas with transparent
outside margins, and add no text or symbols.

For exact geometry, the project icon uses circles centered at (512, 512), outer
radius 480, on a 1024×1024 canvas. The generated central artwork is clipped to the
inner disk. The outer rim is constructed geometrically, rather than relying on
approximate generated outlines. Transparent-border alpha symmetry was checked
within the two-level antialiasing tolerance. PNG is the runtime/release icon;
SVG retains the geometric source. Windows ICO variants are generated at build time.
