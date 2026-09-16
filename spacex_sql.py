"""
Build "Spacex Data Set" (SQLite) from the real Falcon 9 launch history,
2010-06-04 through 2019-12-17 (flights 1-77), transcribed from:
https://en.wikipedia.org/wiki/List_of_Falcon_9_and_Falcon_Heavy_launches_(2010%E2%80%932019)

This range is used (rather than the current live page) because it is the
only stretch of the article containing landing failures — the 2025-2026
slice on the main page is ~99% success and has almost nothing for SQL
aggregate queries to differentiate.

Excluded on purpose:
  - the AMOS-6 pre-flight pad explosion (Flight No. "N/A" in the source;
    the rocket never left the pad, so it has no launch/landing outcome)
  - the three Falcon Heavy flights (FH 1-3), since the task is Falcon 9

Landing_Outcome values follow the conventional phrasing used in this kind
of exercise: 'Success (ground pad)', 'Success (drone ship)',
'Failure (drone ship)', 'Failure (ocean)', 'Failure (parachute)',
'Controlled (ocean)' (deliberate un-recovered test splashdown),
'Precluded (drone ship)' (in-flight breakup before a landing could be
attempted), and 'No attempt' (expendable flight, no legs/grid fins).
"""

import csv
import sqlite3

# FlightNo, Date, Time, BoosterVersion, BoosterSerial, LaunchSite, Payload,
# PayloadMassKG (None = unknown/classified), Orbit, Customer, MissionOutcome,
# LandingOutcome
ROWS = [
(1,"2010-06-04","18:45","F9 v1.0","B0003","CCAFS SLC-40","Dragon Qualification Unit",None,"LEO","SpaceX","Success","Failure (parachute)"),
(2,"2010-12-08","15:43","F9 v1.0","B0004","CCAFS SLC-40","COTS Demo Flight 1 (Dragon C101)",None,"LEO","NASA (COTS)","Success","Failure (parachute)"),
(3,"2012-05-22","07:44","F9 v1.0","B0005","CCAFS SLC-40","COTS Demo Flight 2 (Dragon C102)",525,"ISS","NASA (COTS)","Success","No attempt"),
(4,"2012-10-08","00:35","F9 v1.0","B0006","CCAFS SLC-40","SpaceX CRS-1 (Dragon C103)",4700,"ISS","NASA (CRS)","Success","No attempt"),
(5,"2013-03-01","15:10","F9 v1.0","B0007","CCAFS SLC-40","SpaceX CRS-2 (Dragon C104)",4877,"ISS","NASA (CRS)","Success","No attempt"),
(6,"2013-09-29","16:00","F9 v1.1","B1003","VAFB SLC-4E","CASSIOPE",500,"PO","MDA","Success","Failure (ocean)"),
(7,"2013-12-03","22:41","F9 v1.1","B1004","CCAFS SLC-40","SES-8",3170,"GTO","SES","Success","No attempt"),
(8,"2014-01-06","22:06","F9 v1.1","B1005","CCAFS SLC-40","Thaicom 6",3325,"GTO","Thaicom","Success","No attempt"),
(9,"2014-04-18","19:25","F9 v1.1","B1006","CCAFS SLC-40","SpaceX CRS-3 (Dragon C105)",2296,"ISS","NASA (CRS)","Success","Controlled (ocean)"),
(10,"2014-07-14","15:15","F9 v1.1","B1007","CCAFS SLC-40","Orbcomm-OG2-1",1316,"LEO","Orbcomm","Success","Controlled (ocean)"),
(11,"2014-08-05","08:00","F9 v1.1","B1008","CCAFS SLC-40","AsiaSat 8",4535,"GTO","AsiaSat","Success","No attempt"),
(12,"2014-09-07","05:00","F9 v1.1","B1011","CCAFS SLC-40","AsiaSat 6",4428,"GTO","AsiaSat","Success","No attempt"),
(13,"2014-09-21","05:52","F9 v1.1","B1010","CCAFS SLC-40","SpaceX CRS-4 (Dragon C106.1)",2216,"ISS","NASA (CRS)","Success","Failure (ocean)"),
(14,"2015-01-10","09:47","F9 v1.1","B1012","CCAFS SLC-40","SpaceX CRS-5 (Dragon C107)",2395,"ISS","NASA (CRS)","Success","Failure (drone ship)"),
(15,"2015-02-11","23:03","F9 v1.1","B1013","CCAFS SLC-40","DSCOVR",570,"ES-L1","NASA/NOAA/USAF","Success","Controlled (ocean)"),
(16,"2015-03-02","03:50","F9 v1.1","B1014","CCAFS SLC-40","ABS-3A / Eutelsat 115 West B",4159,"GTO","ABS/Eutelsat","Success","No attempt"),
(17,"2015-04-14","20:10","F9 v1.1","B1015","CCAFS SLC-40","SpaceX CRS-6 (Dragon C108.1)",1898,"ISS","NASA (CRS)","Success","Failure (drone ship)"),
(18,"2015-04-27","23:03","F9 v1.1","B1016","CCAFS SLC-40","TurkmenAlem 52E / MonacoSAT",4707,"GTO","Turkmenistan NSA","Success","No attempt"),
(19,"2015-06-28","14:21","F9 v1.1","B1018","CCAFS SLC-40","SpaceX CRS-7 (Dragon C109)",1952,"ISS","NASA (CRS)","Failure","Precluded (drone ship)"),
(20,"2015-12-22","01:29","F9 FT","B1019","CCAFS SLC-40","Orbcomm-OG2-2",2034,"LEO","Orbcomm","Success","Success (ground pad)"),
(21,"2016-01-17","18:42","F9 v1.1","B1017","VAFB SLC-4E","Jason-3",553,"LEO","NASA/NOAA/CNES","Success","Failure (drone ship)"),
(22,"2016-03-04","23:35","F9 FT","B1020","CCAFS SLC-40","SES-9",5271,"GTO","SES","Success","Failure (drone ship)"),
(23,"2016-04-08","20:43","F9 FT","B1021","CCAFS SLC-40","SpaceX CRS-8 (Dragon C110.1)",3136,"ISS","NASA (CRS)","Success","Success (drone ship)"),
(24,"2016-05-06","05:21","F9 FT","B1022","CCAFS SLC-40","JCSAT-14",4696,"GTO","SKY Perfect JSAT","Success","Success (drone ship)"),
(25,"2016-05-27","21:39","F9 FT","B1023","CCAFS SLC-40","Thaicom 8",3100,"GTO","Thaicom","Success","Success (drone ship)"),
(26,"2016-06-15","14:29","F9 FT","B1024","CCAFS SLC-40","ABS-2A / Eutelsat 117 West B",3600,"GTO","ABS/Eutelsat","Success","Failure (drone ship)"),
(27,"2016-07-18","04:45","F9 FT","B1025","CCAFS SLC-40","SpaceX CRS-9 (Dragon C111.1)",2257,"ISS","NASA (CRS)","Success","Success (ground pad)"),
(28,"2016-08-14","05:26","F9 FT","B1026","CCAFS SLC-40","JCSAT-16",4600,"GTO","SKY Perfect JSAT","Success","Success (drone ship)"),
(29,"2017-01-14","17:54","F9 FT","B1029","VAFB SLC-4E","Iridium NEXT-1",9600,"PO","Iridium Communications","Success","Success (drone ship)"),
(30,"2017-02-19","14:39","F9 FT","B1031","KSC LC-39A","SpaceX CRS-10 (Dragon C112.1)",2490,"ISS","NASA (CRS)","Success","Success (ground pad)"),
(31,"2017-03-16","06:00","F9 FT","B1030","KSC LC-39A","EchoStar 23",5600,"GTO","EchoStar","Success","No attempt"),
(32,"2017-03-30","22:27","F9 FT","B1021","KSC LC-39A","SES-10",5300,"GTO","SES","Success","Success (drone ship)"),
(33,"2017-05-01","11:15","F9 FT","B1032","KSC LC-39A","NROL-76",None,"LEO","NRO","Success","Success (ground pad)"),
(34,"2017-05-15","23:21","F9 FT","B1034","KSC LC-39A","Inmarsat-5 F4",6070,"GTO","Inmarsat","Success","No attempt"),
(35,"2017-06-03","21:07","F9 FT","B1035","KSC LC-39A","SpaceX CRS-11 (Dragon C106.2)",2708,"ISS","NASA (CRS)","Success","Success (ground pad)"),
(36,"2017-06-23","19:10","F9 FT","B1029","KSC LC-39A","BulgariaSat-1",3669,"GTO","Bulsatcom","Success","Success (drone ship)"),
(37,"2017-06-25","20:25","F9 FT","B1036","VAFB SLC-4E","Iridium NEXT-2",9600,"LEO","Iridium Communications","Success","Success (drone ship)"),
(38,"2017-07-05","23:38","F9 FT","B1037","KSC LC-39A","Intelsat 35e",6761,"GTO","Intelsat","Success","No attempt"),
(39,"2017-08-14","16:31","F9 B4","B1039","KSC LC-39A","SpaceX CRS-12 (Dragon C113.1)",3310,"ISS","NASA (CRS)","Success","Success (ground pad)"),
(40,"2017-08-24","18:51","F9 FT","B1038","VAFB SLC-4E","Formosat-5",475,"SSO","NSPO","Success","Success (drone ship)"),
(41,"2017-09-07","14:00","F9 B4","B1040","KSC LC-39A","Boeing X-37B OTV-5",4990,"LEO","USAF","Success","Success (ground pad)"),
(42,"2017-10-09","12:37","F9 B4","B1041","VAFB SLC-4E","Iridium NEXT-3",9600,"PO","Iridium Communications","Success","Success (drone ship)"),
(43,"2017-10-11","22:53","F9 FT","B1031","KSC LC-39A","SES-11 / EchoStar 105",5400,"GTO","SES/EchoStar","Success","Success (drone ship)"),
(44,"2017-10-30","19:34","F9 B4","B1042","KSC LC-39A","Koreasat 5A",3500,"GTO","KT Corporation","Success","Success (drone ship)"),
(45,"2017-12-15","15:36","F9 FT","B1035","CCAFS SLC-40","SpaceX CRS-13 (Dragon C108.2)",2205,"ISS","NASA (CRS)","Success","Success (ground pad)"),
(46,"2017-12-23","01:27","F9 FT","B1036","VAFB SLC-4E","Iridium NEXT-4",9600,"PO","Iridium Communications","Success","Controlled (ocean)"),
(47,"2018-01-08","01:00","F9 B4","B1043","CCAFS SLC-40","Zuma",None,"LEO","US Government","Success","Success (ground pad)"),
(48,"2018-01-31","21:25","F9 FT","B1032","CCAFS SLC-40","GovSat-1 (SES-16)",4230,"GTO","SES","Success","Controlled (ocean)"),
(49,"2018-02-22","14:17","F9 FT","B1038","VAFB SLC-4E","Paz",2150,"SSO","Hisdesat","Success","No attempt"),
(50,"2018-03-06","05:33","F9 B4","B1044","CCAFS SLC-40","Hispasat 30W-6",6092,"GTO","Hispasat","Success","Controlled (ocean)"),
(51,"2018-03-30","14:14","F9 B4","B1041","VAFB SLC-4E","Iridium NEXT-5",9600,"PO","Iridium Communications","Success","No attempt"),
(52,"2018-04-02","20:30","F9 B4","B1039","CCAFS SLC-40","SpaceX CRS-14 (Dragon C110.2)",2647,"ISS","NASA (CRS)","Success","No attempt"),
(53,"2018-04-18","22:51","F9 B4","B1045","CCAFS SLC-40","TESS",362,"HEO","NASA (LSP)","Success","Success (drone ship)"),
(54,"2018-05-11","20:14","F9 B5","B1046","KSC LC-39A","Bangabandhu-1",3600,"GTO","Thales-Alenia/BTRC","Success","Success (drone ship)"),
(55,"2018-05-22","19:47","F9 B4","B1043","VAFB SLC-4E","Iridium NEXT-6 / GRACE-FO",6460,"PO","Iridium/GFZ/NASA","Success","No attempt"),
(56,"2018-06-04","04:45","F9 B4","B1040","CCAFS SLC-40","SES-12",5384,"GTO","SES","Success","No attempt"),
(57,"2018-06-29","09:42","F9 B4","B1045","CCAFS SLC-40","SpaceX CRS-15 (Dragon C111.2)",2697,"ISS","NASA (CRS)","Success","No attempt"),
(58,"2018-07-22","05:50","F9 B5","B1047","CCAFS SLC-40","Telstar 19V",7075,"GTO","Telesat","Success","Success (drone ship)"),
(59,"2018-07-25","11:39","F9 B5","B1048","VAFB SLC-4E","Iridium NEXT-7",9600,"PO","Iridium Communications","Success","Success (drone ship)"),
(60,"2018-08-07","05:18","F9 B5","B1046","CCAFS SLC-40","Merah Putih",5800,"GTO","Telkom Indonesia","Success","Success (drone ship)"),
(61,"2018-09-10","04:45","F9 B5","B1049","CCAFS SLC-40","Telstar 18V / Apstar-5C",7060,"GTO","Telesat","Success","Success (drone ship)"),
(62,"2018-10-08","02:22","F9 B5","B1048","VAFB SLC-4E","SAOCOM 1A",3000,"SSO","CONAE","Success","Success (ground pad)"),
(63,"2018-11-15","20:46","F9 B5","B1047","KSC LC-39A","Es'hail 2",5300,"GTO","Es'hailSat","Success","Success (drone ship)"),
(64,"2018-12-03","18:34","F9 B5","B1046","VAFB SLC-4E","SSO-A (SmallSat Express)",4000,"SSO","Spaceflight Industries","Success","Success (drone ship)"),
(65,"2018-12-05","18:16","F9 B5","B1050","CCAFS SLC-40","SpaceX CRS-16 (Dragon C112.2)",2500,"ISS","NASA (CRS)","Success","Failure (ground pad)"),
(66,"2018-12-23","13:51","F9 B5","B1054","CCAFS SLC-40","GPS III-01",4400,"MEO","USAF","Success","No attempt"),
(67,"2019-01-11","15:31","F9 B5","B1049","VAFB SLC-4E","Iridium NEXT-8",9600,"PO","Iridium Communications","Success","Success (drone ship)"),
(68,"2019-02-22","01:45","F9 B5","B1048","CCAFS SLC-40","Nusantara Satu",4850,"GTO","PSN/SpaceIL/IAI","Success","Success (drone ship)"),
(69,"2019-03-02","07:49","F9 B5","B1051","KSC LC-39A","Crew Dragon Demo-1",12055,"ISS","NASA (CCD)","Success","Success (drone ship)"),
(70,"2019-05-04","06:48","F9 B5","B1056","CCAFS SLC-40","SpaceX CRS-17 (Dragon C113.2)",2495,"ISS","NASA (CRS)","Success","Success (drone ship)"),
(71,"2019-05-24","02:30","F9 B5","B1049","CCAFS SLC-40","Starlink v0.9",13620,"LEO","SpaceX","Success","Success (drone ship)"),
(72,"2019-06-12","14:17","F9 B5","B1051","VAFB SLC-4E","RADARSAT Constellation",4200,"SSO","Canadian Space Agency","Success","Success (ground pad)"),
(73,"2019-07-25","22:01","F9 B5","B1056","CCAFS SLC-40","SpaceX CRS-18 (Dragon C108.3)",2268,"ISS","NASA (CRS)","Success","Success (ground pad)"),
(74,"2019-08-06","23:23","F9 B5","B1047","CCAFS SLC-40","AMOS-17",6500,"GTO","Spacecom","Success","No attempt"),
(75,"2019-11-11","14:56","F9 B5","B1048","CCAFS SLC-40","Starlink Launch 1",15600,"LEO","SpaceX","Success","Success (drone ship)"),
(76,"2019-12-05","17:29","F9 B5","B1059","CCAFS SLC-40","SpaceX CRS-19 (Dragon C106.3)",2617,"ISS","NASA (CRS)","Success","Success (drone ship)"),
(77,"2019-12-17","00:10","F9 B5","B1056","CCAFS SLC-40","JCSat-18 / Kacific 1",6956,"GTO","Sky Perfect JSAT/Kacific","Success","Success (drone ship)"),
]

COLUMNS = ["FlightNumber","Date","Time","BoosterVersion","BoosterSerial","LaunchSite",
           "Payload","PayloadMassKG","Orbit","Customer","MissionOutcome","LandingOutcome"]

# --- write the plain CSV, for anyone who wants the raw data ---
with open("spacex_sql_dataset.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(COLUMNS)
    w.writerows(ROWS)

# --- build "Spacex Data Set" ---
DB_PATH = "Spacex Data Set.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS SPACEXTABLE")
cur.execute("""
    CREATE TABLE SPACEXTABLE (
        FlightNumber    INTEGER PRIMARY KEY,
        Date            TEXT,
        Time            TEXT,
        BoosterVersion  TEXT,
        BoosterSerial   TEXT,
        LaunchSite      TEXT,
        Payload         TEXT,
        PayloadMassKG   REAL,
        Orbit           TEXT,
        Customer        TEXT,
        MissionOutcome  TEXT,
        LandingOutcome  TEXT
    )
""")
cur.executemany(f"INSERT INTO SPACEXTABLE VALUES ({','.join('?'*len(COLUMNS))})", ROWS)
conn.commit()
print(f"Loaded {cur.execute('SELECT COUNT(*) FROM SPACEXTABLE').fetchone()[0]} rows into {DB_PATH}")


def run(title, sql, params=()):
    print(f"\n{'='*70}\n{title}\n{'='*70}")
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print(" | ".join(cols))
    for r in rows:
        print(" | ".join(str(x) for x in r))
    return rows


# 1. Unique launch sites
run("1. Unique launch sites",
    "SELECT DISTINCT LaunchSite FROM SPACEXTABLE;")

# 2. 5 records where launch site begins with 'CCA'
run("2. Five records where LaunchSite LIKE 'CCA%'",
    "SELECT * FROM SPACEXTABLE WHERE LaunchSite LIKE 'CCA%' LIMIT 5;")

# 3. Total payload mass carried by boosters launched by NASA (CRS)
run("3. Total payload mass for customer = 'NASA (CRS)'",
    "SELECT SUM(PayloadMassKG) AS TotalPayloadMassKG FROM SPACEXTABLE WHERE Customer = 'NASA (CRS)';")

# 4. Average payload mass carried by booster version F9 v1.1
run("4. Average payload mass for BoosterVersion = 'F9 v1.1'",
    "SELECT AVG(PayloadMassKG) AS AvgPayloadMassKG FROM SPACEXTABLE WHERE BoosterVersion = 'F9 v1.1';")

# 5. Date of the first successful ground-pad landing
run("5. First successful ground-pad landing",
    "SELECT MIN(Date) AS FirstGroundPadSuccess FROM SPACEXTABLE WHERE LandingOutcome = 'Success (ground pad)';")

# 6. Boosters with drone-ship success and 4000 < payload mass < 6000
run("6. Boosters: drone-ship success, 4000 < payload < 6000 kg",
    """SELECT BoosterSerial, BoosterVersion, PayloadMassKG
       FROM SPACEXTABLE
       WHERE LandingOutcome = 'Success (drone ship)'
         AND PayloadMassKG > 4000 AND PayloadMassKG < 6000
       ORDER BY PayloadMassKG;""")

# 7. Total successful and failure mission outcomes
run("7. Total success vs failure mission outcomes",
    "SELECT MissionOutcome, COUNT(*) AS Total FROM SPACEXTABLE GROUP BY MissionOutcome;")

# 8. Booster_versions carrying the maximum payload mass (subquery)
run("8. Booster version(s) carrying the maximum payload mass",
    """SELECT DISTINCT BoosterVersion, BoosterSerial, PayloadMassKG
       FROM SPACEXTABLE
       WHERE PayloadMassKG = (SELECT MAX(PayloadMassKG) FROM SPACEXTABLE);""")

# 9. Month name, failure landing outcome in drone ship, booster version,
#    launch site, for months in 2015
run("9. 2015 records with 'Failure (drone ship)' landings",
    """SELECT
           CASE CAST(strftime('%m', Date) AS INTEGER)
               WHEN 1 THEN 'January'  WHEN 2 THEN 'February' WHEN 3 THEN 'March'
               WHEN 4 THEN 'April'    WHEN 5 THEN 'May'      WHEN 6 THEN 'June'
               WHEN 7 THEN 'July'     WHEN 8 THEN 'August'   WHEN 9 THEN 'September'
               WHEN 10 THEN 'October' WHEN 11 THEN 'November' WHEN 12 THEN 'December'
           END AS MonthName,
           LandingOutcome, BoosterVersion, LaunchSite
       FROM SPACEXTABLE
       WHERE strftime('%Y', Date) = '2015'
         AND LandingOutcome = 'Failure (drone ship)';""")

# 10. Rank landing outcome counts between 2010-06-04 and 2017-03-20, descending
run("10. Landing outcome counts, 2010-06-04 to 2017-03-20, ranked descending",
    """SELECT LandingOutcome, COUNT(*) AS OutcomeCount,
           RANK() OVER (ORDER BY COUNT(*) DESC) AS Rank
       FROM SPACEXTABLE
       WHERE Date BETWEEN '2010-06-04' AND '2017-03-20'
       GROUP BY LandingOutcome
       ORDER BY OutcomeCount DESC;""")

conn.close()
