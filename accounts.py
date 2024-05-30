import pywikibot
import pandas as pd
import csv
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

site = pywikibot.Site('en', 'wikipedia')
user_list = ['Doug butler', 'Doug', 'John']
test_user = pywikibot.User(site, 'Doug butler')

# Creates a CSV file of user information based on inputed usernames
def get_info(users):
    column_names = ['Username', 'Registered', 'Anonymous', 'Account Creation', 'Edit Count', 'Gender', 'Groups', 'Rights']
    accounts = []

    for users in user_list:
        user = pywikibot.User(site, users)
        accounts.append([user.username, user.isRegistered(), user.isAnonymous(), user.getprops()['registration'], user.editCount(), user.gender(), user.groups(), user.rights()])

    df = pd.DataFrame(accounts, columns = column_names)
    print(df)

    df.to_csv('accounts.csv')
    
# Gets the last x number of edits a user has made and also creates a list on the hour those edits were made
def get_contribs(user):
    editNum = 1000
    times = []
    hourData = []
    edits = user.contributions(editNum)
    
    for contrib in edits:
        x = contrib[2]
        times.append(datetime(x.year, x.month, x.day, x.hour, x.minute, x.second))
        hourData.append(x.hour)
        
    makeHistogram(hourData)
    
# Makes a histrogram of the hour of day an edit was made based on the last x number of edits a user has made
def makeHistogram(data):
    plt.hist(data, bins=24)
    plt.xticks(np.arange(0, 24, 1.0))
    plt.title('Edits vs Hour')
    plt.ylabel('Number of Edits')
    plt.xlabel('Hour of the Day')
    plt.show()
    

# get_info(user_list)
get_contribs(test_user)