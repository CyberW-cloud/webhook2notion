# looking next monday
today = datetime.datetime.now().date()

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


to_do = {
    "cc": {
       "mon": {"Header": "Block header or empty",
            "text": "Some text or empty",
            "to_do": [
                        "Do some work 1",
                        "Do some work 2",
                        "Do some work 3",
                      ]
            },
       "tue": {"Header": "",
            "text": "",
            "to_do": [
                "just to do 1",
                "just to do 2",
                "just to do 3"
                      ]
            },
       "wed": {"Header": "",
            "text": "",
            "to_do": [
                      ]
            },
       "thu": {"Header": "",
            "text": "Just text",
            "to_do": [
                "Написать апдейты по ведомым контрактам и проектам",
                      ]
            },
       "fri": {"Header": "",
            "text": "",
            "to_do": [
                      ]
            },
       "sat": {"Header": "",
            "text": "",
            "to_do": [
                      ]
            },
       "sun": {"Header": "",
            "text": "",
            "to_do": [
                      ]
            }
   },
    "bidder": {
       "mon": {"Header": "Block header or empty",
            "text": "Some text or empty",
            "to_do": [
                        "Do some work 1",
                        "Do some work 2",
                        "Do some work 3",
                      ]
            },
       "tue": {"Header": "",
            "text": "",
            "to_do": [
                "just to do 1",
                "just to do 2",
                "just to do 3"
                      ]
            },
       "wed": {"Header": "Just header",
            "text": "",
            "to_do": [
                      ]
            },
       "thu": {"Header": "",
            "text": "Just text",
            "to_do": [
                      ]
            },
       "fri": {"Header": "",
            "text": "",
            "to_do": [
                      ]
            },
       "sat": {"Header": "",
            "text": "",
            "to_do": [
                      ]
            },
       "sun": {"Header": "",
            "text": "",
            "to_do": [
                      ]
            }
    },
   "pa": {
       "mon": {"Header": "",
            "text": "",
            "to_do": [ ""
                       
                      ]
            },
       "tue": {"Header": "",
            "text": "",
            "to_do": [
               
                      ]
            },
       "wed": {"Header": "",
            "text": "",
            "to_do": [
                      ]
            },
       "thu": {"Header": "",
            "text": "",
            "to_do": [
                      ]
            },
       "fri": {"Header": "",
            "text": "",
            "to_do": [ "Проверить у кого должен быть 1-1 на этой неделе и запланировать звонки, инфо внести в календарь"
                      ]
            },
       "sat": {"Header": "",
            "text": "",
            "to_do": [
                      ]
            },
       "sun": {"Header": "",
            "text": "",
            "to_do": [
                      ]
            }

   }
}

