# page-table name -> TSV name, for the rows the automatic matcher could not pair up
ALIAS = {
 ('Griffin','Griffin Capital (Heritage - Bedford, NH) DST (Estimated)'):'Heritage Apartments',
 ('Griffin','Griffin Capital (South Beach - Vegas) DST'):'South Beach Apartments',
 ('Hamilton Point','HPI Fund I'):'HPI Apartment Opportunity Fund I',
 ('Hamilton Point','HPI Fund II'):'HPI Apartment Opportunity Fund II',
 ('Hamilton Point','HPI Fund IV'):'HPI Real Estate Fund IV',
 ('Hamilton Point','HPI Fund V'):'HPI Real Estate Fund V',
 ('Hamilton Point','HPI Fund VI'):'HPI Real Estate Fund VI',
 ('Hamilton Point','HPI Fund VII'):'HPI Real Estate Fund VII',
 ('Hamilton Point','HPI Fund VIII'):'HPI Real Estate Fund VIII',
 ('NLCA','GSA FBI/NARA Portfolio DST'):'US Government - GSA FBI & National Archives (2014 DST)',
 ('Olympus','1400 Chestnut'):'1400 Chestnut (Development)',
 ('Passco','Almeria at Ocotillo'):'Almeria',
 ('Passco','Arlington at Eastern Shore'):'Arlington',
 ('Passco','Asheville Exchange'):'Asheville',
 ('Passco','Carrington at Brier Creek'):'Brier Creek',
 ('Passco','Estates at Crossroads'):'Estates',
 ('Passco','Haven at West Melbourne'):'Haven',
 ('Passco','Legends at Wolfchase'):'Wolfchase',
 ('Passco','Merritt at Sugarloaf'):'Merritt',
 ('Passco','The Lexington'):'Lexington',
 ('Passco','Veranda at Norton Commons'):'Veranda',
 ('Passco','Vinings at Laurel Creek'):'Vinings',
 ('Passco','Voyager at Space Center'):'Voyager',
}
# page rows that aggregate several TSV rows — the TSV components are kept, the page roll-up is dropped
DROP = {
 ('Bluerock','Lynd Portfolio (Mesa Ridge / Meadows / Stratford)'),
 ('Bluerock','Marquis Portfolio (Stone Oak / Crown Ridge / TPC / Cascades)'),
 ('Bluerock','Sorrel Phillips Creek / Sovereign Apartments (Portfolio)'),
}
