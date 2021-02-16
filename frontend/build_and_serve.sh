#!/bin/sh

npm run build

./node_modules/.bin/serve dist -l 8001
