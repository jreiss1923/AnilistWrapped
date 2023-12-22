import json
import requests
import time
import collections
import matplotlib.pyplot as plt 

url = 'https://graphql.anilist.co'

def getUserIdFromUsername(username):

    query = '''
    query($userName: String) {
        User(name: $userName) {
            id
        }
    }
    '''

    variables = {'userName': username}

    response = requests.post(url, json={'query': query, 'variables': variables}).json()
    if ('errors' in response):
        raise Exception("Username does not exist.")
    return response['data']['User']['id']

def isSequel(relations):
    for relation in relations:
        if relation['relationType'] == 'PREQUEL':
            return True
    return False

def queryUserFavorites(userid):
    query = '''
    query($userId: Int) {
        User(id: $userId) {
            favourites {
                anime {
                    nodes {
                        title {
                            romaji
                        }
                    }
                }
            }
        }
    }
    '''

    variables = {'userId': userid}

    response = requests.post(url, json={'query': query, 'variables': variables}).json()
    return response



def queryUserStatuses(userid, page):

    query = '''
    query($userId: Int, $page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            pageInfo {
                hasNextPage
            }
            activities(userId: $userId, createdAt_greater: 1672549200) {
            ... on ListActivity {
                type
                status
                progress
                media {
                    studios {
                        nodes {
                            name
                            isAnimationStudio
                        }
                    }
                    tags {
                        name
                        category
                        rank
                    }
                    genres
                    id
                    title {
                        romaji
                    }
                    duration
                    seasonYear
                    format
                    relations {
                        edges {
                            relationType
                        }
                    }
                    averageScore
                }
            }
        }
        }
        
    }'''

    variables = {'userId': userid, 'page': page, 'perPage': 50}

    response = requests.post(url, json={'query': query, 'variables': variables}).json()
    return response

def queryMediaRating(userid):
    query = '''
    query($userId: Int, $page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            pageInfo {
                hasNextPage
            }
            mediaList(userId: $userId) {
                score(format: POINT_100)
                media {
                    title {
                        romaji
                    }
                    type
                }
            }
        }
    }
    '''

    hasNextPage = True
    page = 0
    showScoreDict = {}

    while (hasNextPage):
        variables = {'userId': userid, 'page': page, 'perPage': 50}

        response = requests.post(url, json={'query': query, 'variables': variables}).json()
        mediaList = response['data']['Page']['mediaList']

        for mediaEntry in mediaList:
            if mediaEntry['media']['type'] == 'ANIME':
                showScoreDict[mediaEntry['media']['title']['romaji']] = mediaEntry['score']

        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page += 1

        time.sleep(1)

    return showScoreDict

def getDaysWatched(username):

    userId = getUserIdFromUsername(username)

    hasNextPage = True
    page = 0

    minutes_watched = 0

    while (hasNextPage):
        response = queryUserStatuses(userId, page)

        statuses = response['data']['Page']['activities']

        for status in statuses:
            if 'status' in status:
                minutes_watched += timeWatchedHelper(status)
                

        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1

    return minutes_watched/60/24

def getRewatchDays(username):
    userId = getUserIdFromUsername(username)

    hasNextPage = True
    page = 0

    minutes_watched = 0

    while (hasNextPage):
        response = queryUserStatuses(userId, page)

        statuses = response['data']['Page']['activities']

        for status in statuses:
            if 'status' in status:
                if status['status'] == 'rewatched episode':
                    if len(status['progress']) == 1:
                        minutes_watched += status['media']['duration']
                    else:
                        start_ep = int(status['progress'].split(" ")[0])
                        end_ep = int(status['progress'].split(" ")[-1])
                        minutes_watched += (1 + int(end_ep) - int(start_ep)) * status['media']['duration']

                elif status['status'] == 'rewatched':
                    minutes_watched += status['media']['duration']

        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1

    return minutes_watched/60/24


def getDaysWatchedSeasonals(username):

    userId = getUserIdFromUsername(username)

    hasNextPage = True
    page = 0

    minutes_watched = 0

    while (hasNextPage):
        response = queryUserStatuses(userId, page)

        statuses = response['data']['Page']['activities']


        for status in statuses:
            if 'status' in status:
                if status['media']['seasonYear'] == 2023 and status['media']['format'] != 'MOVIE' and not isSequel(status['media']['relations']['edges']):
                    if status['status'] == 'watched episode':
                        if len(status['progress']) == 1:
                            minutes_watched += status['media']['duration']
                        else:
                            start_ep = int(status['progress'].split(" ")[0])
                            end_ep = int(status['progress'].split(" ")[-1])
                            minutes_watched += (1 + int(end_ep) - int(start_ep)) * status['media']['duration']
                    elif status['status'] == 'completed' and status['type'] == 'ANIME_LIST':
                        minutes_watched += status['media']['duration']

        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1

    return minutes_watched/60/24

def getFavoriteFive(username):

    userId = getUserIdFromUsername(username)

    hasNextPage = True
    page = 0

    allMediaScoreDict = queryMediaRating(userId)
    mediaScoreDict = {}

    while (hasNextPage):
        response = queryUserStatuses(userId, page)

        statuses = response['data']['Page']['activities']

        for status in statuses:
            if 'status' in status:
                if status['status'] == 'watched episode' or status['status'] == 'rewatched episode' or status['status'] == 'rewatched' or (status['status'] == 'completed' and status['type'] == 'ANIME_LIST'):
                    if status['media']['title']['romaji'] not in mediaScoreDict:
                        try:
                            mediaScoreDict[status['media']['title']['romaji']] = allMediaScoreDict[status['media']['title']['romaji']]
                        except KeyError:
                            print("Title differs in AniList")
                        
        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1

    
    return filterTopFive(mediaScoreDict, userId)

def filterTopFive(mediaScoreDict, userId):
    topFiveShowsArr = []
    topFiveScores = {}
    sortedDict = dict(sorted(mediaScoreDict.items(), key=lambda item: -item[1]))

    for item in list(sortedDict.items()):
        if len(topFiveShowsArr) < 5 or topFiveScores[topFiveShowsArr[-1]] == item[1]:
            topFiveShowsArr.append(item[0])
            topFiveScores[item[0]] = item[1]
    
    if len(topFiveShowsArr) > 5:
        newTopFive = []
        tiebreaks = []
        favorites = []
        favoritesList = [x['title']['romaji'] for x in queryUserFavorites(userId)['data']['User']['favourites']['anime']['nodes']]
        for item in list(topFiveScores.items()):
            if item[1] > list(topFiveScores.items())[-1][1]:
                newTopFive.append(item[0])
            else:
                tiebreaks.append(item[0])

        for item in favoritesList:
            if item in tiebreaks:
                favorites.append(item)
        
        if len(favorites) + len(newTopFive) == 5:
            newTopFive.append(favorites)
            newTopFive = [item for sublist in newTopFive for item in sublist]
        elif len(favorites) + len(newTopFive) < 5:
            newTopFive.append(favorites)
            newTopFive = [item for sublist in newTopFive for item in sublist]

            for item in list(topFiveScores.items()):
                if item[0] not in newTopFive and len(newTopFive) < 5:
                    newTopFive.append(item[0])
        else:
            for item in favorites:
                if len(newTopFive) < 5:
                    newTopFive.append(item)

        topFiveShowsArr = newTopFive

    return topFiveShowsArr

def addLabels(x, y, labels):
    for i in range(len(x)):
        plt.text(y[i] + len(labels[i])/23 + 1/10, i, labels[i], ha = 'center')

def getFavoriteGenre(username):

    userid = getUserIdFromUsername(username)
    hasNextPage = True
    page = 0

    genreDict = {}
    showList = []

    allMediaScoreDict = queryMediaRating(userid)

    while hasNextPage:
        response = queryUserStatuses(userid, page)

        statuses = response['data']['Page']['activities']

        for status in statuses:
            if 'status' in status:
                if status['media']['title']['romaji'] not in showList and (status['status'] == 'watched episode' or status['status'] == 'rewatched episode' or status['status'] == 'rewatched' or (status['status'] == 'completed' and status['type'] == 'ANIME_LIST')):
                    showList.append(status['media']['title']['romaji'])
                    for item in status['media']['genres']:
                        if item in list(genreDict.keys()):
                            genreDict[item][1] += 1
                            if allMediaScoreDict[status['media']['title']['romaji']] > allMediaScoreDict[genreDict[item][0]]:
                                genreDict[item][0] = status['media']['title']['romaji']
                        else:
                            genreDict[item] = [status['media']['title']['romaji'], 1]

        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1

    genreDict = dict(sorted(genreDict.items(), key=lambda item: -item[1][1]))
    genreNames = list(genreDict.keys())
    genreData = [x[1] for x in list(genreDict.values())]
    genreLabels = [x[0] for x in list(genreDict.values())]

    fig = plt.figure(figsize = (20, 10))

    plt.barh(genreNames, genreData, color ='maroon', 
        height = 0.8)

    plt.xlabel("Number of Shows")
    plt.ylabel("Genres")
    addLabels(genreNames, genreData, genreLabels)
    plt.title(username + " Favorite Genres 2023")
    plt.show()

def getFavoriteStudio(username):

    userid = getUserIdFromUsername(username)
    hasNextPage = True
    page = 0

    studioDict = {}
    showList = []

    while hasNextPage:

        response = queryUserStatuses(userid, page)

        statuses = response['data']['Page']['activities']

        for status in statuses:
            if 'status' in status:
                if status['media']['title']['romaji'] not in showList and (status['status'] == 'watched episode' or status['status'] == 'rewatched episode' or status['status'] == 'rewatched' or (status['status'] == 'completed' and status['type'] == 'ANIME_LIST')):
                    showList.append(status['media']['title']['romaji'])
                    for studio in status['media']['studios']['nodes']:
                        if studio['isAnimationStudio']:
                            if studio['name'] not in list(studioDict.keys()):
                                studioDict[studio['name']] = 1
                            else:
                                studioDict[studio['name']] += 1

        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1

    studioDict = dict(sorted(studioDict.items(), key=lambda item: -item[1]))
    return list(studioDict.items())[0][0]

def timeWatchedHelper(status):
    if status['status'] == 'watched episode' or status['status'] == 'rewatched episode':
        if len(status['progress']) == 1:
            return status['media']['duration']
        else:
            start_ep = int(status['progress'].split(" ")[0])
            end_ep = int(status['progress'].split(" ")[-1])
            return (1 + int(end_ep) - int(start_ep)) * status['media']['duration']
    elif status['status'] == 'rewatched' or status['status'] == 'completed' and status['type'] == 'ANIME_LIST':
        return status['media']['duration']


def getMostTimeSpentWatchingShow(username):

    userid = getUserIdFromUsername(username)
    hasNextPage = True
    page = 0

    timeDict = {}

    while hasNextPage:

        response = queryUserStatuses(userid, page)

        statuses = response['data']['Page']['activities']

        for status in statuses:
            if 'status' in status:
                if status['status'] == 'watched episode' or status['status'] == 'rewatched episode' or status['status'] == 'rewatched' or (status['status'] == 'completed' and status['type'] == 'ANIME_LIST'):
                    if status['media']['title']['romaji'] in list(timeDict.keys()):
                        timeDict[status['media']['title']['romaji']] += timeWatchedHelper(status)
                    else:
                        timeDict[status['media']['title']['romaji']] = timeWatchedHelper(status)

        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1

    timeDict = dict(sorted(timeDict.items(), key=lambda item: -item[1]))
    return list(timeDict.items())[0][0]

def getFavoriteTag(username, tagType):

    userid = getUserIdFromUsername(username)
    hasNextPage = True
    page = 0

    themeDict = {}
    castDict = {}
    demoDict = {}
    showList = []

    while hasNextPage:

        response = queryUserStatuses(userid, page)

        statuses = response['data']['Page']['activities']

        for status in statuses:
            if 'status' in status:
                if status['media']['title']['romaji'] not in showList and (status['status'] == 'watched episode' or status['status'] == 'rewatched episode' or status['status'] == 'rewatched' or (status['status'] == 'completed' and status['type'] == 'ANIME_LIST')):
                    showList.append(status['media']['title']['romaji'])
                    for tag in status['media']['tags']:
                        if tag['category'][0:6] == "Theme-" and tagType == "Theme":
                            if tag['name'] not in list(themeDict.keys()):
                                themeDict[tag['name']] = tag['rank']
                            else:
                                themeDict[tag['name']] += tag['rank']
                        elif tag['category'][0:11] == "Cast-Traits" and tagType == "Cast":
                            if tag['name'] not in list(castDict.keys()):
                                castDict[tag['name']] = tag['rank']
                            else:
                                castDict[tag['name']] += tag['rank']
                        elif tag['category'][0:4] == "Demo" and tagType == "Demo":
                            if tag['name'] not in list(demoDict.keys()):
                                demoDict[tag['name']] = tag['rank']
                            else:
                                demoDict[tag['name']] += tag['rank']

        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1

    themeDict = dict(sorted(themeDict.items(), key=lambda item: -item[1]))
    castDict = dict(sorted(castDict.items(), key=lambda item: -item[1]))
    demoDict = dict(sorted(demoDict.items(), key=lambda item: -item[1]))
    
    if tagType == "Cast":
        return [x[0] for x in list(castDict.items())[0:3]]
    elif tagType == "Theme":
        return [x[0] for x in list(themeDict.items())[0:3]]
    elif tagType == "Demo":
        return list(demoDict.items())[0][0]
    

def getControversyScore(username):

    userid = getUserIdFromUsername(username)
    hasNextPage = True
    page = 0

    showList = []
    showScoreDict = queryMediaRating(userid)

    sumDiffs = 0

    while hasNextPage:

        response = queryUserStatuses(userid, page)

        statuses = response['data']['Page']['activities']

        for status in statuses:
            if 'status' in status:
                if status['media']['title']['romaji'] not in showList and (status['status'] == 'watched episode' or status['status'] == 'rewatched episode' or status['status'] == 'rewatched' or (status['status'] == 'completed' and status['type'] == 'ANIME_LIST')):
                    showList.append(status['media']['title']['romaji'])
                    try:
                        if showScoreDict[status['media']['title']['romaji']] != 0:
                            sumDiffs += abs(showScoreDict[status['media']['title']['romaji']] - status['media']['averageScore'])
                    except KeyError:
                            print("Title differs in AniList")

        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1
        
    return sumDiffs / len(showList)


def getRatingBias(username):
    userid = getUserIdFromUsername(username)
    hasNextPage = True
    page = 0

    showList = []
    showScoreDict = queryMediaRating(userid)

    sumDiffs = 0

    while hasNextPage:

        response = queryUserStatuses(userid, page)

        statuses = response['data']['Page']['activities']

        for status in statuses:
            if 'status' in status:
                if status['media']['title']['romaji'] not in showList and (status['status'] == 'watched episode' or status['status'] == 'rewatched episode' or status['status'] == 'rewatched' or (status['status'] == 'completed' and status['type'] == 'ANIME_LIST')):
                    showList.append(status['media']['title']['romaji'])
                    try:
                        if showScoreDict[status['media']['title']['romaji']] != 0:
                            sumDiffs += showScoreDict[status['media']['title']['romaji']] - status['media']['averageScore']
                    except KeyError:
                            print("Title differs in AniList")

        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1

    return sumDiffs / len(showList)


def getScoreDistribution(username):
    userid = getUserIdFromUsername(username)
    hasNextPage = True
    page = 0

    showList = []
    showScoreDict = queryMediaRating(userid)

    scoresDistributionDict = {"0-5": 0, "5-10":0, "10-15":0, "15-20":0, "20-25":0, "25-30":0, "30-35":0, "35-40":0, "40-45":0, "45-50":0, "50-55": 0, "55-60":0, "60-65":0, "65-70":0, "70-75":0, "75-80":0, "80-85":0, "85-90":0, "90-95":0, "95-100":0}

    while hasNextPage:

        response = queryUserStatuses(userid, page)

        statuses = response['data']['Page']['activities']

        for status in statuses:
            if 'status' in status:
                if status['media']['title']['romaji'] not in showList and (status['status'] == 'watched episode' or status['status'] == 'rewatched episode' or status['status'] == 'rewatched' or (status['status'] == 'completed' and status['type'] == 'ANIME_LIST')):
                    showList.append(status['media']['title']['romaji'])
                    try:
                        if showScoreDict[status['media']['title']['romaji']] != 0:
                            if showScoreDict[status['media']['title']['romaji']] < 5 and showScoreDict[status['media']['title']['romaji']] > 0:
                                scoresDistributionDict["0-5"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 10 and showScoreDict[status['media']['title']['romaji']] >= 5:
                                scoresDistributionDict["5-10"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 15 and showScoreDict[status['media']['title']['romaji']] >= 10:
                                scoresDistributionDict["10-15"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 20 and showScoreDict[status['media']['title']['romaji']] >= 15:
                                scoresDistributionDict["15-20"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 25 and showScoreDict[status['media']['title']['romaji']] >= 20:
                                scoresDistributionDict["20-25"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 30 and showScoreDict[status['media']['title']['romaji']] >= 25:
                                scoresDistributionDict["25-30"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 35 and showScoreDict[status['media']['title']['romaji']] >= 30:
                                scoresDistributionDict["30-35"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 40 and showScoreDict[status['media']['title']['romaji']] >= 35:
                                scoresDistributionDict["35-40"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 45 and showScoreDict[status['media']['title']['romaji']] >= 40:
                                scoresDistributionDict["40-45"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 50 and showScoreDict[status['media']['title']['romaji']] >= 45:
                                scoresDistributionDict["45-50"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 55 and showScoreDict[status['media']['title']['romaji']] >= 50:
                                scoresDistributionDict["50-55"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 60 and showScoreDict[status['media']['title']['romaji']] >= 55:
                                scoresDistributionDict["55-60"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 65 and showScoreDict[status['media']['title']['romaji']] >= 60:
                                scoresDistributionDict["60-65"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 70 and showScoreDict[status['media']['title']['romaji']] >= 65:
                                scoresDistributionDict["65-70"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 75 and showScoreDict[status['media']['title']['romaji']] >= 70:
                                scoresDistributionDict["70-75"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 80 and showScoreDict[status['media']['title']['romaji']] >= 75:
                                scoresDistributionDict["75-80"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 85 and showScoreDict[status['media']['title']['romaji']] >= 80:
                                scoresDistributionDict["80-85"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] < 90 and showScoreDict[status['media']['title']['romaji']] >= 85:
                                scoresDistributionDict["85-90"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] <= 95 and showScoreDict[status['media']['title']['romaji']] >= 90:
                                scoresDistributionDict["90-95"] += 1
                            elif showScoreDict[status['media']['title']['romaji']] <= 100 and showScoreDict[status['media']['title']['romaji']] >= 95:
                                scoresDistributionDict["95-100"] += 1
                    except KeyError as e:
                        print(e)

        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1     

    scoreLabels = list(scoresDistributionDict.keys())
    scoreValues = [x for x in list(scoresDistributionDict.values())]

    fig = plt.figure(figsize = (20, 10))

    plt.bar(scoreLabels, scoreValues, color ='maroon')

    plt.xlabel("Score Range")
    plt.ylabel("Number of Shows")
    plt.yticks(range(0, max(scoreValues) + 1))
    plt.title(username + " Score Distribution 2023")
    plt.show()


