"""The places DayWright can import statutory holidays for, bundled so that choosing one needs no network.

COUNTRIES is Nager.Date's own list of the countries it covers (its AvailableCountries, 204 of them in October 2026),
by ISO 3166-1 code, with Nager.Date's English name; the interface names them in its language. A country's regions
come from the holidays imported for it, by ISO 3166-2 code, as Nager.Date gives them; REGION_NAMES names those of a
few countries, in English, and in Chinese for Canada's. A region not named here is shown by its code.
"""

from __future__ import annotations

COUNTRIES = (
    ("AD", "Andorra"), ("AG", "Antigua and Barbuda"), ("AI", "Anguilla"), ("AL", "Albania"), ("AM", "Armenia"),
    ("AO", "Angola"), ("AR", "Argentina"), ("AT", "Austria"), ("AU", "Australia"), ("AW", "Aruba"),
    ("AX", "Åland Islands"), ("BA", "Bosnia and Herzegovina"), ("BB", "Barbados"), ("BD", "Bangladesh"),
    ("BE", "Belgium"), ("BF", "Burkina Faso"), ("BG", "Bulgaria"), ("BH", "Bahrain"), ("BI", "Burundi"),
    ("BJ", "Benin"), ("BL", "Saint Barthélemy"), ("BM", "Bermuda"), ("BO", "Bolivia"), ("BQ", "Caribbean Netherlands"),
    ("BR", "Brazil"), ("BS", "Bahamas"), ("BW", "Botswana"), ("BY", "Belarus"), ("BZ", "Belize"), ("CA", "Canada"),
    ("CC", "Cocos (Keeling) Islands"), ("CD", "DR Congo"), ("CF", "Central African Republic"), ("CG", "Congo"),
    ("CH", "Switzerland"), ("CI", "Ivory Coast"), ("CK", "Cook Islands"), ("CL", "Chile"), ("CM", "Cameroon"),
    ("CN", "China"), ("CO", "Colombia"), ("CR", "Costa Rica"), ("CU", "Cuba"), ("CV", "Cape Verde"), ("CW", "Curaçao"),
    ("CX", "Christmas Island"), ("CY", "Cyprus"), ("CZ", "Czechia"), ("DE", "Germany"), ("DJ", "Djibouti"),
    ("DK", "Denmark"), ("DM", "Dominica"), ("DO", "Dominican Republic"), ("DZ", "Algeria"), ("EC", "Ecuador"),
    ("EE", "Estonia"), ("EG", "Egypt"), ("ER", "Eritrea"), ("ES", "Spain"), ("ET", "Ethiopia"), ("FI", "Finland"),
    ("FK", "Falkland Islands"), ("FM", "Micronesia"), ("FO", "Faroe Islands"), ("FR", "France"), ("GA", "Gabon"),
    ("GB", "United Kingdom"), ("GD", "Grenada"), ("GE", "Georgia"), ("GF", "French Guiana"), ("GG", "Guernsey"),
    ("GH", "Ghana"), ("GI", "Gibraltar"), ("GL", "Greenland"), ("GM", "Gambia"), ("GN", "Guinea"), ("GP", "Guadeloupe"),
    ("GQ", "Equatorial Guinea"), ("GR", "Greece"), ("GT", "Guatemala"), ("GW", "Guinea-Bissau"), ("GY", "Guyana"),
    ("HK", "Hong Kong"), ("HN", "Honduras"), ("HR", "Croatia"), ("HT", "Haiti"), ("HU", "Hungary"), ("ID", "Indonesia"),
    ("IE", "Ireland"), ("IM", "Isle of Man"), ("IQ", "Iraq"), ("IS", "Iceland"), ("IT", "Italy"), ("JE", "Jersey"),
    ("JM", "Jamaica"), ("JP", "Japan"), ("KE", "Kenya"), ("KH", "Cambodia"), ("KI", "Kiribati"), ("KM", "Comoros"),
    ("KN", "Saint Kitts and Nevis"), ("KR", "South Korea"), ("KY", "Cayman Islands"), ("KZ", "Kazakhstan"),
    ("LC", "Saint Lucia"), ("LI", "Liechtenstein"), ("LR", "Liberia"), ("LS", "Lesotho"), ("LT", "Lithuania"),
    ("LU", "Luxembourg"), ("LV", "Latvia"), ("LY", "Libya"), ("MA", "Morocco"), ("MC", "Monaco"), ("MD", "Moldova"),
    ("ME", "Montenegro"), ("MF", "Saint Martin"), ("MG", "Madagascar"), ("MH", "Marshall Islands"),
    ("MK", "North Macedonia"), ("ML", "Mali"), ("MN", "Mongolia"), ("MP", "Northern Mariana Islands"),
    ("MQ", "Martinique"), ("MR", "Mauritania"), ("MS", "Montserrat"), ("MT", "Malta"), ("MW", "Malawi"),
    ("MX", "Mexico"), ("MZ", "Mozambique"), ("NA", "Namibia"), ("NC", "New Caledonia"), ("NE", "Niger"),
    ("NF", "Norfolk Island"), ("NG", "Nigeria"), ("NI", "Nicaragua"), ("NL", "Netherlands"), ("NO", "Norway"),
    ("NR", "Nauru"), ("NU", "Niue"), ("NZ", "New Zealand"), ("PA", "Panama"), ("PE", "Peru"),
    ("PF", "French Polynesia"), ("PG", "Papua New Guinea"), ("PH", "Philippines"), ("PL", "Poland"),
    ("PM", "Saint Pierre and Miquelon"), ("PN", "Pitcairn Islands"), ("PR", "Puerto Rico"), ("PT", "Portugal"),
    ("PW", "Palau"), ("PY", "Paraguay"), ("RO", "Romania"), ("RS", "Serbia"), ("RU", "Russia"), ("RW", "Rwanda"),
    ("SB", "Solomon Islands"), ("SC", "Seychelles"), ("SD", "Sudan"), ("SE", "Sweden"), ("SG", "Singapore"),
    ("SH", "Saint Helena, Ascension and Tristan da Cunha"), ("SI", "Slovenia"), ("SJ", "Svalbard and Jan Mayen"),
    ("SK", "Slovakia"), ("SL", "Sierra Leone"), ("SM", "San Marino"), ("SN", "Senegal"), ("SO", "Somalia"),
    ("SR", "Suriname"), ("SS", "South Sudan"), ("ST", "São Tomé and Príncipe"), ("SV", "El Salvador"),
    ("SX", "Sint Maarten"), ("SY", "Syria"), ("SZ", "Eswatini"), ("TC", "Turks and Caicos Islands"), ("TD", "Chad"),
    ("TG", "Togo"), ("TK", "Tokelau"), ("TN", "Tunisia"), ("TO", "Tonga"), ("TR", "Türkiye"),
    ("TT", "Trinidad and Tobago"), ("TV", "Tuvalu"), ("TZ", "Tanzania"), ("UA", "Ukraine"), ("UG", "Uganda"),
    ("US", "United States"), ("UY", "Uruguay"), ("VA", "Vatican City"), ("VC", "Saint Vincent and the Grenadines"),
    ("VE", "Venezuela"), ("VG", "British Virgin Islands"), ("VI", "United States Virgin Islands"), ("VN", "Vietnam"),
    ("VU", "Vanuatu"), ("WF", "Wallis and Futuna"), ("WS", "Samoa"), ("YE", "Yemen"), ("ZA", "South Africa"),
    ("ZM", "Zambia"), ("ZW", "Zimbabwe"),
)

COUNTRY_CODES = frozenset(code for code, _ in COUNTRIES)

# The Chinese names Ava knows a few countries by when asked to import their holidays; the interface names every
# country in its own language.
COUNTRY_NAMES_ZH = {"AU": "澳大利亚", "CA": "加拿大", "CN": "中国", "DE": "德国", "GB": "英国", "US": "美国"}

# Canada's provinces and territories, in English and Chinese.
_CANADA = {
    "CA-AB": ("Alberta", "艾伯塔省"), "CA-BC": ("British Columbia", "不列颠哥伦比亚省"), "CA-MB": ("Manitoba", "曼尼托巴省"),
    "CA-NB": ("New Brunswick", "新不伦瑞克省"), "CA-NL": ("Newfoundland and Labrador", "纽芬兰与拉布拉多省"),
    "CA-NS": ("Nova Scotia", "新斯科舍省"), "CA-NT": ("Northwest Territories", "西北地区"), "CA-NU": ("Nunavut", "努纳武特地区"),
    "CA-ON": ("Ontario", "安大略省"), "CA-PE": ("Prince Edward Island", "爱德华王子岛省"), "CA-QC": ("Quebec", "魁北克省"),
    "CA-SK": ("Saskatchewan", "萨斯喀彻温省"), "CA-YT": ("Yukon", "育空地区"),
}

# The regions of the United States, Australia, the United Kingdom and Germany, in English.
_ENGLISH_ONLY = {
    "US-AL": "Alabama", "US-AK": "Alaska", "US-AZ": "Arizona", "US-AR": "Arkansas", "US-CA": "California",
    "US-CO": "Colorado", "US-CT": "Connecticut", "US-DE": "Delaware", "US-DC": "District of Columbia",
    "US-FL": "Florida", "US-GA": "Georgia", "US-HI": "Hawaii", "US-ID": "Idaho", "US-IL": "Illinois",
    "US-IN": "Indiana", "US-IA": "Iowa", "US-KS": "Kansas", "US-KY": "Kentucky", "US-LA": "Louisiana",
    "US-ME": "Maine", "US-MD": "Maryland", "US-MA": "Massachusetts", "US-MI": "Michigan", "US-MN": "Minnesota",
    "US-MS": "Mississippi", "US-MO": "Missouri", "US-MT": "Montana", "US-NE": "Nebraska", "US-NV": "Nevada",
    "US-NH": "New Hampshire", "US-NJ": "New Jersey", "US-NM": "New Mexico", "US-NY": "New York",
    "US-NC": "North Carolina", "US-ND": "North Dakota", "US-OH": "Ohio", "US-OK": "Oklahoma", "US-OR": "Oregon",
    "US-PA": "Pennsylvania", "US-RI": "Rhode Island", "US-SC": "South Carolina", "US-SD": "South Dakota",
    "US-TN": "Tennessee", "US-TX": "Texas", "US-UT": "Utah", "US-VT": "Vermont", "US-VA": "Virginia",
    "US-WA": "Washington", "US-WV": "West Virginia", "US-WI": "Wisconsin", "US-WY": "Wyoming",
    "AU-ACT": "Australian Capital Territory", "AU-NSW": "New South Wales", "AU-NT": "Northern Territory",
    "AU-QLD": "Queensland", "AU-SA": "South Australia", "AU-TAS": "Tasmania", "AU-VIC": "Victoria",
    "AU-WA": "Western Australia",
    "GB-ENG": "England", "GB-NIR": "Northern Ireland", "GB-SCT": "Scotland", "GB-WLS": "Wales",
    "DE-BW": "Baden-Württemberg", "DE-BY": "Bavaria", "DE-BE": "Berlin", "DE-BB": "Brandenburg", "DE-HB": "Bremen",
    "DE-HH": "Hamburg", "DE-HE": "Hesse", "DE-MV": "Mecklenburg-Vorpommern", "DE-NI": "Lower Saxony",
    "DE-NW": "North Rhine-Westphalia", "DE-RP": "Rhineland-Palatinate", "DE-SL": "Saarland", "DE-SN": "Saxony",
    "DE-ST": "Saxony-Anhalt", "DE-SH": "Schleswig-Holstein", "DE-TH": "Thuringia",
}

# Each named region's name by language, "en" and, for Canada's, "zh"; the interface shows the English one in
# Chinese when there is no Chinese one.
REGION_NAMES = {**{code: {"en": english, "zh": chinese} for code, (english, chinese) in _CANADA.items()},
                **{code: {"en": english} for code, english in _ENGLISH_ONLY.items()}}
