from app.services.docs import docs_lookup, set_docs_cache


def test_docs_lookup_basic():
    html = """
    <html><body>
    <h2>ACC</h2>
    <p>IMU accelerometer data. AccX m/s/s acceleration along X axis</p>
    <h2>AHR2</h2>
    <p>Backup AHRS data. Alt m Estimated altitude</p>
    </body></html>
    """
    set_docs_cache(html)
    out = docs_lookup("AHR2")
    assert out["snippets"], "should return at least one snippet"
    assert any("AHR2" in s.get("title", "") for s in out["snippets"]) or any("AHR2" in s.get("excerpt", "") for s in out["snippets"])    


