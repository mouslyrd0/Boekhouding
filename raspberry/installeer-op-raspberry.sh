#!/usr/bin/env bash
# Maakt op een Raspberry Pi een gedeelde map "MijnArchief" voor het programma
# Mijn Archief. De map is alleen bereikbaar binnen je eigen thuisnetwerk.
#
# Gebruik (op de Raspberry Pi):
#   sudo bash installeer-op-raspberry.sh            # map: /srv/mijnarchief
#   sudo bash installeer-op-raspberry.sh /mnt/ssd/mijnarchief   # eigen map, bijv. op een USB-schijf
#
# Je kunt het script gerust opnieuw uitvoeren; het past dan alleen de instellingen aan.

set -euo pipefail

SHARE="MijnArchief"
MAP="${1:-/srv/mijnarchief}"
CONF="/etc/samba/smb.conf"
BEGIN="# >>> Mijn Archief >>>"
EINDE="# <<< Mijn Archief <<<"

if [ "$(id -u)" -ne 0 ]; then
    echo "Start het script met sudo:  sudo bash $0 $*"
    exit 1
fi
GEBRUIKER="${SUDO_USER:-}"
if [ -z "$GEBRUIKER" ] || [ "$GEBRUIKER" = "root" ]; then
    echo "Start het script vanuit je gewone gebruiker (bijv. 'pi') met sudo, niet als root."
    exit 1
fi
case "$MAP" in
    /*) ;;
    *) echo "Geef de map op als volledig pad, bijv. /srv/mijnarchief"; exit 1 ;;
esac
case "$MAP" in
    /media/*)
        echo "Let op: schijven onder /media worden alleen gekoppeld als iemand op de Pi is ingelogd."
        echo "Koppel de schijf liever vast (bijv. onder /mnt) zodat het archief altijd bereikbaar is."
        ;;
esac

echo "==> Samba installeren (voor de gedeelde map)…"
apt-get update -q
apt-get install -y -q samba
# Zorgt dat de Pi zichtbaar is onder 'Netwerk' in de Windows Verkenner (optioneel).
apt-get install -y -q wsdd >/dev/null 2>&1 || apt-get install -y -q wsdd2 >/dev/null 2>&1 || true

echo "==> Map $MAP klaarzetten…"
mkdir -p "$MAP"
chown "$GEBRUIKER:$GEBRUIKER" "$MAP"
chmod 770 "$MAP"

echo "==> Gedeelde map '$SHARE' instellen…"
[ -f "$CONF.voor-mijnarchief" ] || cp "$CONF" "$CONF.voor-mijnarchief"
sed -i "/^$BEGIN\$/,/^$EINDE\$/d" "$CONF"
cat >> "$CONF" <<EOF
$BEGIN
[$SHARE]
   comment = Mijn Archief
   path = $MAP
   browseable = yes
   read only = no
   valid users = $GEBRUIKER
   force user = $GEBRUIKER
   create mask = 0660
   directory mask = 0770
   # Alleen bereikbaar vanuit het eigen thuisnetwerk, nooit vanaf internet.
   hosts allow = 127. 10. 172.16.0.0/12 192.168.
   hosts deny = 0.0.0.0/0
   # Veilig voor de database van Mijn Archief (geen caching van vergrendelingen).
   oplocks = no
   level2 oplocks = no
   strict locking = yes
$EINDE
EOF
testparm -s "$CONF" >/dev/null 2>&1 || { echo "De Samba-instellingen kloppen niet (zie: testparm)."; exit 1; }

echo
echo "==> Kies een wachtwoord voor de gedeelde map."
echo "    Dit typ je straks één keer op je Windows-pc. Het mag hetzelfde zijn als je Pi-wachtwoord."
smbpasswd -a "$GEBRUIKER"

systemctl enable --now smbd >/dev/null 2>&1 || true
systemctl restart smbd
systemctl restart nmbd >/dev/null 2>&1 || true

NAAM="$(hostname)"
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
echo "============================================================"
echo " Klaar! De gedeelde map voor Mijn Archief staat op de Pi."
echo
echo " Netwerkadres:    \\\\$NAAM\\$SHARE"
[ -n "$IP" ] && echo " Werkt dat niet:  \\\\$IP\\$SHARE"
echo " Gebruikersnaam:  $GEBRUIKER"
echo " Wachtwoord:      het wachtwoord dat je net hebt gekozen"
echo
echo " Volgende stap op je Windows-pc: zie raspberry/LEESMIJ.md"
echo "============================================================"
