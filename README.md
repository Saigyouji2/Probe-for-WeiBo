## 项目背景
**本**项目仅是一个学生的自娱自乐，性能一般，无法当做正规数据获取工具。
## 安装
**推**荐在任何支持python的编辑器中使用,在CMD里用python xxx.py 命令亦可启动
**本程序的运行需要lxml库 4.4.1版本 以上，及Pymysql插件**
## 基本功能
### 只需提供一个用户昵称和一个cookie字符串，就可以使用以下功能
#### 1.获得用户的可见信息
- 用户昵称
- 用户所在位置（个人设置的）
- 性别
- 生日
- 简介
- 注册时间
- 就职企业名称
- 就职区域
- 职称
- 所在大学

#### 2.获得用户关注数，粉丝数
#### 3.获取用户微博
你可以选择如下设置
- 按照数量限制获取微博数量
- 输入一个时间，获得这个时间以后直至当前的所有微博
- 选择是获取原创微博，还是转发微博，或者是两者皆有
- 选择是否获取转发微博的源微博的正文

一篇完整的微博信息包括
- 该微博是否转发
- 该篇文章id(在网页中的参数)
- 该篇文章mid(在网页中的参数)
- 发布日期 (xxxx-xx-xx)
- 正文（如果你选择了获取转发微博源微博正文，源微博正文将拼接到这里）
- 点赞数
- 转发数
- 评论数

#### 4.获取微博下的图片（不包括转发内容的源微博）
- 如果你在初始设置中选择了获取微博图片，那么你需要指定一个路径（最好是存在路径+一个文件夹名），如果这个文件夹不存在，程序将自动创建。

#### 5.获取微博评论（不包括转发内容的源微博下的评论）
- 你可以在初始设置中输入你对于每一条微博需要多少条评论，假如你需要5条，那么对于爬取的每一条微博都只会读取5条评论

一篇完整的评论包括
- 评论时间
- 评论人昵称
- 评论内容
- 获赞数

#### 6.获取微博评论中的图片
- 图片将存放到你一开始设置的路径里

#### 7.把你获取的所有信息存储为一个txt文件
- 该文件将默认放到本程序所在的文件夹里，文件名默认为用户昵称并会在后边加一个数字，比如张三0，张三1，以此类推。

#### 8.把你获取的所有信息存储到你的MYSQL数据库里
- 你需要输入你的mysql账户，密码，以及选定的数据库
- 本程序将自动为你创建三张表，用于储存个人信息，微博正文内容，微博评论内容
- 如果你想要把微博正文和微博评论对应起来看，直接根据评论表内和正文表内的id和mid两个函数join一下即可得到
- id和mid不会在txt文档内出现

```sql
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
```
```sql
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
```
```sql
            create table if not exists comments
            (
                id varchar(50) not null,
                mid varchar(50) not null,
                commentTime varchar(50) not null,
                commenterName varchar(50) not null,
                text varchar(7000),
                compliments int not null
            )
```

#### 9.当你处于微博正文的过程时，会有一个进度条指示你当前的进度
![](https://github.com/Saigyouji2/-/blob/master/%E6%8D%95%E8%8E%B7.PNG)

## 使用
**在**你使用这个程序之前，你需要获取一个cookie字符串
- 请在微博登录页面输入您的账号密码：https://passport.weibo.cn/signin/login
- 登录成功后跳转到：https://weibo.cn
- 按F12打开开发者工具，并按CTRL+R重载页面，点开network选项卡，在下边的列表内可以看见一个叫weibo.cn的内容
- 点开它，看到header选项，找到requests header标题下的cookie，复制这一串字符串（不包括cookie标题及冒号）
- 创建一个txt文件“cookie.txt”，把字符串粘贴到里面，然后把这个文件放入程序根目录即可

然后输入用户昵称，根据提示（Y/N）进行选择即可
![](https://github.com/Saigyouji2/-/blob/master/%E6%8D%95%E8%8E%B72.PNG)
当你完成你的设置时，程序会自动把你的设置保存到config.txt文件内，在下一次启动程序时将读取它，再由用户决定是否按照之前的设置运行程序。

如果一切正常，你可以在txt文件，你指定的图片文件夹，或者mysql数据库内看见你需要的信息

## 后记
**本**程序的cookie采集原计划是用selenium自动实现，然而微博的cookie是若干个项随机拼接的，无法验证- -，所以准备cookie那么麻烦都得怪微博。当你使用本程序时出现卡顿，大概率是被反爬机制稍稍限流了一下，关闭程序，稍等再启动就好。

## 计划内的更新（挖坑）
- 使用selenium获取cookie
- 连续输入多个昵称，分别进行爬取
- 将信息保存为csv文件
- 获取一些额外的小信息（比如微博发布工具）
- 尽量优化程序速率
