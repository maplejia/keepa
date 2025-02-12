import time
import sys
import os

import numpy as np
import pytest

import keepa
import datetime

py2 = sys.version_info.major == 2
py37 = sys.version_info.major == 3 and sys.version_info.minor == 7

# slow down number of offers for testing
keepa.interface.REQLIM = 2

try:
    path = os.path.dirname(os.path.realpath(__file__))
    keyfile = os.path.join(path, 'key')
    weak_keyfile = os.path.join(path, 'weak_key')
except:
    keyfile = '/home/alex/books/keepa/tests/key'
    weak_keyfile = '/home/alex/books/keepa/tests/weak_key'

if os.path.isfile(keyfile):
    with open(keyfile) as f:
        TESTINGKEY = f.read()
    with open(weak_keyfile) as f:
        WEAKTESTINGKEY = f.read()
else:
    # from travis-ci or appveyor
    TESTINGKEY = os.environ.get('KEEPAKEY')
    WEAKTESTINGKEY = os.environ.get('WEAKKEEPAKEY')


# this key returns "payment required"
DEADKEY = '8ueigrvvnsp5too0atlb5f11veinerkud47p686ekr7vgr9qtj1t1tle15fffkkm'


# harry potter book ISBN
PRODUCT_ASIN = '0439064872'

# ASINs of a bunch of chairs
# categories = API.search_for_categories('chairs')
# asins = []
# for category in categories:
#     asins.extend(API.best_sellers_query(category))
# PRODUCT_ASINS = asins[:40]

PRODUCT_ASINS = ['B00IAPNWG6', 'B01CUJMSB2', 'B01CUJMRLI',
                 'B00BMPT7CE', 'B00IAPNWE8', 'B0127O51FK',
                 'B01CUJMT3E', 'B01A5ZIXKI', 'B00KQPBF1W',
                 'B000J3UZ58', 'B00196LLDO', 'B002VWK2EE',
                 'B00E2I3BPM', 'B004FRSUO2', 'B00CM1TJ1G',
                 'B00VS4514C', 'B075G1B1PK', 'B00R9EAH8U',
                 'B004L2JKTU', 'B008SIDW2E', 'B078XL8CCW',
                 'B000VXII46', 'B07D1CJ8CK', 'B07B5HZ7D9',
                 'B002VWK2EO', 'B000VXII5A', 'B004N1AA5W',
                 'B002VWKP3W', 'B00CM9OM0G', 'B002VWKP4G',
                 'B004N18JDC', 'B07MDHF4CP', 'B002VWKP3C',
                 'B07FTVSNL2', 'B002VWKP5A', 'B002O0LBFW',
                 'B07BM1Q64Q', 'B004N18JM8', 'B004N1AA02',
                 'B002VWK2EY']


# open connection to keepa
API = keepa.Keepa(TESTINGKEY)
assert API.tokens_left
assert API.time_to_refill >= 0



def test_invalidkey():
    with pytest.raises(Exception):
        keepa.Api('thisisnotavalidkey')


def test_deadkey():
    with pytest.raises(Exception):
        keepa.Api(DEADKEY)

# @pytest.mark.skipif(not py37, reason="Too much throttling for travisCI")
# def test_throttling():
#     api = keepa.Keepa(WEAKTESTINGKEY)
#     keepa.interface.REQLIM = 20

#     # exaust tokens
#     while api.tokens_left > 0:
#         api.query(PRODUCT_ASINS[:5])

#     # this must trigger a wait...
#     t_start = time.time()
#     products = api.query(PRODUCT_ASINS)
#     assert (time.time() - t_start) > 1
#     keepa.interface.REQLIM = 2


def test_productquery_nohistory():
    pre_update_tokens = API.tokens_left
    request = API.query(PRODUCT_ASIN, history=False)
    assert API.tokens_left != pre_update_tokens

    product = request[0]
    assert product['csv'] is None
    assert product['asin'] == PRODUCT_ASIN


def test_not_an_asin():
    with pytest.raises(Exception):
        asins = ['0000000000', '000000000x']
        request = API.query(asins)

def test_isbn13():
    isbn13 = '9780786222728'
    request = API.query(isbn13, product_code_is_asin=False, history=False)


def test_productquery_update():
    request = API.query(PRODUCT_ASIN, update=0, stats=90, rating=True)
    product = request[0]

    # should be live data
    now = datetime.datetime.now()
    delta = now - product['data']['USED_time'][-1]
    assert delta.days <= 30

    # check for empty arrays
    history = product['data']
    for key in history:
        assert history[key].any()

        # should be a key pair
        if 'time' not in key:
            assert history[key].size == history[key + '_time'].size

    # check for stats
    assert 'stats' in product

    # no offers requested by default
    assert product['offers'] is None


def test_productquery_offers():
    request = API.query(PRODUCT_ASIN, offers=20)
    product = request[0]

    offers = product['offers']
    for offer in offers:
        assert offer['lastSeen']
        assert not len(offer['offerCSV']) % 3

    # also test offer conversion
    offer = offers[1]
    times, prices = keepa.convert_offer_history(offer['offerCSV'])
    assert times.dtype == datetime.datetime
    assert prices.dtype == np.double
    assert len(times)
    assert len(prices)


def test_productquery_offers_invalid():
    with pytest.raises(ValueError):
        request = API.query(PRODUCT_ASIN, offers=2000)


def test_productquery_offers_multiple():
    products = API.query(PRODUCT_ASINS)

    asins = np.unique([product['asin'] for product in products])
    assert len(asins) == len(PRODUCT_ASINS)
    assert np.in1d(asins, PRODUCT_ASINS).all()


def test_domain():
    request = API.query(PRODUCT_ASIN, history=False, domain='DE')
    product = request[0]
    assert product['asin'] == PRODUCT_ASIN


def test_invalid_domain():
    with pytest.raises(ValueError):
        request = API.query(PRODUCT_ASIN, history=False, domain='XX')


def test_bestsellers():
    category = '402333011'
    asins = API.best_sellers_query(category)
    valid_asins = keepa.format_items(asins)
    assert len(asins) == valid_asins.size


def test_categories():
    categories = API.search_for_categories('chairs')
    catids = list(categories.keys())
    for catid in catids:
        assert 'chairs' in categories[catid]['name'].lower()


def test_categorylookup():
    categories = API.category_lookup(0)
    for cat_id in categories:
        assert categories[cat_id]['name']


def test_invalid_category():
    with pytest.raises(Exception):
        API.category_lookup(-1)


def test_stock():
    request = API.query(PRODUCT_ASIN, history=False, stock=True,
                        offers=20)

    # all live offers must have stock
    product = request[0]
    assert product['offersSuccessful']
    live = product['liveOffersOrder']
    for offer in product['offers']:
        if offer['offerId'] in live:
            if 'stockCSV' in offer:
                assert offer['stockCSV'][-1]


def test_keepatime():
    keepa_st_ordinal = datetime.datetime(2011, 1, 1)
    assert keepa_st_ordinal == keepa.keepa_minutes_to_time(0)
    assert keepa.keepa_minutes_to_time(0, to_datetime=False)


@pytest.mark.skipif(py2, reason="Requires python 3.5+ for testing")
def test_plotting():
    request = API.query(PRODUCT_ASIN, history=True)
    product = request[0]
    keepa.plot_product(product, show=False)


@pytest.mark.skipif(py2, reason="Requires python 3.5+ for testing")
def test_empty():
    import matplotlib.pyplot as plt
    plt.close('all')
    products = API.query(['B01I6KT07E', 'B01G5BJHVK', 'B017LJP1MO'])
    with pytest.raises(Exception):
        keepa.plot_product(products[0], show=False)


def test_seller_query():
    seller_id = 'A2L77EE7U53NWQ'
    seller_info = API.seller_query(seller_id)
    assert len(seller_info) == 1
    assert seller_id in seller_info
    

def test_seller_query_list():
    seller_id = ['A2L77EE7U53NWQ', 'AMMEOJ0MXANX1']
    seller_info = API.seller_query(seller_id)
    assert len(seller_info) == len(seller_id)
    assert set(seller_info).issubset(seller_id)


def test_seller_query_long_list():
    seller_id = ['A2L77EE7U53NWQ']*200
    with pytest.raises(RuntimeError):
        seller_info = API.seller_query(seller_id)


def test_product_finder_query():
    product_parms = {'author': 'jim butcher'}
    asins = API.product_finder(product_parms)
    assert asins
