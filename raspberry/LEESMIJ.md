# Mijn Archief op je Raspberry Pi

Je kunt je archief op een Raspberry Pi bewaren in plaats van op je pc. Het programma blijft gewoon op je
Windows-pc draaien, maar alle documenten en de database staan op de Pi.

- Alles blijft binnen je eigen thuisnetwerk. Er gaat niets naar internet; de gedeelde map weigert verbindingen
  van buiten je thuisnetwerk.
- Je pc kan uit of kapot gaan zonder dat je archief verloren gaat.
- Gebruik het archief op **één computer tegelijk**. Opent iemand het op een tweede computer, dan waarschuwt
  het programma.

## Wat heb je nodig?

- Een Raspberry Pi met Raspberry Pi OS, aangesloten op je thuisnetwerk (bij voorkeur met een netwerkkabel)
- Bij voorkeur een USB-SSD of USB-stick voor de opslag (geheugenkaartjes slijten sneller)
- Toegang tot de Pi: met een toetsenbord en scherm, of via SSH vanaf je pc

## Stap 1: de Pi klaarmaken (alleen als die nog niet draait)

1. Installeer op je pc **Raspberry Pi Imager** via https://www.raspberrypi.com/software/
2. Stop de geheugenkaart van de Pi in je pc en start Raspberry Pi Imager.
3. Kies je Pi-model en bij het besturingssysteem **Raspberry Pi OS Lite (64-bit)**
   (te vinden onder *Raspberry Pi OS (other)*). Kies daarna de geheugenkaart.
4. Klik op **Volgende** en dan op **Instellingen bewerken**:
   - Hostnaam: `raspberrypi`
   - Kies een gebruikersnaam en wachtwoord en schrijf ze op
   - Vul je wifi-naam en -wachtwoord in (niet nodig met een netwerkkabel)
   - Tabblad *Services*: vink **SSH inschakelen** aan, met *wachtwoord-authenticatie*
5. Klik op **Opslaan** en **Ja** en wacht tot het schrijven klaar is.
6. Stop de kaart in de Pi, sluit eventueel de netwerkkabel aan en zet de Pi aan. Wacht 3 minuten.

Draait je Pi al? Zet SSH dan aan op de Pi zelf: `sudo raspi-config` > *Interface Options* > *SSH* > *Ja*.

## Stap 2: alles vanaf je pc op de Pi installeren

1. Dubbelklik in de map *Mijn Archief* op **Raspberry Pi instellen**.
2. Beantwoord de vragen:
   - Naam van de Pi: druk op Enter voor `raspberrypi.local`, of typ het IP-adres van de Pi
   - Gebruikersnaam: de naam die je in stap 1 koos
   - Map op de Pi: druk op Enter
3. Typ twee keer het wachtwoord van je Pi als daarom gevraagd wordt. Je ziet tijdens het typen geen tekens;
   dat is normaal.
4. Kies daarna een wachtwoord voor de gedeelde map en typ het twee keer.
5. Aan het eind opent de Verkenner de gedeelde map. Log in met je Pi-gebruikersnaam en het wachtwoord
   voor de gedeelde map, en vink **Mijn referenties onthouden** aan.

Lukt het niet met `raspberrypi.local`? Gebruik dan het IP-adres van de Pi, bijvoorbeeld `192.168.1.50`. Dat
vind je in de app of op de webpagina van je router. Geef de Pi daar bij voorkeur een vast IP-adres.

Liever direct op de Pi werken? Kopieer de map `raspberry` naar de Pi en voer daar uit:
`sudo bash installeer-op-raspberry.sh`

## Stap 3: in Mijn Archief

**Heb je al documenten in Mijn Archief?** Verhuis het archief dan naar de Pi:

1. Kies in het menu **Bestand › Archief verhuizen (bijv. naar Raspberry Pi)…**
2. Controleer het netwerkadres en klik op **Kopiëren en overstappen**.
3. Alles wordt gekopieerd. Daarna werkt het programma met de Pi. Je oude archief op de pc blijft voor de
   zekerheid staan; die map kun je later zelf verwijderen.

**Begin je net?** Typ bij de eerste start het netwerkadres (bijv. `\\raspberrypi.local\MijnArchief`) in het veld **Archiefmap** en klik op
**Starten**. Een bestaand archief op de Pi open je via **Bestand › Ander archief openen…**

## Als de Pi uit staat

Start je Mijn Archief terwijl de Pi uit staat of niet bereikbaar is, dan meldt het programma dat het archief
niet gevonden is. Zet de Pi aan, wacht een minuut en klik op **Opnieuw proberen**.

## Back-up

Maak regelmatig een back-up via **Bestand › Back-up maken** en bewaar die op een USB-stick of externe schijf.
Zo ben je ook beschermd als de geheugenkaart of schijf van de Pi kapotgaat.
