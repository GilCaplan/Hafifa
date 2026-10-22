from functools import cache

from pymongo import *
from consts import *

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
    return MongoClient(MONGO_URI)


def load_db():
    return get_client()[DB_NAME][COLLECTION_NAME]

def main():
    db = load_db()
    # (q13, q31, q48, q59, q85)
    for exc_func in (q13, q31, q48, q59, q85):
        results = exc_func(db)
        if results is None:
            continue
        print(f"\n{exc_func.__name__} exercise \n")
        for doc in list(results)[:10]:
            print(doc)


if __name__ == "__main__":
    main()