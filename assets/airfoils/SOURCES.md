# Airfoil coordinate sources

The installed library contains candidate profiles for FSAE and low-Reynolds-number/high-lift comparisons. Profile inclusion is not a recommendation or a promise of maximum downforce.

## Sources

- [UIUC coordinate database](https://m-selig.ae.illinois.edu/ads/coord_database.html): Selig, Eppler, Wortmann and comparison airfoils.
- [Nick Morse's original coordinate database](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat): Benzing coordinate tables and any documented fallback entries.
- [Enrico Benzing's published profiles](http://www.benzing.it/enrico.profili.htm): original design reference. [Be 153 source table](http://www.benzing.it/images/Fig-B-05.JPG) cross-checked for Be 153-055, 105 and 175.
- [Pakkam's original MSHD thesis](https://repository.lib.ncsu.edu/bitstreams/56e62390-f800-4126-af2a-f06873e998d9/download): Figure 3.1 on printed page 30 / PDF page 47 supplies a vector-derived outline, labeled as an approximation in the app. The original numeric DAT is not supplied by this extraction.

## Processing and limits

UIUC coordinate files are preserved byte-for-byte. Benzing values are exported from the original online MATLAB database without coordinate smoothing. The optimizer then applies its existing chord normalization and cosine-spaced panel resampling.

MSHD's PDF contains a single blue, 194-point polyline. Its vertices were extracted without pixel tracing, the PDF y-axis reversed, and both axes divided by the plotted chord. The optimizer subsequently applies its normal chord normalization. Geometry was checked against Table 3.1: thickness 0.12923 at 0.164 chord and camber 0.13684 at 0.524 chord, compared with published 0.129 at 0.16 and 0.138 at 0.51. This agreement supports the recovered plot scale, while the profile remains a figure-derived approximation. Its thin trailing-edge curvature is retained.

All installed files pass finite-coordinate, perimeter-order and polygon validity checks after panel resampling. Files with self-intersections are excluded; no automatic polygon repair is applied. Coordinate validation does not establish aerodynamic or manufacturing suitability.

The catalog stores each installed file's SHA-256, exact coordinate source, family, point count and processing method. Third-party coordinate provenance is separate from the Python code's MIT license.

## Installed profiles

| Profile | Family | Source points | Coordinate source |
| --- | --- | ---: | --- |
| Be 092-046 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 092-075 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 094-056 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 103-077 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 103-115 | Benzing | 34 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 122-046 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 122-075 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 122-125 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 122-155 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 122-185 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 123-075 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 123-076 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 123-077 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 123-115 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 123-125 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 123-126 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 123-155 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 123-156 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 124-056 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 152-075 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 152-105 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 152-125 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 152-155 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 152-175 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-055 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-056 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-075 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-076 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-077 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-105 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-106 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-115 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-125 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-126 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-155 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-156 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-175 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 153-176 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 154-056 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 162-104 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 162-124 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 162-144 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 183-055 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 183-056 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 183-075 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 183-076 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 183-105 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 183-106 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 183-125 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 183-126 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 183-155 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 183-156 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 183-175 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| Be 183-176 | Benzing | 33 | [Source](https://github.com/nick-morse/MultiElementWingGenerator/blob/master/airfoildatabase.mat) |
| CH10SM | Comparison | 79 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/ch10sm.dat) |
| GOE652 | Comparison | 33 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/goe652.dat) |
| LNV109A | Comparison | 101 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/lnv109a.dat) |
| E193 | Eppler | 61 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e193.dat) |
| E205 | Eppler | 61 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e205.dat) |
| E211 | Eppler | 61 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e211.dat) |
| E214 | Eppler | 61 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e214.dat) |
| E374 | Eppler | 61 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e374.dat) |
| E387 | Eppler | 61 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e387.dat) |
| E420 | Eppler | 72 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e420.dat) |
| E421 | Eppler | 72 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e421.dat) |
| E422 | Eppler | 72 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e422.dat) |
| E423 | Eppler | 72 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e423.dat) |
| E426 | Eppler | 40 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e426.dat) |
| E428 | Eppler | 40 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e428.dat) |
| E664 | Eppler | 61 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/e664.dat) |
| MSHD (figure-derived) | Motorsport | 194 | [Source](https://repository.lib.ncsu.edu/bitstreams/56e62390-f800-4126-af2a-f06873e998d9/download) |
| S1091 | Selig | 81 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/s1091.dat) |
| S1210 | Selig | 81 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/s1210.dat) |
| S1221 | Selig | 72 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/s1221.dat) |
| S1223 | Selig | 81 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/s1223.dat) |
| S1223 RTL | Selig | 100 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/s1223rtl.dat) |
| S5010 | Selig | 61 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/s5010.dat) |
| S7012 | Selig | 81 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/s7012.dat) |
| S7055 | Selig | 81 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/s7055.dat) |
| SD7032 | Selig | 61 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/sd7032.dat) |
| SD8020 | Selig | 61 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/sd8020.dat) |
| FX 63-137 | Wortmann | 97 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/fx63137.dat) |
| FX 74-CL5-140 | Wortmann | 87 | [Source](https://m-selig.ae.illinois.edu/ads/coord_seligFmt/fx74cl5140.dat) |

## Excluded source profiles

- s3021: Profile outline is self-intersecting or degenerate.
- sd7003: Profile outline is self-intersecting or degenerate.
- sd7062: Profile outline is self-intersecting or degenerate.
- sd7080: Profile outline is self-intersecting or degenerate.
- be152-046: Profile outline is self-intersecting or degenerate.
