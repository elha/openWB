#!/bin/bash
. /var/www/html/openWB/openwb.conf

# liest ccgx Daten und postet nach mqtt
# inputs
# Vorzeichen: + liefert in Hausnetz, - zieht aus Hausnetz


CCGXIP=$bezug_victronip

mosquitto_pub -h $CCGXIP -t "R/e8eb11e2c8b4/system/0/Serial" -m ''
PBATTERYW=`mosquitto_sub -h $CCGXIP -C 1 -t "N/+/system/0/Dc/Vebus/Power" | grep -Eo " [-0-9]+"`
SOCBATTERY=`mosquitto_sub -h $CCGXIP -C 1 -t "N/+/system/0/Dc/Battery/Soc" | grep -Eo " [-0-9]+"`

#Den Wert in die Ramdisk geschrieben, dies ist für das Webinterface sowie das Logging und ggf. externe Abfragen
echo $PBATTERYW > /var/www/html/openWB/ramdisk/speicherleistung
echo $SOCBATTERY > /var/www/html/openWB/ramdisk/speichersoc
