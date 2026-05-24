# 基于CMDB配置平台实现游戏业务主机资源管理-后端

## 一、概述

基于蓝鲸SaaS开发框架开发一个独立SaaS应用，借助蓝鲸CMDB配置平台实现游戏业务主机资源拉取与查询，通过蓝鲸网关/ESB组件API联通 CMDB平台实现数据获取，并根据CMDB主机数据结构，设计查询条件与对应接口。

蓝鲸CMDB配置平台：https://cmdb.ce.bktencent.com/#/

蓝鲸网关/组件API文档：https://apigw.ce.bktencent.com/

## 二、快速开始

### 1、安装依赖

手把手搭建蓝鲸SaaS开发环境-Windows系统：[环境搭建教程文档-完整版](https://doc.weixin.qq.com/doc/w3_AX8A1AafADs10e95lReRLOYOveqc2?scode=AJEAIQdfAAoewToWYH)

实训环境：[华工软件实训环境](https://doc.weixin.qq.com/doc/w3_AMwARAbdAFw7OiLE1N6RKSBLGwTWZ?scode=AJEAIQdfAAoOEGaZ3h)

- 环境依赖：python3.6.12 + MySQL8.3 + Django 3.2.4

- 更换PIP源：

  ```bash
  pip config set global.index-url https://mirrors.tencent.com/tencent_pypi/simple/
  ```

- 安装依赖：

  ```bash
  pip install -r requirements.txt
  ```

### 2、配置环境变量

<font color=red size=6>可以直接修改项目目录下的test.env文件，将其中的APP_ID、APP_TOKEN、APP_SECRET更改为你自己的值</font>

```python
DJANGO_SETTINGS_MODULE=settings
APP_ID=替换为你的应用ID
APP_TOKEN=替换为你的应用TOKEN，即bk_app_secret
BKPAAS_APP_ID=替换为你的应用ID
BKPAAS_APP_SECRET=替换为你的应用SECRET
BKPAAS_ENGINE_REGION=default
BKPAAS_LOGIN_URL=https://ce.bktencent.com/login/
BKAPP_DEPLOY_MODULE=default
BKPAAS_BK_CRYPTO_TYPE=CLASSIC
BKPAAS_MAJOR_VERSION=3
BKPAAS_BK_DOMAIN=ce.bktencent.com
BKPAAS_URL=https://bkpaas.ce.bktencent.com
BKPAAS_CC_URL=https://cmdb.ce.bktencent.com
BKPAAS_JOB_URL=https://job.ce.bktencent.com
BKPAAS_USER_URL=https://bkuser.ce.bktencent.com
BK_API_URL_TMPL=https://bkapi.ce.bktencent.com/api/{api_name}
BK_COMPONENT_API_URL=https://bkapi.ce.bktencent.com
BK_PAAS2_URL=https://ce.bktencent.com
BKPAAS_REMOTE_STATIC_URL=http://example.com/static_api/
BKPAAS_LOGIN_URL=https://ce.bktencent.com/login/
BK_LOGIN_URL=https://ce.bktencent.com/login/
BK_CC_HOST=https://cmdb.ce.bktencent.com
BK_JOB_HOST=https://job.ce.bktencent.com
```

### 3、配置DB

- 创建本地数据库

  ```sql
  CREATE DATABASE '你期望的数据库名称' DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
  ```

- 更改`config/dev.py`中的数据库连接信息

  ![img](https://ctenet-1306582193.cos.ap-nanjing.myqcloud.com/1-20240422102231075.png)

- 数据迁移

- ```python
  python manage.py makemigrations
  python manage.py migrate
  ```

### 4、更改host

```python
在Windows下，hosts 文件位于 C:\Windows\System32\drivers\etc 目录中。要修改 hosts 文件，请按照以下步骤操作：
1、打开文件资源管理器，导航到 C:\Windows\System32\drivers\etc 目录。
2、右键点击 hosts 文件，选择“打开方式”，然后选择“记事本”或其他文本编辑器。
如果没有看到“打开方式”的选项，那么请先将鼠标右键点击记事本图标，然后选择“以管理员身份运行”，在记事本中打开                       C:\Windows\System32\drivers\etc\hosts 文件。

3、在打开的 hosts 文件中，可以添加或修改相应的域名和IP地址映射。每行应包含一个IP地址，后跟一个空格或制表符，然后是域名。如：
# CE环境
127.0.0.1 appdev.ce.bktencent.com
127.0.0.1 dev.ce.bktencent.com
4、完成修改后，保存并关闭 hosts 文件。

5、为使更改生效，可能需要清除DNS缓存。按下 Win + R 键，输入 cmd 并按下 Enter 键打开命令提示符。在命令提示符中输入以下命令并执行
ipconfig /flushdns
现在，已成功修改了 Windows 下的 etc/hosts 配置。
```

![img](https://ctenet-1306582193.cos.ap-nanjing.myqcloud.com/1-20240422102331018.png)

在hosts文件中添加以下两行配置：

```python
# CE环境
127.0.0.1 appdev.ce.bktencent.com
127.0.0.1 dev.ce.bktencent.com
```

### 5、启动Django服务

![img](https://ctenet-1306582193.cos.ap-nanjing.myqcloud.com/1-20240422102413786.png)

命令如下（建议通过IDE中的启动配置来启动）
<font color=red size=6>在IDE中添加Django启动配置，并安装EnvFile插件</font>
![image-20240430092835720](https://ctenet-1306582193.cos.ap-nanjing.myqcloud.com/image-20240430092835720.png)
![img](https://ctenet-1306582193.cos.ap-nanjing.myqcloud.com/1-20240430092754278.png)

```python
python manage.py runserver {{你的host}}
```

## 三、开发样例说明-实现业务列表拉取接口

接口文档：[业务列表拉取接口文档-search_business](https://apigw.ce.bktencent.com/docs/component-api/default/CC/search_business/doc)

### API组件的访问方式

在这里，我们使用shortcuts的方式来访问组件API，使用示例如下：

```python
from blueking.component.shortcuts import get_client_by_request
# 从环境配置获取APP信息，从request获取当前用户信息
client = get_client_by_request(request)
kwargs = {'bk_biz_id': 1}		# 请求参数
result = client.cc.get_app_host_list(kwargs)	# 在这里填写想要调用的API名称，client.组件名称.API名称
```

### 实现业务拉取接口

在`home_application.views`下编写接口，实现业务列表拉取

```python
def get_bizs_list(request):
    """
    获取业务列表
    """
    # 从环境配置获取APP信息，从request获取当前用户信息
    client = get_client_by_request(request)
    # 请求参数
    kwargs = {
        "fields": [
            "bk_biz_id",
            "bk_biz_name"
        ],
        # 社区版环境中业务数量有限，故不考虑分页情况
        "page": {
            "start": 0,
            "limit": 10,
            "sort": ""
        }
    }
    # 这里需要填写对应的组件API的入口地址
    result = client.cc.search_business(kwargs)
    return JsonResponse(result)
```

![image-20240416171654087](https://ctenet-1306582193.cos.ap-nanjing.myqcloud.com/image-20240416171654087.png)

实现接口后，需要在`urls.py`中定义接口的对外访问路由：

![image-20240416172419599](https://ctenet-1306582193.cos.ap-nanjing.myqcloud.com/image-20240416172419599.png)

启动Django服务，访问地址http://dev.ce.bktencent.com:8000/biz-list，即可看到接口响应数据

![image-20240416172705462](https://ctenet-1306582193.cos.ap-nanjing.myqcloud.com/image-20240416172705462.png)

##
