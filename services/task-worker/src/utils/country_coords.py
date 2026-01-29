"""Country code to geographic coordinates mapping.

Maps ISO 3166-1 alpha-2 country codes to (latitude, longitude) tuples.
Used for 3D map visualization and geolocation features.
"""

# Comprehensive mapping of country codes to approximate center coordinates
COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    # North America
    "US": (37.0902, -95.7129),  # United States
    "CA": (56.1304, -106.3468),  # Canada
    "MX": (23.6345, -102.5528),  # Mexico

    # South America
    "BR": (-14.2350, -51.9253),  # Brazil
    "AR": (-38.4161, -63.6167),  # Argentina
    "CL": (-35.6751, -71.5430),  # Chile
    "CO": (4.5709, -74.2973),   # Colombia
    "PE": (-9.1900, -75.0152),   # Peru
    "VE": (6.4238, -66.5897),   # Venezuela

    # Europe - Western
    "GB": (55.3781, -3.4360),   # United Kingdom
    "FR": (46.2276, 2.2137),    # France
    "DE": (51.1657, 10.4515),   # Germany
    "NL": (52.1326, 5.2913),    # Netherlands
    "BE": (50.5039, 4.4699),    # Belgium
    "ES": (40.4637, -3.7492),   # Spain
    "IT": (41.8719, 12.5674),   # Italy
    "PT": (39.3999, -8.2245),   # Portugal
    "IE": (53.4129, -8.2439),   # Ireland
    "CH": (46.8182, 8.2275),    # Switzerland
    "AT": (47.5162, 14.5501),   # Austria

    # Europe - Northern
    "SE": (60.1282, 18.6435),   # Sweden
    "NO": (60.4720, 8.4689),    # Norway
    "FI": (61.9241, 25.7482),   # Finland
    "DK": (56.2639, 9.5018),    # Denmark
    "IS": (64.9631, -19.0208),  # Iceland

    # Europe - Eastern
    "PL": (51.9194, 19.1451),   # Poland
    "CZ": (49.8175, 15.4730),   # Czech Republic
    "UA": (48.3794, 31.1656),   # Ukraine
    "RU": (61.5240, 105.3188),  # Russia
    "RO": (45.9432, 24.9668),   # Romania
    "HU": (47.1625, 19.5033),   # Hungary
    "SK": (48.6690, 19.6990),   # Slovakia
    "BG": (42.7339, 25.4858),   # Bulgaria
    "RS": (44.0165, 21.0059),   # Serbia
    "HR": (45.1, 15.2),         # Croatia
    "LT": (55.1694, 23.8813),   # Lithuania
    "LV": (56.8796, 24.6032),   # Latvia
    "EE": (58.5953, 25.0136),   # Estonia

    # Middle East
    "TR": (38.9637, 35.2433),   # Turkey
    "IL": (31.0461, 34.8516),   # Israel
    "AE": (23.4241, 53.8478),   # United Arab Emirates
    "SA": (23.8859, 45.0792),   # Saudi Arabia
    "IR": (32.4279, 53.6880),   # Iran
    "IQ": (33.2232, 43.6793),   # Iraq
    "JO": (30.5852, 36.2384),   # Jordan
    "KW": (29.3117, 47.4818),   # Kuwait
    "QA": (25.3548, 51.1839),   # Qatar
    "BH": (26.0667, 50.5577),   # Bahrain
    "OM": (21.4735, 55.9754),   # Oman

    # Asia - East
    "CN": (35.8617, 104.1954),  # China
    "JP": (36.2048, 138.2529),  # Japan
    "KR": (35.9078, 127.7669),  # South Korea
    "TW": (23.6978, 120.9605),  # Taiwan
    "HK": (22.3193, 114.1694),  # Hong Kong
    "MO": (22.1987, 113.5439),  # Macau

    # Asia - Southeast
    "SG": (1.3521, 103.8198),   # Singapore
    "TH": (15.8700, 100.9925),  # Thailand
    "VN": (14.0583, 108.2772),  # Vietnam
    "MY": (4.2105, 101.9758),   # Malaysia
    "PH": (12.8797, 121.7740),  # Philippines
    "ID": (-0.7893, 113.9213),  # Indonesia

    # Asia - South
    "IN": (20.5937, 78.9629),   # India
    "PK": (30.3753, 69.3451),   # Pakistan
    "BD": (23.6850, 90.3563),   # Bangladesh
    "LK": (7.8731, 80.7718),    # Sri Lanka

    # Oceania
    "AU": (-25.2744, 133.7751), # Australia
    "NZ": (-40.9006, 174.8860), # New Zealand

    # Africa
    "ZA": (-30.5595, 22.9375),  # South Africa
    "EG": (26.8206, 30.8025),   # Egypt
    "NG": (9.0820, 8.6753),     # Nigeria
    "KE": (-0.0236, 37.9062),   # Kenya
    "MA": (31.7917, -7.0926),   # Morocco
    "DZ": (28.0339, 1.6596),    # Algeria
    "TN": (33.8869, 9.5375),    # Tunisia
    "GH": (7.9465, -1.0232),    # Ghana
}
