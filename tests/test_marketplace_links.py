from snkrs.marketplace_links import goat_slug, listing_size, marketplace_links, search_name, stockx_product_link


def _urls(site):
    return [(o["by"], o["size_label"], o["url"]) for o in site["options"]]


def test_listing_size_reads_mens_womens_and_converts_eu():
    assert listing_size("US 10") == ("M", 10.0)
    assert listing_size("US M 10.5") == ("M", 10.5)
    assert listing_size("US W 11.5") == ("W", 11.5)
    assert listing_size("EU 44") == ("M", 10.0)
    assert listing_size("") is None


def test_search_name_drops_stockx_gender_tags():
    assert search_name("adidas Yeezy Desert Boot Oil Men's") == "adidas Yeezy Desert Boot Oil"
    assert search_name("Nike Blazer Mid 77 Vintage Light Bone Alabaster (Women's)") == "Nike Blazer Mid 77 Vintage Light Bone Alabaster"
    assert search_name("Nike D/MS/X Ghoswift Black Deep Royal Blue Bright Crimson Men's") == "Nike Ghoswift Black Deep Royal Blue Bright Crimson"
    assert search_name(None) is None


def test_model_search_finds_listings_titled_by_model_only():
    links = marketplace_links("BQ5108-002", "US 9.5", product_name="Nike D/MS/X Ghoswift Black Deep Royal Blue Bright Crimson Men's",
                              product_model="Nike D/MS/X Ghoswift")
    assert ("model", None, "https://www.vinted.com/catalog?search_text=Nike%20Ghoswift") in _urls(links["vinted"])
    assert [o["by"] for o in links["ebay"]["options"]] == ["code", "code", "name", "name", "model", "model"]


def test_links_by_code_and_name_at_the_size_and_all_sizes():
    links = marketplace_links("dv7006-001", "US W 12", product_name="Nike Blazer Mid 77 Vintage Light Bone Alabaster (Women's)")
    assert _urls(links["vinted"]) == [
        ("code", "US W 12", "https://www.vinted.com/catalog?search_text=DV7006-001&size_ids[]=63"),
        ("code", None, "https://www.vinted.com/catalog?search_text=DV7006-001"),
        ("name", "US W 12", "https://www.vinted.com/catalog?search_text=Nike%20Blazer%20Mid%2077%20Vintage%20Light%20Bone%20Alabaster&size_ids[]=63"),
        ("name", None, "https://www.vinted.com/catalog?search_text=Nike%20Blazer%20Mid%2077%20Vintage%20Light%20Bone%20Alabaster"),
    ]
    assert _urls(links["ebay"])[:2] == [
        ("code", "US W 12", "https://www.ebay.com/sch/i.html?_nkw=DV7006-001&US%2520Shoe%2520Size=12"),
        ("code", None, "https://www.ebay.com/sch/i.html?_nkw=DV7006-001"),
    ]
    # The main link is the most precise one
    assert (links["ebay"]["url"], links["ebay"]["size_label"]) == (_urls(links["ebay"])[0][2], "US W 12")


def test_without_a_name_only_style_code_searches():
    links = marketplace_links("EG6463", "US 10")
    assert [o["by"] for o in links["ebay"]["options"]] == ["code", "code"]
    assert links["vinted"]["url"] == "https://www.vinted.com/catalog?search_text=EG6463&size_ids[]=786"


def test_goat_needs_its_product_page_for_a_size():
    no_page = marketplace_links("EG6463", "US 10", product_name="adidas Yeezy Desert Boot Oil Men's")["goat"]
    assert (no_page["url"], no_page["size_specific"]) == ("https://www.goat.com/search?query=EG6463", False)
    assert _urls(no_page)[1] == ("name", None, "https://www.goat.com/search?query=adidas+Yeezy+Desert+Boot+Oil")

    page = marketplace_links("EG6463", "US 10", goat_url="https://www.goat.com/sneakers/yeezy-desert-boot-eg6463")["goat"]
    assert page["url"] == "https://www.goat.com/sneakers/yeezy-desert-boot-eg6463?tab=new&expandedSize=10"
    used = marketplace_links("EG6463", "US 10", used=True, goat_url="https://www.goat.com/sneakers/yeezy-desert-boot-eg6463")["goat"]
    assert "tab=used" in used["url"]
    assert goat_slug("https://www.goat.com/search?query=EG6463") is None


def test_unknown_size_only_offers_all_sizes():
    links = marketplace_links("EG6463", "US 30")
    assert _urls(links["vinted"]) == [("code", None, "https://www.vinted.com/catalog?search_text=EG6463")]
    assert links["vinted"]["size_specific"] is False


def test_stockx_links_open_on_the_size():
    url = "https://stockx.com/adidas-yeezy-desert-boot-oil"
    links = marketplace_links("EG6463", "US 10", stockx_url=url, stockx_size_key="M10", product_name="adidas Yeezy Desert Boot Oil Men's")
    assert (links["stockx"]["url"], links["stockx"]["size_label"]) == (url + "?size=10", "US M 10")
    # StockX Used searches by name first
    assert _urls(links["stockx_used"])[0] == ("name", "US M 10", "https://stockx.com/listings?s=adidas+Yeezy+Desert+Boot+Oil&listing-mens-shoe-size=US+M+10")

    women = marketplace_links("DC1165-001", "US W 8", stockx_url="https://stockx.com/nike-af1-w", stockx_size_key="W8")
    assert women["stockx"]["url"] == "https://stockx.com/nike-af1-w?size=8W"
    assert women["stockx_used"]["url"] == "https://stockx.com/listings?s=DC1165-001&listing-womens-shoe-size=US+W+8"

    # Not synced yet: the typed size still opens the right size; no product page means a search
    assert stockx_product_link("https://stockx.com/x", None, "US W 8.5") == "https://stockx.com/x?size=8.5W"
    assert marketplace_links("EG6463", "US 10")["stockx"]["size_specific"] is False
