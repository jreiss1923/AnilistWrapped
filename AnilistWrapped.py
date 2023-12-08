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
                score
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

def getFavoriteGenre(username):

    userid = getUserIdFromUsername(username)
    hasNextPage = True
    page = 0

    genreDict = {}
    showList = []

    while hasNextPage:
        response = queryUserStatuses(userid, page)

        statuses = response['data']['Page']['activities']

        for status in statuses:
            if 'status' in status:
                if status['media']['title']['romaji'] not in showList and (status['status'] == 'watched episode' or status['status'] == 'rewatched episode' or status['status'] == 'rewatched' or (status['status'] == 'completed' and status['type'] == 'ANIME_LIST')):
                    showList.append(status['media']['title']['romaji'])
                    for item in status['media']['genres']:
                        if item in list(genreDict.keys()):
                            genreDict[item] += 1
                        else:
                            genreDict[item] = 1

        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1

    genreDict = dict(sorted(genreDict.items(), key=lambda item: -item[1]))
    genreNames = list(genreDict.keys())
    genreData = list(genreDict.values())

    fig = plt.figure(figsize = (20, 10))

    plt.bar(genreNames, genreData, color ='maroon', 
        width = 0.8)

    plt.xlabel("Genres")
    plt.ylabel("Number of Shows")
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



