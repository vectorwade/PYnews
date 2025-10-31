def test_scraper_importable():
    import importlib
    spec = importlib.util.find_spec('scraper')
    assert spec is not None, "scraper module should be importable"
