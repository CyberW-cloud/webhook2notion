from time import sleep

from notion.collection import NotionDate
from notion.block import TodoBlock, HeaderBlock, TextBlock
import datetime


def get_date_from_title(title):
    if isinstance(title, list):
        for el in title:
            if len(el) < 2:
                continue
            else:
                try:
                    if el[1][0][0] == 'd':
                        return el
                except Exception:
                    raise Exception('Unexpected format')
    else:
        return None


def get_user_id_from_title(title):
    if isinstance(title, list):
        for el in title:
            if len(el) < 2:
                continue
            else:
                try:
                    if el[1][0][0] == 'u':
                        return el[1][0][1]
                except Exception:
                    raise Exception('Unexpected format')
    else:
        return None


def get_previous_or_target_headers(page, target_date):
    prev_date = datetime.datetime.strptime('1900-01-01', '%Y-%m-%d').date()
    store = page.children[0]
    for child in page.children:
        block_type = child.get('type')
        if 'header' in block_type:
            prop = child.get('properties')
            if prop is None:
                continue
            title = prop['title']
            date = get_date_from_title(title)
            if date:
                d = NotionDate.from_notion([date])
                if isinstance(d.start, datetime.datetime):
                    date = d.start.date()
                else:
                    date = d.start
                if date == target_date:
                    return 'exact', child
                else:
                    if prev_date < date < target_date:
                        store = child
                        prev_date = date
    return 'prev', store


def move_task_before(task, block):
    task['header'].move_to(block, "before")
    try:
        if task['text']:
            task['text'].move_to(task['header'], "after")
            #task['to-do'][0].move_to(task['text'], "after")
        else:
            task['to-do'][0].move_to(task['header'], "after")
            for num, td in enumerate(task['to-do'][1:]):
                td.move_to(task['to-do'][num], "after")
    except IndexError:
        pass


def create_new_task(page, header, date, text, timezone, tasks):
    type, parent = get_previous_or_target_headers(page, date)
    if type == 'exact':
        if header:
            prop = parent.get('properties')
            prop['title'].append([' '])
            prop['title'].append([header])
            parent.set('properties', prop)
        if text:
            tx = page.children.add_new(TextBlock, title=text)
            tx.move_to(parent, "after")
            parent = tx
        for task in tasks:
            td = parent.children.add_new(TodoBlock, title=task)
            td.checked = False
            if not text: 
               td.move_to(tx, "first-child") 
            td.move_to(parent, "after")                    
            parent = td

    else:
        title = NotionDate(date, timezone=timezone).to_notion()
        if header:
            title.append([' '])
            title.append([header])
        new_child = page.children.add_new(HeaderBlock, title=" . ")
        prop = new_child.get('properties')
        prop['title'] = title
        new_child.set('properties', prop)
        ret = {'header': new_child, 'to-do': list()}
        if text:
            tx = page.children.add_new(TextBlock, title=text)
            ret['text'] = tx
        else:
            ret['text'] = None
        for task in tasks:
            if ret['text'] is not None:
                obj = ret['text']
            else:
                obj = page
            td = obj.children.add_new(TodoBlock, title=task)
            td.checked = False
            ret['to-do'].append(td)
        move_task_before(ret, parent)
