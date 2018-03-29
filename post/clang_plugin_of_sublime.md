## sublimeText的clang插件

发现我现在越来越懒了，当时一时的兴趣弄出来的blog，本打算好好记录自己做过的一些有意思的事情。但发现搞完之后却各种懒得去写blog记录~~ Orz

------
前段时间花了一周空闲的时间，做了个sublimeText3的clang自动补全插件[clang-complete](https://github.com/lvzixun/clang-complete)。之所以有这个想法，主要是因为用sublimeText2的[sublimeClang](https://github.com/quarnster/SublimeClang)这个插件经常遇到假死和失败的情况，而且作者也已经停止了继续维护。之前也曾经想过去手动改下sublimeClang的代码。无奈的是代码太多了而且很乱，再加上我自己本身都没正经用python写过多少行代码。看了半天只是大致知道它的自动补全是用的clang的[code complete](http://clang.llvm.org/doxygen/group__CINDEX__CODE__COMPLET.html)和正则扫描一起做的。

我在没看代码之前有尝试过用作者新的项目[completion](https://github.com/quarnster/completion)，但是发现这个自动补全的接口是基于服务的跟[ycmd](https://github.com/Valloric/ycmd)类似。不同的地方是completion使用go写的，而ycmd用的是C++/python来实现的。但他们最终对C/C++/OC这类的自动补全都是调用clang的[code complete](http://clang.llvm.org/doxygen/group__CINDEX__CODE__COMPLET.html)来做，所以在补全效果上是一样的。completion中的sublimeText插件功能很简单，而且我觉得自动补全做成服务虽然可以很容易实现不同平台的编辑，但是会在每次调用接口时要保证你的服务上有这个文件而且每次complete都要传输当前unsave files的全内容。于是觉得，如果只是用编辑器的自动补全的话，做lib的方式应该会更快和更方便些。 反正我目前的需求只是想对C/C++/OC这样的语言补全就行了。所以就想着自己用clang的code complete模块来实现个玩下。

我本来以为可能需要遍历clang获得AST，找到对应的函数声明和变量，之后根据不同的block来生成符号表。再根据提供的行和列找到对应的符号表从而去查找返回结果。但当看过clang的[code complete](http://clang.llvm.org/doxygen/group__CINDEX__CODE__COMPLET.html)之后，发现我想的太复杂了，大部分需求其实只需要[clang_codeCompleteAt](http://clang.llvm.org/doxygen/group__CINDEX__CODE__COMPLET.html#ga50fedfa85d8d1517363952f2e10aa3bf)这一个API就能实现。看到此，真心觉得clang是个造福人类的项目啊！

只需要做的是把`completeAt`返回的结果集，提供给python(sublimeText的插件是用python实现)去用。同时提供查询接口，方便进行查询(这里我用C简单实现了个trie树来对结果集进行查找)。

当实现sublimeText的插件时发现：查找这个接口其实是用不到的，因为sublimeText本身有`on_query_completions`这个接口来做查找，而且还是subsequence match。所以，我之前写的trie树就基本上用不到。但是考虑到别的编辑器的补全接口没有像sublimeText那样完善时，是可以用trie树接口来进行查找的，于是就保留了那段代码。

整个项目大部分都耗费在对sublimeText的插件实现上，主要是因为第一次写sublimeText的插件，而且还想支持sublimeText 2/3，但结果发现sublimeText2/3分别用的是python2.X和python3.X。Orz
最后想来想去还是放弃对2的支持，只对3做了支持。这段时间踩的坑还是蛮多的，不过最后还是用起来了。添加了自动补全，语法诊断，以及标示符跳转。最初想要的功能都有了，而且跟之前的sublimeClang这个插件一样的精准。哈哈

### preview
<img src="http://ww4.sinaimg.cn/large/7608d17fgw1eo4dgrggc0g20da0bi44p.gif" width="50%" />