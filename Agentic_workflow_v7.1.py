import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Tuple, TypedDict
from astrapy import DataAPIClient
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

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
app = FastAPI(title="Recommendation API", description="API for generating product recommendations using Astra DB", version="7.1")

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

# Define the workflow state
class WorkflowState(TypedDict):
    customer_id: str
    user_interests: dict
    user_vectors_with_interests: list  # List of (vector, InterestName, InterestDescription) tuples
    ad_url: str
    product: str
    similarity_score: float
    play_ad: bool
    top_recommendations: list

# Initialize Astra DB client
client = DataAPIClient(ASTRA_DB_TOKEN)
db = client.get_database_by_api_endpoint(ASTRA_DB_ENDPOINT)
userinterests_collection = db.get_collection(USERINTERESTS_COLLECTION)
advertisements_collection = db.get_collection(ADVERTISEMENTS_COLLECTION)

# Agent 1: CustomerID Selection Node
def agent_1_node(state: WorkflowState) -> WorkflowState:
    logger.info("Starting agent_1_node with UserId: %s", state["customer_id"])
    try:
        customer_id = state["customer_id"]
        if not customer_id:
            logger.error("No CustomerID provided")
            raise ValueError("No CustomerID provided")

        entries = list(userinterests_collection.find(
            {"UserId": customer_id},
            projection={"UserId": 1, "InterestName": 1, "InterestDescription": 1, "$vector": 1}
        ))
        if not entries:
            logger.error("No entries found for UserId: %s", customer_id)
            raise ValueError(f"No entries found for UserId: {customer_id}")

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
            raise ValueError(f"No valid $vector found for UserId: {customer_id}")

        logger.info("Retrieved data for CustomerID: %s, Interests: %s, Number of Vectors: %s", 
                    customer_id, user_interests, len(user_vectors_with_interests))
        return {
            "customer_id": customer_id,
            "user_interests": user_interests,
            "user_vectors_with_interests": user_vectors_with_interests,
            "ad_url": state.get("ad_url", ""),
            "product": "",
            "similarity_score": 0.0,
            "play_ad": False,
            "top_recommendations": []
        }

    except Exception as e:
        logger.error("Error in agent_1_node: %s", str(e))
        raise

# Agent 2: Advertisement Selection Node (Selection Approach Only)
def agent_2_node(state: WorkflowState) -> WorkflowState:
    logger.info("Starting agent_2_node with CustomerID: %s", state["customer_id"])
    try:
        all_recommendations = []
        for idx, (user_vector, interest_name, interest_description) in enumerate(state["user_vectors_with_interests"]):
            logger.info("Performing similarity search for vector %s/%s (Interest: %s, Description: %s)", 
                        idx + 1, len(state["user_vectors_with_interests"]), interest_name, interest_description)
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
            raise ValueError("No advertisements found across all vectors (Selection Approach)")

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
        ad_url = top_match["url"]
        product = top_match["product"]
        similarity_score = top_match["score"]
        logger.info("Top advertisement (vector %s, Selection Approach): %s, Product: %s, Similarity Score: %s", 
                    top_match["vector_idx"] + 1, ad_url, product, similarity_score)

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
            "customer_id": state["customer_id"],
            "user_interests": state["user_interests"],
            "user_vectors_with_interests": state["user_vectors_with_interests"],
            "ad_url": ad_url,
            "product": product,
            "similarity_score": similarity_score,
            "play_ad": False,  # Will be decided in agent_3_node
            "top_recommendations": top_recommendations
        }

    except Exception as e:
        logger.error("Error in agent_2_node: %s", str(e))
        raise

# Agent 3: Similarity Score Validation Node
def agent_3_node(state: WorkflowState) -> WorkflowState:
    logger.info("Starting agent_3_node, evaluating similarity score: %s", state["similarity_score"])
    SIMILARITY_THRESHOLD = 0.7
    DEFAULT_AD_URL = "https://www.youtube.com/watch?v=default_ad&autoplay=1&mute=1"
    DEFAULT_PRODUCT = "Generic Product"

    if state["similarity_score"] >= SIMILARITY_THRESHOLD:
        logger.info(
            "Similarity score %s meets threshold %s, approving advertisement (Selection Approach): %s",
            state["similarity_score"], SIMILARITY_THRESHOLD, state["ad_url"]
        )
        play_ad = True
    else:
        logger.warning(
            "Similarity score %s below threshold %s, using default advertisement (Selection Approach), interests: %s",
            state["similarity_score"], SIMILARITY_THRESHOLD, state["user_interests"]
        )
        play_ad = False
        state["ad_url"] = DEFAULT_AD_URL
        state["product"] = DEFAULT_PRODUCT
        state["similarity_score"] = 0.0
        state["top_recommendations"] = []

    return {
        "customer_id": state["customer_id"],
        "user_interests": state["user_interests"],
        "user_vectors_with_interests": state["user_vectors_with_interests"],
        "ad_url": state["ad_url"],
        "product": state["product"],
        "similarity_score": state["similarity_score"],
        "play_ad": play_ad,
        "top_recommendations": state["top_recommendations"]
    }

# Error Handler Node
def error_handler_node(state: WorkflowState) -> WorkflowState:
    logger.error("Error handler triggered: No valid CustomerID or recommendations found")
    return {
        "customer_id": state["customer_id"],
        "user_interests": state.get("user_interests", {}),
        "user_vectors_with_interests": state.get("user_vectors_with_interests", []),
        "ad_url": "https://www.youtube.com/watch?v=default_video&autoplay=1&mute=1",
        "product": "",
        "similarity_score": 0.0,
        "play_ad": False,
        "top_recommendations": []
    }

# Build the LangGraph workflow
workflow = StateGraph(WorkflowState)
workflow.add_node("agent_1", agent_1_node)
workflow.add_node("agent_2", agent_2_node)
workflow.add_node("agent_3", agent_3_node)
workflow.add_node("error_handler", error_handler_node)

workflow.add_edge(START, "agent_1")
workflow.add_conditional_edges(
    "agent_1",
    lambda state: "agent_2" if state["customer_id"] else "error_handler"
)
workflow.add_edge("agent_2", "agent_3")
workflow.add_edge("agent_3", END)
workflow.add_edge("error_handler", END)

# Compile the graph
graph = workflow.compile()

@app.get("/recommend/{user_id}", response_model=RecommendationResponse)
async def get_recommendations(user_id: str):
    """API endpoint to get product recommendations for a specified UserId using the Selection Approach."""
    try:
        logger.info("Received request for recommendations for UserId: %s", user_id)

        # Invoke the LangGraph workflow with the prescribed UserId
        result = graph.invoke({
            "customer_id": user_id,
            "user_interests": {},
            "user_vectors_with_interests": [],
            "ad_url": "",
            "product": "",
            "similarity_score": 0.0,
            "play_ad": False,
            "top_recommendations": []
        })

        # Check if the workflow failed to produce a valid result
        if not result["customer_id"] or not result["top_recommendations"]:
            logger.error("Workflow failed to produce valid recommendations for UserId: %s", user_id)
            raise HTTPException(status_code=404, detail="Failed to generate recommendations")

        # Construct the response
        response = {
            "customer_id": result["customer_id"],
            "user_interests": result["user_interests"],
            "selection_approach": {
                "top_ad": {
                    "url": result["ad_url"],
                    "product": result["product"],
                    "score": result["similarity_score"]
                },
                "top_recommendations": result["top_recommendations"]
            }
        }
        logger.info("Successfully generated recommendations for UserId: %s", user_id)
        return response

    except HTTPException as e:
        logger.error("HTTP error: %s", str(e))
        raise
    except Exception as e:
        logger.error("Error in recommendation process: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")