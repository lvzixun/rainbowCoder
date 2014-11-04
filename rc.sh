#!/bin/bash

echo "[git] add...."
git add --all ~/codes/rainbowCoder/post
echo "[git] comit...."
git ci -m "$(date) posting[by rainbowcoder]"
echo "[git] push...."
git push


echo "[rainbowcoder] post...."
ssh zixun@www.rainbowcoder.com "cd ~/codes/rainbowCoder; python building.py building_update; python building.py building_rss;"

