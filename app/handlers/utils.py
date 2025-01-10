import asyncio
from rapidfuzz import process
from rapidfuzz import fuzz

async def dynamic_search(keyword: str, products: list, min_similarity=90.0):
    names = [product["name"] for product in products]
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, lambda: process.extract(query=keyword.lower(),
                                                                        choices=names,
                                                                        scorer=fuzz.partial_ratio,
                                                                        limit=None))
    filtered_results = [
        {
            "product":product, "similarity":similarity
        } 
        for product, similarity, _ in results if similarity >= min_similarity
    ]
    
    seen_ids = set()
    enhanced_results = []
    for res in filtered_results:
        matching_products = [
            item for item in products if item["name"] == res["product"]
        ]
        for match in matching_products:
            if match["id"] not in seen_ids:
                enhanced_results.append({
                    "id": match["id"],
                    "name": match["name"],
                    "date": match["date"],
                    "remaining_pieces": match["remaining_pieces"],
                    "lost_pieces": match["lost_pieces"],
                    "sale_price": match["sale_price"],
                    "promotion_price": match["promotion_price"],
                    "similarity": res["similarity"]
                })
                seen_ids.add(match["id"])

    return enhanced_results