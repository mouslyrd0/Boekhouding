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

## Stap 1: op de Raspberry Pi

1. Kopieer de map `raspberry` naar de Pi, bijvoorbeeld met een USB-stick.
2. Open een terminal op de Pi, ga naar die map en voer uit:

   ```
   sudo bash installeer-op-raspberry.sh
   ```

   Wil je het archief op een USB-schijf die vast gekoppeld is op `/mnt/ssd`? Gebruik dan:

   ```
   sudo bash installeer-op-raspberry.sh /mnt/ssd/mijnarchief
   ```

3. Kies een wachtwoord als daarom gevraagd wordt.
4. Aan het eind zie je het **netwerkadres**, bijvoorbeeld `\\raspberrypi\MijnArchief`. Schrijf dat op,
   samen met de gebruikersnaam.

## Stap 2: op je Windows-pc, eenmalig inloggen

1. Open de **Verkenner** (Windows-toets + E).
2. Klik bovenin op de adresbalk, typ het netwerkadres, bijvoorbeeld `\\raspberrypi\MijnArchief`, en druk op
   Enter.
3. Vul de gebruikersnaam en het wachtwoord van stap 1 in en vink **Mijn referenties onthouden** aan.
4. Je ziet nu de (nog lege) map. Je kunt de Verkenner sluiten.

Werkt `\\raspberrypi\MijnArchief` niet? Gebruik dan het IP-adres dat het script liet zien, bijvoorbeeld
`\\192.168.1.50\MijnArchief`. Geef de Pi in je router bij voorkeur een vast IP-adres.

## Stap 3: in Mijn Archief

**Heb je al documenten in Mijn Archief?** Verhuis het archief dan naar de Pi:

1. Kies in het menu **Bestand › Archief verhuizen (bijv. naar Raspberry Pi)…**
2. Controleer het netwerkadres en klik op **Kopiëren en overstappen**.
3. Alles wordt gekopieerd. Daarna werkt het programma met de Pi. Je oude archief op de pc blijft voor de
   zekerheid staan; die map kun je later zelf verwijderen.

**Begin je net?** Typ bij de eerste start het netwerkadres in het veld **Archiefmap** en klik op
**Starten**. Een bestaand archief op de Pi open je via **Bestand › Ander archief openen…**

## Als de Pi uit staat

Start je Mijn Archief terwijl de Pi uit staat of niet bereikbaar is, dan meldt het programma dat het archief
niet gevonden is. Zet de Pi aan, wacht een minuut en klik op **Opnieuw proberen**.

## Back-up

Maak regelmatig een back-up via **Bestand › Back-up maken** en bewaar die op een USB-stick of externe schijf.
Zo ben je ook beschermd als de geheugenkaart of schijf van de Pi kapotgaat.
