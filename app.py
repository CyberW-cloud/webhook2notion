import re
import urllib.parse
from datetime import timedelta
import calendar, time
import pytz
import math
import traceback
import uuid
from flask import Flask, request, url_for

import notion
from notion.block import *
from notion.client import NotionClient
from notion.collection import CollectionRowBlock, Collection
from notion_helpers import *
from notion.utils import extract_id
from notion.operations import build_operation

import upwork
from upwork.routers.messages import Api as messageAPI
from upwork.routers.auth import Api as authAPI
from upwork.routers.organization.companies import Api as companyAPI
from upwork.routers.organization.users import Api as userAPI
from upwork.routers.freelancers.profile import Api as profileAPI
from upwork.routers.hr.freelancers.applications import Api as applicationAPI
from upwork.routers.hr.jobs import Api as jobsAPI
from upwork.routers.jobs.profile import Api as jobInfoAPI
from upwork.routers.hr.engagements import Api as engagementAPI

import psycopg2

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

timezone = "Europe/Kiev"

app = Flask(__name__)
cache = {}


#@app.errorhandler(Exception)
def before_request(error):
	print(error)
	email_report(request.path + " FAILED", datetime.datetime.now().strftime('%d, %b %Y')+"\n\n"+str(''.join(traceback.format_exception(None, error, error.__traceback__))))
	raise error 

def email_report(subject, body):
	global email_log

	gmail_user = 'tech@etcetera.kiev.ua'
	gmail_password = os.environ.get("GmailPassword")

	target = "nocommas555@gmail.com"

	# Create message container - the correct MIME type is multipart/alternative.
	msg = MIMEMultipart('alternative')
	msg['Subject'] = subject
	msg['From'] = gmail_user
	msg['To'] = target


	# Create the body of the message (a plain-text and an HTML version).
	text = ""
	html = """\
	<html>
	  <head></head>
	  <body>
		"""+body.replace("\n", "<br>")+"""
	  </body>
	</html>
	"""

	# Record the MIME types of both parts - text/plain and text/html.
	part1 = MIMEText(text, 'plain')
	part2 = MIMEText(html, 'html')

	# Attach parts into message container.
	# According to RFC 2046, the last part of a multipart message, in this case
	# the HTML message, is best and preferred.
	msg.attach(part1)
	msg.attach(part2)
	# Send the message via local SMTP server.
	mail = smtplib.SMTP('smtp.gmail.com', 587)

	mail.ehlo()

	mail.starttls()

	mail.login(gmail_user, gmail_password)
	mail.sendmail(gmail_user, target, msg.as_string())
	mail.quit()

	email_log = ""


@app.route('/tmp')
def tmp():
	#get upwork client
	login_config = upwork.Config({\
		'consumer_key': os.environ.get("ConsumerKey"),\
		'consumer_secret': os.environ.get("ConsumerSecret"),\
		'access_token': os.environ.get("AccessToken"),\
		'access_token_secret': os.environ.get("AccessSecret")})

	client = upwork.Client(login_config)

	token = os.environ.get("TOKEN")
	notion_client = NotionClient(token)

	print(get_client_from_invite(notion_client.get_block("https://www.notion.so/427842658-4ccd8a28fd3249beb5d64f95f68adf50")))

	i = 1/0


@app.route('/update_clients', methods = ["GET"])
def update_clients():
	token = os.environ.get("TOKEN")
	notion_client = NotionClient(token)

	date = str(datetime.datetime.now().day) + "." + str(datetime.datetime.now().month) + "." + str(datetime.datetime.now().year)

	clients = notion_client.get_collection_view("https://www.notion.so/0ce71695159145aa84ab4371cc1e094a?v=7daae214ec7e41f4a7130ea4d6313bc5")
	failed = notion_client.get_block("https://www.notion.so/Failed-26abe549b6394242b5c6c148e822f166")

	failed_day_page = None

	active_since_hours = request.args.get("activeSince", "24")

	if active_since_hours == "all":
		activeSince = 0
	else:
		activeSince = datetime.datetime.now() - datetime.timedelta(hours = int(active_since_hours))
		activeSince = int(activeSince.timestamp())

	filter_params = {
		"filters": [
			{
				"filter": {"value":{"type": "exact", "value": {"type": "date", "start_date": datetime.datetime.fromtimestamp(activeSince).strftime('%Y-%m-%d')}}, "operator": "date_is_on_or_after"},
				"property": "Added"
			}
		],
		"operator": "and",	  
	}
	sort_params = [{"direction": "ascending", "property": "Added"}]
	
	clients = clients.build_query(filter=filter_params, sort = sort_params)
	result = clients.execute()

	login_config = upwork.Config({\
		'consumer_key': os.environ.get("ConsumerKey"),\
		'consumer_secret': os.environ.get("ConsumerSecret"),\
		'access_token': os.environ.get("AccessToken"),\
		'access_token_secret': os.environ.get("AccessSecret")})

	client = upwork.Client(login_config)
	
	company = companyAPI(client)
	application = applicationAPI(client)
	job_info = jobInfoAPI(client)
	engagements = engagementAPI(client)


	print([x.name for x in result])
	for row in result:
		print(row.name)
		print(row.get_browseable_url())
		buyer = None

		if len(row.proposal_sent)>0 and buyer == None:
			for proposal in row.proposal_sent: 
				try:
					if proposal.job_url != None and proposal.job_url != "":
						openingCiphertext = re.search("(~|(%7E))\w+",proposal.job_url)
						if openingCiphertext != None:
							openingCiphertext = openingCiphertext.group()
					else:   
						time.sleep(1.6)
						ref = proposal.proposal_id
						openingCiphertext = client.get("/hr/v4/contractors/applications/"+ref)["data"]["openingCiphertext"]
					
					if openingCiphertext != None:
						time.sleep(1.6)
						buyer = job_info.get_specific(openingCiphertext)
						buyer = buyer["profile"]["buyer"]
						break		   
			
				except Exception as e:
					buyer = None
					continue

		if len(row.invites_and_jobs_posted)>0 and buyer == None:
			for invite in row.invites_and_jobs_posted: 
				try:

					if invite.job_url != None and invite.job_url != "":
						openingCiphertext = re.search("(~|(%7E))\w+",invite.job_url)
						if openingCiphertext != None:
							openingCiphertext = openingCiphertext.group()

					elif re.match("^[0-9]$", invite.id) == None:
						openingCiphertext = re.search( "(~|(%7E))[^?\]]*", invite.description).group().replace("%7E", "~")
						
					else:   
						time.sleep(1.6)
						ref = invite.id
						print(ref)
						openingCiphertext = client.get("/hr/v4/contractors/applications/"+ref)["data"]["openingCiphertext"]
			
					if openingCiphertext != None:
						time.sleep(1.6)
						buyer = job_info.get_specific(openingCiphertext)
						buyer = buyer["profile"]["buyer"]
						break

				except Exception as e:
					buyer = None
					continue
		if len(row.contracts)>0 and buyer == None:
			for contract in row.contracts:
				try:
					time.sleep(1.6)
					openingCiphertext = engagements.get_specific(contract.contract_id)["engagement"]["job_ref_ciphertext"]  
					time.sleep(1.6)
					buyer = job_info.get_specific(openingCiphertext)
					buyer = buyer["profile"]["buyer"]
					break
					
				except Exception as e:
					buyer = None
					continue
					
					

		if (buyer != None):
			print(buyer)
			if "op_country" in buyer.keys():
				row.country = buyer["op_country"]

			if "op_state" in buyer.keys():
				row.state = buyer["op_state"]

			if "op_city" in buyer.keys():
				if row.location == "":
					row.location = buyer["op_city"]
				else:
					if buyer["op_city"] not in row.location:
						row.location = row.location + ", " + buyer["op_city"]
				
			
			if "op_contract_date" in buyer.keys():
				row.member_since = datetime.datetime.strptime(buyer["op_contract_date"], '%B %d, %Y')

			if "op_timezone" in buyer.keys():
				time_zone = re.findall("(^UTC[+-][0-9][0-9])(?=:00)", buyer["op_timezone"])
				if len(time_zone)>0:
					row.time_zone = time_zone[0]
				elif "(Coordinated Universal Time)" in buyer["op_timezone"]:
					row.time_zone = "UTC+00"
		
		else:
			if isinstance(failed_day_page, type(None)):
				failed_day_page = failed.children.add_new(PageBlock, title = date)
			
			time.sleep(1)

			add_global_block(failed_day_page, row)


			print("NO INFO FOR CLIENT")




def add_aliases_to_summary(aliases, page, parent_row):
	token = os.environ.get("TOKEN")
	client = NotionClient(token)
	#parent_row should contain {"url", "title", "manager", "freelancer", "client_name"}
	if not isinstance(parent_row["client_name"], type(None)):
		parent_text = "[**" + parent_row["client_name"] + "**]("+ parent_row["client_url"] +"), [**" + parent_row["title"]+ "**](" +  parent_row["url"] + ")"
	else:
		parent_text = "[**" + parent_row["title"] + "**](" +  parent_row["url"] + ")"

	parent_text_block = page.children.add_new(TextBlock, title = parent_text)

	if not isinstance(parent_row["manager"], type(None)):
		if isinstance(parent_row["manager"], notion.user.User):
			cc_name = parent_row["manager"].full_name
		else:
			cc_name = str(parent_row["manager"])

		parent_text_block.children.add_new(TextBlock, title = "**Менеджер:** " + cc_name)

	if not isinstance(parent_row["freelancer"], type(None)):

		if isinstance(parent_row["freelancer"], CollectionRowBlock):

			if len(parent_row["freelancer"].name)>1 and parent_row["freelancer"].name[-1] == " ":
				fl_name = parent_row["freelancer"].name[:-1]
			else:
				fl_name = parent_row["freelancer"].name

		elif isinstance(parent_row["freelancer"], list):
			fl_name = ""
			for freelancer in parent_row["freelancer"]:
				if freelancer.name == "":
					continue

				if freelancer.name[-1] == " ":
					fl_name += freelancer.name[:-1]
				else:
					fl_name += freelancer.name

			#remove ", " at the end
			fl_name = fl_name[:-2]

		parent_text_block.children.add_new(TextBlock, title = "**Фрилансер:** " + fl_name)
	
	parent_text_block.children.add_new(DividerBlock)
	for alias in aliases:
		add_global_block(parent_text_block, alias)

	page.children.add_new(TextBlock, title = "")
	page.children.add_new(DividerBlock)



#PROPERTIES:
# activeSince = количество часов за которые забираются обновления
# table = таблица в которую пишем, урл
# types = базы данных из которых брать ардейты, написаных через запятую (сейчас работают только параметры Proposals,Contracts,Projects) 
# row_name = имя строки, до него обязательно добавляется дата к концу
# date = дата с которой оперирует кикстафф в конце репорта 
# contracts_day, projects_day = дни, до которых брать контракты/пропозалы для кикстафа (оптимизация, смысл ставить не 0 только если брать большой client_days) 
# client_day = неактивонсть(дни), за сколько добавлять контракты/проекты в конец 
# proposals_day = неактивонсть(дни), за сколько добавлять пропозалы в конец
# no_contracts, no_projects, no_proposals = если чтото поставить в ети поля, то контракты/проекты/пропозалы не будут добавлятся в конец репорта

@app.route('/updates_check', methods=["GET"])
def head_summary():
	token = os.environ.get("TOKEN")
	client = NotionClient(token)


	target_table = client.get_block(request.args.get("table", "https://www.notion.so/d134162fbfb14449a7ae426487f56127?v=159b522f95fc460f9171dfdca6d1f6d8"))
	proposals = client.get_collection_view("https://www.notion.so/99055a1ffb094e0a8e79d1576b7e68c2?v=bc7d781fa5c8472699f2d0c1764aa553")
	contracts = client.get_collection_view("https://www.notion.so/5a95fb63129242a5b5b48f18e16ef19a?v=48599e7a184a4f32be2469e696367949")
	projects = client.get_collection_view("https://www.notion.so/addccbcaf545405292db498941c9538a?v=e86f54933acc461ca413afa6a2958cdc")
	

	active_since_hours =  int(request.args.get("activeSince", "24"))
	activeSince = datetime.datetime.now() - datetime.timedelta(hours = active_since_hours)
	activeSince = int(activeSince.timestamp())

	select_dbs = request.args.get("types", "Proposals,Contracts,Projects").lower().split(",")

 
	date = str(datetime.datetime.now().day) + "." + str(datetime.datetime.now().month) + "." + str(datetime.datetime.now().year)
	name = request.args.get("row_name", "")
	name = name + " " + date + " - " + str(active_since_hours)+"h"

	result = []

	if "proposals" in select_dbs:
		result.append(["Type", "Interviews"])

		#get proposals
		filter_params = {
			"filters": [
				{
					"filter": {"value":{"type": "exact", "value": {"type": "date", "start_date": datetime.datetime.fromtimestamp(activeSince).strftime('%Y-%m-%d')}}, "operator": "date_is_on_or_after"},
					"property": "Modified",
				}
			],
			"operator": "and",
			
			
		}
		sort_params = [{"direction": "descending", "property": "Modified"}]

		proposals = proposals.build_query(filter=filter_params, sort = sort_params)
		result += list(proposals.execute()) 

	
	if "projects" in select_dbs:
		result.append(["Type", "Projects"])

		#get projects
		filter_params = {
			"filters": [
				{
					"filter": {"value":{"type": "exact", "value": {"type": "date", "start_date": datetime.datetime.fromtimestamp(activeSince).strftime('%Y-%m-%d')}}, "operator": "date_is_on_or_after"},
					"property": "Updated",
				}
			],
			"operator": "and",
			
			
		}
		sort_params = [{"direction": "descending", "property": "Updated"}]

		projects = projects.build_query(filter=filter_params, sort = sort_params)
		result += list(projects.execute()) 

	if "contracts" in select_dbs:
		result.append(["Type", "Contracts"])

		#get projects
		filter_params = {
			"filters": [
				{
					"filter": {"value":{"type": "exact", "value": {"type": "date", "start_date": datetime.datetime.fromtimestamp(activeSince).strftime('%Y-%m-%d')}}, "operator": "date_is_on_or_after"},
					"property": "Updated",
				}
			],
			"operator": "and",
			
			
		}
		sort_params = [{"direction": "descending", "property": "Updated"}]

		contracts = contracts.build_query(filter=filter_params, sort = sort_params)
		result += list(contracts.execute()) 


	i = 0  
	row_type = ""
	add_row = False
	rows = {}
	for row in result:
		if isinstance(row, list):
			row_type = row[1]
			print("Parsing " + row[1])
			add_row = True
			continue


		print(row.title)
		print(row.get_browseable_url())

		aliases = []
		i = 0
		while 1:
			
			# the 200 limit is just a failsafe to prevent infinite loops 
			if i >= len(row.children) or i == 200:
				print("reached end of blocks, moving on")
				break

			if type(row.children[i]) == FactoryBlock \
			  or (type(row.children[i]) == TextBlock and row.children[i].title == ""):
				i+=1
				continue			


			created_time = get_block_create_date(client, row.children[i])
			if created_time/1000<activeSince:
				break
				
			aliases.append(row.children[i])

			i+=1

		target_row = {"url":row.get_browseable_url(), "title":row.title, "manager": None, "freelancer":None, "client_name": None}
		
		if row_type == "Interviews":
			if len(row.cc)>0:
				target_row["manager"] = row.cc[0]
			else:
				target_row["manager"] = row.sent_by

			if len(row.fl)>0:
				target_row["freelancer"] = row.fl[0]

			if len(row.client) > 0:
				if row.client[0].name[-1] == " ":
					target_row["client_name"] = row.client[0].name[:-1]
				else:
					target_row["client_name"] = row.client[0].name
				

				target_row["client_url"] = row.client[0].get_browseable_url()

			if row.job_name != None and row.job_name != "":
				target_row["title"] += ", " + row.job_name

		elif row_type == "Contracts":
			if len(row.coordinator) > 0:
				target_row["manager"] = row.coordinator[0].name

			if len(row.freelancer)>0:
				target_row["freelancer"] = row.freelancer[0]

			if len(row.client_name) > 0 and not isinstance(row.client_name[0], type(None)):
				if row.client_name[0].name[-1] == " ":
					target_row["client_name"] = row.client_name[0].name[:-1]
				else:
					target_row["client_name"] = row.client_name[0].name
				

				target_row["client_url"] = row.client_name[0].get_browseable_url()

			if row.contract_name != None and row.contract_name != "":
				target_row["title"] += ", " + row.contract_name

		elif row_type == "Projects":
			if len(row.pm)>0:
				target_row["manager"] = row.pm[0].name

			freelancers = []
			for contract in row.contracts:
				if len(contract.freelancer):
					freelancers.append(contract.freelancer[0])
			target_row["freelancer"] = freelancers

			if len(row.client_name) > 0 and not isinstance(row.client_name[0], type(None)):
				target_row["client_name"] = row.client_name[0].name
				target_row["client_url"] = row.client_name[0].get_browseable_url()

		if len(aliases)>0:
			#we do this to not add empty rows
			if (add_row):
				target = target_table.collection.add_row()
				target.tags = row_type
				target.title = name
				rows[row_type] = target
				add_row = False

			add_aliases_to_summary(aliases, target, target_row)
			print(aliases)

	print("starting copied kickstaff")
	date = request.args.get("date", None)
	contracts_day = request.args.get("contracts_day", 0, type=int)
	projects_day = request.args.get("projects_day", contracts_day, type=int)
	client_days_before = request.args.get("client_day", 7, type=int)
	proposal_days = request.args.get("proposals_day", 3, type=int)
	cc_tag = request.args.get("no_contracts", None)
	pm_tag = request.args.get("no_projects", None)
	prop_tag = request.args.get("no_proposals", None)
	cc = True if cc_tag is None else False
	pm = True if pm_tag is None else False
	prop = True if prop_tag is None else False
	
	if cc:
		contracts = get_contracts(token, contracts_day)
		print("contracts done")
	else:
		contracts = []
	if pm:
		projects = get_projects(token, projects_day)
		print("projects done")
	else:
		projects = []

	if prop:
		proposals = get_proposals(token, proposal_days)
		print("proposals done")
	else:
		proposals = []

	todo = dict()
	todo = parse_staff(todo, contracts, "contracts", client_days_before)
	todo = parse_staff(todo, projects, "projects", client_days_before)
	todo = parse_staff(todo, proposals, "proposals", proposal_days)
	
	flag_contracts = True
	flag_proposals = True
	flag_projects = True

	for manager in todo.keys():
		if len(todo[manager]["contracts"])>0:
			if "Contracts" in rows.keys():
				if(flag_contracts):
					rows["Contracts"].children.add_new(TextBlock, title = "**Not Updated in "+str(client_days_before)+" days:**")
					flag_contracts = False

				parent_block = rows["Contracts"].children.add_new(TextBlock, title = "["+manager+": ]("+todo[manager]["todo_url"]+")")
				for i in todo[manager]["contracts"]:
					parent_block.children.add_new(TextBlock, title = "["+i[0]+"]("+i[1]+")")
				print(todo[manager]["contracts"])		   

		if len(todo[manager]["proposals"])>0:
			if "Interviews" in rows.keys():
				if (flag_proposals):
					rows["Interviews"].children.add_new(TextBlock, title = "**Not Updated in "+str(proposal_days)+" days:**")
					flag_proposals = False

				parent_block = rows["Interviews"].children.add_new(TextBlock, title = "["+manager+": ]("+todo[manager]["todo_url"]+")")
				for i in todo[manager]["proposals"]:
					parent_block.children.add_new(TextBlock, title = "["+i[0]+"]("+i[1]+")")
				print(todo[manager]["proposals"])   
			
		if len(todo[manager]["projects"])>0:
			if "Projects" in rows.keys():
				if (flag_projects):
					rows["Projects"].children.add_new(TextBlock, title = "**Not Updated in "+str(client_days_before)+" days:**")
					flag_projects = False

				parent_block = rows["Projects"].children.add_new(TextBlock, title = "["+manager+": ]("+todo[manager]["todo_url"]+")")
				for i in todo[manager]["projects"]:
					parent_block.children.add_new(TextBlock, title = "["+i[0]+"]("+i[1]+")")
				print(todo[manager]["projects"])


@app.route('/refresh_db', methods=["GET"])
def update_db():
	token = os.environ.get("TOKEN")
	notion_client = NotionClient(token)

	contracts = notion_client.get_collection_view("https://www.notion.so/5a95fb63129242a5b5b48f18e16ef19a?v=81afe49071ef41bba4c85922ff134407")
	proposals = notion_client.get_collection_view("https://www.notion.so/99055a1ffb094e0a8e79d1576b7e68c2?v=bc7d781fa5c8472699f2d0c1764aa553")

	
	DATABASE_URL = os.environ['DATABASE_URL']
	conn = psycopg2.connect(DATABASE_URL, sslmode='require')
	cur = conn.cursor()

	
	""" SINCE WHEN IS 3 " NOT A COMMENT?!?!?!?!?!?!?"""
	cur.execute("""Select MAX(Date) from contracts""")
	start_from_contracts = cur.fetchone()[0]
	cur.execute("""Select MAX(Date) from proposals""")
	start_from_proposals = cur.fetchone()[0]

	print(start_from_contracts)
	if start_from_contracts == None:
		start_from_contracts = 0

	if start_from_proposals == None:
		start_from_proposals = 0

	# ----------------- START DOWNLOADING CONTRACTS ------------------
	#get only updates
	filter_params = {
		"filters": [
			{
				"filter": {"value":{"type": "exact", "value": {"type": "date", "start_date": datetime.datetime.fromtimestamp(start_from_contracts).strftime('%Y-%m-%d')}}, "operator": "date_is_on_or_after"},
				"property": "Updated",
			}
		],
		"operator": "and",
		
		
	}
	sort_params = [{"direction": "ascending", "property": "Updated"}]

	contracts = contracts.build_query(filter=filter_params, sort = sort_params)
	result = contracts.execute()

	print(len(result))
	for row in result:

		contract_id = str(row.contract_id)
		if contract_id == '':
			contract_id == "-999"

		try:
			cur.execute("""Insert into contracts ("contract_id", "chat_url", "contract_url", "ended", "added_to_db", "date") values ('"""+ contract_id +"""','"""+ str(row.chat_url) +"""','"""+ str(row.get_browseable_url()) +"""','"""+ str(row.status == "Ended") +"""','"""+ str(int(datetime.datetime.now().timestamp())) +"""','"""+ str(int(row.updated.timestamp())) +"""')""")
			conn.commit()
			print(cur.query)
	
		except Exception as e:
			print(e)
			pass	


	#remove duplicates (based on contract_id) 
	cur.execute("""DELETE FROM contracts a USING contracts b WHERE a.id < b.id AND a.contract_id = b.contract_id;""")
	conn.commit()

	print("Contracts Done!")
	# ----------------- START DOWNLOADING PROPOSALS------------------
	#get only updates 
	filter_params = {
		"filters": [
			{
				"filter": {"value":{"type": "exact", "value": {"type": "date", "start_date": datetime.datetime.fromtimestamp(start_from_proposals).strftime('%Y-%m-%d')}}, "operator": "date_is_on_or_after"},
				"property": "Modified",
			}
		],
		"operator": "and",
		
		
	}
	sort_params = [{"direction": "ascending", "property": "Modified"}]

	proposals = proposals.build_query(filter=filter_params, sort = sort_params)
	result = proposals.execute()

	print(len(result))
	
	for row in result:

		proposal_id = str(row.proposal_id)

		
		try:
			cur.execute("""Insert into proposals ("proposal_id", "chat_url", "proposal_url", "added_to_db", "date") values ('"""+ proposal_id +"""','"""+ str(row.chat_link) +"""','"""+ str(row.get_browseable_url()) +"""','"""+ str(int(datetime.datetime.now().timestamp())) +"""','"""+ str(int(row.modified.timestamp())) +"""')""")
			conn.commit()
			print(cur.query)
	
		except Exception as e:
			print(e)
			pass	


	#remove duplicates (based on contract_id)   
	cur.execute("""DELETE FROM proposals a USING proposals b WHERE a.id < b.id AND a.proposal_id = b.proposal_id;""")
	conn.commit()

	print("Proposals Done!")


#accepted users should be an array of id's or "all" for accepting all users
def parse_tokens(tokens, accepted_users = "all"):
	
	tokens = [x.group() for x in re.finditer("({})*.+?(?=})", tokens)]

	ret = []
	for i in range(len(tokens)):
		try:
			strings = [x.group()[1:-1] for x in re.finditer('".+?(?=")+"', tokens[i])]

			if strings[0] in accepted_users or accepted_users == "all":
				ret.append({"id": strings[0], strings[1]:strings[2], strings[3]:strings[4]})
		
		except Exception as e:
			pass

	return ret

def update_parsed_rooms(parsed_rooms, update):

	#check if the record doesn't exist
	if update["id"] not in [x["id"] for x in parsed_rooms]:
		parsed_rooms.append(update)
		return parsed_rooms

#PROPERTIES:
# activeSince - количество часов, за которые брать месседжы

@app.route('/message_review', methods=["GET"])
def message_review():
	#download updates to the database we are using
	update_db()

	DATABASE_URL = os.environ['DATABASE_URL']
	conn = psycopg2.connect(DATABASE_URL, sslmode='require')
	db = conn.cursor()

	token = os.environ.get("TOKEN")
	notion_client = NotionClient(token)
	
	contracts = notion_client.get_collection_view("https://www.notion.so/5a95fb63129242a5b5b48f18e16ef19a?v=81afe49071ef41bba4c85922ff134407")
	proposals = notion_client.get_collection_view("https://www.notion.so/99055a1ffb094e0a8e79d1576b7e68c2?v=bc7d781fa5c8472699f2d0c1764aa553")
	message_review = auto_retry_lambda(notion_client.get_block,"https://www.notion.so/d134162fbfb14449a7ae426487f56127?v=159b522f95fc460f9171dfdca6d1f6d8")

	tokens = os.environ.get('TOKENS')

	parsed_rooms = []
	
	
	active_since_hours =  int(request.args.get("activeSince", "24"))
	activeSince = datetime.datetime.now() - datetime.timedelta(hours = active_since_hours)
	activeSince = int(activeSince.timestamp())*1000

	print(activeSince)

	date = str(datetime.datetime.now().day) + "." + str(datetime.datetime.now().month) + "." + str(datetime.datetime.now().year)
	row_name = request.args.get("row_name", "")
	row_name = row_name + " " + date + " - " + str(active_since_hours)+"h"

	rows = {}

	login_config = upwork.Config({\
			'consumer_key': os.environ.get("ConsumerKey"),\
			'consumer_secret': os.environ.get("ConsumerSecret"),\
			'access_token': os.environ.get("AccessToken"),\
			'access_token_secret': os.environ.get("AccessSecret")})

	client = upwork.Client(login_config)

	company = companyAPI(client)
	messages = messageAPI(client)

	
	freelancer_ids = [x["public_url"].split("/")[-1] for x in company.get_users(os.environ.get("CompanyRef"))["users"]]
	
	#skip owner to parse quicker
	tokens = parse_tokens(tokens, freelancer_ids)

	for freelancer in tokens:
		#log in as each freelancer
		client = upwork.Client(upwork.Config({\
			'consumer_key': os.environ.get("ConsumerKey"),\
			'consumer_secret': os.environ.get("ConsumerSecret"),\
			'access_token': freelancer["accessToken"],\
			'access_token_secret': freelancer["accessSecret"]}))

		userApi = userAPI(client)
		messages_api = messageAPI(client)
		
		user_data = userApi.get_my_info()
		print(user_data)
		if "user" not in user_data.keys():
			continue
			
		user_id = user_data["user"]["id"]

		if user_data["user"]["profile_key"] not in cache.keys():
			cache[user_data["user"]["profile_key"]] = user_data["user"]["first_name"] + " " + user_data["user"]["last_name"]

		profileApi = profileAPI(client)
		


		try:
			rooms = messages_api.get_rooms(os.environ.get("TeamID"), {"activeSince": str(activeSince), "limit":1000, "includeFavoritesIfActiveSinceSet": "false", "includeUnreadIfActiveSinceSet": "false"})["rooms"]
		except Exception as e:
			print(str(e) + " 4")
			rooms = []
		
		time.sleep(1.6)
		
		try:
			user_rooms = messages_api.get_rooms(user_id, {"activeSince": str(activeSince), "limit":1000, "includeFavoritesIfActiveSinceSet": "false", "includeUnreadIfActiveSinceSet": "false"})["rooms"]
		except Exception as e:
			print(str(e) + " 5")
			user_rooms = []


		rooms = rooms + user_rooms
		


		for room in rooms:
			# double check activeSince
			if int(room["latestStory"]["updated"])<activeSince:
				print("ERROR: activeSince did not filter a room")
				continue



			#sometimes throws an error, just default to no info
			try:
				db.execute("""select * from contracts where chat_url like '%"""+room["roomId"]+"""%'""")
				contracts_found = db.fetchall()
			except Exception as e:
				print(str(e) + " 1")
				contracts_found = []
			
			try:	
				db.execute("""select * from proposals where chat_url like '%"""+room["roomId"]+"""%'""")
				proposals_found = db.fetchall()
			except Exception as e:
				print(str(e) + " 2")
				proposals_found = []

			time.sleep(1.6)
			try:
				messages = {}
				messages = messages_api.get_room_messages(os.environ.get("TeamID"), room["roomId"], {"limit":15})
				if "stories_list" not in messages.keys():
					messages = messages_api.get_room_messages(user_id, room["roomId"], {"limit":15})
			except Exception as e:
				print(str(e) + " 3")
				print("		" + str(messages))
				messages = {}
			
			time.sleep(1.6)
			
			if len(contracts_found)>0:
				if not contracts_found[0][4]:
					update_parsed_rooms(parsed_rooms, {"id": room["roomId"], "room":room, "type": "Contracts", "messages":messages, "link":contracts_found[0][3]})
					print("ACTIVE CONTRACT: " + str(room))
				else:
					update_parsed_rooms(parsed_rooms, {"id": room["roomId"], "room":room, "type": "Ended contracts", "messages":messages, "link":contracts_found[0][3]})
					print("ENDED CONTRACT: " + str(room))
		
			elif len(proposals_found)>0:		
				update_parsed_rooms(parsed_rooms, {"id": room["roomId"], "room":room, "type": "Interviews", "messages":messages, "link":proposals_found[0][3]})
				print("PROPOSAL: " + str(room))

			else:
				update_parsed_rooms(parsed_rooms, {"id": room["roomId"], "room":room, "type": "No info", "link":"", "messages":messages})
				print("NO DATA " + str(room))

	time.sleep(3.2)
	print("finished parsing rooms")
	target_page = create_page("https://www.notion.so/Message-Review-33cbe6e92b9e4894890d768f1ea7b970","testing without the db for now")

	for room in parsed_rooms:
		client = upwork.Client(upwork.Config({\
			'consumer_key': os.environ.get("ConsumerKey"),\
			'consumer_secret': os.environ.get("ConsumerSecret"),\
			'access_token': os.environ.get("AccessToken"),\
			'access_token_secret': os.environ.get("AccessSecret")}))

		profileApi = profileAPI(client)

		link = "https://www.upwork.com/messages/rooms/" + room["id"]
		link_text = "[Room]("+link+")"
		
		if room["type"] == "No info":
			type_text = "***No info***"
			#to add to the interview column
			room["type"] = "Interviews"

		else:
			if room["type"] == "Interviews":
				type_text = "[Proposal]("+room["link"]+")"
			else:
				type_text = "["+room["type"]+"]("+room["link"]+")" 


		if room["type"] not in rows.keys():
			rows[room["type"]] = auto_retry_lambda(message_review.collection.add_row)
			rows[room["type"]].name = row_name
			rows[room["type"]].tags = room["type"]

		target_row = rows[room["type"]]

		if room["room"]["roomName"] == None:
			room["room"]["roomName"] == "None"
		if room["room"]["topic"] == None:
			room["room"]["topic"] == "None"

		try:
			title = room["room"]["roomName"]+", **"+room["room"]["topic"] + "**"
		except Exception:
			print(room)
			continue

		parent_text_block = auto_retry_lambda(target_row.children.add_new,TextBlock, title = title)
		text_block = auto_retry_lambda(parent_text_block.children.add_new,TextBlock, title =type_text+" , "+link_text)

		try:
			stories = room["messages"]["stories_list"]["stories"]
		except Exception:
			auto_retry_lambda(parent_text_block.remove,permanently = True)
			print("FAILED TO GET MESSAGES")
			continue

		#if the message ends in a sinature like [Line Start][Capital][* amount of lowercase][space][Capital][Dot][EOF] 
		if isinstance(stories[0]["message"], str) and re.findall("^[A-Z][a-z]* [A-Z]\.\Z", stories[0]["message"], re.M) and room["type"] == "Interview":
			auto_retry_lambda(parent_text_block.remove,permanently = True)
			print("bot detected, skipped")
			continue


		written = 0
		for i in stories:
			if not isinstance(i["message"],str) or i["message"] == "" or i["userId"] == None or i["isSystemStory"]:
				print(i)
				continue

			if written>=3:
				break

			message_time = datetime.datetime.fromtimestamp(i["updated"]/1000).strftime('%Y-%m-%d %H:%M:%S')
			text = "["+message_time+"]\n"

			try:
				if i["userId"] not in cache.keys(): 
					
					#simple retry
					try:
						name = profileApi.get_specific(i["userId"])["profile"]["dev_short_name"][:-1]
					except:
						name = profileApi.get_specific(i["userId"])["profile"]["dev_short_name"][:-1]
					
					cache[i["userId"]] = name
				else:
					name = cache[i["userId"]]
			except Exception as e:
				print(i)
				print(i["userId"])
				name = "ERROR"

			text += "**"+name+":**\n"
			text += i["message"]

			message = auto_retry_lambda(parent_text_block.children.add_new,CodeBlock, title = text)
			message.language = "Plain text"
			message.wrap = True

			auto_retry_lambda(message.move_to,parent_text_block, position = "first-child")


			written +=1

		auto_retry_lambda(text_block.move_to,parent_text_block, position = "first-child")
		auto_retry_lambda(parent_text_block.children.add_new,TextBlock)
		auto_retry_lambda(target_row.children.add_new,DividerBlock)

	print("message_review all done!")  
	print(cache)

	return str(parsed_rooms)

def get_offset_to_closest_weekday(source, targets):
	
	#check if we got an int or string array
	if type(targets[0]) == type(""):
		week = ["Mo", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
		
		#transform the string array to an int array
		for i in range(len(targets)):
			if targets[i] in week:
				targets[i] = week.index(targets[i])			 

	#sort array just in case it wasn't sorted before
	targets.sort()


	day = source.weekday()
	target_day = -1

	#get the first weekday that is > source weekday
	for i in targets:
		if i>day:
			target_day = i
			break

	#if the closest weekday is on the next week		
	if target_day == -1:
		target_day = targets[0]
		return datetime.timedelta(7 + target_day-day)

	else:
		return datetime.timedelta(target_day-day)
	

def create_page(parent_url, title):
	token = os.environ.get("TOKEN")
	client = NotionClient(token)

	parent = client.get_block(parent_url)
	parent.children.add_new(PageBlock, title=title)

	return parent.children[-1]

#PROPERTIES:
# target_site = таблица, в которой туду находятся

@app.route("/hb_tasks", methods=["GET"])
def Hb_tasks():
   
	#connect to the desk
	site = request.args.get("target_site", "https://www.notion.so/Head-board-749105cdfebe4d0282469b04191a24c8")
	token_v2 = os.environ.get("TOKEN")

	#get all tasks
	client = NotionClient(token_v2)
	cv = client.get_collection_view(site)

	# filter out projects without TODO status
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
			



	
	#s can be used to get debug output
	s = ""
	changes = []
	for todo in result:
		
		if todo.set_date == None:
			todo.set_date = NotionDate(todo.created)
		
		if isinstance(todo.set_date.start, datetime.datetime):
			set_start = todo.set_date.start.date()
		else:
			set_start = todo.set_date.start

		n = datetime.datetime.now()
		period = todo.periodicity

		if (todo.due_date == None):
			todo.due_date = NotionDate(todo.updated)


		due_start = datetime.datetime(todo.due_date.start.year, todo.due_date.start.month, todo.due_date.start.day, 17)
		
		

		# if weekdays / periodicity has not been set up
		if(len(period)<=1):

			if(len(period)==0):
				period.append("No Period")

			#apply default values depending on the periodicity
			if "1t/" in period[0]:
				period.append("Wed")
			elif "2t/" in period[0]:
				period.append("Tue")
				period.append("Thu")
			elif "3t" in period[0]:
				period.append("Mo")
				period.append("Wed")
				period.append("Fri")

		#fix period[0]
		if("/" not in period[0] and period[0] != "Daily"):
			ended = False
			for i in range(1,len(period)):
				if "/" in period[0] or period[0] == "Daily":
					tmp = period[0]
					period[0] = period[i]
					period[i] = tmp
					ended = True
					break
			#if we didn't break already, skip this row
			if not ended:
				continue

		#skip result if we already handled it or if periodicity has not been set
		if(n.date()>set_start and period[0] != "No Period"):
			
			if("Daily" == period[0]):
				
				yesterday = datetime.datetime.combine(datetime.datetime.now().date()-timedelta(1), due_start.time())
				#limit to working days
				due_date = yesterday + get_offset_to_closest_weekday(yesterday, [0,1,2,3,4])
	
				set_date = due_date - datetime.timedelta(0,0,0,0,0,12)

				changes.append({"set":set_date , "due":due_date , "id":todo.id})

			elif("w" in period[0]):

				#if format is *t/w 
				if("w" == period[0][3]):
					times_per_week = int(period[0][0])

					#set the next correct weekday as the target
					due_date = datetime.datetime.today().date() + get_offset_to_closest_weekday(datetime.datetime.today().date(),period[1:])

					#we have to do this because .today() returns time as well, so we have to change it
					due_date = datetime.datetime.combine(due_date, datetime.time(due_start.hour, due_start.minute, 0, 0))

				   
				#if format is 1t/*w, don't need to correct for weekdays bc adding weeks doesn't change them
				else:
					offset = datetime.timedelta(int(period[0][3]) * 7)

					due_date = due_start + offset


				set_date = due_date - datetime.timedelta(1,0,0,0,0,12)

				changes.append({"set":set_date , "due":due_date , "id":todo.id})

			#the format is 1/*m, we just offset by * month(s) and find the closest correct weekday to set it to 
			elif("m" in period[0]):
				if("1t/m" == period[0]):
					months = 1
					offset = 1  
				else:
					months = int(period[0][3])
					offset = 2

				#this formula tries to get the closest weekday in 30*month days 
				#we have to do -1 because get_offset looks from the next day forward
				due_date = due_start + datetime.timedelta(math.floor(30*months//7) * 7 -1)

				#not needed tbh, but it is just a failsafe in case the previous line doesn't land on the day before a chosen weekday
				#also helps to mitigate a bug (if the previous due_date != target weekday, the previous line doesn't work)
				due_date = due_date + get_offset_to_closest_weekday(due_date, period[1:])

				set_date = due_date - datetime.timedelta(0,0,0,0,0,12,offset)


				changes.append({"set":set_date , "due":due_date , "id":todo.id})
		
		
		

	#commit our changes (we find the rows with the id of one of our changes and update it accordingly)
	for record in cv.collection.get_rows():
		for change in changes:
			if change["id"] == record.id:
				record.set_property("Due Date", change["due"])
				record.set_property("Set date", change["set"])
				record.set_property("Completed", record.updated)
				#we refresh the change so we can use the updated result in the next for
				record.refresh()
			

	#go over all tasks and change the status to TODO if the task should be set today	
	for todo in result:
		if todo.set_date.start == None:
			todo.set_date.start = todo.created

		if isinstance(todo.set_date.start, datetime.datetime):
			set_start = todo.set_date.start.date()
		else:
			set_start = todo.set_date.start




		if(set_start == datetime.datetime.now().date()):
			todo.status = "TO DO"


	s+= "changes:  " + str(changes)


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
			todo[person]["todo_url"] = row["person"].todo.replace(" ", "")
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
				if len(contract.coordinator)>0:
					if contract.coordinator[0].name != "selfCC" and contract.status == "In Progress":
						project["person"] = contract.coordinator[0]
						break
		if "person" in project.keys():
			project["person_name"] = project["person"].name.replace("\xa0", "")
		else:
			project["person"] = None
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
				continue

		proposal["url"] = str(row.Proposal_ID).replace("\xa0", ""), row.get_browseable_url()
		proposal["client"] = None
		if proposal["person"] is None:
			continue
		else:
			res.append(proposal)
	return res


#PROPERTIES:
# date = дата за которую добавляют todo 
# contracts_day, projects_day = дни, до которых брать контракты/пропозалы для кикстафа (оптимизация, смысл ставить не 0 только если брать большой client_days) 
# client_day = неактивонсть(дни), за сколько добавлять контракты/проекты в конец 
# no_contracts, no_projects = если чтото поставить в ети поля, то контракты/проекты/пропозалы не будут добавлятся в конец репорта

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


#PROPERTIES:
# days_before = неактивонсть(дни), за сколько добавлять контракты/проекты в конец 

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

	timeout = time.time()+10 #timeout after 10 seconds 
	added = False
	while time.time()<timeout:
		try:
			create_new_task(page, "", text=text, date=date, timezone=timezone, tasks=tasks)	
			added = True
			break
		except Exception as e:
			print("retrying due to: " + str(e))
		
	if not added:
		raise IOError("Notion is most likely down. F")


#PROPERTIES:
# member = урл страницы человека, которому добавить todo 
# todo = само туду, если их несколько, то разделять разные при помощи "||"
# text = задача под todo c галочкой
# date = дата, за которую создается туду

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
		#		if pa['name'] != 'Denys Safonov':
		#			continue
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
			todo.append(f"Заполнить цифры по Who vieved and discovered в [Profile Stats](https://www.notion.so/501c314abddb45bfb35d91a217d709d8?v=f22acd6b1b1f4697bdab81734f86301a) по {freelancers}")
			
		create_todo(token, calendar["mon"], pa["todo_url"], todo, text="")

		# Tuesday
		todo = list()
		for f in map(lambda c: "[{}]({})".format(c[0], c[1]), pa["pa_for"]):
			todo.append(f"Обновить профиль {f}")
		todo.append("Проверить заливку рабочих материалов на pCloud/Github по активным контрактам ")
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
		# todo = list()
		# todo.append("Проверить заливку рабочих материалов на pCloud/Github")
		# create_todo(token, calendar["wed"], pa["todo_url"], todo, text="")

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
		#	 continue
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
		todo.append(f"Загрузи [статы](https://bit.ly/30k15In) по [ссылке]({fl['stats_upload']})")
		todo.append(f"Коментом, тегнув {fl['pa_name']}, напиши свою планируемую загрузку на неделю")
		create_todo(token, calendar["mon"], fl["todo_url"], todo, text="")
	print("Mon FL done")

def friday_todo_fl(token, staff, calendar):
	print("Fri Fl's start")
	for fl in staff:
#		if fl['name'] == 'Denys Safonov':		 
		print(f"FL {fl['name']} start")
		# Friday
		todo = list()
		todo.append(f"Коментом напиши какие day-off ты планируешь на следующую неделю и тегни {fl['pa_name']}, иначе напиши - Не планирую")
		create_todo(token, calendar["fri"], fl["todo_url"], todo, text="")	  
	print("Fri FL done")	

def weekly_todo_bidder(token, staff, calendar):
	print("bidders start")
	for bidder in staff:
		#		if bidder['name'] != 'Denys Safonov':
		#		continue
		print(f"bidder {bidder['name']} start")

		# Monday
		todo = list()
		todo.append("Обработать входящие инвайты и PCJ за выходные")
		todo.append("Проверить статус комнат UAMS")
		create_todo(token, calendar["mon"], bidder["todo_url"], todo, text="")

		# Wednesday
		#		todo = list()
		#		todo.append('Добавить и структурировать шаблоны в [Proposal templates]'
		#					'(https://www.notion.so/bd59fed23f2a43b9b5fec15a57537790#2f798130e8ca44cba913a5c645fe33fc) '
		#					'по итогам Cross-review')
		#		create_todo(token, calendar['wed'], bidder['todo_url'], todo, text='Еженедельные задачи')

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
		#	 {"property": "Roles", "comparator": "enum_contains", "value": role},
		#	 {"property": "out of Team now", "comparator": "checkbox_is", "value": "No"},
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
			#	 {"property": "title", "comparator": "string_contains", "value": person.name.replace("\xa0", "")}
			# ]
			# person_stat = stats.build_query(filter=filter_params).execute()

			# person_stat = stats_df[stats_df['name'] == person['name']]

			# if person:
			# d["stats"] = person[0]
			if person["todo"]=="":
				continue

			d["todo_url"] = person["todo"].split()[1]
			#handle links
			if "[" in d["todo_url"]:
				d["todo_url"] = re.search("(?<=\().*(?=\))", d["todo_url"]).group()			 

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
			#	 print(person.name.replace("\xa0", ""), "not found in stats")
	# print(*todo_list.items(), sep="\n")
	return todo_list


#PROPERTIES:
# roles = роли на которых запускается kickstaff, если несколько, то между ними можно ставить '/' , '\' , '.' , ';' , '|' , ' ' , ',' 
# date = дата, за которую добавляется туду

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


#PROPERTIES:
# roles = роли на которых запускается kickstaff, если несколько, то между ними можно ставить '/' , '\' , '.' , ';' , '|' , ' ' , ',' 
# date = дата, за которую добавляется туду
  
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


#PROPERTIES:
# collectionURL = таблица, в которую добавить строку
# subject = проперти name етой строки
# link = ссылка с которой получили rss
# description = проперти decription етой строки

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
	client = NotionClient(token)
	cv = client.get_collection_view(collection_url)
	
	try:
		row = cv.collection.add_row()
	except Exception as e:
		sort_params = [{"direction": "ascending", "property": "Date"}]
		time.sleep(3)
		row = cv.build_query(sort = sort_params).execute()[-1]
	
	row.name = subject[:-9]
	row.description = description
	row.status = "New"
	row.to = invite_to
	row.link = "https://www.upwork.com/ab/jobs/search/?previous_clients=all&q={}&sort=recency".format(
		urllib.parse.quote(subject[:-9])
	)
	
	item_id = re.search("%7E[0-9][\w]+", link)
	row.id = item_id.group()[3:]
	return row


#PROPERTIES:
# collectionURL = таблица, в которую добавить строку
# subject = проперти name етой строки
# link = проперти URL rss, с него получаем id
# description = проперти decription етой строки
# inviteto = кому пришел инвайт, ссылка на тим директори

@app.route("/pcj", methods=["POST"])
def pcj():
	collection_url = request.form.get("collectionURL")
	description = request.form.get("description")
	subject = request.form.get("subject")
	token_v2 = os.environ.get("TOKEN")
	invite_to = request.form.get("inviteto")
	link = request.form.get("link")
	print(f"add {subject} {link}")
	pcj = create_pcj(token_v2, collection_url, subject, description, invite_to, link)
	return f"added {subject} receipt to " + pcj.get_browseable_url()


def get_client_from_invite(invite):
	#get upwork client
	login_config = upwork.Config({\
		'consumer_key': os.environ.get("ConsumerKey"),\
		'consumer_secret': os.environ.get("ConsumerSecret"),\
		'access_token': os.environ.get("AccessToken"),\
		'access_token_secret': os.environ.get("AccessSecret")})

	client = upwork.Client(login_config)
	notion_client = NotionClient(os.environ.get("TOKEN"))

	client_db = notion_client.get_collection_view("https://www.notion.so/21a8e8245c9e4024848613cecdc8e88f?v=ff14989e8f96401db5f7c3527a4cd8b7")
	
	time.sleep(3.2)

	application = applicationAPI(client)
	job_info = jobInfoAPI(client)

	try:
		application = application.get_specific(invite.ID)
		ciphertext = application["data"]["openingCiphertext"]
		
		job_info = job_info.get_specific(ciphertext)
		buyer = job_info["profile"]["buyer"]

		buyer["skills"] = job_info["profile"]["op_required_skills"]["op_required_skill"]
		buyer["ciphertext"] = ciphertext
	except Exception as e:
		print("Idk, some error while getting the client " + str(e))
		return []


	print(buyer)

	contract_datetime = datetime.datetime.strptime(buyer["op_contract_date"], "%B %d, %Y")

	client_name = None
	description = invite.description.split("\n")
	print(description)
	for i, line in enumerate(description):
		if ": https://upwork.com/applications/" in line:
			client_name = description[i-2]
			break

	print(client_name)

	if client_name == None:
		return None

	result = client_db.collection.get_rows(search = client_name)
	checked_result = []
	for x in result:
		if client_name in x.name:
			print(1)
			if buyer["op_country"] == x.country or x.country == "":
				print(2)
				if buyer["op_city"] == x.location or x.location == "":
					print(3)
					if buyer["op_state"] == x.state or x.state == "":
						print(buyer["op_timezone"][:6])
						if buyer["op_timezone"][:6] in x.time_zone or "(Coordinated Universal Time)" in buyer["op_timezone"] and "UTC+00" in x.timezone:
							checked_result.append(x)

	print([x.name for x in checked_result])

	return (buyer,checked_result[0]) if len(checked_result)>0 else None


def create_invite(token, collection_url, subject, description, invite_to):
	# notion
	match = re.search("https://upwork.com/applications/\d+", description)
	url = match.group()
	item_id = re.search("\d+", url)
	client = NotionClient(token)
	cv = client.get_collection_view(collection_url)

	try:
		row = cv.collection.add_row()
	except Exception as e:
		sort_params = [{"direction": "ascending", "property": "Date"}]
		time.sleep(3)
		row = cv.build_query(sort = sort_params).execute()[-1]

	row.name = subject
	row.description = description
	row.status = "New"
	
	row.to = invite_to

	row.link = url
	row.id = item_id.group()

	upwork_client = get_client_from_invite(row)
	if upwork_client != None:
		row.client = upwork_client[1]
		row.job_url = "https://www.upwork.com/jobs/"+upwork_client[0]["ciphertext"]
		row.country = upwork_client[0]["op_country"]
		row.time_zone = upwork_client[0]["op_timezone"]
		[row.skills := row.skills + x.values()[0] for x in upwork_client[0]["skills"]]

	return row


#PROPERTIES:
# collectionURL = таблица, в которую добавить строку
# subject = проперти name етой строки
# description = проперти decription етой строки
# inviteto = кому пришел инвайт, ссылка на тим директори

@app.route("/invites", methods=["POST"])
def invites():
	collection_url = request.form.get("collectionURL")
	description = request.form.get("description")
	subject = request.form.get("subject")
	token_v2 = os.environ.get("TOKEN")
	invite_to = request.form.get("inviteto")
	print(f"add {subject}")
	invite = create_invite(token_v2, collection_url, subject, description, invite_to)
	return f"added {subject} receipt to " + invite.get_browseable_url()

def get_id_from_upwork_url(url):

	if "~" in url:
		return url[url.find("~") + 1: url.find("~") + 19]
	else:
		upwork_id = re.findall("(?<=fl\/)[\w]+", url)
		if len(upwork_id)>0:
			return upwork_id[0]
		else:
			print("unknown url type " + url)
			return None

def create_response(applicant_type, data):
	# Development
	# collection_url = "https://www.notion.so/c8cc4837308c4b299a88d36d07bc2f4f?v=dd587a4640aa41bd9ff88ca268aff553"
	# Production
	collection_url = "https://www.notion.so/1f4aabb8710f4c89a3411de53fc7222a?v=0e8184ceca384767917f928bb3d20e6f"
	token = os.environ.get("TOKEN")
	client = NotionClient(token)

	print(data)

	cv = client.get_collection_view(collection_url)
	upwork_profile = data["Upwork profile"]
	upwork_id = get_id_from_upwork_url(upwork_profile)
	email = data["Email"]

	records = cv.collection.get_rows()
	row_exist = None
	for record in records:
		
		if upwork_id == None:
			rec_email = record.get_property("email")
			if email == rec_email:
				row_exist = record
				break
		else:
			rec_profile = record.get_property("upwork_profile")
			if rec_profile != "":
				
				uw_id = get_id_from_upwork_url(rec_profile)

				if uw_id == upwork_id:
					row_exist = record
					break

	print(row_exist)
	if not isinstance(row_exist, type(None)):
		print(row_exist.name)
		
	row = row_exist if row_exist is not None else cv.collection.add_row()
	row.set_property("Type", applicant_type)
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
