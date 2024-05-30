import pywikibot
import pandas as pd
import numpy as np
from datetime import datetime
from datetime import timedelta
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from wordcloud import STOPWORDS
from get_edits import get_edits
import nltk 
import re
import time
import simplejson as json
import cv2

numberOfContribs = 20 # 50
start_time = time.time()
site = pywikibot.Site('en', 'wikipedia')
stopWords = ['ref', 'REDIRECT', 'cite', 'date', 'article', 'title', 'via', 'flag', 'web', 'date', 'User', 'Talk', 'page', 'This' + 'stop', 'the', 'to', 'and', 'a', 'in', 'it', 'is', 'I', 'that', 'had', 'on', 'for', 'were', 'was'] + list(STOPWORDS)


def temp():
    accountList = []
    length = 0

    # test = {'Cracker-Kun': False, "Phirmbutzian": True, "213.190.141.189": False, "194.242.148.92": False, "Ccmccann": False}
    # test = {'Cracker-Kun': False, "Phirmbutzian": True, "213.190.141.189": False, "194.242.148.92": False, "204.113.147.175": False, "Ccmccann": False, "99.181.139.6": False, "69.2.52.29": False}
    
    test = {
        "42.200.239.199": [
            "Abbott_Laboratories 2020-3"
        ],
        "75.81.119.191": [
            "Abbott_Laboratories 2021-1"
        ],
        "151.30.96.245": [
            "Abbott_Laboratories 2021-10"
            "Abbott_Laboratories 2022-11"
        ],
        "2601:989:4002:EF90:CDEA:7D59:AEBE:6A35": [
            "Abbott_Laboratories 2021-10"
        ]
    }
    
    test = list(test.items())

    for i in range(0, len(test)):
        length = len(test[i][1][0])
        accountList.append([test[i][0], test[i][1], test[i][1][0][length-7:]])
    
    return accountList


# get_flagged_account_list makes a list of user data from a json dictioary
# it returns a list of users and thier flag status
def get_flagged_account_list():
    flaggedAccountList = []
    length = 0

    with open("pages_edited_sus_sp500_anonyoung.json", "r") as tagged:
        tagged_dict = json.load(tagged)

    tagged_dict = list(tagged_dict.items())
    
    for i in range(0, len(tagged_dict)):
        length = len(tagged_dict[i][1][0])
        flaggedAccountList.append([tagged_dict[i][0], tagged_dict[i][1], tagged_dict[i][1][0][length-7:]])
    
    return flaggedAccountList


# sort_by_birth tkaes in a list of user information and reorders it based on account registration date
# it returns a list is lists, where the inner lists contain a user, their flag, and their date of registration.
def sort_by_birth(userList):
    noneUserList = []
    sortedUserList = []
    for i in range (0, len(userList)):
        user = pywikibot.User(site, userList[i][0])
        sortedUserList.append([user, userList[i][1], userList[i][2]])

    sortedUserList = sorted(sortedUserList, key=lambda x:x[2])[:]

    return sortedUserList



# get_contribs() takes in a user account and a number of edits
# returns a ditionary of user contribution information
def get_contribs(user, num):
    contrib = user.contributions(num)
    return contrib


# get_edit() takes in a user account and a number of edits
# returns a list of contribution data
def get_edit(user, num):
    edit = list(map(get_edit_from_contrib, get_contribs(user, num)))
    return edit



# get_edit_from_contrib() takes in a tuple of contributions
# Returns a list of what is added and removed within an edit from those contributions
def get_edit_from_contrib(contrib: tuple) -> dict:
    page = contrib[0]
    timestamp = contrib[2]

    return get_edits(page.title(), page.site, 
        start_time = timestamp + timedelta(seconds=1),
        end_time = timestamp - timedelta(seconds=1))[0]



# get_changed() takes in a list of edits
# returns a list of strings of what has been changed (based on label) within an edit
def get_changes(revision, label):
    changes = []

    for i in range(0, len(revision)):
        changes += clean_edits(revision[i][label])

    changes = [item for sublist in changes for item in sublist if len(item) > 2]

    return changes



# clean_edits takes in a list of additons or removals and removed non-English words and characters
# returns a list appeneded with the additional addition or removal
def clean_edits(edits):
    words = set(nltk.corpus.words.words())
    cleanedEdit = []

    for change in edits:
        edit = " ".join(w for w in nltk.wordpunct_tokenize(change) if w.lower() in words or not w.isalpha()) # removes non-English words
        edit = re.sub(r'[^a-zA-Z ]', '', edit) # removes non-alphabet characters

        if(edits and edit.strip()):
            wordList = re.sub("[^\w]", " ",  edit).split()
            cleanedEdit.append(wordList)

    return cleanedEdit



#  get_additions takes in an edit and returns what was added in that edit
def get_additions(edit):
    return get_changes(edit, 'added')



#  get_removals takes in an edit and returns what was removed in that edit
def get_removals(edit):
    return get_changes(edit, 'removed')




# make_word_cloud takes in a list of words, a tag to say if they were removals or additions, a user name, and a flag status
# it returns a word cloud
def make_word_cloud(originalWordList, user, tag, noFlag, num):
    cloudList = []
    fontColor = 'Greens'
    if tag == 'Removals':
        fontColor = 'Blues_r'

    status = 'Not Flagged'
    if noFlag:
        status = 'Flagged'
    wordList = [w for w in originalWordList if w.lower() not in (s.lower() for s in stopWords)]
    if not wordList:
        wordList += ['null']
        
    unique_string = (" ").join(wordList)

    print(user, wordList)
    wordcloud = WordCloud(stopwords = None, width = 800, height = 400, colormap = fontColor).generate(unique_string)
    fig = plt.figure(figsize=(15,8))
    plt.title(user.username + " - " + str(user.registration())[:10] + " - " + status + " - " + str(num) + " Contributions" + " - " + tag)

    wordcloud.to_file(tag + ".png")
    cloudList.append(fig)
    plt.close()

    return cloudList



# get_word_cloud calls make_word_cloud twice, once for additions and once for removals
# It returns a list of word clouds.
def get_word_cloud(user, num, flag):
    edit = get_edit(user, num)
    userWordCloudList = []

    additions = make_word_cloud(get_additions(edit), user, 'Additions', flag, num)
    removals = make_word_cloud(get_removals(edit), user, 'Removals', flag, num)

    userWordCloudList.append(additions + removals)

    return userWordCloudList



# get_tags takes in an edit and a tag that serves as a label
# it returns a list that counts when a tag is counted in a given hour
def get_tags(contribs, label):
    tags = []
    contribByTag = []

    for i in range(0, len(contribs)):
        if label == 'Mobile': # gets edits with tags for modble edits
            if 'mobile web edit' in contribs[i]['tags']:
                contribByTag.append(contribs[i])
        elif label == 'Non-Mobile': # gets edits with tags not non-mobile edits
            if 'mobile web edit' not in contribs[i]['tags']:
                contribByTag.append(contribs[i])
    
    return contribByTag



# get_hours takes in a list of edits and a user to find the times that an edit was made
# it returns a list of hour times a user made their edits 
def get_hours(edits, user):
    hourData = [0] * 24

    for contrib in edits:
        time = contrib['timestamp']
        time = time.replace("T", " ")
        time = time.replace("Z", ".0")

        hours = datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')
        hourData[hours.hour] += 1
        
    return hourData



# get_bar_graph_data takes in a user an a number of edits to gather data on when a user has posted
# it returns a list of of edit information and graphing traits
def get_bar_graph_data(user, num):
    edit = get_edit(user, num)
    dataList = []

    graphOne = [get_hours(get_tags(edit, 'Non-Mobile'), user), "Non-Mobile", "hotpink"]
    graphTwo = [get_hours(get_tags(edit, 'Mobile'), user), "Mobile", "dodgerblue"]
    dataList += (graphOne + graphTwo)

    return dataList

    

# make_bar_graphs creates a bar_graph of the hour of day a user has edited a page
# it returns a list of hisotgrams
def make_bar_graph(data, user, flag, num):
    graphList = []
    status = ' '
    colors = [data[2], data[5]]
    legend = [data[1], data[4]]
    times = [*range(24)]
    

    # if flag:
    #     status = 'Flagged'
    # else:
    #     status = 'Not Flagged'

    fig = plt.figure()
    plt.bar(times, data[0], color = colors[0], alpha = 0.5, width = 0.95)
    plt.bar(times, data[3], color = colors[1], alpha = 0.5, width = 0.95)
    plt.title(user.username + " - " + str(user.registration())[:10], fontsize = 16)
    # plt.text(0.05, 0.95, ((str(flag)[2:]).split(" ", 1))[0], transform=fig.transFigure, size=15)
    plt.text(0.01, 0.95, flag[0], transform=fig.transFigure, size=15)
    plt.ylabel('Number of Edits')
    plt.xlabel('Hour of the Day')
    plt.xticks(np.arange(min(times), max(times)+1, 1))
    plt.legend(labels = legend)

    plt.savefig('hour_of_edit.png')
    graphList.append(fig)
    
    return graphList



# write_PDF creats a PDF page of the word clouds and bar_graphs for a list of users
# no return value
def write_PDF(userList):
    pdf = PdfPages('info.pdf')
    imageList = []
    pageList = []
    figList = []
    rows = 3

    for i in range(0, len(userList)):
        bar_graphs = make_bar_graph(get_bar_graph_data(userList[i][0], numberOfContribs), userList[i][0], userList[i][1], numberOfContribs)
        wordClouds = get_word_cloud(userList[i][0], numberOfContribs, userList[i][1])

        graph = cv2.imread("hour_of_edit.png")
        additions = cv2.imread("Additions.png")
        removals = cv2.imread("Removals.png")
        imageList.append([graph, additions, removals])
    

    for i in range(0, len(userList), rows):
        plt.figure()
        fig, axarr = plt.subplots(rows, 3, figsize = (50, 30))
        for row in range(i, min(i+rows, len(userList))):
            axarr[row % rows][0].imshow(imageList[row][0])
            axarr[row % rows][1].imshow(imageList[row][1])
            axarr[row % rows][2].imshow(imageList[row][2])

            axarr[row % rows][0].axes.xaxis.set_visible(False)
            axarr[row % rows][0].axes.yaxis.set_visible(False)
            axarr[row % rows][1].axes.xaxis.set_visible(False)
            axarr[row % rows][1].axes.yaxis.set_visible(False)
            axarr[row % rows][2].axes.xaxis.set_visible(False)
            axarr[row % rows][2].axes.yaxis.set_visible(False)
        figList.append(fig)

    for plot in figList:
        pdf.savefig(plot, orientation='landscape')

    pdf.close()


# write_PDF(sort_by_birth(temp())) # Creates PDF
write_PDF(sort_by_birth(get_flagged_account_list())) # Creates PDF


print("--- %s seconds ---" % (time.time() - start_time))