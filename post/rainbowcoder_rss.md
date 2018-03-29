## 添加了RSS

今天才看feedy的时候，突发奇想：要不对rainbowcoder也添加下RSS源支持吧。[KK](http://weibo.com/lisphacker?from=myfollow_all)童鞋说可以用Yahoo的[pipes](http://pipes.yahoo.com/pipes/)很方便的自动帮你生成RSS源。但是想到自己的整个blog都是手工山寨出来的，禁不住想，要不自己也手工山寨生成一个。XD

google了一下RSS的工作流程，本来以为是一个很复杂的东西，没想到我只需要生成一个按照RSS2.0格式填写的xml文件就行了。之后再feedly里面输入这个xml的连接地址，就能读取了。我只需要在每次build生成新html之后，再遍历当前的post目录，生成下一个记录所有post的RSS xml文件就ok了。 于是，在下午的时候，花了1个小时的时间用lua写了一个生成RSS xml的代码([rss.lua](https://github.com/lvzixun/rainbowCoder/blob/master/rss.lua))。

为什么不是用python，而是lua，主要原因是前段时间用lua刚实现过sprotodump，python实在是不熟悉，不太想折腾了。于是，为了快速实现，就用lua实现了。 Orz 

这篇[RSS tutorial](https://www.mnot.net/rss/tutorial/) 写的很详细。当我写完之后，才发现python是有[rss.py](https://gist.github.com/mnot/221419)这个库的。而且实现的还很完善，看来，我又造了个蹩脚的轮子，不过整个过程还是玩的很开心，哈哈



