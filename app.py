from notion.client import NotionClient
from notion.block import *
from flask import Flask
from flask import request
from notion_helpers import *
import re
import urllib.parse
import pytz
import datetime
from datetime import timedelta

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
    a = page.children.add_new(TextBlock, title=" . ")
    b = page.children.add_new(DividerBlock)
    c = page.children.add_new(TextBlock,
                              title="**{data}** {msg}".format(data=datetime.datetime.now().strftime("%d-%m-%Y %H:%M"),
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


def get_toto_url_by_name(token, name):
    client = NotionClient(token)
    stats = client.get_collection_view(
        "https://www.notion.so/e4d36149b9d8476e9985a2c658d4a873?v=3238ddee2ea04d5ea302d99fc2a2d5cc")
    filter_params = [{
        "property": "title",
        "comparator": "string_contains",
        "value": name,
    }]
    person_stat = stats.build_query(filter=filter_params).execute()
    return person_stat[0].todo if person_stat else None


def create_todo(token, date, link, todo, text):
    # notion
    if date is not None:  # if date not provided use now()
        if isinstance(date, str):
            date = datetime.datetime.strptime(urllib.parse.unquote("{}".format(date)), "%Y-%m-%dT%H:%M:%S.%fZ").date()
    else:
        date = datetime.datetime.now().date()

    client = NotionClient(token)
    page = client.get_block(link)
    tasks = todo

    return create_new_task(page, "", text=text,
                           date=date, timezone=timezone,
                           tasks=tasks
                           )


def get_contracts(token, days_before):
    client = NotionClient(token)
    cv = client.get_collection_view(
        "https://www.notion.so/5a95fb63129242a5b5b48f18e16ef19a?v=48599e7a184a4f32be2469e696367949")
    # 48599e7a184a4f32be2469e696367949 - no_filters_view
    # 02929acd595a48dda28cb9e2ff6ae210 - python_view

    # calculate date for filter now() - days_before. Stupid notion starts new day at 12:00 a.m.
    n = datetime.datetime.now(pytz.timezone("Europe/Kiev"))
    n = n.replace(hour=12, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days_before)

    # get contracts In Progress with date less when now()-days before and w/o project
    filter_params = [{
        "property": "Status",
        "comparator": "enum_is",
        "value": "In Progress",
    },
        {
            "property": "Updated",
            "comparator": "date_is_on_or_before",
            "value_type": 'exact_date',
            "value": int(n.timestamp()) * 1000,
        },
        {
            "property": "Project",
            "comparator": "is_empty",
        }
    ]
    result = cv.build_query(filter=filter_params).execute()
    res = []
    # for every contract get person (how care this about contract and client for next check
    for row in result:
        contract = dict()
        contract['person'] = row.Coordinator[0] if row.Coordinator else None
        if contract['person'] is None:
            continue
        else:
            contract['person_name'] = contract['person'].name.replace(u'\xa0', u'')
        if contract['person_name'] == 'selfCC':  # if selfCC get a freelancer name
            contract['person'] = row.freelancer[0] if row.freelancer else None
            if contract['person']:
                contract['person_name'] = contract['person'].name.replace(u'\xa0', u'')
        contract['client'] = row.client_name[0] if row.client_name else None
        contract['url'] = row.contract_name.replace(u'\xa0', u''), row.get_browseable_url()
        res.append(contract)
    return res


def get_projects(token, days_before):
    client = NotionClient(token)
    cv = client.get_collection_view(
        "https://www.notion.so/addccbcaf545405292db498941c9538a?v=e86f54933acc461ca413afa6a2958cdc")
    # e86f54933acc461ca413afa6a2958cdc - no_filters_view
    # 1ed5f8ce4e834f1382ffb447976e944f - python_view

    # calculate date for filter now() - days_before. Stupid notion starts new day at 12:00 a.m.
    n = datetime.datetime.now(pytz.timezone("Europe/Kiev"))
    n = n.replace(hour=12, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days_before)

    # get projects InProgress with date less when now()-days before
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

    # for every project get person and client
    for row in result:
        project = dict()
        if row.PM:
            project['person'] = row.PM[0]
        else:
            project['person'] = row.contracts[0].Coordinator[0] if row.contracts[0].Coordinator[0] else None
        if project['person']:
            project['person_name'] = project['person'].name.replace(u'\xa0', u'')
        project['client'] = row.client_name[0] if row.client_name else None
        project['url'] = row.name.replace(u'\xa0', u''), row.get_browseable_url()
        if project['person'] is None:
            continue
        else:
            res.append(project)
    return res


def get_proposals(token, days_before):
    client = NotionClient(token)
    cv = client.get_collection_view(
        "https://www.notion.so/99055a1ffb094e0a8e79d1576b7e68c2?v=bc7d781fa5c8472699f2d0c1764aa553")

    # calculate date for filter now() - days_before. Stupid notion starts new day at 12:00 a.m.
    n = datetime.datetime.now(pytz.timezone("Europe/Kiev"))
    n = n.replace(hour=12, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days_before)
    stats = client.get_collection_view(
        "https://www.notion.so/e4d36149b9d8476e9985a2c658d4a873?v=3238ddee2ea04d5ea302d99fc2a2d5cc")
    # get proposal replied, not declined and with empty contract field
    filter_params = [{
        "property": "Reply",
        "comparator": "checkbox_is",
        "value": "Yes",
    },
    {
        "property": "Declined",
        "comparator": "checkbox_is",
        "value": "No",
    },
    {
        "property": "Contract",
        "comparator": "isget_empty",
    },
    {
        "property": "Modified",
        "comparator": "date_is_on_or_before",
        "value_type": 'exact_date',
        "value": int(n.timestamp()) * 1000,
    }
    ]
    cv = cv.build_query(filter=filter_params)
    result = cv.execute()
    res = []
    # for every proposal get person
    for row in result:
        proposal = dict()
        if row.CC:
            proposal['person'] = row.CC[0]
        else:
            proposal['person'] = row.Sent_by if row.Sent_by else None
        if proposal['person']:
            proposal['person_name'] = proposal['person'].full_name.replace(u'\xa0', u'')
        # person field is class User, so we need linked it to stats DB. Try to Find person in stats DB
            filter_params = [{
                "property": "title",
                "comparator": "string_contains",
                "value": proposal['person_name'],
            }]
            person_stat = stats.build_query(filter=filter_params).execute()
            if person_stat:
                proposal['person'] = person_stat[0]
            else:
                print(proposal['person_name'], 'not found in stats')
        proposal['url'] = str(row.Proposal_ID).replace(u'\xa0', u''), row.get_browseable_url()
        proposal['client'] = None
        if proposal['person'] is None:
            continue
        else:
            res.append(proposal)
    return res


def parse_staff(todo, table, obj, client_days_before):
    test_date = datetime.datetime.now()
    test_date = test_date.replace(hour=12,
                                  minute=0,
                                  second=0,
                                  microsecond=0) - datetime.timedelta(days=client_days_before)
    # Preparing data to make task in Notion.
    # group and clarify (by set behavior) data by person_name
    for row in table:
        person = row['person_name']
        if person not in todo:
            todo[person] = dict()
            todo[person]['todo_url'] = row['person'].todo
            todo[person]['projects'] = set()
            todo[person]['contracts'] = set()
            todo[person]['clients'] = set()
            todo[person]['proposals'] = set()
        todo[person][obj].add(row['url'])
        # check updates of client and add to task if it's need
        if row['client'] is not None:
            if row['client'].Modified <= test_date:
                todo[person]['clients'].add((row['client'].name.replace(u'\xa0', u''),
                                             row['client'].get_browseable_url()))
    return todo


def get_todo_list_by_role(token, roles):
    client = NotionClient(token)
    team = client.get_collection_view(
        "https://www.notion.so/7113e573923e4c578d788cd94a7bddfa?v=536bcc489f93433ab19d697490b00525")
    # python 536bcc489f93433ab19d697490b00525
    # no_filters 375e91212fc4482c815f0b4419cbf5e3
    stats = client.get_collection_view(
        "https://www.notion.so/e4d36149b9d8476e9985a2c658d4a873?v=3238ddee2ea04d5ea302d99fc2a2d5cc")
    todo_list = dict()
    for role in roles:
        filter_params = [{
            "property": "Roles",
            "comparator": "enum_contains",
            "value": role,
        },
            {
                "property": "out of Team now",
                "comparator": "checkbox_is",
                "value": "No",
            }
        ]
        people = team.build_query(filter=filter_params).execute()
        todo_list[role] = []
        for person in people:
            d = dict()
            filter_params = [{
                "property": "title",
                "comparator": "string_contains",
                "value": person.name.replace(u'\xa0', u''),
            }]
            person_stat = stats.build_query(filter=filter_params).execute()
            if person_stat:
                d['stats'] = person_stat[0]
                d['todo_url'] = person_stat[0].todo
                d['team'] = person
                d['name'] = person.name.replace(u'\xa0', u'')
                d['pa_for'] = []
                d['bidder_for'] = []
                for f in person_stat[0].pa_role:
                    d['pa_for'].append((f.name.replace(u'\xa0', u''), f.get_browseable_url()))
                for f in person_stat[0].bidder_role_for:
                    d['bidder_for'].append((f.name.replace(u'\xa0', u''), f.get_browseable_url()))
                todo_list[role].append(d)
            else:
                print(person.name.replace(u'\xa0', u''), 'not found in stats')
    return todo_list


def weekly_todo_pa(token, staff, calendar):
    print('pa start')
    for pa in staff:
#        if pa['name'] != 'Denys Safonov':
#            continue
        freelancers = ', '.join(map(lambda c: '[{}]({})'.format(c[0], c[1]), pa['pa_for']))
        print(f"{pa['name']} start")

        # Monday
        todo = list()
        todo.append('Memo - проверить наличие и адекватность [Timelogs]'
                    '(https://www.upwork.com/reports/pc/timelogs)')
        todo.append(f'Запросить available and planned hours у {freelancers}')
        todo.append(f'Заполнить fact в [Workload]'
                    f'(https://www.notion.so/Workload-ef6a6d4e3bbb41d8b4286b339f603aba) по '
                    f'{freelancers}')
        todo.append(f'Собрать Stats из Upwork и Загрузить на pCLoud по {freelancers}')
        create_todo(token, calendar['mon'], pa['todo_url'], todo, text='')

        # Tuesday
        todo = list()
        for f in map(lambda c: '[{}]({})'.format(c[0], c[1]), pa['pa_for']):
            todo.append(f'Обновить профиль {f}')
        todo.append('Проверить наличие апдейтов в pcloud по активным контрактам ')
        create_todo(token, calendar['tue'], pa['todo_url'], todo, text='')

        # Wednesday
        todo = list()
        todo.append('Ревизия профилей [https://www.upwork.com/freelancers/agency/roster#/]'
                    '(https://www.upwork.com/freelancers/agency/roster#/)')
        todo.append('Сказать, если set to private '
                    '[https://support.upwork.com/hc/en-us/articles/115003975967-Profile-Changed-to-Private-]'
                    '(https://support.upwork.com/hc/en-us/articles/115003975967-Profile-Changed-to-Private-)'
                    'волшебная ссылка активации профиля: '
                    '[https://support.upwork.com/hc/en-us?request=t_private_profile]'
                    '(https://support.upwork.com/hc/en-us?request=t_private_profile)')
        for f in map(lambda c: '[{}]({})'.format(c[0], c[1]), pa['pa_for']):
            todo.append(f'Проконтролировать выполнение Обновления профиля {f}')
        create_todo(token, calendar['wed'], pa['todo_url'], todo, text='')

        # Thursday
        todo = list()
        todo.append('Проверить заливку рабочих материалов на pCloud/Github')
        create_todo(token, calendar['wed'], pa['todo_url'], todo, text='')

        # Friday
        todo = list()
        todo.append(f'Проверить ДР своих фрилансеров на следующей неделе {freelancers}')
        todo.append(f'Запросить информацию по отпускам и day-off {freelancers}')
        todo.append(f'Занести информацию по отпускам и day-off {freelancers} в Календарь')
        create_todo(token, calendar['fri'], pa['todo_url'], todo, text='')
        print(f"{pa['name']} done")
    print('pa done')

def weekly_todo_cc(token, staff, calendar):
    print('CC start')
    for cc in staff:
#        if cc['name'] != 'Denys Safonov':
#           continue
        print(f"{cc['name']} start")
        # Monday
        todo = list()
        todo.append('Ping клиентов с открытыми контрактами, которые пропали')
        create_todo(token, calendar['mon'], cc['todo_url'], todo, text='')

        # Tuesday
        todo = list()
        todo.append('Проверить заливку рабочих материалов на pCloud/Github')
        create_todo(token, calendar['tue'], cc['todo_url'], todo, text='')

        # Thursday
        todo = list()
        todo.append('Апдейт по всем открытым контрактам в [Contracts]'
                    '(https://www.notion.so/bd59fed23f2a43b9b5fec15a57537790#fe3f6f286ee54565b1c4b8a9fed7d36b)')
        create_todo(token, calendar['thu'], cc['todo_url'], todo, text='')

        # Friday
        todo = list()
        todo.append('Проверить,что фрилансер сообщил клиентам о day-off или отпуске на следующей неделе')
        create_todo(token, calendar['fri'], cc['todo_url'], todo, text='')
        print(f"{cc['name']} done")
    print('CC done')

def weekly_todo_bidder(token, staff, calendar):
    print('bidder start')
    for bidder in staff:
#        if bidder['name'] != 'Denys Safonov':
#            continue
        print(f"{bidder['name']} start")

        # Monday
        todo = list()
        todo.append('Обработать входящие инвайты и PCJ за выходные')
        todo.append('Проверить статус комнат UAMS')
        create_todo(token, calendar['mon'], bidder['todo_url'], todo, text='')

        # Wednesday
#        todo = list()
#        todo.append('Добавить и структурировать шаблоны в [Proposal templates]'
#                    '(https://www.notion.so/bd59fed23f2a43b9b5fec15a57537790#2f798130e8ca44cba913a5c645fe33fc) '
#                    'по итогам Cross-review')
#        create_todo(token, calendar['wed'], bidder['todo_url'], todo, text='Еженедельные задачи')

        # Thursday
        todo = list()
        todo.append('Проанализировать Product Updates Upwork')
        create_todo(token, calendar['thu'], bidder['todo_url'], todo, text='')

        # Friday
        todo = list()
        todo.append('Расчистить [Invites and Jobs]'
                    '(https://www.notion.so/Invites-and-Jobs-1378d59f909a408faa2974d74f65d98f) '
                    'перед выходными')
        create_todo(token, calendar['fri'], bidder['todo_url'], todo, text='')
        print(f"{bidder['name']} done")
    print('bidder done')


@app.route('/weekly_todo', methods=['GET'])
def weekly_todo():
    token_v2 = os.environ.get("TOKEN")
    d = request.args.get("date", datetime.datetime.now().date())
    roles = request.args.get("roles", '')
    roles = re.split('[, ;|\\\\/|.]', roles)  # get role list from arguments
    staff = get_todo_list_by_role(token_v2, roles)
    print('roles get done')
    
    # looking next monday
    if d.weekday() == 0:
        today = d
    else:
        today = d + timedelta(7 - d.weekday())
    # calculate days date
    dates = {
        "mon": today + timedelta(0),
        "tue": today + timedelta(1),
        "wed": today + timedelta(2),
        "thu": today + timedelta(3),
        "fri": today + timedelta(4),
        "sat": today + timedelta(5),
        "sun": today + timedelta(6)
    }

    for role in roles:
        if role == 'PA':
            weekly_todo_pa(token_v2, staff[role], dates)
        elif role == 'CC':
            weekly_todo_cc(token_v2, staff[role], dates)
        elif role == 'Bidder':
            weekly_todo_bidder(token_v2, staff[role], dates)
        else:
            return f"Can't find Function for role {role}"
    return 'Done!'


@app.route('/kick_staff', methods=['GET'])
def kick_staff():
    token_v2 = os.environ.get("TOKEN")
    date = request.args.get("date", None)
    contracts_day = request.args.get("contracts_day", 9, type=int)
    projects_day = request.args.get("projects_day", contracts_day, type=int)
    client_days_before = request.args.get("client_day", 14, type=int)
    cc_tag = request.args.get("no_contracts", None)
    pm_tag = request.args.get("no_projects", None)
    cc = True if cc_tag is None else False
    pm = True if pm_tag is None else False
    if cc:
        contracts = get_contracts(token_v2, contracts_day)
        print('contracts done')
    else:
        contracts = []
    if pm:
        projects = get_projects(token_v2, projects_day)
        print('projects done')
    else:
        projects = []

    todo = dict()
    todo = parse_staff(todo, contracts, 'contracts', client_days_before)
    todo = parse_staff(todo, projects, 'projects', client_days_before)
    for key in todo:
        task = todo[key]
        print('start todo')
        if task['contracts']:
            create_todo(token_v2, date, task['todo_url'], map(lambda c: '[{}]({})'.format(c[0], c[1]),
                                                              task['contracts']),
                        "Контракты не получали обновления на прошлой неделе. Пожалуйста, срочно обнови:")

        if task['projects']:
            create_todo(token_v2, date, task['todo_url'], map(lambda p: '[{}]({})'.format(p[0], p[1]),
                                                              task['projects']),
                        "Проекты не получали обновления на прошлой неделе. Пожалуйста, срочно обнови:")

        if task['clients']:
            create_todo(token_v2, date, task['todo_url'], map(lambda t: '[{}]({})'.format(t[0], t[1]),
                                                              task['clients']),
                        "Занеси новую информацию которую ты узнал про клиентов:")
    return "Done!"


@app.route('/proposals_check', methods=['GET'])
def proposals_check():
    token_v2 = os.environ.get("TOKEN")
    date = request.args.get("date", None)
    days = request.args.get("days_before", 7, type=int)
    proposals = get_proposals(token_v2, days)
    todo = dict()
    todo = parse_staff(todo, proposals, 'proposals', 0)
    for key in todo:
        task = todo[key]
        print('start todo')
        if task['proposals']:
            create_todo(token_v2, date, task['todo_url'], map(lambda p: '[{}]({})'.format(p[0], p[1]),
                                                              task['proposals']),
                        "Теплый клиент остывает, нужно срочно что то делать. Проверь:")
    return "Done!"


@app.route('/todoone', methods=['GET'])
def todo_one():
    member = request.args.get("member")
    token_v2 = os.environ.get("TOKEN")
    todo = "{}".format(request.args.get("todo")).split("||")
    text = request.args.get("text")
    date = request.args.get("date", None)
    if urllib.parse.unquote(member).find("https://www.notion.so") != -1: 
        todo_url = urllib.parse.unquote(member)
    else: 
        todo_url = get_toto_url_by_name(token_v2, member)
    if todo_url is not None:
        create_todo(token_v2, date, todo_url, todo, text)
        return f'added to {member} {text if text else ""} {todo}  to Notion'
    else:
        return f'{member} not found in StatsDB in Notion or not Notion URL'


@app.route('/rss', methods=['POST'])
def rss():
    collection_url = request.form.get("collectionURL")
    subject = request.form.get('subject')
    token_v2 = os.environ.get("TOKEN")
    link = request.form.get('link')
    description = request.form.get('description')
    print(f'add {subject} {link}')
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
    collection_url = request.form.get("collectionURL")
    description = request.form.get('description')
    subject = request.form.get('subject')
    token_v2 = os.environ.get("TOKEN")
    invite_to = request.form.get('inviteto')
    link = request.form.get('link')
    print(f'add {subject} {link}')
    create_pcj(token_v2, collection_url, subject, description, invite_to, link)
    return f'added {subject} receipt to Notion'


@app.route('/invites', methods=['POST'])
def invites():
    collection_url = request.form.get("collectionURL")
    description = request.form.get('description')
    subject = request.form.get('subject')
    token_v2 = os.environ.get("TOKEN")
    invite_to = request.form.get('inviteto')
    print(f'add {subject}')
    create_invite(token_v2, collection_url, subject, description, invite_to)
    return f'added {subject} receipt to Notion'


if __name__ == '__main__':
    app.debug = True
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
