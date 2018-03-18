# -*- coding: utf-8 -*-
import scrapy
import time
import json
import execjs
import os
from PIL import Image
import base64
from scrapy.http.cookies import CookieJar
from zhihu_login.settings import zhihu_account
class login(scrapy.Spider):
    name = 'login'
    allowed_domains = ['www.zhihu.com']
    start_urls = ['http://www.zhihu.com/']
    login_url = 'https://www.zhihu.com/api/v3/oauth/sign_in'  # 登陆的url
    # 验证码地址; 'PUT'方式提交是获取验证码， 'POST'方式提交是检验验证码是否正确，'GET'是查看是否有验证码
    captcha_url = 'https://www.zhihu.com/api/v3/oauth/captcha?lang=en'
    #私信链接
    inbox_url='https://www.zhihu.com/inbox'

    #登陆时，需要的信息
    user = zhihu_account['user']
    password= zhihu_account['password']
    client_id = 'c3cef7c66a1843f8b3a9e6a1e3160e20'

    headers = {
        'authorization':'oauth '+client_id, #oauth 后面一定要加个空格，教训啊。。。
        #'authorization': 'oauth c3cef7c66a1843f8b3a9e6a1e3160e20',
        'Host': 'www.zhihu.com',
        'Origin': 'https://www.zhihu.com',
        'Referer': 'https://www.zhihu.com/signup?next=%2F',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36 QQBrowser/4.3.4986.400',
        'X-UDID':'AFBtxXeoNg2PTos0vtZBaxkscRPXn4bJ7po=',
        'X-Xsrftoken':'77400f66-053a-43b0-a7bb-96075224f6da',
        'If-None-Match':'7eb4ebdc523b46e04c7fa978993f57f559d7ed8b'
    }

    #为这个爬虫，单独设置的settings，这个settings会覆盖掉全局的settings的设置
    custom_settings={
        "COOKIES_ENABLED": True,
        "DOWNLOAD_DELAY": 0.5,
        #'LOG_FILE' : "zhihu.log",
        #'LOG_LEVEL':'WARNING',
    }


    def parse(self, response):
        '''登陆验证结束，正式开始处理爬虫'''
        if response.status == 200:
            print('访问私信页面,成功')
            #print(response.text)
        else:
            print(response.text)


    #公用函数
    def get_timestamp(self):
        timestamp = int(time.time() * 1000)  # 时间戳
        return str(timestamp)

    def get_signature(self):
        path = os.path.dirname(os.path.abspath(__file__))
        fp=open(path+'/zhihu.js')
        js=fp.read()
        fp.close()
        ctx=execjs.compile(js)
        signature=ctx.call('getSignature',self.get_timestamp())
        return signature

    def start_requests(self):
        #开始请求验证码url，看是否存在验证码
        yield scrapy.Request('https://www.zhihu.com/api/v3/oauth/captcha?lang=en',headers=self.headers,
                             callback=self.ifCaptcha,dont_filter=True)

    def ifCaptcha(self,response):
        captcha_info = json.loads(response.text)
        #登陆时 需要传递的参数；
        params={
            'client_id':self.client_id,
            'grant_type':'password',
            'timestamp':self.get_timestamp(),
            'source':'com.zhihu.web',
            'signature':self.get_signature(),
            'username':self.user,
            'password':self.password,
            'captcha':'',
            'lang':'cn',
            'ref_source':'homepage',
            'utm_source':'',
        }
        if 'show_captcha' in captcha_info:
            if captcha_info['show_captcha']:
                 print('出现验证码')
                 yield scrapy.Request(url=self.captcha_url, headers=self.headers, method='PUT', callback=self.captcha_process, meta=params)
            else:
                print('无验证码')
                yield scrapy.FormRequest(url=self.login_url, headers=self.headers, formdata=params, method='POST', callback=self.check_login)
        else:
            self.logger.warning('出现未知异常： %s', response.text)
            #print("出现未知异常： "+response.text)



    def captcha_process(self,response):
        '''处理验证码'''
        #第一步： 获取验证码(把base64图片数据流解码，生成图片)
        print(response.text)
        res_dit = json.loads(response.text)
        img_base64=res_dit['img_base64']
        pictureData = base64.b64decode(img_base64)
        with open("captcha.gif", "wb") as f:
            f.write(pictureData)
            f.close()
        try:
            img=Image.open('captcha.gif')
            img.show()
        except:
            print('转图片失效')

        #params = response.meta
        #检查验证码是否写的正确
        captcha = input("输入验证码")
        params_checkCaptcha={
            'input_text':captcha
        }
        yield scrapy.FormRequest(url=self.captcha_url, headers=self.headers, formdata=params_checkCaptcha, method='POST',
                                 meta=params_checkCaptcha, callback=self.check_captcha)



    def check_captcha(self,response):
        '''检查验证码是否正确'''
        res_dit=json.loads(response.text)

        #print(response.meta)
        params={
            'client_id':self.client_id,
            'grant_type':'password',
            'timestamp':self.get_timestamp(),
            'source':'com.zhihu.web',
            'signature':self.get_signature(),
            'username':self.user,
            'password':self.password,
            'captcha':'',
            'lang':'cn',
            'ref_source':'homepage',
            'utm_source':'',
        }
        params['captcha']=response.meta['input_text']

        if 'success' in res_dit:
            print('验证码正确')#验证码正确，访问登陆链接
            yield scrapy.FormRequest(url=self.login_url, headers=self.headers, formdata=params, method='POST',
                                    callback=self.check_login)
        else:
            print(response.text)


    def check_login(self,response):
        '''登陆结果判断'''
        response_dit=json.loads(response.text)

        if 'user_id' in response_dit:
            print('登陆成功')
            #登陆成功后，执行get_cookies函数
            self.get_cookies(response)
            yield scrapy.Request(url=self.inbox_url, headers=self.headers, callback=self.parse)
        else:
            print('登陆异常 ： '+response.text)


    def get_cookies(self,res):
        '''获取登陆成功后的cookies'''
        cookie_jar = CookieJar()
        cookie_jar.extract_cookies(res, res.request)
        # cookiejar是类字典类型的,将它写入到文件中
        with open('cookies.txt', 'w') as f:
            for cookie in cookie_jar:
                f.write(str(cookie) + '\n')












