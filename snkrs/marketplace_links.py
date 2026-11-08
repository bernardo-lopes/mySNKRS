"""
Links to StockX, StockX Used, GOAT, eBay and Vinted filtered to your size. When a site can't be filtered to the size
(unknown size, or no GOAT product page known), the link falls back to all sizes and says so.
"""

import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote, urlencode

from .models import SizeSystem
from .size_converter import SizeConverter

# Vinted size filter ids (vinted.com, footwear), read from its catalog size filter
VINTED_MEN = {
    5: 776, 5.5: 777, 6: 778, 6.5: 779, 7: 780, 7.5: 781, 8: 782, 8.5: 783, 9: 784, 9.5: 785,
    10: 786, 10.5: 787, 11: 788, 11.5: 789, 12: 790, 12.5: 791, 13: 792, 13.5: 793, 14: 794,
    14.5: 795, 15: 1190, 15.5: 1621, 16: 1191, 16.5: 1327, 17: 1622, 17.5: 1623,
}
VINTED_WOMEN = {
    3: 1364, 3.5: 1580, 4: 55, 4.5: 1195, 5: 56, 5.5: 1196, 6: 57, 6.5: 1197, 7: 58, 7.5: 1198,
    8: 59, 8.5: 1199, 9: 60, 9.5: 1200, 10: 61, 10.5: 1201, 11: 62, 11.5: 1579, 12: 63,
    12.5: 1573, 13: 1574, 13.5: 1575, 14: 1576, 14.5: 1577, 15: 1578,
}


def _num(v: float) -> str:
    return f"{v:g}"


def listing_size(size_input: str) -> Optional[Tuple[str, float]]:
    """("W", 8.5) or ("M", 10.0) for the size you typed; EU/UK/cm are converted to US men's."""
    system, value = SizeConverter.parse_size_string(size_input or "")
    if value is None:
        return None
    if system == SizeSystem.US_WOMEN:
        return "W", value
    if system == SizeSystem.US_MEN:
        return "M", value
    return "M", SizeConverter.normalize(size_input)["us_m"]


def stockx_size_param(size_key: Optional[str] = None, size_input: Optional[str] = None) -> Optional[str]:
    """StockX's ?size= value: "10" for men's and unisex, "8.5W" for women's, "5Y" for youth.
    Uses the synced size key ("M10", "W8.5") when there is one, else the size you typed."""
    if size_key and size_key[0] in "MWY":
        return size_key[1:] + ("" if size_key[0] == "M" else size_key[0])
    size = listing_size(size_input or "")
    return (_num(size[1]) + ("W" if size[0] == "W" else "")) if size else None


def stockx_product_link(product_url: Optional[str], size_key: Optional[str] = None, size_input: Optional[str] = None) -> Optional[str]:
    """A StockX product page opened on your size; search pages and unknown sizes are left as they are."""
    if not product_url or "/search" in product_url:
        return product_url
    param = stockx_size_param(size_key, size_input)
    return f"{product_url.split('?')[0]}?{urlencode({'size': param})}" if param else product_url


def goat_slug(url: Optional[str]) -> Optional[str]:
    """Product slug from a GOAT product URL like https://www.goat.com/sneakers/yeezy-desert-boot-eg6463."""
    marker = "goat.com/sneakers/"
    if not url or marker not in url:
        return None
    slug = url.split(marker, 1)[1].split("?")[0].strip("/")
    return slug or None


def search_name(product_name: Optional[str]) -> Optional[str]:
    """A StockX name as sellers would write it: without StockX's "Men's" / "(Women's)" tags and
    collab marks like "D/MS/X" ("Nike D/MS/X Ghoswift" -> "Nike Ghoswift")."""
    if not product_name:
        return None
    name = re.sub(r"\s*\(Women's\)|\s+Men's$", "", product_name)
    name = " ".join(w for w in name.split() if "/" not in w)
    return name or None


def marketplace_links(
    sku: str,
    size_input: str,
    used: bool = False,
    goat_url: Optional[str] = None,
    stockx_url: Optional[str] = None,
    stockx_size_key: Optional[str] = None,
    product_name: Optional[str] = None,
    product_model: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Links per marketplace: {"url", "size_specific", "size_label", "options"}.

    "url" is the most precise link (your size, by style code; StockX Used by name). "options"
    lists every search the site allows, by style code and by product name, at your size and
    across all sizes, since not every seller lists the style code or a size filter can come up empty.
    "model" searches the model without its colorway ("Nike Ghoswift"), as many sellers title listings:
    [{"by": "code"|"name"|"model", "size_label": "US M 10" or None for all sizes, "url"}]."""
    sku = sku.strip().upper()
    size = listing_size(size_input)
    label = f"US {size[0]} {_num(size[1])}" if size else None
    name, model = search_name(product_name), search_name(product_model)
    terms = [("code", sku)] + ([("name", name)] if name else []) + ([("model", model)] if model and model != name else [])

    def option(by: str, url: str, sized: bool) -> Dict[str, Any]:
        return {"by": by, "size_label": label if sized else None, "url": url}

    def site(options) -> Dict[str, Any]:
        main = options[0]
        return {"url": main["url"], "size_specific": bool(main["size_label"]), "size_label": main["size_label"], "options": options}

    # GOAT: only its product page opens on a size; search covers all sizes
    goat_options = []
    slug = goat_slug(goat_url)
    if slug and size:
        goat_options.append(option("code", f"https://www.goat.com/sneakers/{slug}?" + urlencode({"tab": "used" if used else "new", "expandedSize": _num(size[1])}), True))
    goat_options += [option(by, "https://www.goat.com/search?" + urlencode({"query": q}), False) for by, q in terms]

    # eBay's "US Shoe Size" filter; the double-encoded space is how eBay writes aspect names in URLs
    def ebay_url(q: str, sized: bool) -> str:
        params = {"_nkw": q}
        if sized:
            params["US%2520Shoe%2520Size"] = _num(size[1])
        return "https://www.ebay.com/sch/i.html?" + urlencode(params, safe="%")

    vinted_id = (VINTED_WOMEN if size[0] == "W" else VINTED_MEN).get(size[1]) if size else None

    def vinted_url(q: str, sized: bool) -> str:
        return "https://www.vinted.com/catalog?search_text=" + quote(q) + (f"&size_ids[]={vinted_id}" if sized else "")

    # StockX Listings: its second-hand marketplace. Its search is loose, so the name comes first.
    def stockx_used_url(q: str, sized: bool) -> str:
        params = {"s": q}
        if sized:
            params["listing-womens-shoe-size" if size[0] == "W" else "listing-mens-shoe-size"] = label
        return "https://stockx.com/listings?" + urlencode(params)

    def sized_and_all(make_url, can_size: bool, order) -> list:
        return [option(by, make_url(q, sized), sized) for by, q in order for sized in ([True, False] if can_size else [False])]

    stockx_page = stockx_url or "https://stockx.com/search?" + urlencode({"s": sku})
    stockx_sized = stockx_product_link(stockx_page, stockx_size_key, size_input)

    return {
        "stockx": site([option("code", stockx_sized, stockx_sized != stockx_page)]),
        "stockx_used": site(sized_and_all(stockx_used_url, bool(size), terms[1:] + terms[:1])),
        "goat": site(goat_options),
        "ebay": site(sized_and_all(ebay_url, bool(size), terms)),
        "vinted": site(sized_and_all(vinted_url, bool(vinted_id), terms)),
    }
