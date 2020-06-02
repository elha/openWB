#!/bin/bash
. /var/www/html/openWB/openwb.conf

# liest ccgx Daten und postet nach mqtt
# inputs
# Vorzeichen: + liefert in Hausnetz, - zieht aus Hausnetz


CCGXIP=$bezug_victronip

mosquitto_pub -h $CCGXIP -t "R/e8eb11e2c8b4/system/0/Serial" -m ''

PL1=`mosquitto_sub -h $CCGXIP -C 1 -t "N/+/system/0/Ac/PvOnGrid/L1/Power" | grep -Eo " [-0-9]+"`
PL2=`mosquitto_sub -h $CCGXIP -C 1 -t "N/+/system/0/Ac/PvOnGrid/L2/Power" | grep -Eo " [-0-9]+"`
PL3=`mosquitto_sub -h $CCGXIP -C 1 -t "N/+/system/0/Ac/PvOnGrid/L3/Power" | grep -Eo " [-0-9]+"`
PPVW=`echo "scale=0;($PL1.0+$PL2.0+$PL3.0)/-1" | bc`

#Der Hauptwert (Watt) wird als echo an die Regellogik zurückgegeben
echo $PPVW
#Zusätzlich wird der Wert in die Ramdisk geschrieben, dies ist für das Webinterface sowie das Logging und ggf. externe Abfragen
echo $PPVW > /var/www/html/openWB/ramdisk/pvwatt
