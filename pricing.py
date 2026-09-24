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


def _model_vehicle(name):
    """Provide a useful body type for legacy list-style model catalogs."""
    value = name.lower()
    if any(word in value for word in ('van', 'voyager', 'odyssey', 'sienna', 'caravan', 'promaster', 'transit', 'sprinter')):
        return 'van' if 'mini' not in value else 'minivan'
    if any(word in value for word in ('truck', 'pickup', 'tacoma', 'tundra', 'ranger', 'f-150', 'f-250', 'f-350', 'silverado', 'sierra', 'frontier', 'titan', 'ridgeline')):
        return 'truck'
    if any(word in value for word in ('suv', 'cross', 'sporto', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'q3', 'q5', 'q7', 'q8', 'gl', 'gle', 'gla', 'glb', 'glc', 'gls', 'cayenne', 'macan', 'urus', 'defender', 'discovery', 'range rover', 'evoque', 'pilot', 'explorer', 'escape', 'tahoe', 'suburban', 'wrangler', 'cherokee', 'outback', 'forester', 'ascent')):
        return 'suv'
    if any(word in value for word in ('coupe', 'cayman', 'boxster', 'mustang', 'camaro', 'challenger', 'charger', 'corvette', 'miata', 'roadster', 'spyder')):
        return 'coupe'
    if any(word in value for word in ('hatch', 'golf', 'fit', 'mini', 'leaf', 'bolt', 'prius')):
        return 'hatchback'
    return 'sedan'


# The original catalog used lists for some brands. Convert those lists once so
# the API and browser receive {model: body_type}, rather than array indexes
# (which produced options such as 0, 1, 2 in the model dropdown).
for _brand, _models in list(MODELS.items()):
    if isinstance(_models, list):
        MODELS[_brand] = {model.strip(): _model_vehicle(model) for model in _models if model.strip()}


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
