import datetime
from flask import Flask
from flask_restful import reqparse, Api, Resource
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_cors import CORS

app = Flask(__name__)
api = Api(app)
CORS(app, resources={r"/transactions/*": {"origins": "*"}})

client = MongoClient("localhost", 27017)

db = client.bank

ts = db.transactions
new_ts = db.newTransactions


parser = reqparse.RequestParser()
parser.add_argument("startDate", required=True, type=str, location="json")
parser.add_argument("endDate", required=True, type=str, location="json")
parser.add_argument("mode", choices=("count", "amount"), required=True, type=str)
parser.add_argument(
    "currency", choices=("rial", "toman"), location="json", required=True, type=str
)
parser.add_argument(
    "period",
    choices=("day", "week", "month", "year"),
    required=True,
    type=str,
    location="json",
)


def datetime_parser(date_str: str) -> datetime.datetime:
    return datetime.datetime.strptime(date_str, "%Y-%m-%d")


def format_fixer(period: str) -> dict:
    if period == "day":
        return "%Y-%m-%d"
    elif period == "month":
        return "%Y-%m"
    elif period == "year":
        return "%Y"
    elif period == "week":
        return "%Y-%U"


def project_generator(args: dict) -> dict:
    res = {"_id": 0, "key": "$_id"}
    if args["mode"] == "amount":
        if args["currency"] == "toman":
            res["value"] = {"$divide": ["$amount", 10]}
        else:
            res["value"] = "$amount"
    else:
        res["value"] = "$count"
    return {"$project": res}


class Transactions(Resource):
    def post(self, user_id):
        args = parser.parse_args()
        start_date = datetime_parser(args["startDate"])
        end_date = datetime_parser(args["endDate"])
        res = ts.aggregate(
            [
                {
                    "$match": {
                        "merchantId": ObjectId(user_id),
                        "createdAt": {
                            "$lt": end_date,
                            "$gt": start_date,
                        },
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {
                                "date": "$createdAt",
                                "format": format_fixer(args["period"]),
                            }
                        },
                        "amount": {"$sum": "$amount"},
                        "count": {"$sum": 1},
                    }
                },
                project_generator(args),
            ]
        )
        return list(res)


class AllTransactions(Resource):
    def post(self):
        args = parser.parse_args()
        start_date = datetime_parser(args["startDate"])
        end_date = datetime_parser(args["endDate"])
        res = ts.aggregate(
            [
                {
                    "$match": {
                        "createdAt": {
                            "$lt": end_date,
                            "$gt": start_date,
                        },
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {
                                "date": "$createdAt",
                                "format": format_fixer(args["period"]),
                            }
                        },
                        "amount": {"$sum": "$amount"},
                        "count": {"$sum": 1},
                    }
                },
                project_generator(args),
            ]
        )
        return list(res)


api.add_resource(AllTransactions, "/transactions")
api.add_resource(Transactions, "/transactions/<user_id>")


if __name__ == "__main__":
    app.run(debug=True)
