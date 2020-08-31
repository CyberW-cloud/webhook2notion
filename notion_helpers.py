import datetime
import time
from time import sleep

import pandas as pd
from notion.block import HeaderBlock, TextBlock, TodoBlock
from notion.collection import NotionDate, TableView, TableQueryResult

def auto_retry_lambda(fun, *args, **kwargs):

	# making them function arguments would mess with *args and **kwargs if not given
	retries = 5
	log = True
	sleep = 1

	while 1:
		try:
			return fun(*args, **kwargs)
		
		except Exception as e:
			if log:
				print("Retrying due to:" + str(e))

			if retries <= 0:
				raise e

			retries -= 1
			time.sleep(sleep)


def get_date_from_title(title):
	if isinstance(title, list):  # instance must be list
		for el in title:
			if len(el) < 2:  # element does not contain special markdown
				continue
			else:
				try:
					if el[1][0][0] == "d":  # if exist date return it
						return el
				except Exception:
					raise Exception("Unexpected format")
	else:
		return None


def get_user_id_from_title(title):
	if isinstance(title, list):
		for el in title:
			if len(el) < 2:
				continue
			else:
				try:
					if el[1][0][0] == "u":
						return el[1][0][1]
				except Exception:
					raise Exception("Unexpected format")
	else:
		return None


# looking for headers with target date or return last header
def get_previous_or_target_headers(page, target_date):
	prev_date = datetime.datetime.strptime("1900-01-01", "%Y-%m-%d").date()  # start date for comparison
	store = page.children[0]
	for child in page.children:
		block_type = child.get("type")
		if "header" in block_type:  # check only headers block
			prop = child.get("properties")
			if prop is None:
				continue
			title = prop["title"]
			date = get_date_from_title(title)
			if date:
				d = NotionDate.from_notion([date])
				if isinstance(d.start, datetime.datetime):  # check only date, ignore time
					date = d.start.date()
				else:
					date = d.start
				if date == target_date:  # if date is same return exact date
					return "exact", child
				else:
					if prev_date < date < target_date:  # update last item and continue searching
						store = child
						prev_date = date
	return "prev", store


# move task (header, text and list before block)
def move_task_before(task, block):
	task["header"].move_to(block, "before")
	try:
		if task["text"]:  # all child will be move automatically
			task["text"].move_to(task["header"], "after")
		else:
			task["to-do"][0].move_to(task["header"], "after")
			for num, td in enumerate(task["to-do"][1:]):
				td.move_to(task["to-do"][num], "after")
	except IndexError:
		pass


def create_new_task(page, header, date, text, timezone, tasks):
	type, parent = get_previous_or_target_headers(page, date)
	if type == "exact":  # if header exist
		if header:  # add title to header
			prop = parent.get("properties")
			prop["title"].append([" "])
			prop["title"].append([header])
			parent.set("properties", prop)
		if text:  # add text to task
			tx = page.children.add_new(TextBlock, title=text)
			tx.move_to(parent, "after")
			parent = tx
			for task in tasks:  # if text exist add todos as children of text block
				td = parent.children.add_new(TodoBlock, title=task)
				td.checked = False
		else:
			for task in tasks:
				td = parent.children.add_new(TodoBlock, title=task)
				td.checked = False
				td.move_to(parent, "after")

	else:  # if header not exist create new header and add a task
		title = NotionDate(date, timezone=timezone).to_notion()
		if header:
			title.append([" "])
			title.append([header])
		new_child = page.children.add_new(HeaderBlock, title=" . ")
		#        time.sleep(3)
		prop = new_child.get("properties")
		#       if prop is None:
		#           time.sleep(3)
		#           prop = new_child.get('properties')
		prop["title"] = title
		new_child.set("properties", prop)
		ret = {"header": new_child, "to-do": list()}
		if text:
			tx = page.children.add_new(TextBlock, title=text)
			ret["text"] = tx
		else:
			ret["text"] = None
		for task in tasks:
			if ret["text"] is not None:
				obj = ret["text"]
			else:
				obj = page
			td = obj.children.add_new(TodoBlock, title=task)
			td.checked = False
			ret["to-do"].append(td) 
		move_task_before(ret, parent)



def nview_to_pandas(source):
	"""Convert Notion object to Pandas DataFrame.

	:param source: TableView/TableQueryResult object
	:return: pandas.DataFrame
	"""
	if isinstance(source, TableQueryResult):
		rows = source
	elif isinstance(source, TableView):
		rows = source.collection.get_rows()
	else:
		raise TypeError("Incorrect type for convert to pandas")

	data = []
	for row in rows:
		i = row.get_all_properties()
		i["row"] = row
		data.append(i)

	return pd.DataFrame(data)
