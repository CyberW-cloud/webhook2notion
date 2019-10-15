
import os
import sys
from notion.client import NotionClient
from notion.block import *
from notion.collection import *
from datetime import datetime, date
from flask import Flask
from flask import request, jsonify
from notion_helpers import *
import re
from members import *
from todo import *
import urllib.parse




timezone = "Europe/Kiev"
text = None

app = Flask(__name__)




def createInvite(token, collectionURL, subject, description, inviteto):
    # notion
    match = re.search('https://upwork.com/applications/\d+', description) 
    url = match.group()
    id = re.search('\d+', url)
    client = NotionClient(token)
    cv = client.get_collection_view(collectionURL)
    row = cv.collection.add_row()
    row.name = subject
    row.description = description
    row.status = "New"
    row.to = inviteto
    row.link = url
    row.id = id.group()
 
def createPCJ(token, collectionURL, subject, description, inviteto, link):
    # notion
    id = re.search('%7E[\w]+', link)
    client = NotionClient(token)
    cv = client.get_collection_view(collectionURL)
    row = cv.collection.add_row()
    row.name = subject
    row.description = description
    row.status = "New"
    row.to = inviteto
    row.link = link
    row.id = id.group()[3:]
    
def createMessage(token, parent_page_url, message):
    # notion
    client = NotionClient(token)
    page = client.get_block(parent_page_url)
    a = page.children.add_new(TextBlock, title=" ")
    b = page.children.add_new(DividerBlock)
    c = page.children.add_new(TextBlock, title="**{data}** {msg}".format(data = datetime.now().strftime("%d-%m-%Y %H:%M"), msg = message))
    d = page.children.add_new(DividerBlock)
    a.move_to(page, "first-child")
    b.move_to(a, "after")
    c.move_to(b, "after")
    d.move_to(c, "after")
         

def createRSS(token, collectionURL, subject, link):
    # notion
    client = NotionClient(token)
    cv = client.get_collection_view(collectionURL)
    row = cv.collection.add_row()
    row.name = subject
    row.link = link
    if link.find("https://www.upwork.com/blog/") != -1: row.label = 'upwok blog'
    if link.find("https://community.upwork.com/t5/Announcements/") != -1: row.label = 'upwork community announcements'
   

@app.route('/rss', methods=['POST'])
def rss():
    collectionURL = request.args.get("collectionURL")
    subject = request.args.get('subject')
    token_v2 = os.environ.get("TOKEN")
    link = request.args.get('link')
    createRSS(token_v2, collectionURL, subject, link)
    return f'added {subject} receipt to Notion'    

@app.route('/message', methods=['GET'])
def message():
    parent_page_url = request.args.get("parent_page_url")
    token_v2 = os.environ.get("TOKEN")
    message = request.args.get("message")
    createMessage(token_v2, parent_page_url, message)
    return f'added {message} receipt to Notion'    

    
@app.route('/pcj', methods=['POST'])
def pcj():
    collectionURL = request.args.get("collectionURL")
    description = request.args.get('description')
    subject = request.args.get('subject')
    token_v2 = os.environ.get("TOKEN")
    inviteto = request.args.get('inviteto')
    link = request.args.get('link')
    createPCJ(token_v2, collectionURL, subject, description, inviteto, link)
    return f'added {subject} receipt to Notion'

@app.route('/invites', methods=['POST'])
def invites():
    collectionURL = request.args.get("collectionURL")
    description = request.args.get('description')
    subject = request.args.get('subject')
    token_v2 = os.environ.get("TOKEN")
    inviteto = request.args.get('inviteto')
    createInvite(token_v2, collectionURL, subject, description, inviteto)
    return f'added {subject} receipt to Notion'






if __name__ == '__main__':
    app.debug = True
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
