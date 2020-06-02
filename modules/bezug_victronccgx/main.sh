#!/bin/bash
. /var/www/html/openWB/openwb.conf

# liest ccgx Daten und postet nach mqtt
# inputs
# Vorzeichen: + liefert in Hausnetz, - zieht aus Hausnetz


CCGXIP=$bezug_victronip

mosquitto_pub -h $CCGXIP -t "R/e8eb11e2c8b4/system/0/Serial" -m ''

PGRIDW=`mosquitto_sub -h $CCGXIP -C 1 -t "N/+/grid/30/Ac/Power" | grep -Eo " [-0-9]+"`

#Der Hauptwert (Watt) wird als echo an die Regellogik zurückgegeben
echo $PGRIDW
#Zusätzlich wird der Wert in die Ramdisk geschrieben, dies ist für das Webinterface sowie das Logging und ggf. externe Abfragen
echo $PGRIDW > /var/www/html/openWB/ramdisk/wattbezug
