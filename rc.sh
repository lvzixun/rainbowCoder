#!/bin/bash

echo "[git] add...."
git add --all post
echo "[git] comit...."
git ci -m "$(date) posting[by rainbowcoder]"
echo "[git] push...."
git push


echo "[rainbowcoder] post...."
ssh rainbowcoder "cd ~/codes/rainbowCoder; python building.py building_update; python building.py building_rss;"

