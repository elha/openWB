#!/bin/bash
sudo python /var/www/html/openWB/runs/dac.py 3505
echo 27 > /var/www/html/openWB/ramdisk/llsoll
echo 1 > /var/www/html/openWB/ramdisk/ladestatus