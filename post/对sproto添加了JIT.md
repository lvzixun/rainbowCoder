## 对sproto添加了JIT

近期自己一直是在瞎折腾给云风之前写的[sproto](https://github.com/cloudwu/sproto)添加JIT。对协议解析添加JIT这个想法最早是来至于前年看到[upb](https://github.com/haberman/upb)的作者Heberman的一篇blog，他给他自己的upb项目尝试性的用[dynasm](http://corsix.github.io/dynasm-doc/index.html)添加了JIT，来用于进行协议的decode和encode。他仅仅是做了简单的尝试，其性能有50%+的提升：

> Parsing an 80k protobuf into a data structure repeatedly,
> calling Clear() between each parse.  (proto2 == Google protobuf)
>
>
> |  lib    |  performance |
> |:-------:|:------------:|
> | proto2 table-based parser    |   38 MB/s |
> | proto2 generated code parser |  265 MB/s |
> | upb table-based parser       |  340 MB/s |
> | upb JIT parser               |  741 MB/s |

当时也正是因为看完这篇blog以及他的另外一篇[Hello, JIT World: The Joy of Simple JITs](http://blog.reverberate.org/2012/12/hello-jit-world-joy-of-simple-jits.html)才想到要去给[A2](https://github.com/lvzixun/A2)添加JIT的。在之后使用dynasm的痛苦日中，JIT给A2在某些特定的测试用例下提升效果还是很明显的。对A2的这次JIT优化，仅仅是做了最基础的inline threading。针对访问频繁的opcode做了动态代码生成，JIT本身并未对生成的机器码做任何的后端编译优化。JIT的工作只是将原来`switch case`这样的direct threading改为了inline threading。减少指令dispatch的开销，增加CPU缓冲的命中率。 最后的结果是，A2进行这样简单的JIT优化，对性能竟然有40%+的提升。

----

当看到[sproto](https://github.com/cloudwu/sproto)之后，如果像Heberman的ubp那样，也使用dynasm添加JIT的话，根据之前添加JIT的经验来看在性能上应该也会有不错的提升。抱着这样简单的想法，花了1，2周的断断续续时间给添加了inline threading的优化。但测试的结果很不理想，在最好状态下仅仅是有14%+的性能提升。:(

### spro-JIT

其主要工作是在`import_type`生成`struct sproto_type`对象的时候，生成对协议数据encode/decode的代码。
`struct sproto_type`的定义如下:

~~~.c
struct sproto_type {
  const char * name;
  int n;
  int base;
  int maxn;
  struct field *f;

  decode_code decode_func; 
  encode_code encode_func;
};
~~~

其中`decode_func`和`encode_func`既为JIT生成的encode/decode代码。对于之前的解释执行:

~~~.c
    switch(type) {
      case SPROTO_TSTRING: {
        sz = encode_string(cb, ud, f, data, size);
        break;
      }
      case SPROTO_TSTRUCT: {
        sz = encode_struct(cb, ud, f, data, size);
        break;
      }
      case SPROTO_TINTEGER: 
      case SPROTO_TBOOLEAN: {
         // .... encode integer boolean
        break;
      }
    }
~~~
转换成, 如果有以下协议:

```
  .Test {
    var1 0: integer
    var2 1: boolean
    var3 2: string
    var4 3: integer
    var5 4: string 
  }
```
所对应的`struct sproto_type`中生成`decode_func`代码则为：
```
  decode_integer 
  decode_boolean 
  decode_string 
  decode_integer 
  decode_string 
```
`encode_func`则为反之。`decode_xxxx`是生成的解析`xxx`类型的机器码，根据proto的定义按照field进行生成。由于运行时能够知道对应的proto的每个定义，所以在之前的decode中的`findtag`的开销也能省去。对于cpu来说，只需要顺着生成的机器码去执行就行了。但是由于sproto是通过callback的方式来进行填充数据和解析数据的，在真正运行时，callback的开销本身就占到了60%+。如果不去改sproto对lua的绑定代码的话，性能不会有太大的提升。然而我还是倾向于保证sproto库的完整性，不想去修改API和协议数据格式。这就导致了添加JIT本身对使用callback机制的sproto很难有质上的提升。:(


### 对比

A2和upb使用inline threading这样的简单方式就能够有很高的性能提升，跟其测试用例也是有一定关系。A2的测试用例是对5000个数据进行选择排序。JIT对进行排序操作的prototype生成了机器码，整个性能测试仅仅一次进入生成的机器码进行执行，upb也是对一个很大message的数据进行做测试。

于此不同的是sproto的测试是对一个简单的proto做100M次的测试。生成的机器码同时也被调用了100M次。而且sproto本身支持的类型和proto-buffer比起来少很多。


### 可能的优化

对于proto本身还可以进行一个可以尝试的优化，就是对有嵌套定义的proto进行展开encode/decode，对于如下proto：
```
  .Test {
    var1 0: string
    .Test2 {
      tvar1 0: integer
    }

    var2 1: Test2
  }
```
将生成的原来encode代码：
```
 encode_string
 encode_struct
```
改为:
```
 encode_string
 encode_integer
```
这样会减少一次encode的调用，从而提升性能。 这个优化已经打算要加到TODO LIST中了。 ;)

### PS
在[readme](https://github.com/lvzixun/sproto-JIT/blob/master/README.md)上的测试用例中，我故意将proto的tag写的比较乱，增加了原来的sprot在解释过程中findtag的开销，从而与sproto-JIT相比，让其能够看起来有更高的性能，XD。 所以我才在readme里面说道是最好有14%+的提升， 哈哈

















