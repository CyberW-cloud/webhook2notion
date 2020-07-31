import re
import urllib.parse
from datetime import timedelta
import calendar
import pytz
from flask import Flask, request
from notion.block import *
from notion.client import NotionClient
from notion.collection import CollectionRowBlock

from notion_helpers import *

timezone = "Europe/Kiev"

app = Flask(__name__)



    

@app.route("/todo_test", methods=["GET"])
def todo_test():
   

    site = "https://www.notion.so/0aead28cb9f34ec2b41a9af19b96817a?v=1266d9ce8cbd4c968d29b4b877bed345"
    token_v2 = os.environ.get("TOKEN")

    client = NotionClient(token_v2)
    cv = client.get_collection_view(site)

    # get projects with TODO status
    filter_params = {
        "filters": [
            {
                "filter": {"value": {"type": "exact", "value": "DONE"}, "operator": "enum_is"},
                "property": "Status",
            }
        ],
        "operator": "and",
    }
    cv = cv.build_query(filter=filter_params)
    result = cv.execute()
            



    # adding 12 hrs bc notion thinks that days start at 12 am
    
    #going over all results to send them for addition simultaneously
    s = ""
    page = client.get_block(site)
    changes = []
    for todo in result:
        set_date = todo.set_date.start + datetime.timedelta(0,0,0,0,0,12)
        n = datetime.datetime.now()
        if(n.date()>set_date.date()):
            
            if("Daily" == todo.periodicity[0]):
                
                due_date = todo.due_date.start + datetime.timedelta(1)
    
                set_date = due_date - datetime.timedelta(0,0,0,0,0,12)

                changes.append({"set":set_date , "due":due_date , "id":todo.id})

            if("w" in todo.periodicity[0]):
                
                #if format is *t/w and includes days
                if("w" == todo.periodicity[0][3]):
                    times_per_week = int(todo.periodicity[0][0])
                    
                    week = ["Mo", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                    per_numbered = []
                    day = datetime.datetime.today().weekday()
                    
                    target = -1
                    for i in todo.periodicity:
                        if i in week:
                            per_numbered.append(week.index(i))

                    per_numbered.sort()
                    
                    target_day = -1
                    for i in per_numbered:
                        if i>day:
                            target_day = i

                    if target_day == -1:
                        
                        target_day = per_numbered[0]
                        offset = datetime.timedelta(7 + target_day-day)

                    else:
                        offset = datetime.timedelta(target_day-day)

                    due_date = datetime.datetime.today() + offset

                #if format is 1t/*w
                else:
                    offset = datetime.timedelta(int(todo.periodicity[0][3]) * 7)

                    due_date = todo.due_date.start + datetime.timedelta(offset)


                set_date = due_date - datetime.timedelta(1)

                changes.append({"set":set_date , "due":due_date , "id":todo.id})

            if("m" in todo.periodicity[0]):
                if("1t/m" == todo.periodicity[0]):
                    months = 1
                    offset = 1    
                else:
                    months = int(todo.periodicity[0][3])
                    offset = 2

                month = todo.due_date.start.month - 1 + months
                year = todo.due_date.start.year + month // 12
                month = month % 12 + 1
                day = min(todo.due_date.start.day, calendar.monthrange(year,month)[1])
                
                due_date = datetime.datetime(year, month, day, todo.due_date.start.hour, todo.due_date.start.minute)

                set_date = due_date - datetime.timedelta(0,0,0,0,0,12,offset)

                changes.append({"set":set_date , "due":due_date , "id":todo.id})
        else:
            s = str(set_date.date()) + " ||| " + str(datetime.datetime.now().date())
            if(todo.set_date.start.date() == datetime.datetime.now().date()):
                todo.status = "TO DO"


    for record in cv.collection.get_rows():
        for i in changes:
            if i["id"] == record.id:
                record.set_property("Due Date", i["due"])
                record.set_property("Set date", i["set"])
    
    return(s)

def parse_staff(todo, table, obj, client_days_before):
    test_date = datetime.datetime.now()
    test_date = test_date.replace(hour=12, minute=0, second=0, microsecond=0) - datetime.timedelta(
        days=client_days_before
    )
    # Preparing data to make task in Notion.
    # group and clarify (by set behavior) data by person_name
    for row in table:
        person = row["person_name"]
        if person not in todo:
            todo[person] = dict()
            todo[person]["todo_url"] = row["person"].todo
            todo[person]["projects"] = set()
            todo[person]["contracts"] = set()
            todo[person]["clients"] = set()
            todo[person]["proposals"] = set()
        todo[person][obj].add(row["url"])
        # check updates of client and add to task if it's need
        if row["client"] is not None:
            if row["client"].Modified <= test_date:
                todo[person]["clients"].add(
                    (row["client"].name.replace("\xa0", ""), row["client"].get_browseable_url())
                )
    print(todo)            
    return todo


def get_projects(token, days_before):
    client = NotionClient(token)
    cv = client.get_collection_view(
        "https://www.notion.so/addccbcaf545405292db498941c9538a?v=e86f54933acc461ca413afa6a2958cdc"
    )
    # e86f54933acc461ca413afa6a2958cdc - no_filters_view
    # 1ed5f8ce4e834f1382ffb447976e944f - python_view

    # calculate date for filter now() - days_before. Stupid notion starts new day at 12:00 a.m.
    # n = datetime.datetime.now(pytz.timezone("Europe/Kiev"))
    n = datetime.datetime.now()
    n = n.replace(hour=12, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days_before)

    # get projects InProgress with date less when now()-days before
    filter_params = {
        "filters": [
            {
                "filter": {"value": {"type": "exact", "value": "inProgress"}, "operator": "enum_is"},
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
    res = []
    # for every project get person and client
    # for row in result:
    for index, row in result.iterrows():
        project = dict()
        if row["pm"]:
            project["person"] = row["pm"][0]
        else:
            for contract in row["contracts"]:
                if contract.coordinator[0]:
                    if contract.coordinator[0].name != "selfCC" and contract.status == "In Progress":
                        project["person"] = contract.coordinator[0]
                        break
        if project["person"]:
            project["person_name"] = project["person"].name.replace("\xa0", "")
        project["client"] = row["client_name"][0] if row["client_name"] else None
        project["url"] = row["name"].replace("\xa0", ""), row["row"].get_browseable_url()
        if project["person"] is None:
            continue
        else:
            res.append(project)
    return res


def get_contracts(token, days_before):
    client = NotionClient(token)
    cv = client.get_collection_view(
        "https://www.notion.so/5a95fb63129242a5b5b48f18e16ef19a?v=48599e7a184a4f32be2469e696367949"
    )
    # 48599e7a184a4f32be2469e696367949 - no_filters_view
    # 02929acd595a48dda28cb9e2ff6ae210 - python_view

    # calculate date for filter now() - days_before. Stupid notion starts new day at 12:00 a.m.
    # n = datetime.datetime.now(pytz.timezone("Europe/Kiev"))
    n = datetime.datetime.now()
    n = n.replace(hour=12, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days_before)

    # get contracts In Progress with date less when now()-days before and w/o project
    filter_params = {
        "filters": [
            {
                "filter": {"value": {"type": "exact", "value": "In Progress"}, "operator": "enum_is"},
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
            {"filter": {"operator": "is_empty"}, "property": "Project"},
        ],
        "operator": "and",
    }
    cv = cv.build_query(filter=filter_params)
    result = cv.execute()

    result = nview_to_pandas(result)
    res = []
    # for every contract get person (how care this about contract and client for next check
    for index, row in result.iterrows():
        contract = dict()
        if not row["coordinator"]:
            continue
        else:
            contract["person"] = row["coordinator"][0]
            if contract["person"].name.replace("\xa0", "") == "selfCC":
                contract["person"] = row["freelancer"][0] if row["freelancer"] else None
            if contract["person"]:
                contract["person_name"] = contract["person"].name.replace("\xa0", "")
        contract["client"] = row["client_name"][0] if row["client_name"] else None
        contract["url"] = row["contract_name"].replace("\xa0", ""), row["row"].get_browseable_url()
        res.append(contract)
    return res

def get_proposals(token, days_before):
    client = NotionClient(token)
    cv = client.get_collection_view(
        "https://www.notion.so/99055a1ffb094e0a8e79d1576b7e68c2?v=bc7d781fa5c8472699f2d0c1764aa553"
    )

    # calculate date for filter now() - days_before. Stupid notion starts new day at 12:00 a.m.
    n = datetime.datetime.now(pytz.timezone("Europe/Kiev"))
    n = n.replace(hour=12, minute=0, second=0, microsecond=0) - datetime.timedelta(days=days_before)
    stats = client.get_collection_view(
        "https://www.notion.so/e4d36149b9d8476e9985a2c658d4a873?v=3238ddee2ea04d5ea302d99fc2a2d5cc"
    )
    # get proposal replied, not declined and with empty contract field
    filter_params = {
        "filters": [
            {"property": "Reply", "filter": {"operator": "checkbox_is", "value": {"type": "exact", "value": True}}},
            {"property": "Declined", "filter": {"operator": "checkbox_is", "value": {"type": "exact", "value": False}}},
            {"property": "Contract", "filter": {"operator": "is_empty"}},
            {
                "property": "Modified",
                "filter": {
                    "operator": "date_is_on_or_before",
                    "value": {
                        "type": "exact",
                        "value": {
                            "type": "date",
                            "start_date": str(n.date())
                            # "start_date": "2020-03-24",
                        },
                    },
                },
            },
        ],
        "operator": "and",
    }

    cv = cv.build_query(filter=filter_params)
    result = cv.execute()
    res = []
    # for every proposal get person
    for row in result:
        proposal = dict()
        if row.CC:
            proposal["person"] = row.CC[0]
        else:
            proposal["person"] = row.Sent_by if row.Sent_by else None
        if proposal["person"]:
            proposal["person_name"] = proposal["person"].full_name.replace("\xa0", "")
            # person field is class User, so we need linked it to stats DB. Try to Find person in stats DB
            filter_params = {
                "filters": [
                    {
                        "property": "title",
                        "filter": {
                            "operator": "string_contains",
                            "value": {"type": "exact", "value": proposal["person_name"]},
                        },
                    }
                ],
                "operator": "and",
            }
            person_stat = stats.build_query(filter=filter_params).execute()
            if person_stat:
                proposal["person"] = person_stat[0]
            else:
                print(proposal["person_name"], "not found in stats")
        proposal["url"] = str(row.Proposal_ID).replace("\xa0", ""), row.get_browseable_url()
        proposal["client"] = None
        if proposal["person"] is None:
            continue
        else:
            res.append(proposal)
    return res


@app.route("/kick_staff", methods=["GET"])
def kick_staff():
    print("starting kickstaff")
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
        print("contracts done")
    else:
        contracts = []
    if pm:
        projects = get_projects(token_v2, projects_day)
        print("projects done")
    else:
        projects = []

    todo = dict()
    todo = parse_staff(todo, contracts, "contracts", client_days_before)
    todo = parse_staff(todo, projects, "projects", client_days_before)
    for key in todo:
        task = todo[key]
        if task["contracts"]:
            create_todo(
                token_v2,
                date,
                task["todo_url"],
                map(lambda c: "[{}]({})".format(c[0], c[1]), task["contracts"]),
                "Контракты не получали обновления на прошлой неделе. Пожалуйста, срочно обнови:",
            )

        if task["projects"]:
            create_todo(
                token_v2,
                date,
                task["todo_url"],
                map(lambda p: "[{}]({})".format(p[0], p[1]), task["projects"]),
                "Проекты не получали обновления на прошлой неделе. Пожалуйста, срочно обнови:",
            )

        if task["clients"]:
            create_todo(
                token_v2,
                date,
                task["todo_url"],
                map(lambda t: "[{}]({})".format(t[0], t[1]), task["clients"]),
                "Занеси новую информацию которую ты узнал про клиентов:",
            )
    print("kickstaff done")
    return "Done!"




@app.route("/proposals_check", methods=["GET"])
def proposals_check():
    print(f"Proposal check started")
    token_v2 = os.environ.get("TOKEN")
    date = request.args.get("date", None)
    days = request.args.get("days_before", 7, type=int)
    proposals = get_proposals(token_v2, days)
    todo = dict()
    todo = parse_staff(todo, proposals, "proposals", 0)
    for key in todo:
        task = todo[key]
        print("start todo")
        print(task["todo_url"])
        if task["proposals"]:
            print(f"ToDo: {task['todo_url']}")
            create_todo(
                token_v2,
                date,
                task["todo_url"],
                map(lambda p: "[{}]({})".format(p[0], p[1]), task["proposals"]),
                "Теплый клиент остывает, нужно срочно что то делать. Проверь:",
            )
    print(f"Proposal check finished")
    return "Done!"


def get_todo_url_by_name(token, name):
    client = NotionClient(token)
    stats = client.get_collection_view(
        "https://www.notion.so/e4d36149b9d8476e9985a2c658d4a873?v=3238ddee2ea04d5ea302d99fc2a2d5cc"
    )
    filter_params = [{"property": "title", "comparator": "string_contains", "value": name}]
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
    print(link)
    page = client.get_block(link)
    tasks = todo

    return create_new_task(page, "", text=text, date=date, timezone=timezone, tasks=tasks)


@app.route("/todoone", methods=["GET"])
def todo_one():
    member = request.args.get("member")
    token_v2 = os.environ.get("TOKEN")
    todo = "{}".format(request.args.get("todo")).split("||")
    text = request.args.get("text")
    date = request.args.get("date", None)
    if urllib.parse.unquote(member).find("https://www.notion.so") != -1:
        todo_url = urllib.parse.unquote(member)
    else:
        todo_url = get_todo_url_by_name(token_v2, member)
    if todo_url is not None:
        create_todo(token_v2, date, todo_url, todo, text)
        print(f'added to {member} {text if text else ""} {todo}  to Notion')
        return f'added to {member} {text if text else ""} {todo}  to Notion'
    else:
        print(f"{member} not found in StatsDB in Notion or not Notion URL")
        return f"{member} not found in StatsDB in Notion or not Notion URL"


def weekly_todo_pa(token, staff, calendar):
    print("PAs start")
    for pa in staff:
        #        if pa['name'] != 'Denys Safonov':
        #            continue
        print(f"PA {pa['name']} start")
        freelancers = ", ".join(map(lambda c: "[{}]({})".format(c[0], c[1]), pa["pa_for"]))

        # Monday
        todo = list()
        todo.append("Memo - проверить наличие и адекватность [Timelogs]" "(https://www.upwork.com/reports/pc/timelogs)")
        if freelancers:
            todo.append(f"Запросить available and planned hours у {freelancers}")
            todo.append(
                f"Заполнить fact в [Workload]"
                f"(https://www.notion.so/Workload-ef6a6d4e3bbb41d8b4286b339f603aba) по "
                f"{freelancers}"
            )
            todo.append(f"Собрать Stats из Upwork и Загрузить на pCLoud по {freelancers}")
        create_todo(token, calendar["mon"], pa["todo_url"], todo, text="")

        # Tuesday
        todo = list()
        for f in map(lambda c: "[{}]({})".format(c[0], c[1]), pa["pa_for"]):
            todo.append(f"Обновить профиль {f}")
        todo.append("Проверить наличие апдейтов в pcloud по активным контрактам ")
        create_todo(token, calendar["tue"], pa["todo_url"], todo, text="")

        # Wednesday
        todo = list()
        todo.append(
            "Ревизия профилей [https://www.upwork.com/freelancers/agency/roster#/]"
            "(https://www.upwork.com/freelancers/agency/roster#/)"
        )
        todo.append(
            "Сказать, если set to private "
            "[https://support.upwork.com/hc/en-us/articles/115003975967-Profile-Changed-to-Private-]"
            "(https://support.upwork.com/hc/en-us/articles/115003975967-Profile-Changed-to-Private-)"
            "волшебная ссылка активации профиля: "
            "[https://support.upwork.com/hc/en-us?request=t_private_profile]"
            "(https://support.upwork.com/hc/en-us?request=t_private_profile)"
        )
        for f in map(lambda c: "[{}]({})".format(c[0], c[1]), pa["pa_for"]):
            todo.append(f"Проконтролировать выполнение Обновления профиля {f}")
        create_todo(token, calendar["wed"], pa["todo_url"], todo, text="")

        # Thursday
        todo = list()
        todo.append("Проверить заливку рабочих материалов на pCloud/Github")
        create_todo(token, calendar["wed"], pa["todo_url"], todo, text="")

        # Friday
        todo = list()
        todo.append(f"Проверить ДР своих фрилансеров на следующей неделе {freelancers}")
        todo.append(f"Запросить информацию по отпускам и day-off {freelancers}")
        todo.append(f"Занести информацию по отпускам и day-off {freelancers} в Календарь")
        create_todo(token, calendar["fri"], pa["todo_url"], todo, text="")

        print(f"PA {pa['name']} done")
    print("PAs done")


def weekly_todo_cc(token, staff, calendar):
    print("CCs start")
    for cc in staff:
        # if cc['name'] != 'Davyd Podosian':
        #     continue
        print(f"CC {cc['name']} start")
        # Monday
        todo = list()
        todo.append("Ping клиентов с открытыми контрактами, которые пропали")
        todo.append("Обнови свой профиль, он тоже может приносить лиды (если не знаешь что улучшить спроси у коллег")
        create_todo(token, calendar["mon"], cc["todo_url"], todo, text="")

        # Tuesday
        todo = list()
        todo.append("Проверить заливку рабочих материалов на pCloud/Github")
        create_todo(token, calendar["tue"], cc["todo_url"], todo, text="")

        # Thursday
        todo = list()
        todo.append(
            "Апдейт по всем открытым контрактам в [Contracts]"
            "(https://www.notion.so/bd59fed23f2a43b9b5fec15a57537790#fe3f6f286ee54565b1c4b8a9fed7d36b)"
        )
        create_todo(token, calendar["thu"], cc["todo_url"], todo, text="")

        # Friday
        todo = list()
        todo.append("Проверить,что фрилансер сообщил клиентам о day-off или отпуске на следующей неделе")
        create_todo(token, calendar["fri"], cc["todo_url"], todo, text="")
        print(f"CC {cc['name']} done")
    print("CCs done")

def weekly_todo_fl(token, staff, calendar):
    print("Mon Fl's start")
    for fl in staff:
        print(f"FL {fl['name']} start")
        # Monday
        todo = list()
        todo.append(f"Загрузи [статы](https://www.upwork.com/ab/g/who-viewed/) по [ссылке]({fl['stats_upload']})")
        todo.append(f"Коментом, тегнув {fl['pa_name']}, напиши свою планируемую загрузку на неделю")
        create_todo(token, calendar["mon"], fl["todo_url"], todo, text="")
    print("Mon FL done")

def friday_todo_fl(token, staff, calendar):
    print("Fri Fl's start")
    for fl in staff:
#        if fl['name'] == 'Denys Safonov':         
        print(f"FL {fl['name']} start")
        # Friday
        todo = list()
        todo.append(f"Коментом напиши какие day-off ты планируешь на следующую неделю и тегни {fl['pa_name']}, иначе напиши - Не планирую")
        create_todo(token, calendar["fri"], fl["todo_url"], todo, text="")		
    print("Fri FL done")    

def weekly_todo_bidder(token, staff, calendar):
    print("bidders start")
    for bidder in staff:
        #        if bidder['name'] != 'Denys Safonov':
        #        continue
        print(f"bidder {bidder['name']} start")

        # Monday
        todo = list()
        todo.append("Обработать входящие инвайты и PCJ за выходные")
        todo.append("Проверить статус комнат UAMS")
        create_todo(token, calendar["mon"], bidder["todo_url"], todo, text="")

        # Wednesday
        #        todo = list()
        #        todo.append('Добавить и структурировать шаблоны в [Proposal templates]'
        #                    '(https://www.notion.so/bd59fed23f2a43b9b5fec15a57537790#2f798130e8ca44cba913a5c645fe33fc) '
        #                    'по итогам Cross-review')
        #        create_todo(token, calendar['wed'], bidder['todo_url'], todo, text='Еженедельные задачи')

        # Thursday
        todo = list()
        todo.append("Проанализировать Product Updates Upwork")
        create_todo(token, calendar["thu"], bidder["todo_url"], todo, text="")

        # Friday
        todo = list()
        todo.append(
            "Расчистить [Invites and Jobs]"
            "(https://www.notion.so/Invites-and-Jobs-1378d59f909a408faa2974d74f65d98f) "
            "перед выходными"
        )
        create_todo(token, calendar["fri"], bidder["todo_url"], todo, text="")
        print(f"bidder {bidder['name']} done")
    print("bidders done")


def get_todo_list_by_role(token, roles):
    client = NotionClient(token)
    team = client.get_collection_view(
        "https://www.notion.so/7113e573923e4c578d788cd94a7bddfa?v=536bcc489f93433ab19d697490b00525"
    )
    team_df = nview_to_pandas(team)
    # python 536bcc489f93433ab19d697490b00525
    # no_filters 375e91212fc4482c815f0b4419cbf5e3
    stats = client.get_collection_view(
        "https://www.notion.so/e4d36149b9d8476e9985a2c658d4a873?v=3238ddee2ea04d5ea302d99fc2a2d5cc"
    )
    # stats_df = nview_to_pandas(stats)
    todo_list = dict()
    for role in roles:
        # filter_params = [
        #     {"property": "Roles", "comparator": "enum_contains", "value": role},
        #     {"property": "out of Team now", "comparator": "checkbox_is", "value": "No"},
        # ]
        # people = team.build_query(filter=filter_params).execute()

        team_df.loc[:, "pa_name"] = team_df.pa.map(lambda x: next(iter(x), None))
        team_df.pa_name = team_df.pa_name.apply(lambda x: x.name.replace("\xa0", "") if x else "")
        team_df.loc[:, "bidder_name"] = team_df.bidder.map(lambda x: next(iter(x), None))
        team_df.bidder_name = team_df.bidder_name.apply(lambda x: x.name.replace("\xa0", "") if x else "")
        people = team_df[[role in x for x in team_df["roles"]]]
        people = people[people["out_of_team_now"] != True]

        todo_list[role] = []
        for index, person in people.iterrows():
            d = dict()
            # filter_params = [
            #     {"property": "title", "comparator": "string_contains", "value": person.name.replace("\xa0", "")}
            # ]
            # person_stat = stats.build_query(filter=filter_params).execute()

            # person_stat = stats_df[stats_df['name'] == person['name']]

            # if person:
            # d["stats"] = person[0]
            d["todo_url"] = person["todo"].split()[1]
            d["stats_upload"] = person["stats_upload"]
            d["team"] = person
            d["name"] = person["name"].replace("\xa0", "")
            d["pa_for"] = []
            d["bidder_for"] = []
            d["pa_name"] = person["pa_name"]
            for i, f in team_df[team_df["pa_name"] == person["name"]].iterrows():
                d["pa_for"].append((f["name"], f["row"].get_browseable_url()))
            for i, f in team_df[team_df["bidder_name"] == person["name"]].iterrows():
                d["bidder_for"].append((f["name"], f["row"].get_browseable_url()))
            todo_list[role].append(d)
            # else:
            #     print(person.name.replace("\xa0", ""), "not found in stats")
    # print(*todo_list.items(), sep="\n")
    return todo_list


@app.route("/weekly_todo", methods=["GET"])
def weekly_todo():
    roles = request.args.get("roles", "")
    roles = re.split("[, ;|\\\\/|.]", roles)  # get role list from arguments
    print(f"weekly todo for {roles} start")
    token_v2 = os.environ.get("TOKEN")
    d = request.args.get("date", datetime.datetime.now().date())
    staff = get_todo_list_by_role(token_v2, roles)
    print("roles get done")

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
        "sun": today + timedelta(6),
    }
    for role in roles:
        if role == "PA":
            weekly_todo_pa(token_v2, staff[role], dates)
        elif role == "CC":
            weekly_todo_cc(token_v2, staff[role], dates)
        elif role == "Bidder":
            weekly_todo_bidder(token_v2, staff[role], dates)
        elif role == "FL":
            weekly_todo_fl(token_v2, staff[role], dates)    
        else:
            return f"Can't find Function for role {role}"
    print(f"weekly todo for {roles} done")
    return "Done!"
  
@app.route("/friday_todo", methods=["GET"])
def friday_todo():
    roles = request.args.get("roles", "")
    roles = re.split("[, ;|\\\\/|.]", roles)  # get role list from arguments
    print(f"Friday todo for {roles} start")
    token_v2 = os.environ.get("TOKEN")
    d = request.args.get("date", datetime.datetime.now().date())
    staff = get_todo_list_by_role(token_v2, roles)
    print("roles get done")

    today = d

    dates = {
        "fri": today,
    }
    for role in roles:
        if  role == "FL":
            friday_todo_fl(token_v2, staff[role], dates)    
        else:
            return f"Can't find Function for role {role}"
    print(f"Fiday todo for {roles} done")
    return "Done!"


def create_rss(token, collection_url, subject, link, description):
    # notion
    client = NotionClient(token)
    cv = client.get_collection_view(collection_url)
    row = cv.collection.add_row()
    row.name = subject
    row.link = link
    row.description = description
    if link.find("https://www.upwork.com/blog/") != -1:
        row.label = "upwok blog"
    if link.find("https://community.upwork.com/t5/Announcements/") != -1:
        row.label = "upwork community announcements"


@app.route("/rss", methods=["POST"])
def rss():
    collection_url = request.form.get("collectionURL")
    subject = request.form.get("subject")
    token_v2 = os.environ.get("TOKEN")
    link = request.form.get("link")
    description = request.form.get("description")
    print(f"add {subject} {link}")
    create_rss(token_v2, collection_url, subject, link, description)
    return f"added {subject} receipt to Notion"


def create_message(token, parent_page_url, message_content):
    # notion
    client = NotionClient(token)
    page = client.get_block(parent_page_url)

    pattern = '#"(?$0'
    insert_after = None
    div = 0
    divs = 0
    for child in page.children:
        if child.type == "factory":
            insert_after = child
            break
        if child.type == "text" and child.title == pattern:
            insert_after = child
            break
        if child.type == "divider":
            if div == 1:
                divs += 1
            else:
                div = 1
                divs = 1
            if divs == 3:
                insert_after = child
                break
            else:
                continue
        div = 0

    a = page.children.add_new(TextBlock, title=" . ")
    b = page.children.add_new(DividerBlock)
    c = page.children.add_new(
        TextBlock,
        title="{data} {msg}".format(data=datetime.datetime.now().strftime("%d-%m-%Y %H:%M"), msg=message_content),
    )
    d = page.children.add_new(DividerBlock)

    if insert_after is None:
        a.move_to(page, "first-child")
    else:
        a.move_to(insert_after, "after")
    b.move_to(a, "after")
    c.move_to(b, "after")
    d.move_to(c, "after")
    a.title = ""


@app.route("/message", methods=["GET"])
def message():
    parent_page_url = request.args.get("parent_page_url")
    token_v2 = os.environ.get("TOKEN")
    message_content = request.args.get("message")
    create_message(token_v2, parent_page_url, message_content)
    return f"added {message_content} receipt to Notion"


def create_pcj(token, collection_url, subject, description, invite_to, link):
    # notion
    item_id = re.search("%7E[\w]+", link)
    client = NotionClient(token)
    cv = client.get_collection_view(collection_url)
    row = cv.collection.add_row()
    row.name = subject[:-9]
    row.description = description
    row.status = "New"
    row.to = invite_to
    row.link = "https://www.upwork.com/ab/jobs/search/?previous_clients=all&q={}&sort=recency".format(
        urllib.parse.quote(subject[:-9])
    )
    row.id = item_id.group()[3:]


@app.route("/pcj", methods=["POST"])
def pcj():
    collection_url = request.form.get("collectionURL")
    description = request.form.get("description")
    subject = request.form.get("subject")
    token_v2 = os.environ.get("TOKEN")
    invite_to = request.form.get("inviteto")
    link = request.form.get("link")
    print(f"add {subject} {link}")
    create_pcj(token_v2, collection_url, subject, description, invite_to, link)
    return f"added {subject} receipt to Notion"


def create_invite(token, collection_url, subject, description, invite_to):
    # notion
    match = re.search("https://upwork.com/applications/\d+", description)
    url = match.group()
    item_id = re.search("\d+", url)
    client = NotionClient(token)
    cv = client.get_collection_view(collection_url)
    row = cv.collection.add_row()
    row.name = subject
    row.description = description
    row.status = "New"
    row.to = invite_to
    row.link = url
    row.id = item_id.group()


@app.route("/invites", methods=["POST"])
def invites():
    collection_url = request.form.get("collectionURL")
    description = request.form.get("description")
    subject = request.form.get("subject")
    token_v2 = os.environ.get("TOKEN")
    invite_to = request.form.get("inviteto")
    print(f"add {subject}")
    create_invite(token_v2, collection_url, subject, description, invite_to)
    return f"added {subject} receipt to Notion"


def create_response(type, data):
    # Development
    # collection_url = "https://www.notion.so/c8cc4837308c4b299a88d36d07bc2f4f?v=dd587a4640aa41bd9ff88ca268aff553"
    # Production
    collection_url = "https://www.notion.so/1f4aabb8710f4c89a3411de53fc7222a?v=0e8184ceca384767917f928bb3d20e6f"
    token = os.environ.get("TOKEN")
    client = NotionClient(token)

    cv = client.get_collection_view(collection_url)
    upwork_profile = data["Upwork profile"]
    upwork_id = upwork_profile[upwork_profile.find("~") + 1: upwork_profile.find("~") + 19]
    records = cv.collection.get_rows()
    row_exist = None
    for record in records:
        rec_profile = record.get_property("upwork_profile")
        if rec_profile != "":
            uw_id = rec_profile[rec_profile.find("~") + 1: rec_profile.find("~") + 19]
            if uw_id == upwork_id:
                row_exist = record
                break
    row = row_exist if row_exist is not None else cv.collection.add_row()
    row.set_property("Type", type)
    for i in data:
        print(f"{i}: {data[i]}")
        if i == "timestamp":
            row.set_property("Form filled", datetime.datetime.strptime(data[i], "%Y-%m-%dT%H:%M:%S.%fZ"))
        else:
            if "_".join(str.lower(i).split()) in row.get_all_properties().keys():
                try:
                    row.set_property("_".join(str.lower(i).split()), data[i])
                except Exception:
                    print(f'unable to insert value "{data[i]}" into column "{i}"')
            else:
                print(f'no column "{i}" in target table')
    row.set_property("Status", "Form filled")





@app.route("/responses", methods=["POST"])
def responses():
    accepted_types = ["designer", "developer", "manager", "bidders", "recruiter"]
    print("start new response")
    res_type = request.args.get("type")
    data = request.get_json()
    if res_type in accepted_types:
        print(f'start creating {res_type} response from {data["Name"]}')
        create_response(res_type, data)
    else:
        print(f"type '{res_type}' is not supported yet")
        return f"type '{res_type}' is not supported yet"
    print(f'created new {res_type} response from {data["Name"]}')
    return f'created new {res_type} response from {data["Name"]}'




def parse_data_from_manychat(data):
    # Development
    # collection_url = "https://www.notion.so/d6efa1a128ea44fd92e9e2a5665a1e2b?v=b65bdd6109384d9faf30eaa8a95ec33d"
    # Production
    collection_url = "https://www.notion.so/1f4aabb8710f4c89a3411de53fc7222a?v=0e8184ceca384767917f928bb3d20e6f"
    token = os.environ.get("TOKEN")
    client = NotionClient(token)
    cv = client.get_collection_view(collection_url)

    records = nview_to_pandas(cv)
    records["upwork_id"] = records["upwork_profile"].apply(lambda x: x[x.find("~") + 1: x.find("~") + 19])

    user_info = data["user_info"]
    upwork_profile = user_info["upwork_profile"]
    email = user_info['email']
    rec = None
    if upwork_profile is not None and upwork_profile.find("~") > 0:
        upwork_id = upwork_profile[upwork_profile.find("~") + 1: upwork_profile.find("~") + 19] if upwork_profile.find("~") > 0 else None
        rec = records[records["upwork_id"] == upwork_id]
    if (rec is None or len(rec) == 0) and email is not None:
        rec = records[records["email"] == email]
    if rec is not None and len(rec) != 0:
        row = rec["row"].values[0]
    else:
        row = cv.collection.add_row()
        row.set_property("name", user_info['name'])
        if user_info['gender'] == 'male':
            gender = 'М'
        elif user_info['gender'] == 'female':
            gender = 'Ж'
        else:
            gender = ''
        row.set_property('gender', gender)
        row.set_property("email", email if email is not None else "")
        row.set_property("upwork_profile", upwork_profile if upwork_profile is not None else "")

    res = {}
    fields = data['data']
    for i in fields:
        print(f"{i}: {fields[i]}")
        res[i] = fields[i]

        if "_".join(str.lower(i).split()) in row.get_all_properties().keys():
            try:
                row.set_property("_".join(str.lower(i).split()), fields[i])
            except Exception:
                print(f'unable to insert value "{fields[i]}" into column "{i}"')
        else:
            print(f'no column "{i}" in target table')

    print(f"Data for {row.get_property('name')} updated")
    return res


@app.route("/manychat", methods=["POST"])
def manychat():
    data = request.get_json()
    result = parse_data_from_manychat(data)
    return {'version': 'v2', 'content': {}, 'data': result}


if __name__ == "__main__":
    app.debug = True
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
