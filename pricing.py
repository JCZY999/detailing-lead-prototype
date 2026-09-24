"""Fictional, tax-inclusive demo prices in USD; not market price data."""
from car_models import MODELS
BASE = {'interior': 149, 'exterior': 89, 'full': 219}
# Interior, exterior, full service surcharges.
VEHICLES = dict(zip(
    ('coupe', 'sedan', 'hatchback', 'wagon', 'crossover', 'suv', 'truck', 'van', 'minivan'),
    ((0, 0, 0), (0, 0, 0), (0, 0, 0), (15, 10, 20), (20, 10, 25),
     (35, 20, 45), (25, 25, 40), (50, 30, 65), (45, 25, 60))))
TIERS = {'standard': (0, 0, 0), 'premium': (20, 15, 30), 'specialty': (40, 30, 60)}
BRANDS = {brand: tier for tier, brands in {
    'standard': 'Toyota,Honda,Ford,Chevrolet,Nissan,Hyundai,Kia,Mazda,Subaru,Volkswagen,Jeep,Ram,GMC,Buick,Mitsubishi',
    'premium': 'BMW,Mercedes-Benz,Audi,Lexus,Acura,Infiniti,Genesis,Volvo,Cadillac,Lincoln,Tesla,Polestar',
    'specialty': 'Porsche,Land Rover,Jaguar,Maserati,Bentley,Ferrari,Lamborghini,Aston Martin,Rolls-Royce',
}.items() for brand in brands.split(',')}
ALIASES = {'mercedes': 'Mercedes-Benz', 'benz': 'Mercedes-Benz', 'vw': 'Volkswagen',
           'chevy': 'Chevrolet', 'range rover': 'Land Rover'}

def quote(profile):
    if not all(profile.get(k) for k in ('service', 'vehicle', 'brand')):
        return None
    if profile['brand'] not in BRANDS:
        return None
    service = profile['service']
    index = list(BASE).index(service)
    tier = BRANDS[profile['brand']]
    base, vehicle, brand = BASE[service], VEHICLES[profile['vehicle']][index], TIERS[tier][index]
    return {'base_usd': base, 'vehicle_adjustment_usd': vehicle, 'brand_adjustment_usd': brand,
            'total_usd': base + vehicle + brand, 'brand_tier': tier,
            'currency': 'USD', 'demo': True, 'version': 'demo-v2'}

def catalog():
    return {'notice': 'Fictional demo prices, including tax. Not market rates. Unlisted brands require a manual quote.',
            'base_prices': BASE, 'vehicle_adjustments': {k: dict(zip(BASE, v)) for k, v in VEHICLES.items()},
            'brand_adjustments': {k: dict(zip(BASE, v)) for k, v in TIERS.items()},
            'brands': BRANDS, 'models': MODELS}
