#!/bin/bash

# In this example, AsereHFS runs behind a NGINX proxy
# AsereHFS listens to a socket in order to not use a port number
# NGINX itself will deliver to the client any requested file

/etc/init.d/nginx start

./asere-hfs.amd64 \
	--socket /var/run/asere-http-file-server.socket \
	--master /var/www/html/files \
	--proxy-appname asere-hfs \
	--proxy-static /served-by-nginx
