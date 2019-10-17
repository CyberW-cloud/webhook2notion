from notion.client import NotionClient
from notion.block import *
from flask import Flask
from flask import request
from notion_helpers import *
import re
from members import *
from todo import *
import urllib.parse

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


def create_todo_one(token, date, member, todo, text):
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


@app.route('/todoone', methods=['GET'])
def todo_one():
    member = request.args.get("member")
    token_v2 = os.environ.get("TOKEN")
    todo = request.args.get("todo"))
#    todo = "{}".format(request.args.get("todo")).split("||")
    text = request.args.get("text")
    date = request.args.get("date")
    create_todo_one(token_v2, date, member, todo, text)
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
