# coding: UTF-8
from __future__ import print_function

from python_modules import json
from python_modules import urllib
from python_modules import boto3
from python_modules import random
from python_modules import os.path
from python_modules import requests
from python_modules import time
from python_modules import urlparse

from python_modules.wand.image import Image
from python_modules.wand.drawing import Drawing
from python_modules.wand.color import Color


def send2slack(text, channel, icon):
    payload_dic = {
        "text": text,
        "icon_emoji": icon,
        "channel": channel,
        "username": "Seat Changer",
    }
    url = "https://hooks.slack.com/services/XXXXXXXXXXXX"
    r = requests.post(url, data=json.dumps(payload_dic))


def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'text': err.message if err else res,
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def handler(event, context):

    bucketname = "changeseats"

    try:
        #print(event)
        get = event["queryStringParameters"]
        post = urlparse.parse_qs(event["body"])

        if post["token"][0] != "xxxxxSlackToken1xxxx" and post["token"][0] != "xxxxxSlackToken1xxxx":
            respond(None, "token error:"+post["token"][0])

        if get["action"] == "add":
            action = "add"
        else:
            action = "start"

        channel = post["channel_name"][0]
        #print(channel)
        filename = "changeseats_"+channel+".png"
        file_path = '/tmp/'+filename
        client = boto3.client('s3')
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(bucketname)

        data_file = '/tmp/changeseats_data_'+channel+'.txt'
        s3_data_key = "changeseats/changeseats_data_"+channel+".txt"

        print(action)
        if action == "start":
            sizestr = post["text"][0]
            print(sizestr)
            sizearr = sizestr.split("x")
        else:
            bucket.download_file(s3_data_key, data_file)
            with open(data_file, "r") as f:
                dict = json.loads(f.read())
            list = dict["list"]
            sizestr = dict["size"]
            sizearr = sizestr.split("x")
            account = post["user_name"][0]

        rectsize = 100
        offsetx = 20
        offsety = 20
        rowsize = int(sizearr[0])
        colsize = int(sizearr[1])
        arrsize = rowsize*colsize
        width = colsize*rectsize+offsetx*2
        height = rowsize*rectsize+offsety*2

        if action == "add":
            oc = 0
            for item in list:
                if item != "":
                    oc += 1

                    if item == account:
                        send2slack('Already selected', channel, ":older_adult:")
                        return respond(None, "")

            if oc == arrsize:
                send2slack('Already finished', channel, ":older_adult:")
                return respond(None, "")

            seatnum = random.randrange(arrsize)
            count = 0
            while (list[seatnum] != ""):
                seatnum = random.randrange(arrsize)
                count+=1
                if count > arrsize*2:
                    break
            list[seatnum] = account
            print(str(seatnum)+":"+account)


        else:
            #init
            list = ["" for i in range(arrsize)]

        with open(data_file, "w") as f:
            f.write(json.dumps({'size':sizestr, 'list':list}))

        #client.upload_file(data_file, bucket, s3_data_key)
        bucket.upload_file(data_file, s3_data_key)

        with Drawing() as draw:
            draw.stroke_color = Color('#000')
            draw.fill_color = Color('#fff')
            draw.font_size = 14
            slot = 0
            text_x = 0
            text_y = 0
            for i in range(rowsize):
                for j in range(colsize):
                    x0 = j*rectsize+offsetx
                    y0 = i*rectsize+offsety
                    x1 = (j+1)*rectsize+offsetx
                    y1 = (i+1)*rectsize+offsety
                    #print("x0:"+str(x0)+", y0:"+str(y0)+" x1:"+str(x1)+", y1:"+str(y1))
                    draw.rectangle(left=x0, top=y0, right=x1, bottom=y1)
                    if action == "add":
                        if list[slot] != "":
                            text_x = x0 + 5
                            text_y = y0 + (y1 - y0)/2
                            draw.text(text_x, text_y, list[slot])
                    slot += 1
            with Image(width=width, height=height) as image:
                print(image.size)
                draw.draw(image)
                image.format = 'png'
                image.save(filename=file_path)
        crumb = str(int(time.time()))
        url = "https://s3-ap-northeast-1.amazonaws.com/xxxxxxxx/changeseats/changeseats_"+channel+".png?"+crumb
        text = url+"\n"
        if action == "add":
            if oc-1 == arrsize:
                text += 'The seat change is over'
            else:
                text += 'Selected your seat'
        else:
            text += 'Let\'s change your seat. Please execute \'/selectseat\' command'
        bucket.upload_file(file_path, "changeseats/changeseats_"+channel+".png", ExtraArgs={'ACL': 'public-read'})
        send2slack(text, channel, ":older_adult:")
        return respond(None, text)

    except Exception as e:
        print(e)
