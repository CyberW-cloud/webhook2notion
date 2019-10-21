from notion.client import NotionClient
from notion.block import *
from flask import Flask
from flask import request
from notion_helpers import *
import re
from members import *
from todo import *
import urllib.parse
import pytz
import datetime

timezone = "Europe/Kiev"

app = Flask(__name__)


def create_invite(token, collection_url, subject, description, invite_to):
    # notion
    match = re.search('https://upwork.com/applications/\d+', description) 
    url = match.group()
    item_id = re.search('\d+', url)
    client = NotionClient(token)
    cv = client.get_collection_view(collection_url)
    row = cv.collection.add_row()
    row.name = subject
    row.description = description
    row.status = "New"
    row.to = invite_to
    row.link = url
    row.id = item_id.group()


def create_pcj(token, collection_url, subject, description, invite_to, link):
    # notion
    item_id = re.search('%7E[\w]+', link)
    client = NotionClient(token)
    cv = client.get_collection_view(collection_url)
    row = cv.collection.add_row()
    row.name = subject[:-9]
    row.description = description
    row.status = "New"
    row.to = invite_to
    row.link = "https://www.upwork.com/ab/jobs/search/?previous_clients=all&q={}&sort=recency".format(
        urllib.parse.quote(subject[:-9]))
    row.id = item_id.group()[3:]


def create_message(token, parent_page_url, message_content):
    # notion
    client = NotionClient(token)
    page = client.get_block(parent_page_url)
    a = page.children.add_new(TextBlock, title=" ")
    b = page.children.add_new(DividerBlock)
    c = page.children.add_new(TextBlock,
                              title="**{data}** {msg}".format(data=datetime.now().strftime("%d-%m-%Y %H:%M"),
                                                              msg=message_content))
    d = page.children.add_new(DividerBlock)
    a.move_to(page, "first-child")
    b.move_to(a, "after")
    c.move_to(b, "after")
    d.move_to(c, "after")
         

def create_rss(token, collection_url, subject, link, description):
    # notion
    client = NotionClient(token)
    cv = client.get_collection_view(collection_url)
    row = cv.collection.add_row()
    row.name = subject
    row.link = link
    row.description = description
    if link.find("https://www.upwork.com/blog/") != -1:
        row.label = 'upwok blog'
    if link.find("https://community.upwork.com/t5/Announcements/") != -1:
        row.label = 'upwork community announcements'


def create_todo(token, date, member, todo, text):
    # notion
    date = datetime.strptime(urllib.parse.unquote("{}".format(date)), "%Y-%m-%dT%H:%M:%S.%fZ").date()
    client = NotionClient(token)
    page = client.get_block(members[member]['todo'])
    tasks = todo

    # place to do in right date
    create_new_task(page, "", text=text,
                    date=date, timezone=timezone,
                    tasks=tasks
                    )


def get_contracts(token, days_before):
    client = NotionClient(token)
    cv = client.get_collection_view(
        "https://www.notion.so/5a95fb63129242a5b5b48f18e16ef19a?v=48599e7a184a4f32be2469e696367949")
    # 48599e7a184a4f32be2469e696367949 - no_filters_view
    # 02929acd595a48dda28cb9e2ff6ae210 - python_view
    n = datetime.datetime.now(pytz.timezone("Europe/Kiev"))
    n = n.replace(hour=12, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days_before)

    filter_params = [{
        "property": "Status",
        "comparator": "enum_is",
        "value": "In Progress",
        },
        {
            "property": "Updated",
            "comparator": "date_is_on_or_before",
            "value_type": 'exact_date',
            "value": int(n.timestamp())*1000,
        }
        ]
    result = cv.build_query(filter=filter_params).execute()
    res = []
    for row in result:
        contract = dict()
        contract['coordinator'] = row.Coordinator[0] if row.Coordinator else None
        if contract['coordinator']:
            contract['coordinator_name'] = contract['coordinator'].name.replace(u'\xa0', u'')
        contract['freelancer'] = row.freelancer[0] if row.freelancer else None
        if contract['freelancer']:
            contract['freelancer_name'] = contract['freelancer'].name.replace(u'\xa0', u'')
        contract['client'] = row.client_name[0] if row.client_name else None
        contract['contract_url'] = row.get_browseable_url()
        if contract['coordinator'] is None:
            continue
        else:
            res.append(contract)
    return res


def get_projects(token, days_before):
    client = NotionClient(token)
    cv = client.get_collection_view(
        "https://www.notion.so/addccbcaf545405292db498941c9538a?v=e86f54933acc461ca413afa6a2958cdc")
    # e86f54933acc461ca413afa6a2958cdc - no_filters_view
    # 1ed5f8ce4e834f1382ffb447976e944f - python_view
    n = datetime.datetime.now(pytz.timezone("Europe/Kiev"))
    n = n.replace(hour=12, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days_before)
    filter_params = [{
        "property": "Status",
        "comparator": "enum_is",
        "value": "inProgress",
    },
    {
        "property": "Updated",
        "comparator": "date_is_on_or_before",
        "value_type": 'exact_date',
        "value": int(n.timestamp()) * 1000,
    }
    ]
    cv = cv.build_query(filter=filter_params)
    result = cv.execute()
    res = []
    for row in result:
        project = dict()
        project['pm'] = row.PM[0] if row.PM else None
        if project['pm']:
            project['pm_name'] = project['pm'].name.replace(u'\xa0', u'')
        project['client'] = row.client_name[0] if row.client_name else None
        project['project_url'] = row.get_browseable_url()
        if project['pm'] is None:
            continue
        else:
            res.append(project)
    return res


@app.route('/kick_staff', methods=['GET'])
def kick_staff():
    token_v2 = os.environ.get("TOKEN")
    contracts = get_projects(token_v2, 7)
    return f'{contracts}'


@app.route('/todoone', methods=['GET'])
def todo_one():
    member = request.args.get("member")
    token_v2 = os.environ.get("TOKEN")
    todo = "{}".format(request.args.get("todo")).split("||")
    text = request.args.get("text")
    date = request.args.get("date")
    create_todo(token_v2, date, member, todo, text)
    return f'added to {member} {text if text else ""} {todo}  to Notion'


@app.route('/rss', methods=['POST'])
def rss():
    collection_url = request.form.get("collectionURL")
    subject = request.form.get('subject')
    token_v2 = os.environ.get("TOKEN")
    link = request.form.get('link')
    description = request.form.get('description')
    create_rss(token_v2, collection_url, subject, link, description)
    return f'added {subject} receipt to Notion'    


@app.route('/message', methods=['GET'])
def message():
    parent_page_url = request.args.get("parent_page_url")
    token_v2 = os.environ.get("TOKEN")
    message_content = request.args.get("message")
    create_message(token_v2, parent_page_url, message_content)
    return f'added {message_content} receipt to Notion'

    
@app.route('/pcj', methods=['POST'])
def pcj():
    collection_url = request.args.get("collectionURL")
    description = request.args.get('description')
    subject = request.args.get('subject')
    token_v2 = os.environ.get("TOKEN")
    invite_to = request.args.get('inviteto')
    link = request.args.get('link')
    create_pcj(token_v2, collection_url, subject, description, invite_to, link)
    return f'added {subject} receipt to Notion'


@app.route('/invites', methods=['POST'])
def invites():
    collection_url = request.args.get("collectionURL")
    description = request.args.get('description')
    subject = request.args.get('subject')
    token_v2 = os.environ.get("TOKEN")
    invite_to = request.args.get('inviteto')
    create_invite(token_v2, collection_url, subject, description, invite_to)
    return f'added {subject} receipt to Notion'


if __name__ == '__main__':
    app.debug = True
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
