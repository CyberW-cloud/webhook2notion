from datetime import timedelta

import pytz
from flask import Flask, request
from notion.block import *
from notion.client import NotionClient
from notion.collection import CollectionRowBlock

from notion_helpers import *


app = Flask(__name__)

site = "https://www.notion.so/0aead28cb9f34ec2b41a9af19b96817a?v=1266d9ce8cbd4c968d29b4b877bed345"
token_v2 = os.environ.get("TOKEN")

client.get_collection_view(site)

n = datetime.datetime.now()
n = n.replace(hour=12, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days_before)

# get projects InProgress with date less when now()-days before
filter_params = {
    "filters": [
        {
            "filter": {"value": {"type": "exact", "value": "TODO"}, "operator": "enum_is"},
            "property": "Status",
        },
        {
            "property": "Updated",
            "filter": {
                "operator": "date_is_on_or_before",
                "value": {
                    "type": "exact",
                    "value": {
                        "type": "date",
                        "start_date": str(n.date())
                        # "start_date": '2020-03-19'
                    },
                },
            },
        },
    ],
    "operator": "and",
}
cv = cv.build_query(filter=filter_params)
result = cv.execute()

result = nview_to_pandas(result)
print(result)