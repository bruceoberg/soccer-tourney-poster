#!/usr/bin/env python3

year = 2026
strFileBase = f'{year}-mens-world-cup'
strYearTitle = f'{year} World Cup'
strSquadsPage = f'{year}_FIFA_World_Cup_squads'
strDateStart = 'June 11, 2026'

mpStrGroupStrColor: dict[str, str] ={
	"A":	"#b9deb7",	# green
	"B":	"#ffbcb9",	# red
	"C":	"#e9e8b5",	# yellow
	"D":	"#b0d0ee",	# blue
	"E":	"#ffc79e",	# orange
	"F":	"#bbdccf",	# teal
	"G":	"#d6d2e5",	# mauve
	"H":	"#b5dbe4",	# aqua
	"I":	"#bbb1d6",	# purple
	"J":	"#f0cdbd",	# salmon
	"K":	"#f9c4f1",	# pink
	"L":	"#e1aab6",	# burgundy
}

mpStrFifaCodeStrSeed: dict[str, str] = {
	"MEX": "A1",	
	"RSA": "A2",	
	"KOR": "A3",	
	"CZE": "A4",	
	"CAN": "B1",	
	"BIH": "B2",	
	"QAT": "B3",	
	"SUI": "B4",	
	"BRA": "C1",	
	"MAR": "C2",	
	"HAI": "C3",	
	"SCO": "C4",	
	"USA": "D1",	
	"PAR": "D2",	
	"AUS": "D3",	
	"TUR": "D4",	
	"GER": "E1",	
	"CUW": "E2",	
	"CIV": "E3",	
	"ECU": "E4",	
	"NED": "F1",	
	"JPN": "F2",	
	"SWE": "F3",	
	"TUN": "F4",	
	"BEL": "G1",	
	"EGY": "G2",	
	"IRN": "G3",	
	"NZL": "G4",	
	"ESP": "H1",	
	"CPV": "H2",	
	"KSA": "H3",	
	"URU": "H4",	
	"FRA": "I1",	
	"SEN": "I2",	
	"IRQ": "I3",	
	"NOR": "I4",	
	"ARG": "J1",	
	"ALG": "J2",	
	"AUT": "J3",	
	"JOR": "J4",	
	"POR": "K1",	
	"COD": "K2",	
	"UZB": "K3",	
	"COL": "K4",	
	"ENG": "L1",	
	"CRO": "L2",	
	"GHA": "L3",	
	"PAN": "L4",		
}