import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Tuple
from astrapy import DataAPIClient
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('workflow.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set astrapy logging to INFO for debugging
logging.getLogger("astrapy").setLevel(logging.INFO)

# Load environment variables
load_dotenv()

# Verify environment variables
ASTRA_DB_ENDPOINT = os.getenv("ASTRA_DB_ENDPOINT")
ASTRA_DB_TOKEN = os.getenv("ASTRA_DB_TOKEN")
USERINTERESTS_COLLECTION = os.getenv("USERINTERESTS_COLLECTION", "userinterests")
ADVERTISEMENTS_COLLECTION = os.getenv("ADVERTISEMENTS_COLLECTION", "advertisements")

if not ASTRA_DB_ENDPOINT or not ASTRA_DB_TOKEN:
    logger.error("Missing required environment variables: ASTRA_DB_ENDPOINT or ASTRA_DB_TOKEN")
    raise ValueError("Missing required environment variables: ASTRA_DB_ENDPOINT or ASTRA_DB_TOKEN")

logger.info("Environment variables loaded")
logger.debug("ASTRA_DB_ENDPOINT: %s", ASTRA_DB_ENDPOINT)
logger.debug("ASTRA_DB_TOKEN: %s", ASTRA_DB_TOKEN)

# FastAPI app
app = FastAPI(title="Recommendation API", description="API for generating product recommendations using Astra DB", version="7.0")

# Pydantic models for response
class Recommendation(BaseModel):
    url: str
    product: str
    score: float

class SelectionApproachResponse(BaseModel):
    top_ad: Recommendation
    top_recommendations: List[Recommendation]

class RecommendationResponse(BaseModel):
    customer_id: str
    user_interests: Dict[str, str]
    selection_approach: SelectionApproachResponse

# Initialize Astra DB client
client = DataAPIClient(ASTRA_DB_TOKEN)
db = client.get_database_by_api_endpoint(ASTRA_DB_ENDPOINT)
userinterests_collection = db.get_collection(USERINTERESTS_COLLECTION)
advertisements_collection = db.get_collection(ADVERTISEMENTS_COLLECTION)

def get_user_data(user_id: str) -> Tuple[str, dict, list]:
    """Retrieve user data (ID, interests, vectors with interest details) for the specified UserId."""
    logger.info("Fetching data for specified UserId: %s", user_id)
    entries = list(userinterests_collection.find(
        {"UserId": user_id},
        projection={"UserId": 1, "InterestName": 1, "InterestDescription": 1, "$vector": 1}
    ))
    if not entries:
        logger.error("No entries found for UserId: %s", user_id)
        raise HTTPException(status_code=404, detail=f"No entries found for UserId: {user_id}")

    customer_id = user_id
    logger.info("Found entries for UserId: %s", customer_id)

    user_interests = {
        "InterestName": ", ".join(set(entry.get("InterestName", "") for entry in entries)),
        "InterestDescription": ", ".join(set(entry.get("InterestDescription", "") for entry in entries))
    }
    user_vectors_with_interests = [
        (entry.get("$vector", []), entry.get("InterestName", ""), entry.get("InterestDescription", ""))
        for entry in entries if entry.get("$vector", [])
    ]
    if not user_vectors_with_interests:
        logger.error("No valid $vector found for UserId: %s", customer_id)
        raise HTTPException(status_code=400, detail=f"No valid $vector found for UserId: {customer_id}")

    return customer_id, user_interests, user_vectors_with_interests

def perform_selection_approach(user_vectors_with_interests: List[Tuple[List[float], str, str]]) -> List[Dict]:
    """Perform the Selection Approach for recommendation."""
    logger.info("Evaluating Selection Approach...")
    all_recommendations = []
    for idx, (user_vector, interest_name, interest_description) in enumerate(user_vectors_with_interests):
        logger.info("Performing similarity search for vector %s/%s (Interest: %s, Description: %s)", 
                    idx + 1, len(user_vectors_with_interests), interest_name, interest_description)
        top_ads = list(advertisements_collection.find(
            {},
            sort={"$vector": user_vector},
            limit=10,
            include_similarity=True,
            projection={"product": 1, "video_link": 1},
        ))
        if not top_ads:
            logger.warning("No advertisements found for vector %s", idx + 1)
            continue

        seen_products = set()
        vector_recommendations = []
        for ad in top_ads:
            product = ad.get("product", "")
            if product in seen_products:
                logger.warning("Duplicate product found in search results for vector %s: %s", idx + 1, product)
                continue
            ad_url = ad.get("video_link", "") + "&autoplay=1&mute=1" if ad.get("video_link") else ""
            if ad_url:
                vector_recommendations.append({
                    "url": ad_url,
                    "product": product,
                    "score": ad.get("$similarity", 0.0),
                    "vector_idx": idx
                })
                seen_products.add(product)

        if vector_recommendations:
            logger.info("Top recommendations for vector %s (Interest: %s, Description: %s):", 
                        idx + 1, interest_name, interest_description)
            for rec in vector_recommendations[:5]:
                logger.info("  - URL: %s, Product: %s, Score: %s", rec["url"], rec["product"], rec["score"])
        all_recommendations.extend(vector_recommendations)

    if not all_recommendations:
        logger.error("No advertisements found across all vectors (Selection Approach)")
        raise HTTPException(status_code=404, detail="No advertisements found across all vectors (Selection Approach)")

    return all_recommendations

def select_top_recommendation(all_recommendations: List[Dict]) -> Dict:
    """Select the highest-scoring ad and top 5 recommendations after deduplication."""
    seen_products = set()
    deduplicated_recommendations = []
    all_recommendations.sort(key=lambda x: (x["score"], -x["vector_idx"]), reverse=True)
    for rec in all_recommendations:
        product = rec["product"]
        if product in seen_products:
            logger.warning("Duplicate product found across all recommendations: %s", product)
            continue
        deduplicated_recommendations.append(rec)
        seen_products.add(product)

    top_match = deduplicated_recommendations[0]
    logger.info("Top advertisement (vector %s, Selection Approach): %s, Product: %s, Similarity Score: %s", 
                top_match["vector_idx"] + 1, top_match["url"], top_match["product"], top_match["score"])

    seen_urls = set()
    top_recommendations = [{
        "url": top_match["url"],
        "product": top_match["product"],
        "score": top_match["score"]
    }]
    seen_urls.add(top_match["url"])

    for rec in deduplicated_recommendations[1:]:
        if rec["url"] not in seen_urls and len(top_recommendations) < 5:
            top_recommendations.append({
                "url": rec["url"],
                "product": rec["product"],
                "score": rec["score"]
            })
            seen_urls.add(rec["url"])

    logger.info("Top 5 aggregated recommendations (Selection Approach):")
    for rec in top_recommendations:
        logger.info("  - URL: %s, Product: %s, Score: %s", rec["url"], rec["product"], rec["score"])

    return {
        "top_ad": {
            "url": top_match["url"],
            "product": top_match["product"],
            "score": top_match["score"]
        },
        "top_recommendations": top_recommendations
    }

@app.get("/recommend/{user_id}", response_model=RecommendationResponse)
async def get_recommendations(user_id: str):
    """API endpoint to get product recommendations for a specified UserId using the Selection Approach."""
    try:
        logger.info("Received request for recommendations for UserId: %s", user_id)

        # Step 1: Retrieve user data
        customer_id, user_interests, user_vectors_with_interests = get_user_data(user_id)

        # Step 2: Perform Selection Approach
        all_recommendations = perform_selection_approach(user_vectors_with_interests)

        # Step 3: Select top recommendation
        selection_result = select_top_recommendation(all_recommendations)

        # Construct the response
        response = {
            "customer_id": customer_id,
            "user_interests": user_interests,
            "selection_approach": selection_result
        }
        logger.info("Successfully generated recommendations for UserId: %s", user_id)
        return response

    except HTTPException as e:
        logger.error("HTTP error: %s", str(e))
        raise
    except Exception as e:
        logger.error("Error in recommendation process: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")