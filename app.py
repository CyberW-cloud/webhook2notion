
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
         



    
def createTODO(token, member, role):
    # notion
    to_do = to_do[role]
    
    client = NotionClient(token)
    page = client.get_block(members[member]['todo'])
    

    
    # place to do in right date
    for todo in to_do:
        if to_do[todo]['Header'] != "" or  to_do[todo]['text'] != "" or  to_do[todo]['to_do'] != []:
            create_new_task(page, header=to_do[todo]['Header'],
                            text=to_do[todo]['text'],
                            date=dates[todo], timezone=timezone,
                            tasks=to_do[todo]['to_do'])
            
                            
def createTODOPA(token, member, role, whom):
    # notion
    to_do = to_do[role]    
    
    client = NotionClient(token)
    page = client.get_block(members[member]['todo'])

            
    for fl in whom : 
        to_do["mon"]['to_do'].append = "Сделать скрины myStats и загрузить на pcloud по ({name})[{link}]".format(name = members[whom], link = members[whom]["profiles"] )    
        to_do["tue"]['to_do'].append = "Обновить профиль ({name})[{link}]".format(name = members[whom], link = members[whom]["profiles"] )
        to_do["wed"]['to_do'].append = "Проверить обновление профиля ({name})[{link}]".format(name = members[whom], link = members[whom]["profiles"] )
    
    to_do["mon"]['to_do'].append = "Запросить инфо об отпусках и day-off по {name} и внести в календарь инфо".format(name=whom)        
    to_do["mon"]['to_do'].append = "Запросить статусы по планируемой загрузке и заполнить планируемую и фактическую загрузку в (Workload)[https://www.notion.so/Workload-ef6a6d4e3bbb41d8b4286b339f603aba] по {name}".format(name=whom)    
 
        
    
    # place to do in right date
    for todo in to_do:
        if to_do[todo]['Header'] != "" or  to_do[todo]['text'] != "" or  to_do[todo]['to_do'] != []:
            create_new_task(page, header=to_do[todo]['Header'],
                            text=to_do[todo]['text'],
                            date=dates[todo], timezone=timezone,
                            tasks=to_do[todo]['to_do'])                            


                            
def createTODOone(token, date, member, todo, text):
    # notion
    client = NotionClient(token)
    page = client.get_block(members[member]['todo'])
    if date is not None: today = datetime.datetime(date).date() 
    tasks = request.args.get("todo").split("||")
    
    header = None
    # place to do in right date
    create_new_task(page, header, text=text,
                    date=today, timezone=timezone,
                    tasks=tasks
                    )                            
                            
@app.route('/todoone', methods=['GET'])
def onetodo():
    member = request.args.get("member")
    token_v2 = os.environ.get("TOKEN")
    todo = request.args.get("todo")
    text = request.args.get("text") 
    createTODOone(token_v2, date, member, todo, text)
    return f'added {message} receipt to Notion' 

@app.route('/todorole', methods=['GET'])
def todorole():
    member = request.args.get("member")
    role = request.args.get("role")
    token_v2 = os.environ.get("TOKEN")   
    whom = request.args.get("whom").split()
    if role == "pa" :
        createTODOPA(token_v2, member, role, whom)
    else:  
        createTODO(token_v2, member, role)
    return f'added {message} receipt to Notion'    

   
    

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
