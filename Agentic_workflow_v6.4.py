import requests
import webbrowser
import re
import os
import random
import logging
import numpy as np
from dotenv import load_dotenv
from typing import TypedDict, List, Tuple
from langgraph.graph import StateGraph, START, END
from astrapy import DataAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('D:\\Synapsewerx_Projects\\Customer_Recommendations\\workflow.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set astrapy logging to INFO for debugging, revert to WARNING after confirming
logging.getLogger("astrapy").setLevel(logging.INFO)

# Load environment variables
load_dotenv(r"D:\Synapsewerx_Projects\Customer_Recommendations\.env")

# Verify environment variables at module level
ASTRA_DB_ENDPOINT = os.getenv("ASTRA_DB_ENDPOINT")
ASTRA_DB_TOKEN = os.getenv("ASTRA_DB_TOKEN")

logger.info("Environment variables loaded")
logger.debug("ASTRA_DB_ENDPOINT: %s", ASTRA_DB_ENDPOINT)
logger.debug("ASTRA_DB_TOKEN: %s", ASTRA_DB_TOKEN)

# Define the workflow state
class WorkflowState(TypedDict):
    customer_id: str
    ad_url: str
    ad_url_agg: str  # For aggregated approach
    user_interests: dict
    user_vectors: list  # Store multiple vectors per UserId (for Aggregation Approach)
    user_vectors_with_interests: list  # Store list of (vector, InterestName, InterestDescription) tuples
    user_vector_agg: list  # Store aggregated vector
    product: str
    product_agg: str  # For aggregated approach
    similarity_score: float
    similarity_score_agg: float  # For aggregated approach
    play_ad: bool
    play_ad_agg: bool  # For aggregated approach
    top_recommendations: list
    top_recommendations_agg: list  # For aggregated approach

# Placeholder for facial recognition
def dummy_facial_recognition() -> str:
    logger.info("Simulating facial recognition")
    return "003dL000008HU8rQAG"

# Function to aggregate vectors
def aggregate_vectors(vectors: List[List[float]]) -> List[float]:
    """Aggregate multiple vectors into a single vector by averaging."""
    if not vectors:
        return []
    try:
        # Convert list of vectors to numpy array and compute mean
        vectors_array = np.array(vectors)
        aggregated_vector = np.mean(vectors_array, axis=0).tolist()
        logger.debug("Aggregated vector (first 5 dims): %s", aggregated_vector[:5])
        return aggregated_vector
    except Exception as e:
        logger.error("Error aggregating vectors: %s", str(e))
        return []

# Function to get a random user ID from the userinterests collection
def get_random_user_id(collection) -> Tuple[str, dict, list, list, list]:
    """Get a random user ID, their interests, vectors, vectors with interest details, and aggregated vector."""
    try:
        # Get total document count with upper_bound for Astra DB compatibility
        total_docs = collection.count_documents({}, upper_bound=1000)
        logger.info("Total documents in userinterests: %s", total_docs)
        
        if total_docs == 0:
            logger.error("No documents found in userinterests collection")
            return None, None, [], [], []

        # Method 1: Skip-based approach WITH sort clause as required by Astra DB
        try:
            # Use a smaller skip value to avoid timeouts (skip at most 100 docs)
            max_skip = min(total_docs - 1, 100) if total_docs > 1 else 0
            skip = random.randint(0, max_skip)
            logger.info("Using optimized skip-based approach with skip=%s", skip)
            
            # Get a batch of documents with sort clause (required by Astra DB for skip)
            batch_size = min(10, total_docs - skip)
            documents = list(collection.find(
                {},
                projection={"UserId": 1, "InterestName": 1, "InterestDescription": 1, "$vector": 1},
                sort={"UserId": 1},  # Sort by UserId to satisfy Astra DB requirement
                skip=skip,
                limit=batch_size
            ))
            
            if documents:
                # Choose a random document and fetch all entries for that UserId
                random_doc = random.choice(documents)
                customer_id = random_doc["UserId"]
                all_entries = list(collection.find(
                    {"UserId": customer_id},
                    projection={"UserId": 1, "InterestName": 1, "InterestDescription": 1, "$vector": 1}
                ))
                
                if not all_entries:
                    logger.error("No entries found for UserId: %s", customer_id)
                    return None, None, [], [], []
                
                # Aggregate interests and collect all vectors with interest details
                user_interests = {
                    "InterestName": ", ".join(set(entry.get("InterestName", "") for entry in all_entries)),
                    "InterestDescription": ", ".join(set(entry.get("InterestDescription", "") for entry in all_entries))
                }
                user_vectors = [entry.get("$vector", []) for entry in all_entries]
                user_vectors = [v for v in user_vectors if v]  # Filter out empty vectors
                # Create list of (vector, InterestName, InterestDescription) tuples
                user_vectors_with_interests = [
                    (entry.get("$vector", []), entry.get("InterestName", ""), entry.get("InterestDescription", ""))
                    for entry in all_entries if entry.get("$vector", [])
                ]
                
                if not user_vectors:
                    logger.error("No valid $vector found for UserId: %s", customer_id)
                    return customer_id, user_interests, [], [], []
                
                # Aggregate vectors
                user_vector_agg = aggregate_vectors(user_vectors)
                if not user_vector_agg:
                    logger.error("Failed to aggregate vectors for UserId: %s", customer_id)
                    return customer_id, user_interests, user_vectors, [], []
                
                return customer_id, user_interests, user_vectors, user_vectors_with_interests, user_vector_agg
        except Exception as e:
            logger.warning("Optimized skip approach failed: %s, trying pagination approach", str(e))

        # Method 2: Get multiple pages and choose randomly (no skip)
        try:
            page_docs = list(collection.find(
                {},
                projection={"UserId": 1, "InterestName": 1, "InterestDescription": 1, "$vector": 1},
                limit=50
            ))
            
            if page_docs:
                random_doc = random.choice(page_docs)
                customer_id = random_doc["UserId"]
                all_entries = list(collection.find(
                    {"UserId": customer_id},
                    projection={"UserId": 1, "InterestName": 1, "InterestDescription": 1, "$vector": 1}
                ))
                
                if not all_entries:
                    logger.error("No entries found for UserId: %s", customer_id)
                    return None, None, [], [], []
                
                user_interests = {
                    "InterestName": ", ".join(set(entry.get("InterestName", "") for entry in all_entries)),
                    "InterestDescription": ", ".join(set(entry.get("InterestDescription", "") for entry in all_entries))
                }
                user_vectors = [entry.get("$vector", []) for entry in all_entries]
                user_vectors = [v for v in user_vectors if v]
                user_vectors_with_interests = [
                    (entry.get("$vector", []), entry.get("InterestName", ""), entry.get("InterestDescription", ""))
                    for entry in all_entries if entry.get("$vector", [])
                ]
                
                if not user_vectors:
                    logger.error("No valid $vector found for UserId: %s", customer_id)
                    return customer_id, user_interests, [], [], []
                
                user_vector_agg = aggregate_vectors(user_vectors)
                if not user_vector_agg:
                    logger.error("Failed to aggregate vectors for UserId: %s", customer_id)
                    return customer_id, user_interests, user_vectors, [], []
                
                return customer_id, user_interests, user_vectors, user_vectors_with_interests, user_vector_agg
        except Exception as e:
            logger.warning("Pagination approach failed: %s, trying simplified approach", str(e))

        # Method 3: Last resort - just get the first document
        try:
            doc = collection.find_one(
                {},
                projection={"UserId": 1, "InterestName": 1, "InterestDescription": 1, "$vector": 1}
            )
            
            if doc:
                customer_id = doc["UserId"]
                all_entries = list(collection.find(
                    {"UserId": customer_id},
                    projection={"UserId": 1, "InterestName": 1, "InterestDescription": 1, "$vector": 1}
                ))
                
                if not all_entries:
                    logger.error("No entries found for UserId: %s", customer_id)
                    return None, None, [], [], []
                
                user_interests = {
                    "InterestName": ", ".join(set(entry.get("InterestName", "") for entry in all_entries)),
                    "InterestDescription": ", ".join(set(entry.get("InterestDescription", "") for entry in all_entries))
                }
                user_vectors = [entry.get("$vector", []) for entry in all_entries]
                user_vectors = [v for v in user_vectors if v]
                user_vectors_with_interests = [
                    (entry.get("$vector", []), entry.get("InterestName", ""), entry.get("InterestDescription", ""))
                    for entry in all_entries if entry.get("$vector", [])
                ]
                
                if not user_vectors:
                    logger.error("No valid $vector found for UserId: %s", customer_id)
                    return customer_id, user_interests, [], [], []
                
                user_vector_agg = aggregate_vectors(user_vectors)
                if not user_vector_agg:
                    logger.error("Failed to aggregate vectors for UserId: %s", customer_id)
                    return customer_id, user_interests, user_vectors, [], []
                
                return customer_id, user_interests, user_vectors, user_vectors_with_interests, user_vector_agg
        except Exception as e:
            logger.error("All approaches failed: %s", str(e))
            
        return None, None, [], [], []
            
    except Exception as e:
        logger.error("Error in get_random_user_id: %s", str(e))
        return None, None, [], [], []

# Agent 1: CustomerID Selection Node
def agent_1_node(state: WorkflowState) -> WorkflowState:
    logger.info("Starting agent_1_node")
    try:
        print("\nSelect Agent 1 mode:")
        print("[1] Random UserId from userinterests collection")
        print("[2] Facial Recognition (placeholder)")
        choice = input("Enter choice (1 or 2): ").strip()
        logger.info("User selected mode: %s", choice)

        if choice == "1":
            if not ASTRA_DB_ENDPOINT or not ASTRA_DB_ENDPOINT.startswith(("http://", "https://")):
                logger.error("ASTRA_DB_ENDPOINT is missing or invalid")
                print("Error: ASTRA_DB_ENDPOINT is missing or invalid")
                return {
                    "customer_id": "",
                    "user_interests": {},
                    "user_vectors": [],
                    "user_vectors_with_interests": [],
                    "user_vector_agg": [],
                    "ad_url": state.get("ad_url", ""),
                    "ad_url_agg": "",
                    "product": "",
                    "product_agg": "",
                    "similarity_score": 0.0,
                    "similarity_score_agg": 0.0,
                    "play_ad": False,
                    "play_ad_agg": False,
                    "top_recommendations": [],
                    "top_recommendations_agg": []
                }

            if not ASTRA_DB_TOKEN:
                logger.error("ASTRA_DB_TOKEN is missing")
                print("Error: ASTRA_DB_TOKEN is missing")
                return {
                    "customer_id": "",
                    "user_interests": {},
                    "user_vectors": [],
                    "user_vectors_with_interests": [],
                    "user_vector_agg": [],
                    "ad_url": state.get("ad_url", ""),
                    "ad_url_agg": "",
                    "product": "",
                    "product_agg": "",
                    "similarity_score": 0.0,
                    "similarity_score_agg": 0.0,
                    "play_ad": False,
                    "play_ad_agg": False,
                    "top_recommendations": [],
                    "top_recommendations_agg": []
                }

            logger.debug("Connecting to Astra DB at %s", ASTRA_DB_ENDPOINT)
            client = DataAPIClient(ASTRA_DB_TOKEN)
            db = client.get_database_by_api_endpoint(ASTRA_DB_ENDPOINT)
            userinterests_collection = db.get_collection("userinterests")
            logger.info("Connected to userinterests collection")

            # Get random user using improved approach
            customer_id, user_interests, user_vectors, user_vectors_with_interests, user_vector_agg = get_random_user_id(userinterests_collection)
            
            if not customer_id:
                logger.error("Could not retrieve random customer ID")
                print("Error: Could not retrieve random customer ID")
                return {
                    "customer_id": "",
                    "user_interests": {},
                    "user_vectors": [],
                    "user_vectors_with_interests": [],
                    "user_vector_agg": [],
                    "ad_url": state.get("ad_url", ""),
                    "ad_url_agg": "",
                    "product": "",
                    "product_agg": "",
                    "similarity_score": 0.0,
                    "similarity_score_agg": 0.0,
                    "play_ad": False,
                    "play_ad_agg": False,
                    "top_recommendations": [],
                    "top_recommendations_agg": []
                }

            if not user_vectors:
                logger.error("No $vector found for user: %s", customer_id)
                print("Error: No embedding vector for user")
                return {
                    "customer_id": customer_id,
                    "user_interests": user_interests,
                    "user_vectors": [],
                    "user_vectors_with_interests": [],
                    "user_vector_agg": [],
                    "ad_url": state.get("ad_url", ""),
                    "ad_url_agg": "",
                    "product": "",
                    "product_agg": "",
                    "similarity_score": 0.0,
                    "similarity_score_agg": 0.0,
                    "play_ad": False,
                    "play_ad_agg": False,
                    "top_recommendations": [],
                    "top_recommendations_agg": []
                }

            logger.info("Selected random CustomerID: %s, Interests: %s, Number of Vectors: %s", 
                        customer_id, user_interests, len(user_vectors))
            print(f"Selected random CustomerID: {customer_id}")
            return {
                "customer_id": customer_id,
                "user_interests": user_interests,
                "user_vectors": user_vectors,
                "user_vectors_with_interests": user_vectors_with_interests,
                "user_vector_agg": user_vector_agg,
                "ad_url": state.get("ad_url", ""),
                "ad_url_agg": "",
                "product": "",
                "product_agg": "",
                "similarity_score": 0.0,
                "similarity_score_agg": 0.0,
                "play_ad": False,
                "play_ad_agg": False,
                "top_recommendations": [],
                "top_recommendations_agg": []
            }

        elif choice == "2":
            logger.debug("Connecting to Astra DB at %s", ASTRA_DB_ENDPOINT)
            client = DataAPIClient(ASTRA_DB_TOKEN)
            db = client.get_database_by_api_endpoint(ASTRA_DB_ENDPOINT)
            userinterests_collection = db.get_collection("userinterests")
            logger.info("Connected to userinterests collection")

            customer_id = dummy_facial_recognition()
            # Query userinterests collection for all entries of the CustomerID
            entries = list(userinterests_collection.find(
                {"UserId": customer_id},
                projection={"UserId": 1, "InterestName": 1, "InterestDescription": 1, "$vector": 1}
            ))
            
            if entries:
                user_interests = {
                    "InterestName": ", ".join(set(entry.get("InterestName", "Unknown") for entry in entries)),
                    "InterestDescription": ", ".join(set(entry.get("InterestDescription", "Placeholder interest") for entry in entries))
                }
                user_vectors = [entry.get("$vector", []) for entry in entries]
                user_vectors = [v for v in user_vectors if v]  # Filter out empty vectors
                user_vectors_with_interests = [
                    (entry.get("$vector", []), entry.get("InterestName", ""), entry.get("InterestDescription", ""))
                    for entry in entries if entry.get("$vector", [])
                ]
                user_vector_agg = aggregate_vectors(user_vectors)
                logger.info("Retrieved data for CustomerID: %s, Interests: %s, Number of Vectors: %s", 
                            customer_id, user_interests, len(user_vectors))
            else:
                logger.warning("No data found in userinterests for CustomerID: %s, using placeholder interests", customer_id)
                user_interests = {"InterestName": "Unknown", "InterestDescription": "Placeholder interest"}
                user_vectors = []
                user_vectors_with_interests = []
                user_vector_agg = []

            print(f"Selected CustomerID from facial recognition: {customer_id}")
            if not user_vectors:
                logger.error("No $vector found for user: %s", customer_id)
                print("Error: No embedding vector for user")
                return {
                    "customer_id": customer_id,
                    "user_interests": user_interests,
                    "user_vectors": [],
                    "user_vectors_with_interests": [],
                    "user_vector_agg": [],
                    "ad_url": state.get("ad_url", ""),
                    "ad_url_agg": "",
                    "product": "",
                    "product_agg": "",
                    "similarity_score": 0.0,
                    "similarity_score_agg": 0.0,
                    "play_ad": False,
                    "play_ad_agg": False,
                    "top_recommendations": [],
                    "top_recommendations_agg": []
                }

            return {
                "customer_id": customer_id,
                "user_interests": user_interests,
                "user_vectors": user_vectors,
                "user_vectors_with_interests": user_vectors_with_interests,
                "user_vector_agg": user_vector_agg,
                "ad_url": state.get("ad_url", ""),
                "ad_url_agg": "",
                "product": "",
                "product_agg": "",
                "similarity_score": 0.0,
                "similarity_score_agg": 0.0,
                "play_ad": False,
                "play_ad_agg": False,
                "top_recommendations": [],
                "top_recommendations_agg": []
            }

        else:
            logger.warning("Invalid mode choice: %s", choice)
            print("Invalid choice. Defaulting to empty CustomerID.")
            return {
                "customer_id": "",
                "user_interests": {},
                "user_vectors": [],
                "user_vectors_with_interests": [],
                "user_vector_agg": [],
                "ad_url": state.get("ad_url", ""),
                "ad_url_agg": "",
                "product": "",
                "product_agg": "",
                "similarity_score": 0.0,
                "similarity_score_agg": 0.0,
                "play_ad": False,
                "play_ad_agg": False,
                "top_recommendations": [],
                "top_recommendations_agg": []
            }

    except Exception as e:
        logger.error("Error in agent_1_node: %s", str(e))
        print(f"Error in Agent 1: {e}")
        return {
            "customer_id": "",
            "user_interests": {},
            "user_vectors": [],
            "user_vectors_with_interests": [],
            "user_vector_agg": [],
            "ad_url": state.get("ad_url", ""),
            "ad_url_agg": "",
            "product": "",
            "product_agg": "",
            "similarity_score": 0.0,
            "similarity_score_agg": 0.0,
            "play_ad": False,
            "play_ad_agg": False,
            "top_recommendations": [],
            "top_recommendations_agg": []
        }

# Agent 2: Advertisement Selection Node (Astra DB Similarity Search)
def agent_2_node(state: WorkflowState) -> WorkflowState:
    logger.info("Starting agent_2_node with CustomerID: %s", state["customer_id"])
    if not state["customer_id"]:
        logger.warning("No CustomerID provided")
        print("No CustomerID provided")
        return {
            "customer_id": state["customer_id"],
            "user_interests": state["user_interests"],
            "user_vectors": state["user_vectors"],
            "user_vectors_with_interests": state["user_vectors_with_interests"],
            "user_vector_agg": state["user_vector_agg"],
            "ad_url": "",
            "ad_url_agg": "",
            "product": "",
            "product_agg": "",
            "similarity_score": 0.0,
            "similarity_score_agg": 0.0,
            "play_ad": False,
            "play_ad_agg": False,
            "top_recommendations": [],
            "top_recommendations_agg": []
        }

    if not state["user_vectors"]:
        logger.warning("No user vectors available for CustomerID: %s", state["customer_id"])
        print("Error: No user vectors available")
        return {
            "customer_id": state["customer_id"],
            "user_interests": state["user_interests"],
            "user_vectors": state["user_vectors"],
            "user_vectors_with_interests": state["user_vectors_with_interests"],
            "user_vector_agg": state["user_vector_agg"],
            "ad_url": "",
            "ad_url_agg": "",
            "product": "",
            "product_agg": "",
            "similarity_score": 0.0,
            "similarity_score_agg": 0.0,
            "play_ad": False,
            "play_ad_agg": False,
            "top_recommendations": [],
            "top_recommendations_agg": []
        }

    try:
        logger.debug("Connecting to Astra DB at %s", ASTRA_DB_ENDPOINT)
        client = DataAPIClient(ASTRA_DB_TOKEN)
        db = client.get_database_by_api_endpoint(ASTRA_DB_ENDPOINT)
        advertisements_collection = db.get_collection("advertisements")
        logger.info("Connected to advertisements collection")

        # Debug: Log all entries in the advertisements collection
        all_ads = list(advertisements_collection.find(
            {},
            projection={"product": 1, "video_link": 1, "_id": 0}
        ))
        logger.info("Contents of advertisements collection: %s", all_ads)

        # Approach 1: Selection Approach
        logger.info("Evaluating Selection Approach...")
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

            # Debug: Log raw data returned by similarity search
            logger.debug("Raw ads for vector %s: %s", idx + 1, top_ads)

            # Deduplicate by product, keeping the highest-scoring ad per product
            seen_products = set()
            vector_recommendations = []
            for ad in top_ads:
                product = ad.get("product", "")
                if product in seen_products:
                    logger.warning("Duplicate product found in search results for vector %s: %s", idx + 1, product)
                    continue  # Skip duplicates
                ad_url = ad.get("video_link", "") + "&autoplay=1&mute=1" if ad.get("video_link") else ""
                if ad_url:
                    vector_recommendations.append({
                        "url": ad_url,
                        "product": product,
                        "score": ad.get("$similarity", 0.0),
                        "vector_idx": idx
                    })
                    seen_products.add(product)

            # Log the top recommendations for this vector
            if vector_recommendations:
                logger.info("Top recommendations for vector %s (Interest: %s, Description: %s):", 
                            idx + 1, interest_name, interest_description)
                for rec in vector_recommendations[:5]:  # Log up to 5 recommendations per vector
                    logger.info("  - URL: %s, Product: %s, Score: %s", rec["url"], rec["product"], rec["score"])
                all_recommendations.extend(vector_recommendations)

        if not all_recommendations:
            logger.error("No advertisements found across all vectors (Selection Approach)")
            print("Error: No advertisements found (Selection Approach)")
            # Proceed to Aggregation Approach
        else:
            # Deduplicate by product across all recommendations, keeping the highest-scoring ad per product
            seen_products = set()
            deduplicated_recommendations = []
            # Sort by score to ensure highest-scoring ad per product is kept
            all_recommendations.sort(key=lambda x: x["score"], reverse=True)
            for rec in all_recommendations:
                product = rec["product"]
                if product in seen_products:
                    logger.warning("Duplicate product found across all recommendations: %s", product)
                    continue  # Skip duplicates
                deduplicated_recommendations.append(rec)
                seen_products.add(product)

            # Log all deduplicated recommendations
            logger.debug("Deduplicated recommendations (Selection Approach): %s", deduplicated_recommendations)

            # Sort deduplicated recommendations by score and select the top match
            deduplicated_recommendations.sort(key=lambda x: x["score"], reverse=True)
            top_match = deduplicated_recommendations[0]
            ad_url = top_match["url"]
            product = top_match["product"]
            similarity_score = top_match["score"]
            logger.info("Top advertisement (vector %s, Selection Approach): %s, Product: %s, Similarity Score: %s", 
                        top_match["vector_idx"] + 1, ad_url, product, similarity_score)

            # Prepare top 5 recommendations (deduplicated by URL, ensuring top ad is included)
            seen_urls = set()
            top_recommendations = [{
                "url": top_match["url"],
                "product": top_match["product"],
                "score": top_match["score"]
            }]
            seen_urls.add(top_match["url"])

            # Add remaining recommendations, up to 5
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
        # Set default values if Selection Approach fails
        if not all_recommendations:
            ad_url = ""
            product = ""
            similarity_score = 0.0
            top_recommendations = []

        # Approach 2: Aggregation Approach
        logger.info("Evaluating Aggregation Approach...")
        if not state["user_vector_agg"]:
            logger.warning("No aggregated user vector available for CustomerID: %s", state["customer_id"])
            ad_url_agg = ""
            product_agg = ""
            similarity_score_agg = 0.0
            top_recommendations_agg = []
        else:
            # Perform similarity search with the aggregated vector
            top_ads_agg = list(advertisements_collection.find(
                {},
                sort={"$vector": state["user_vector_agg"]},
                limit=10,
                include_similarity=True,
                projection={"product": 1, "video_link": 1},
            ))
            if not top_ads_agg:
                logger.warning("No advertisements found for aggregated vector")
                ad_url_agg = ""
                product_agg = ""
                similarity_score_agg = 0.0
                top_recommendations_agg = []
            else:
                # Debug: Log raw data returned by similarity search
                logger.debug("Raw ads for aggregated vector: %s", top_ads_agg)

                # Deduplicate by product, keeping the highest-scoring ad per product
                seen_products_agg = set()
                agg_recommendations = []
                for ad in top_ads_agg:
                    product = ad.get("product", "")
                    if product in seen_products_agg:
                        logger.warning("Duplicate product found in aggregated search results: %s", product)
                        continue  # Skip duplicates
                    ad_url = ad.get("video_link", "") + "&autoplay=1&mute=1" if ad.get("video_link") else ""
                    if ad_url:
                        agg_recommendations.append({
                            "url": ad_url,
                            "product": product,
                            "score": ad.get("$similarity", 0.0),
                            "vector_idx": -1  # Not applicable for aggregated vector
                        })
                        seen_products_agg.add(product)

                if not agg_recommendations:
                    logger.error("No advertisements found for aggregated vector")
                    ad_url_agg = ""
                    product_agg = ""
                    similarity_score_agg = 0.0
                    top_recommendations_agg = []
                else:
                    # Log recommendations for the aggregated vector
                    logger.info("Top recommendations for aggregated vector (Aggregation Approach):")
                    for rec in agg_recommendations[:5]:
                        logger.info("  - URL: %s, Product: %s, Score: %s", rec["url"], rec["product"], rec["score"])

                    # Sort and select top match for aggregated approach
                    agg_recommendations.sort(key=lambda x: x["score"], reverse=True)
                    top_match_agg = agg_recommendations[0]
                    ad_url_agg = top_match_agg["url"]
                    product_agg = top_match_agg["product"]
                    similarity_score_agg = top_match_agg["score"]
                    logger.info("Top advertisement (Aggregation Approach): %s, Product: %s, Similarity Score: %s", 
                                ad_url_agg, product_agg, similarity_score_agg)

                    # Prepare top 5 recommendations for aggregated approach (deduplicated by URL)
                    seen_urls_agg = set()
                    top_recommendations_agg = []
                    for rec in agg_recommendations:
                        if rec["url"] not in seen_urls_agg and len(top_recommendations_agg) < 5:
                            top_recommendations_agg.append({
                                "url": rec["url"],
                                "product": rec["product"],
                                "score": rec["score"]
                            })
                            seen_urls_agg.add(rec["url"])

                    logger.info("Top 5 recommendations (Aggregation Approach):")
                    for rec in top_recommendations_agg:
                        logger.info("  - URL: %s, Product: %s, Score: %s", rec["url"], rec["product"], rec["score"])

        # Compare the two approaches
        logger.info("Comparison of Selection vs Aggregation Approach:")
        logger.info("Selection Approach - Top Ad: %s, Product: %s, Score: %s", top_match["url"], top_match["product"], top_match["score"])
        logger.info("Aggregation Approach - Top Ad: %s, Product: %s, Score: %s", ad_url_agg, product_agg, similarity_score_agg)

        return {
            "customer_id": state["customer_id"],
            "user_interests": state["user_interests"],
            "user_vectors": state["user_vectors"],
            "user_vectors_with_interests": state["user_vectors_with_interests"],
            "user_vector_agg": state["user_vector_agg"],
            "ad_url": top_match["url"],
            "ad_url_agg": ad_url_agg,
            "product": top_match["product"],
            "product_agg": product_agg,
            "similarity_score": top_match["score"],
            "similarity_score_agg": similarity_score_agg,
            "play_ad": False,  # Agent 3 will decide for Selection Approach
            "play_ad_agg": False,  # Agent 3 will decide for Aggregation Approach
            "top_recommendations": top_recommendations,
            "top_recommendations_agg": top_recommendations_agg
        }

    except Exception as e:
        logger.error("Error in agent_2_node: %s", str(e))
        print(f"Error in Agent 2: {e}")
        return {
            "customer_id": state["customer_id"],
            "user_interests": state["user_interests"],
            "user_vectors": state["user_vectors"],
            "user_vectors_with_interests": state["user_vectors_with_interests"],
            "user_vector_agg": state["user_vector_agg"],
            "ad_url": "",
            "ad_url_agg": "",
            "product": "",
            "product_agg": "",
            "similarity_score": 0.0,
            "similarity_score_agg": 0.0,
            "play_ad": False,
            "play_ad_agg": False,
            "top_recommendations": [],
            "top_recommendations_agg": []
        }

# Agent 3: Similarity Score Validation Node
def agent_3_node(state: WorkflowState) -> WorkflowState:
    logger.info("Starting agent_3_node, evaluating similarity score: %s", state["similarity_score"])
    SIMILARITY_THRESHOLD = 0.7
    DEFAULT_AD_URL = "https://www.youtube.com/watch?v=default_ad&autoplay=1&mute=1"
    DEFAULT_PRODUCT = "Generic Product"

    # Validate Selection Approach
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
        print(f"Warning: Low similarity score ({state['similarity_score']}) for product: {state['product']} (Selection Approach)")
        play_ad = False
        state["ad_url"] = DEFAULT_AD_URL
        state["product"] = DEFAULT_PRODUCT

    # Validate Aggregation Approach
    if state["similarity_score_agg"] >= SIMILARITY_THRESHOLD:
        logger.info(
            "Similarity score %s meets threshold %s, approving advertisement (Aggregation Approach): %s",
            state["similarity_score_agg"], SIMILARITY_THRESHOLD, state["ad_url_agg"]
        )
        play_ad_agg = True
    else:
        logger.warning(
            "Similarity score %s below threshold %s, using default advertisement (Aggregation Approach), interests: %s",
            state["similarity_score_agg"], SIMILARITY_THRESHOLD, state["user_interests"]
        )
        print(f"Warning: Low similarity score ({state['similarity_score_agg']}) for product: {state['product_agg']} (Aggregation Approach)")
        play_ad_agg = False
        state["ad_url_agg"] = DEFAULT_AD_URL
        state["product_agg"] = DEFAULT_PRODUCT

    return {
        "customer_id": state["customer_id"],
        "user_interests": state["user_interests"],
        "user_vectors": state["user_vectors"],
        "user_vectors_with_interests": state["user_vectors_with_interests"],
        "user_vector_agg": state["user_vector_agg"],
        "ad_url": state["ad_url"],
        "ad_url_agg": state["ad_url_agg"],
        "product": state["product"],
        "product_agg": state["product_agg"],
        "similarity_score": state["similarity_score"],
        "similarity_score_agg": state["similarity_score_agg"],
        "play_ad": play_ad,
        "play_ad_agg": play_ad_agg,
        "top_recommendations": state["top_recommendations"],
        "top_recommendations_agg": state["top_recommendations_agg"]
    }

# Error Handler Node
def error_handler_node(state: WorkflowState) -> WorkflowState:
    logger.error("Error handler triggered: No valid CustomerID or URL found")
    print("Error: No valid CustomerID or URL found")
    return {
        "customer_id": state["customer_id"],
        "user_interests": state["user_interests"],
        "user_vectors": state["user_vectors"],
        "user_vectors_with_interests": state["user_vectors_with_interests"],
        "user_vector_agg": state["user_vector_agg"],
        "ad_url": "https://www.youtube.com/watch?v=default_video&autoplay=1&mute=1",
        "ad_url_agg": "https://www.youtube.com/watch?v=default_video&autoplay=1&mute=1",
        "product": "",
        "product_agg": "",
        "similarity_score": 0.0,
        "similarity_score_agg": 0.0,
        "play_ad": False,
        "play_ad_agg": False,
        "top_recommendations": [],
        "top_recommendations_agg": []
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

# Main execution
def main():
    logger.info("Starting recommendation workflow")
    result = graph.invoke({
        "customer_id": "",
        "user_interests": {},
        "user_vectors": [],
        "user_vectors_with_interests": [],
        "user_vector_agg": [],
        "ad_url": "",
        "ad_url_agg": "",
        "product": "",
        "product_agg": "",
        "similarity_score": 0.0,
        "similarity_score_agg": 0.0,
        "play_ad": False,
        "play_ad_agg": False,
        "top_recommendations": [],
        "top_recommendations_agg": []
    })

    # Log and print results for both approaches
    logger.info("Final Results Comparison:")
    logger.info("=== Selection Approach ===")
    if result["top_recommendations"]:
        logger.info(
            "Top 5 Recommendations (Selection Approach):\n%s",
            "\n".join(
                f"  - URL: {rec['url']}, Product: {rec['product']}, Score: {rec['score']}"
                for rec in result["top_recommendations"]
            )
        )
        print("Top 5 Recommendations (Selection Approach):")
        for rec in result["top_recommendations"]:
            print(f"  - URL: {rec['url']}, Product: {rec['product']}, Score: {rec['score']}")

    if result["ad_url"] and result["play_ad"]:
        logger.info(
            "Workflow completed, opening advertisement (Selection Approach): %s, User Interests: %s, Product: %s, Similarity Score: %s",
            result["ad_url"],
            result["user_interests"],
            result["product"],
            result["similarity_score"]
        )
        print(f"\nOpening advertisement (Selection Approach): {result['ad_url']}")
        print(f"User Interests: {result['user_interests']}")
        print(f"Matched Product: {result['product']}")
        print(f"Similarity Score: {result['similarity_score']}")
        webbrowser.open(result["ad_url"])
    else:
        logger.warning(
            "Workflow completed with no playable advertisement (Selection Approach), User Interests: %s, Product: %s, Similarity Score: %s",
            result["user_interests"],
            result["product"],
            result["similarity_score"]
        )
        print("\nNo advertisement played (Selection Approach)")
        print(f"User Interests: {result['user_interests']}")
        print(f"Matched Product: {result['product']}")
        print(f"Similarity Score: {result['similarity_score']}")

    logger.info("=== Aggregation Approach ===")
    if result["top_recommendations_agg"]:
        logger.info(
            "Top 5 Recommendations (Aggregation Approach):\n%s",
            "\n".join(
                f"  - URL: {rec['url']}, Product: {rec['product']}, Score: {rec['score']}"
                for rec in result["top_recommendations_agg"]
            )
        )
        print("\nTop 5 Recommendations (Aggregation Approach):")
        for rec in result["top_recommendations_agg"]:
            print(f"  - URL: {rec['url']}, Product: {rec['product']}, Score: {rec['score']}")

    if result["ad_url_agg"] and result["play_ad_agg"]:
        logger.info(
            "Workflow completed, opening advertisement (Aggregation Approach): %s, User Interests: %s, Product: %s, Similarity Score: %s",
            result["ad_url_agg"],
            result["user_interests"],
            result["product_agg"],
            result["similarity_score_agg"]
        )
        print(f"\nOpening advertisement (Aggregation Approach): {result['ad_url_agg']}")
        print(f"User Interests: {result['user_interests']}")
        print(f"Matched Product: {result['product_agg']}")
        print(f"Similarity Score: {result['similarity_score_agg']}")
        webbrowser.open(result["ad_url_agg"])
    else:
        logger.warning(
            "Workflow completed with no playable advertisement (Aggregation Approach), User Interests: %s, Product: %s, Similarity Score: %s",
            result["user_interests"],
            result["product_agg"],
            result["similarity_score_agg"]
        )
        print("\nNo advertisement played (Aggregation Approach)")
        print(f"User Interests: {result['user_interests']}")
        print(f"Matched Product: {result['product_agg']}")
        print(f"Similarity Score: {result['similarity_score_agg']}")

if __name__ == "__main__":
    main()