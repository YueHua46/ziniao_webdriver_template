# 紫鸟WebDriver模板

搭建了一个专门通过紫鸟WebDriver操作紫鸟店铺的项目

## 基础模块架构

包含了一些基础的模块：

- logger模块
    自带清理30天后的日志记录
- config配置模块
- ziniao_func模块

主文件就是main.py

## 使用方式

1. 配置好 `.env` 环境变量文件中的基本配置

.env.example里有示例的配置，自己则要用.env来命名创建一个配置文件去配置

2. 安装第三方依赖

通过 `pip install -r requirements.txt` 来安装必须的第三方依赖包

3. 打开店铺

通过 `ziniao_func.py` 模块中的 `open_store_by_name()` 方法去调用传递对应的店铺名称，就可以打开一个店铺，就跟客户端那种情况一样

示例：

```py
from ziniao_func import open_store_by_name

open_store_by_name('AMZ-TEST')
```