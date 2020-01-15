## zero copy的xml解析器

上周跟[rangercyh](https://github.com/rangercyh)童鞋聊天，他吐槽说wps在编辑excel的时候，有时候会触发一个bug: 明明sheet里面本身没多少数据，但是另存为xml2003格式的时候就会写入一个很大的行列值，导致他们那边倒表解析很慢。当时，我并没怎么关心为啥会有这个bug，主要是在想如果实现个zero copy的xml解析器的话，会不会比用python的`xml.sax`以及其他的xml解析库要快一些？于是就在周末花两天时间实现了[zxml](https://github.com/lvzixun/zxml) ;D

实现的这个xml解析器并不是标准和完备的，比如我没有支持注释和`CDATA`这些语法。主要测试了Excel的 xml2003保存的数据能够正常解析。

----


### zxml

[zxml.h](https://github.com/lvzixun/zxml/blob/master/zxml.h) 头文件里面定义了api。 当你要解析一个xml字符串的时候首先需要创建一个`struct xml_context`这样一个对象，里面主要包含解析过程中需要的内存分配和`reader`对象。 当通过`struct xml_context* xml_create(size_t memory_size);` 接口创建`context`时，需要传入`memory_size`来表示整个parser中对node节点分配的内存池大小。一旦超过这个大小的话，会抛出`XML_MALLOC_ERROR`错误。在parser过程中node里面的值都是直接用指针指向传入的xml字符串的地址，不会再分配内存来存储。同时，因为node节点的分配是在一块连续的内存中，调用者在遍历整个xml树的话，对cpu cache也会很友好。 当实现完之后我简单的跟现有的xml解析做了对比：

| library | parse 200M xml file |
|:-------:|:--------------------:|
| zxml | 0.901s |
| rapidxml | 1.287s |
| tinyxml2 | 3.227s |
| xml.sax of python | 14.996s |

zxml比[rapidxml](http://rapidxml.sourceforge.net/manual.html) 的fastest模式要快个30% ;D

### zxml-lua

为了能够给lua使用，我顺便实现了[lua_zxml.c](https://github.com/lvzixun/zxml/blob/master/lua_zxml.c) 这个lua bind。因为xml本身是有escape转义字符的，但是我又不想把转移放到lua用gsub的方式去做，想在c层面push时直接解析了，
于是就手写了[这段代码](https://github.com/lvzixun/zxml/blob/master/lua_zxml.c#L81-L208) 用来解析转义字符, O(N)的性能开销（本来写的时候脑袋比较乱，写完结果测试发现一遍过了，也是蛮有意思的;D）;

最后我测试了这个lua bind跟我之前实现的libxls的lua bind对比，能快50%左右。

-------

后来跟kk 童鞋解释我实现的这个zxml，又发现了一个json的zero copy的实现[jsmn](https://github.com/zserge/jsmn)。实现的方式差不多，但是他更极致的是，整个实现只有200行，无libc的依赖。