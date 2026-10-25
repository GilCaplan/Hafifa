import logging
from functools import cache

from pymongo import *
from pymongo.errors import ServerSelectionTimeoutError
from pymongo.uri_parser import parse_uri

from consts import *

logger = logging.getLogger(__name__)

def q13(restaurants_db):
    """
    Find restaurants that aren't American, got a grade A, 
    and aren't in Brooklyn. Sort by cuisine, descending.
    """
    restaurants_pipeline = [
        {
            "$match": {
                "cuisine": {"$ne": "American "},
                "grades.grade": "A",
                "borough": {"$ne": "Brooklyn"},
            }
        },
        {"$sort": {"cuisine": DESC}},
        {"$project": {"_id": 0, "name": 1, "cuisine": 1, "borough": 1}},
    ]

    results = restaurants_db.aggregate(restaurants_pipeline)

    return results

def q31(restaurants_db):
    """
    Show the name, borough, longitude, latitude and cuisine
    of restaurants whose name contains "mon".
    """
    restaurants_mon = restaurants_db.find(
        {"name": {"$regex": "mon", "$options": "i"}},
        {
            "_id": 0,
            "name": 1,
            "borough": 1,
            "longitude": {"$arrayElemAt": ["$address.coord", 0]},
            "latitude": {"$arrayElemAt": ["$address.coord", 1]},
            "cuisine": 1,
        },
    )
    return restaurants_mon

def q48(restaurants_db):
    """
    Find restaurants where every grade score is above 5.
    """
    restaurants_grade = restaurants_db.find(
        {"grades.score": {"$not": {"$lte": 5}}},
        {
            "_id": 0,
            "name": 1,
            "borough": 1,
            "cuisine": 1,
            "grades": 1,
        },
    )
    return restaurants_grade

def q59(restaurants_db):
    """
    Count the A grades for each combination of cuisine and borough.
    """
    pipeline = [
        {"$unwind": "$grades"},
        {"$match": {"grades.grade": "A"}},
        {
            "$group": {
                "_id": {"cuisine": "$cuisine", "borough": "$borough"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": DESC}},
    ]
    
    results = restaurants_db.aggregate(pipeline)

    return results


def q85(restaurants_db):
    """
    For each cuisine, find the top 5 restaurants by average score.
    """
    pipeline = [
        {
            "$project": {
                "name": 1,
                "cuisine": 1,
                "avg_score": {"$avg": "$grades.score"},
            }
        },
        {"$sort": {"avg_score": DESC}},
        {
            "$group": {
                "_id": "$cuisine",
                "restaurants": {"$push": {"name": "$name", "avg_score": "$avg_score"}},
            }
        },
        {
            "$project": {
                "_id": 0,
                "cuisine": "$_id",
                "top_5": {"$slice": ["$restaurants", 5]},
            }
        },
        {"$sort": {"cuisine": ASC}},
    ]

    results = restaurants_db.aggregate(pipeline)

    return results


@cache
def get_client():
    hosts = ", ".join(f"{host}:{port}" for host, port in parse_uri(MONGO_URI)["nodelist"])
    logger.info("Connecting to MongoDB at %s", hosts)
    client = MongoClient(MONGO_URI)
    client.admin.command("ping")
    return client


def load_db():
    logger.info("Using collection %s.%s", DB_NAME, COLLECTION_NAME)
    return get_client()[DB_NAME][COLLECTION_NAME]

def main():
    try:
        db = load_db()
    except ServerSelectionTimeoutError as e:
        logger.error("Could not reach MongoDB: %s", e)
        return
    # (q13, q31, q48, q59, q85)
    for exc_func in (q13, q31, q48, q59, q85):
        logger.info("Running %s", exc_func.__name__)
        results = exc_func(db)
        if results is None:
            continue
        docs = list(results)
        logger.info("%s returned %d documents", exc_func.__name__, len(docs))
        print(f"\n{exc_func.__name__} exercise \n")
        for doc in docs[:10]:
            print(doc)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    main()