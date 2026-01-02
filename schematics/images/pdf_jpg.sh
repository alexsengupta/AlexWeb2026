#!/usr/bin/env bash

shopt -s nullglob

for f in *.pdf; do
  echo "Converting: $f"
  magick -density 300 "$f" \
    -background white -alpha remove -alpha off \
    -resize 1800x \
    -quality 90 \
    -set filename:base "%[basename]" "%[filename:base]_%03d.jpg"
done

echo "Done."
