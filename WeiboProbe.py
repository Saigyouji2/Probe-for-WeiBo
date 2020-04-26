from lxml import etree
import requests
import re
import html
import time
import json
import os
import random
import datetime
import pymysql
class WeiboProbe(object):
    '''初始化函数'''
    def __init__(self,username,configuration):
        self.username=username
        self.configuration=configuration
        self.PersonalInfo=dict()
        self.overallData=[]
        self.keys=[]
        self.values=[]
        self.abbrTranslation=dict()
        self.abbrTranslation["Jan"]=1
        self.abbrTranslation["Feb"]=2
        self.abbrTranslation["Mar"]=3
        self.abbrTranslation["Apr"]=4
        self.abbrTranslation["May"]=5
        self.abbrTranslation["Jun"]=6
        self.abbrTranslation["Jul"]=7
        self.abbrTranslation["Aug"]=8
        self.abbrTranslation["Sep"]=9
        self.abbrTranslation["Oct"]=10
        self.abbrTranslation["Nov"]=11
        self.abbrTranslation["Dec"]=12
        self.header={
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36"
        } 
    def DispathProbe(self):
        '''根据传入的设置信息，进行各个方法的调用'''
        try:
            st=time.time()
            tmpres=self.AcquireUID(self.username)
            UID=tmpres[0]
            prefix=tmpres[1]
            if self.configuration["IfPersonalInfo"]==1:
                self.PersonalInfo=self.GetPersonalInfo(UID,prefix)
                if self.configuration["IfSubscription"]==1:
                    additionalInfo=self.AcquireSubscription(UID)
                    for i in additionalInfo.items():
                        self.PersonalInfo[i[0]]=i[1]
            if self.configuration["IfTexts"]==1:
                self.overallData=self.AcquireText(UID,prefix)
            if self.configuration.get("IfImage",0)!=0 or self.configuration.get("IfVedio",0) or self.configuration.get("IfCommentImage",0)!=0:
                 self.DownloadAndSaveFiles()
            if self.configuration.get("IfTxtFile",0)!=0:
                self.SaveAsTxt()
            if self.configuration.get("IfMysql",0)!=0:
                self.SaveInMysql()
            ed=time.time()
            #print(self.overallData)
            print("Total time cost:",format(ed-st,".1f"))
        except Exception as e:
            print("An exception occured,procedure ceased. "+str(e))

    def SendingRequests(self,URL,mode):
        '''发送请求，获取网页HTML信息，并根据需要（mode）打包为ETREE对象或者JSON类型'''
        try:
            if mode==1:
                response=requests.get(URL,headers=self.header,cookies={"Cookie":str(self.configuration["cookie"])}).content
                tmp=etree.HTML(response)
                return tmp      
            else:
                response=requests.get(URL,headers=self.header,cookies={"Cookie":str(self.configuration["cookie"])})
                return response.json()
        except Exception as e:
            print("An error occured during visiting: "+str(URL),str(e))
    
    def AcquireUID(self,username):
        '''获取用户的USERID'''
        try:
             URL="https://s.weibo.com/user?q={name}&Refer=weibo_user".format(name=username)
             res=self.SendingRequests(URL,1)
             index=res.xpath("//div[@class='m-wrap']//div[@class='info']//a[@class='name']/@href")[0]
             pageURL="https:"+index
             prefix=self.AcquirePrefix(pageURL)
             UID=re.search("/u/(.*?)$",index)
             if UID is not None:
                UID=UID.group(1)
                return [UID,prefix]
             else:
                 URL="https:"+index
                 response=self.SendingRequests(URL,1)
                 response=etree.tostring(response,encoding="utf-8").decode("utf-8")
                 UID=re.search("CONFIG\['oid'\]='(.*?)'",response).group(1)
                 return [UID,prefix]
        except Exception as e:
             print("An error occured during acquiring necessary UID:",str(e))

    def AcquirePrefix(self,URL):
        '''一般来说，用户信息所在的URL组成不仅仅需要一个USERID，也需要一个前缀'''
        response=self.SendingRequests(URL,1)
        text=etree.tostring(response,encoding='utf-8').decode('utf-8')
        return re.search("CONFIG\['domain'\]='(.*?)';",text).group(1)

    def GetPersonalInfo(self,UID,prefix):
        '''获取微博用户个人信息，前提是可见'''
        URL="https://weibo.com/p/{pre}{uid}/info?mod=pedit_more".format(pre=prefix,uid=UID)
        res=self.SendingRequests(URL,1)
        response="".join(res.xpath("//script/text()"))
        tmp=html.unescape(response)
        totalinfo=dict()
        personalinfo=dict()
        occupationinfo=dict()
        educationinfo=dict()
        tmp2=re.search(r'<span class=\\"pt_title S_txt2\\">昵称：<\\/span>.*?<span class=\\"pt_detail\\">(.*?)<\\/span><\\/li>',tmp)
        personalinfo["nickname"]=(tmp2.group(1) if (tmp2!=None) else "")
        tmp2=re.search(r'<span class=\\"pt_title S_txt2\\">所在地：<\\/span>.*?<span class=\\"pt_detail\\">(.*?)<\\/span><\\/li>',tmp)
        personalinfo["location"]=(tmp2.group(1) if (tmp2!=None) else "")
        tmp2=re.search(r'<span class=\\"pt_title S_txt2\\">性别：<\\/span>.*?<span class=\\"pt_detail\\">(.*?)<\\/span><\\/li>',tmp)
        personalinfo["sex"]=(tmp2.group(1) if (tmp2!=None) else "")
        tmp2=re.search(r'<span class=\\"pt_title S_txt2\\">生日：<\\/span>.*?<span class=\\"pt_detail\\">(.*?)<\\/span><\\/li>',tmp)
        personalinfo["birthday"]=(tmp2.group(1) if (tmp2!=None) else "")
        tmp2=re.search(r'简介：.*?<span class=\\"pt_detail\\">(.*?)<\\/span>',tmp)
        personalinfo["briefIntroduction"]=(tmp2.group(1) if (tmp2!=None) else "")
        tmp2=re.search(r'注册时间：.*?<span class=\\"pt_detail\\">(.*?)<\\/span>',tmp)
        personalinfo["registerTime"]=(tmp2.group(1).strip("\\r\\n").strip() if (tmp2!=None) else "")
        totalinfo["personalinfo"]=personalinfo
        tmp2=re.search(r"<a href=.*?&work.*?>(.*?)<\\/a>",tmp)
        occupationinfo["enterpriseName"]=(tmp2.group(1) if (tmp2!=None) else "")
        tmp2=re.search(r"&work.*?地区：(.*?)<",tmp)
        occupationinfo["region"]=(tmp2.group(1) if (tmp2!=None) else "")
        tmp2=re.search(r"&work.*?职位：(.*?)<",tmp)
        occupationinfo["title"]=(tmp2.group(1).strip() if (tmp2!=None) else "")
        totalinfo["occupationinfo"]=occupationinfo
        tmp2=re.search(r"<.*?&school.*?>(.*?)<\\/a>",tmp)
        educationinfo["university"]=(tmp2.group(1) if (tmp2!=None) else "")
        totalinfo["educationinfo"]=educationinfo
        return totalinfo

    def AcquireText(self,UID,prefix):
        '''根据用户设置里需求，选择以时间限制来获取微博，或者是以数量限制获取微博'''
        if self.configuration.get("AmountLimit",0)!=0:
            maxLimit=self.configuration["AmountLimit"]
            current=0
            next=0
            finalData=[]
            while current < maxLimit:
                self.ProgressBar(current,maxLimit)
                URL="https://m.weibo.cn/api/container/getIndex?type=uid&value={uid}&containerid=107603{uid}&since_id={next}".format(uid=UID,next=next)
                text=self.SendingRequests(URL,0)
                next=text["data"]["cardlistInfo"]["since_id"] 
                pageLimit=len(text["data"]["cards"])
                overall=text["data"]["cardlistInfo"]["total"]
                maxLimit=min([text["data"]["cardlistInfo"]["total"],maxLimit])
                recentData=self.ParsePageByAmountLimit(text,pageLimit,maxLimit-current)       
                finalData.extend(recentData)
                current=len(finalData)
                self.ProgressBar(current,maxLimit)
                time.sleep(random.uniform(1,3))
            print("This user has "+str(overall)+" texts.")
            return finalData
        else:
            #self.header["X-Requested-With"]="XMLHttpRequest"
            timeBound=self.configuration["TimeLimit"]
            currentTime=time.strftime("%Y-%m-%d",time.localtime())
            currentTime=str(currentTime)
            next=0
            finalData=[]
            timeA=datetime.datetime.strptime(timeBound,"%Y-%m-%d")
            timeB=datetime.datetime.strptime(currentTime,"%Y-%m-%d")
            total=(timeB-timeA).days
            while currentTime >= timeBound:
                timeA=datetime.datetime.strptime(timeBound,"%Y-%m-%d")
                timeB=datetime.datetime.strptime(currentTime,"%Y-%m-%d")
                cur=(timeB-timeA).days    
                self.ProgressBar(total-cur,total)
                URL="https://m.weibo.cn/api/container/getIndex?type=uid&value={uid}&containerid=107603{uid}&since_id={next}".format(uid=UID,next=next)
                response=self.SendingRequests(URL,0)
                next=response["data"]["cardlistInfo"]["since_id"]
                pageLimit=len(response["data"]["cards"])
                overall=response["data"]["cardlistInfo"]["total"]
                recentData=self.ParsePageByTimeLimit(response,pageLimit,timeBound)
                finalData.extend(recentData[1])
                currentTime=recentData[0]                
                timeA=datetime.datetime.strptime(timeBound,"%Y-%m-%d")
                timeB=datetime.datetime.strptime(currentTime,"%Y-%m-%d")
                cur=(timeB-timeA).days    
                self.ProgressBar(total-cur,total)
                time.sleep(random.uniform(1,3))
            print("This user has "+str(overall)+" texts.")
            return finalData

    def ParseTime(self,currentTime):
        '''由于微博文本内的时间有很多种表述格式，所以这个方法把它们转换成统一的xxxx-xx-xx，利于日后整理数据'''
        if re.search("分钟前",currentTime) is not None:
            tmpvar=re.search("([0-9]{1,2})分钟前",currentTime)
            today=datetime.datetime.today()
            delta=datetime.timedelta(minutes=int(tmpvar.group(1)))
            target=today-delta
            currentTime="-".join([str(target.year),str(target.month),str(target.day)])
        elif re.search("小时前",currentTime) is not None:
            tmpvar=re.search("([0-9]{1,2})小时前",currentTime)
            today=datetime.datetime.today()
            delta=datetime.timedelta(hours=int(tmpvar.group(1)))
            target=today-delta
            currentTime="-".join([str(target.year),str(target.month),str(target.day)])
        elif re.search("昨天",currentTime) is not None:
            today=datetime.datetime.today()
            delta=datetime.timedelta(days=1)
            target=today-delta
            currentTime="-".join([str(target.year),str(target.month),str(target.day)])
        elif re.search("([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})",currentTime) is not None:
            tmpvar=re.search("([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})",currentTime)
            y=tmpvar.group(1)
            m=tmpvar.group(2)
            d=tmpvar.group(3)
            if int(m)<10:
                m.zfill(1)
            if int(d)<10:
                d.zfill(1)
            currentTime="-".join([y,m,d])
        else:
            tmpvar=re.search("([0-9]{1,2})-([0-9]{1,2})",currentTime)
            m=tmpvar.group(1)
            d=tmpvar.group(2)
            if int(m)<10:
                m.zfill(1)
            if int(d)<10:
                d.zfill(1)
            currentTime="-".join(["2020",m,d])
        return currentTime

    def ParsePageByTimeLimit(self,text,pageLimit,timeBound):
        '''根据时间限制获取微博'''
        processed=[]
        for i in range(pageLimit):
            try:
                if text["data"]["cards"][i]["card_type"]==11:
                    if i<pageLimit:
                        continue
                currentTime=text["data"]["cards"][i]["mblog"]["created_at"]
                currentTime=self.ParseTime(currentTime)
                if currentTime<timeBound:
                    break
                middleData=dict()
                if text["data"]["cards"][i]["mblog"].get("retweeted_status",0)!=0:
                    middleData["ifReposted"]=1
                    if self.configuration["OriginalOrReposted"]=="O":
                        if i<pageLimit:
                            continue
                    if self.configuration["GetSource"]==1:
                       tempDataB=self.GetRepostedText(text["data"]["cards"][i]["mblog"]["retweeted_status"],i)
                else:
                    middleData["ifReposted"]=0
                    if self.configuration["OriginalOrReposted"]=="R":
                        if i<pageLimit:
                            continue
                middleData=self.ParsePage(middleData,text,i)
                if  self.configuration.get("GetSource",0)==1 and middleData["ifReposted"]==1:
                    middleData["text"]+=" "+tempDataB
                processed.append(middleData)
            except Exception as e:
                print("An exception occured:"+str(e))
        return [currentTime,processed]
                    
    def ParsePage(self,middleData,text,i):
        '''根据JSON获取一页内的微博内容'''
        middleData["imageURL"]=[]
        middleData["videoURL"]=[]
        middleData["id"]=text["data"]["cards"][i]["mblog"]["id"]
        middleData["mid"]=text["data"]["cards"][i]["mblog"]["mid"]
        middleData["date"]=self.ParseTime(text["data"]["cards"][i]["mblog"]["created_at"])
        tmp2=text["data"]["cards"][i]["mblog"].get("text",0)
        tmp=etree.HTML(tmp2)
        if "全文" not in tmp.xpath("//p//a/text()"):
            middleData["text"]=re.sub("<.*?>","",etree.tostring(tmp,encoding="utf-8").decode("utf-8"))
        else:
            tmp=etree.tostring(tmp,encoding="utf-8").decode("utf-8")  
            preres=re.search('.*<a href="(.*?)">全文</a>',tmp)  
            additional=preres.group(1)
            address="https://m.weibo.cn/"+additional
            responding=self.SendingRequests(address,1)
            middleText="".join(responding.xpath("//script//text()"))
            res2=re.search('.*?"text": "(.*?)",',middleText)
            middleData["text"]=res2.group(1)
            middleData["text"]=re.sub("<.*?>","",middleData["text"])
        if middleData["text"].strip()=="":
            middleData["text"]="(Only emojis or spaces)"
        middleData["compliments"]=text["data"]["cards"][i]["mblog"]["attitudes_count"]
        middleData["reposts"]=text["data"]["cards"][i]["mblog"]["reposts_count"]
        middleData["commentsNum"]=text["data"]["cards"][i]["mblog"]["comments_count"] 
        if text["data"]["cards"][i]["mblog"].get("pics",0)!=0:
            middleData["ifHasPics"]=len(text["data"]["cards"][i]["mblog"]["pics"])
            if self.configuration.get("IfImage",0) == 1:
                imageUrl=[]
                for picIndex in range(middleData["ifHasPics"]):
                    imageUrl.append(text["data"]["cards"][i]["mblog"]["pics"][picIndex]["url"])
                middleData["imageURL"].extend(imageUrl)
        else:    
            middleData["ifHasPics"]=0
        if text["data"]["cards"][i]["mblog"].get("page_info",0)!=0 and text["data"]["cards"][i]["mblog"]["page_info"]["type"]== "video":
            middleData["ifHasVideo"]=1
            if self.configuration.get("IfVedio",0) == 1:
                videoUrl=[]
                videoUrl.append(text["data"]["cards"][i]["mblog"]["page_info"]["page_url"])
                middleData["videoURL"].extend(videoUrl)
        else:
            middleData["ifHasVideo"]=0
        if self.configuration["IfComment"]==1:
            middleData["comments"]=self.AcquireComments(text["data"]["cards"][i]["mblog"]["id"],text["data"]["cards"][i]["mblog"]["mid"])
        return middleData

    def ParsePageByAmountLimit(self,text,pageLimit,requirement):
        '''根据数量限制获取微博'''
        processed=[]
        i=0
        while i < pageLimit:
            try:
                if text["data"]["cards"][i]["card_type"]==11:
                    #print("Not visible or it had been deleted.")
                    if i<pageLimit:
                        i+=1
                    continue
                middleData=dict()
                if text["data"]["cards"][i]["mblog"].get("retweeted_status",0)!=0:
                    middleData["ifReposted"]=1
                    if self.configuration["OriginalOrReposted"]=="O":
                        if i<pageLimit:
                            i+=1
                        continue
                    if self.configuration["GetSource"]==1:
                        tempDataB=self.GetRepostedText(text["data"]["cards"][i]["mblog"]["retweeted_status"],i)
                else:
                    middleData["ifReposted"]=0
                    if self.configuration["OriginalOrReposted"]=="R":
                        if i<pageLimit:
                            i+=1
                        continue 
                middleData=self.ParsePage(middleData,text,i)
                if self.configuration.get("GetSource",0)==1 and middleData["ifReposted"]==1:
                    middleData["text"]+=" "+tempDataB
                processed.append(middleData)
                i+=1
                if len(processed)>=requirement:
                    break
            except Exception as e:
                print("Not valid.it should be skipped for an exception:",e)
                continue 
        return processed

    def AlterTimeFormat(self,originalTime):
        '''微博评论内的时间格式不符合我们的标准，在这里更换时间格式'''
        tmpvar=re.search("[A-Za-z]{3}.([A-Za-z]{3}).([0-9]{1,2}).*?([0-9]{4})$",originalTime)
        formatted="-".join([str(tmpvar.group(3)),str(self.abbrTranslation[tmpvar.group(1)]),str(tmpvar.group(2))])
        return formatted
    
    def GetRepostedText(self,text,i):
        '''获取转发微博的源微博文本'''
        sourceTextId=text["id"]
        URL="https://m.weibo.cn/statuses/extend?id={id}".format(id=text["id"])
        response=self.SendingRequests(URL,0)
        sourceText=response["data"]["longTextContent"]
        sourceText=re.sub("<.*?>","",sourceText)
        return sourceText

    def AcquireComments(self,textid,textmid):
        '''获取微博下的评论信息'''
        URL="https://m.weibo.cn/comments/hotflow?id={paraA}&mid={paraB}&max_id_type=0".format(paraA=textid,paraB=textmid)
        response=self.SendingRequests(URL,0)
        requirement=self.configuration["CommentRequirement"]
        packedData=dict()
        packedData["id"]=textid
        packedData["mid"]=textmid
        if response.get("data",0)!=0:
            total=int(response["data"]["total_number"])
            requirement=min([requirement,total])
            #print("This text has "+str(total)+" comment(s).")
            commentsData=[]
            current=0
            while current<requirement:
                pageLimit=len(response["data"])
                next=response["data"]["max_id"]
                pageLimit=min([pageLimit,requirement-current])
                for i in range(pageLimit):
                    try:
                        tempData=dict()
                        tempData["commentTime"]=self.AlterTimeFormat(response["data"]["data"][i]["created_at"])
                        tempData["commenterName"]=response["data"]["data"][i]["user"]["screen_name"]
                        tempText=response["data"]["data"][i]["text"]
                        tempData["text"]=re.sub("<.*?>","",tempText)
                        tempData["compliments"]=response["data"]["data"][i]["like_count"]
                        if self.configuration.get("IfCommentImage",0)==1:
                            imgURL=[]
                            if response["data"]["data"][i].get("pic",0)!=0:
                                imgURL.append(response["data"]["data"][i]["pic"]["url"])
                                tempData["commentImage"]=imgURL
                        commentsData.append(tempData)
                    except Exception as e:
                        print("An error occured in collecting comments:"+str(e))
                current+=len(commentsData)
                time.sleep(random.uniform(1,3))
                if next=="0":
                    break
                URL="https://m.weibo.cn/comments/hotflow?id={paraA}&mid={paraB}&max_id={paraC}&max_id_type=0".format(paraA=textid,paraB=textmid,paraC=next)
                response=self.SendingRequests(URL,0)
            #print(commentsData)
            packedData["commentsData"]=commentsData
            return packedData
        else:
            packedData["commentsData"]=[]
            return packedData

    def AcquireSubscription(self,UID):
        '''获取关注数，粉丝数'''
        URL="https://m.weibo.cn/api/container/getIndex?type=uid&value={uid}&containerid=100505{uid}".format(uid=UID)
        response=self.SendingRequests(URL,0)
        info=dict()
        info["subscription"]=response["data"]["userInfo"]["follow_count"]
        info["fans"]=response["data"]["userInfo"]["followers_count"]
        return info

    def RecordConfiguration(self,configuration):
        '''保存用户设置'''
        jsconfig=json.dumps(configuration)
        with open("config.txt","w",encoding="utf-8") as f:
            f.write(jsconfig)
        print("configuration stored.")

    @staticmethod
    def LoadConfiguration():
        '''读取用户设置'''
        configuration=dict()
        if os.path.exists("config.txt"):
            f=open("config.txt","r")
            js=f.read()
            configuration=json.loads(js)
            f.close()
            return configuration
        else:
            return None
    
    #@staticmethod
    #def SearchCookie():
    #    browser=webdriver.Chrome()
    #    browser.get("https://passport.weibo.cn/signin/login")
    #    time.sleep(20)
    #    browser.get("https://weibo.cn")
    #    cook=browser.get_cookies()
    #    midproduct=dict()
    #    secquence=["SUB","SUHB","SCF","SSOLoginState","_T_WM","WEIBOCN_FROM","MLOGIN","M_WEIBOCN_PARAMS"]
    #    for i in cook:
    #        midproduct[i["name"]]=i["value"]
    #    midproduct["WEIBOCN_FROM"]="1110006030"
    #    cookie="; ".join([i+"="+midproduct[i] for i in secquence])
    #    browser.close()
    #    return cookie

    def InspectPath(self):
        '''查询存储路径是否存在，不存在的话创建一个'''
        filePath=self.configuration["Path"]
        if not os.path.exists(filePath):
            os.makedirs(filePath)
            print("Storage directory created.")
        else:
            print("Storage directory already exists.")

    def SpecialParsingForInfoDictionary(self,paradict):
        '''对于以上方法获得的嵌套字典进行解析'''
        for elemk in paradict.items():
            if isinstance(elemk[1],(int,str))==True:
                self.keys.append(elemk[0])
                self.values.append(elemk[1])
            else:
                    self.SpecialParsingForInfoDictionary(elemk[1])

    def DownloadAndSaveFiles(self):
        '''下载并存储文件'''
        self.InspectPath()
        imgUrlSet=[]
        vedUrlSet=[]
        if self.configuration["IfImage"]==1:
            for elem in self.overallData:
                if elem["ifHasPics"] >= 1:
                    imgUrlSet.extend(elem["imageURL"])
        if self.configuration["IfVedio"]==1:
            for elem in self.overallData:
                if elem["ifHasVideo"] == 1:
                    vedUrlSet.extend(elem["videoURL"])
        if self.configuration["IfCommentImage"]==1:
            for elem in self.overallData:
                for comElem in elem["comments"]: 
                    if comElem != "No comments or comments invisible." and comElem.get("commentImage",0)!=0:
                        imgUrlSet.extend(comElem["commentImage"])
        thereshold=len(os.listdir(self.configuration["Path"]))+1
        currentNum=thereshold
        savedNum=0
        for url in imgUrlSet:
            try:
                response=requests.get(url).content
                file=open(self.configuration["Path"]+"\\"+str(currentNum)+".jpg","wb")
                file.write(response)
                file.close()
                currentNum+=1
                savedNum+=1
            except Exception as e:
                print("An image cant be saved for an error: "+str(e))
        print(str(savedNum)+" images have been saved in your directory.You can check them whenever you like.")
    
    def SaveAsTxt(self):
        '''把爬取的信息存储为TXT'''
        addition=0
        if os.path.exists(str(self.username)+str(addition)+".txt"):
            while os.path.exists(str(self.username)+str(addition)+".txt"):
                addition+=1
        print(str(self.username)+str(addition)+".txt")
        with open(str(self.username)+str(addition)+".txt","w",encoding="utf-8") as f:
            f.write("Visible Infomation\n")
            if self.configuration["IfPersonalInfo"]==1:
                for i in self.PersonalInfo.keys():
                     if isinstance(i,dict)==True:
                         f.write(str(i)+" : "+str(self.PersonalInfo[i])+"\n")
                     elif isinstance(self.PersonalInfo[i],dict)==True:
                         f.write(str(i)+"\n")
                         for j in self.PersonalInfo[i].keys():
                            f.write("  "+str(j)+" : "+str(self.PersonalInfo[i][j])+"\n")
            if self.configuration["IfTexts"]==1:
                for Element in self.overallData:
                    for i in Element.keys():
                        if i=="mid" or i=="id":
                            continue
                        if i!="comments":
                             f.write(str(i)+" : "+str(Element[i])+"\n")
                        else:
                            f.write(str(i)+"\n")
                            for j in Element[i]:
                                if isinstance(Element[i][j],list)==True:
                                    for k in Element[i][j]:
                                        for p in k.keys():
                                            f.write("  "+str(p)+":"+str(k[p])+"\n")
                    f.write("\n")

        f.close()
        print("File saved.")

    def SaveInMysql(self):
        '''存入你的MYSQL数据库内'''
        info=input("Please enter your mysql username,password,and selected database,separated by a space.\n").strip().split(" ")
        connection=pymysql.connect(host="localhost",user=info[0],password=info[1],port=3306,db=info[2])
        command=connection.cursor()
        if self.configuration["IfPersonalInfo"]==1:
            createTable="""
                create table if not exists PersonalInfo 
                (
	                nickname varchar(90) not null primary key,
                    location varchar(20),
                    sex varchar(5),
                    birthday varchar(20),
                    briefIntroduction varchar(100),
	                registerTime varchar(20),
                    enterpriseName varchar(40),
                    region varchar(20),
                    title varchar(20),
                    university varchar(30),
                    subscription int,
                    fans int
                ) """
            self.SpecialParsingForInfoDictionary(self.PersonalInfo)
            tempPara=",".join(["%s"]*len(self.keys))
            insertOrder="insert into PersonalInfo values({parameters}) on duplicate key update ".format(parameters=tempPara)
            addtionalA=",".join(["{x}=%s".format(x=i) for i in self.keys])
            insertOrder+=addtionalA
            payload=tuple(self.values*2)
            command.execute(createTable)
            command.execute(insertOrder,payload)
            connection.commit()
            print("Personal infomation stored.")
        if self.configuration["IfTexts"]==1:
            createTableA="""
            create table if not exists weiboTexts
            (
                ifreposted int not null,
	            id varchar(40) not null,
                mid varchar(40) not null,
                date varchar(40) not null,
                text varchar(10000),
                compliments int not null,
                reposts int not null,
                commentsNum int not null,
                ifHasPics int not null,
                ifHasVideo int not null
            )
            """
            index=list(self.overallData[0].keys())
            index.remove("imageURL")
            index.remove("videoURL")
            index.remove("comments")
            parameters=",".join(["%s"]*len(index))
            insertOrder="insert into weiboTexts values({parameters}) on duplicate key update ".format(parameters=parameters)
            additionalB=",".join(["{x}=%s".format(x=i) for i in index])
            insertOrder+=additionalB
            #print(insertOrder)
            v=[]
            command.execute(createTableA)
            for k in range(len(self.overallData)):
                try:
                    for i in index:
                        v.append(str(self.overallData[k][i]))
                        payloadB=tuple(v*2)
                    command.execute(insertOrder,payloadB)
                    connection.commit()
                    print("Insertation completed.")
                except Exception as e:
                    print("Insertation failed for "+str(e))
        if self.configuration["IfComment"]==1:
            createTableB="""
                create table if not exists comments
            (
                id varchar(50) not null,
                mid varchar(50) not null,
                commentTime varchar(50) not null,
                commenterName varchar(50) not null,
                text varchar(7000),
                compliments int not null
            )
            """
            k=["id","mid"]
            h=list(self.overallData[0]["comments"]["commentsData"][0].keys())
            k.extend(h)
            parameterC=",".join(["%s"]*len(k))
            insertOrderC="insert into comments values({parameterC}) on duplicate key update ".format(parameterC=parameterC)
            extra=",".join(["{x}=%s".format(x=i) for i in k])
            insertOrderC+=extra
            command.execute(createTableB)
            for item in self.overallData:
                for com in item["comments"]["commentsData"]:
                    try:
                        a=[item["id"],item["mid"]]
                        a.extend(list(map(str,com.values())))
                        payloadC=tuple(a*2)
                        command.execute(insertOrderC,payloadC)
                        connection.commit()
                        print("Insertation completed.")
                    except Exception as e:
                        print("Insertation failed for "+str(e))
    
    def ProgressBar(self,current,total):
        '''显示进度条'''
        if current>0:
            print(end="\r")
        for i in range(current*50//total):
            print(">",end="")
        for i in range(50-(current*50//total)):
            print("*",end="")
        print("Current progress: "+str(format(current/total*100,".1f"))+"% ",end="") 

def PreparationBeforeLaunch():
    '''确认用户设置'''
    configuration=dict()
    tmpcookie=""
    configuration["IfVedio"]=0
    if os.path.exists("cookie.txt"):
        with open("cookie.txt","r",encoding="utf-8") as f:
            tmpcookie+=f.readline()
    if tmpcookie is not "":
        configuration["cookie"]=tmpcookie
        print("Cookie payload has been prepared.")
    else:
        print("No reserved cookie.Please login your account to get a cookie.")
    if input("Do you want to get profiles of this user?(Y/N)\n").upper()=="Y":
        configuration["IfPersonalInfo"]=1
        if input("Do you want to know the fans quantity of this user?(Y/N)\n")=="Y":
            configuration["IfSubscription"]=1
    else:
        configuration["IfPersonalInfo"]=0
    if input("Do you want to get texts from this user?(Y/N)\n").upper()=="Y":
        configuration["IfTexts"]=1
        if input("Do you want to obtain texts limited by a certain time (after this time) or a certain amount?(T/A)\n").upper()=="T":
            configuration["TimeLimit"]=input("Please enter the time in the format xxxx-xx-xx\n")
            configuration["AmountLimit"]=0
        else:
            configuration["AmountLimit"]=int(input("Please enter texts amount.\n"))
            configuration["TimeLimit"]="9999-12-31"
        if input("Do you want to obtain the images of every text?(Y/N)\n").upper()=="Y":
            configuration["IfImage"]=1
        else:
            configuration["IfImage"]=0
        configuration["IfVedio"]=0
        tmpres=input("Do you want to obtain both original and reposted texts or original only or reposted only?(B/O/R)\n").upper()
        if tmpres=="B":
            configuration["OriginalOrReposted"]="B"
        elif tmpres=="O":
            configuration["OriginalOrReposted"]="O"
        else:
            configuration["OriginalOrReposted"]="R"
        if configuration["OriginalOrReposted"]=="B" or configuration["OriginalOrReposted"]=="R":
            if input("Do you want to get original contents of reposted texts?(Y/N)\n").upper()=="Y":
                configuration["GetSource"]=1
            else:
                configuration["GetSource"]=0
        if input("Do you want to obtain comments below each text?(Y/N)\n").upper()=="Y":
            configuration["IfComment"]=1
            configuration["CommentRequirement"]=int(input("How many comments do you want to obtain below each text?\n"))
            if input("Do you want to obtain images attached to every comment if it has?(Y/N)\n").upper()=="Y":
                configuration["IfCommentImage"]=1
            else:
                configuration["IfCommentImage"]=0
        else:
            configuration["IfComment"]=0
        if configuration.get("IfImage",0)!=0 or configuration.get("IfVedio",0)!=0 or configuration.get("IfCommentImage",0)!=0:
            configuration["Path"]=input("Please select a path to store pictures or videos.\n")
    else:
        configuration["IfTexts"]=0
    if input("Do you want to store results as a txt file?(Y/N)\n").upper()=="Y":
        configuration["IfTxtFile"]=1
    if input("Do you want to store results in your MySQL database?(Y/N)\n").upper()=="Y":
        configuration["IfMysql"]=1
    Recon=WeiboProbe(username,configuration)
    Recon.RecordConfiguration(configuration)
    Recon.DispathProbe()

if __name__=="__main__":
    configuration=dict()
    username=input("Please enter a username.\n")
    configuration=WeiboProbe.LoadConfiguration()
    engtochi=dict()
    if configuration is not None:
        print("Do you want to retain your the following config recorded with your last manipulation? ")
        for i in configuration.items():
            print(engtochi.get(i[0],i[0]),":",i[1])
        if input("Press Y/N to choose.\n").upper()=="Y":
            Recon=WeiboProbe(username,configuration)
            Recon.DispathProbe()
        else:
            PreparationBeforeLaunch()
    else:
        PreparationBeforeLaunch()
