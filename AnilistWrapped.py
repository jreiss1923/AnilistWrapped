import json
import requests
import time
import collections

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
                if status['status'] == 'watched episode' or status['status'] == 'rewatched episode':
                    if len(status['progress']) == 1:
                        minutes_watched += status['media']['duration']
                    else:
                        start_ep = int(status['progress'].split(" ")[0])
                        end_ep = int(status['progress'].split(" ")[-1])
                        minutes_watched += (1 + int(end_ep) - int(start_ep)) * status['media']['duration']
                elif status['status'] == 'rewatched' or status['status'] == 'completed' and status['type'] == 'ANIME_LIST':
                    minutes_watched += status['media']['duration']
                

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
                            print("anilist y")
                        
        hasNextPage = response['data']['Page']['pageInfo']['hasNextPage']
        page = page + 1

    mediaScoreCounter = collections.Counter(mediaScoreDict)
    return [item[0] for item in mediaScoreCounter.most_common(5)]



