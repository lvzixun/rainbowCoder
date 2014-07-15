## rainbowcoder

折腾这么久，终于搞完了这个将markdown转换为html的blog了。Orz。
好多东西之前也只是听说过，也没真正做过，这次折腾还是加了不少技能点。不过整个过程的乐趣还是挺多的，很开心。
-----

blog的编写和发布主要是通过markdown文件，发布的流程大致如下：
1. 在本地编写好要修改的markdown文本，之后使用`git commit`和`git push` 推送到[github](https://github.com/lvzixun/rainbowCoder)上去.
2. [rainbowcoder](rainbowcoder.com)服务器上也会有一样的`git repository`, 将会把`github`上面的最新提交`git pull`下来，同时与当前的本地提交做diff，筛选出做过更改的markdown文件.
3. 遍历`post`文件夹，重新生成`index.md`文件。与之前的diff出来的markdown文件通过`md.py`进行转换成对应的html。

整个流程其实是有点蛋疼的，不如现有的blog框架实用。但，我初衷仅仅是想用markdown来写blog，一个个静态的html就能满足了，所以不想弄那么庞大的框架来实现这一简单的功能。所以就自己折腾了 ;)。

`github`的主要作用是为了做备份，同时保留历史提交记录。做diff的库是用的[gitpython](https://pythonhosted.org/GitPython/0.3.1/tutorial.html)，库本身还是挺方便的，但是`fetch`的操作经常会触发一个对记录日志的`assert`。之后大致看了下那段代码，应该是对新版本的git的日志分析没有对`POST`添加过滤而导致的，简单的修复了下，目前是能够正常的运行。 

这次的折腾，再次让我知道了`python`是多么的强大，没有做不到的库，只有你想不到的库。`lua`比起来这点简直弱爆了~




