## 正则表达式的实现

之前花了一周的断断续续时间实现了个简单的正则表达式引擎[regex](https://github.com/lvzixun/regex), 之所以想要实现这个项目，主要是因为早期在网上偶然看到了一位名叫airtrack的coder写的[正则表达式的实现1,2](http://airtrack.me/posts/2013/07/05/%E6%AD%A3%E5%88%99%E8%A1%A8%E8%BE%BE%E5%BC%8F%E5%AE%9E%E7%8E%B0%EF%BC%88%E4%B8%80%EF%BC%89)，当看完之后发觉如果按照经典龙书的教程来实现貌似也不是那么的难。正好一直都想实现个正则表达式引擎，于是就开始着手实现了下。

由于之前有过实现解释器[A2](https://github.com/lvzixun/A2)的经验，所以从词法分析->抽象语法树->NFA这整个阶段都还是很顺利的，问题主要是出现在了NFA生成DFA以及DFA化简阶段，用C这种静态而且缺乏各种数据结构的语言去描述各种数学上的解析步骤，写起来简直让人蛋疼无比。数学家在写出实现过程时，未必会去考虑工程师能否很快捷的实现。但，在工程师去实现过程中，却要把这个流程实现的尽可能的高效以及简单。尤其NFA转换成DFA使用的是[subset construction](http://en.wikipedia.org/wiki/Powerset_construction)方法。为了避免多次的进行遍历和创建临时队列，在实现过程中，其实用了一些看起来比较dirty的方法，对于阅读者来说，看代码会觉得比较晦涩。而且在实现时，都会不禁发问是否会有更好的方案来实现，但是最后还是坚持的按照经典教程的案例把DFA实现出来了。

整个代码仅仅是包含了正则表达式最最基础的部分：与(ab), 或(a|b), 重复(a*). 后续我又添加了一些转义字符和匹配特性（详情请见[readme](https://github.com/lvzixun/regex/blob/master/README.md),但是总体上还是比python，perl的正则引擎差些。但这仅仅是功能添加问题，由于DFA生成已经实现，之后添加功能还是比较容易的。

#### 设计

大致流程如下：
```
[parse 解析生成AST] ----> [遍历AST生成 NFA] ----> [DFA 通过子集构造法]
                                                  |
                                                  |
                                                  v
                                      [minimization DFA 最小化DFA]
```
大部分代码主要是去构造最小化DFA，之后拿到生成DFA状态图，进行匹配输入字符串。 由于提供的正则规则比较少，而且没有backreference, capture, not greedy。所以遍历DFA的代码是很简单的，而且是O(N)的性能， N的大小取决于输入的原字符串的长度。通过 `struct reg_pattern* reg_new_pattern(struct reg_env* env, const char* rule);` 这个`API`来生成一个pattern对象，在`struct reg_pattern`数据结构中存储了DFA状态机, 当调用`int reg_match(struct reg_pattern* pattern, const char* source, int len);` API时，其实只是做了DFA遍历。遍历中如果遇到终结状态，则返回。如果遇到无法匹配的状态或者字符串到了结尾，但是依旧没匹配到终结状态，则返回0. 


### parse生成AST

parse的代码主要是在`reg_parse.c`中，由于正则本身的文法就很简单，其实是可以完全省略过生成AST的部分，直接生成NFA状态的。但是在实现的时候，我还是习惯先生成AST，这样在流程上会清晰些， AST的生成用的是递归下降。AST的每个节点是如下结构：

~~~~.c
struct reg_ast_node {
  enum reg_op op;                       // 节点类别
  union {
    struct reg_range range;             // value
  }value;

  struct reg_ast_node* childs[2];       // 子节点
};
~~~~
通过内部API `struct reg_ast_node* parse_exec(struct reg_parse* p, const char* rule, size_t size);` 生成根节点，之后生成NFA。

### NFA 生成

NFA状态机的生成是在`state_gen.c`中，遍历AST，不同类型的节点对应着不同的NFA状态图，一下列出主要的NFA状态图：

rule: ab
```
<start> --a--> <s1> --ε--> <s2> --b--> <end> 
```

rule: a|b
```
   |----ε----> <s1> --a--> <s2> ---ε-------|
   |                                       ∨
<start> --ε--> <s3> --b--> <s4> ---ε---> <end>
```

rule: a*
```
    |------------------ε-------------------|
    |                                      ∨
  <start> --ε--> <s1> --a--> <s2> --ε--> <end> 
                  ^            |
                  |-----ε------|
```

rule: [a-b]
```
<start> --[a-b]--> <end>
```
符号`ε`是epsilon空边，可以不需要接受任何字符跳转到下个状态。最终的整个NFA是有这些一个个的子NFA连接成的。其实在此，拿到NFA之后就能够进行match工作了，但是NFA的性能还是比较差劲，因为你没法确定给定一个字符，到达的下个状态是否也是确定的。因此，就不得不backtracing回溯状态节点去做匹配。所以我们需要将NFA化简为DFA来提升匹配的性能。


### DFA 生成
我们很难一步去构造出来DFA。因此需要通过NFA进行化简生成DFA，使用的是子集构造法 [wiki](http://en.wikipedia.org/wiki/Powerset_construction)，其算法主要是如下：

1. 构造起始状态的closure(start) 其中closure的意思是start状态通过epsilon空边也能够到达的状态集合。添加到DFA SUBSET中。

2. 获得DFA SUBSET中一个状态current subset。对其遍历所有的edge集合，获得next_subset, 与DFA SUBSET中的各个集合匹配，如果不存在，则添加到NFA SUBSET中。同时记录下map[current, edge] -> next_subset。

3. 在DFA SUBSET中取出下一个 subset，重复2步骤，直到DFA SUBSET中包含了 NFA中的所有状态。

新生成的map，即为构造出来的DFA。这段代码的实现主要是在`state_gen.c`中的 `_gen_dfa`函数。


### DFA最小化
通过NFA转化生成的DFA并不是最小化的DFA，还会有些冗余的状态，所以需要最小化. 最小化是通过split算法来实现的，[wiki](http://en.wikipedia.org/wiki/DFA_minimization)，其算法如下：

1. 根据DFA中的终结状态和非终结状态来标记出两个subset(可能是一个，DFA中全部都是终结状态)， 将其添加到MIN_DFA SUBSET中.

2. 从MIN_DFA SUBSET中取出一个状态集，对其所有edge进行遍历，如果发现有条边，将会吧当前的subset分割成两个subset。所谓的分割(split)主要对于这条edge，遍历当前的subset，发现其中有的状态根据这条边所到达的subset，是属于不同的subset。则将其state 分裂到新的subset中。 

3. 重复2步骤，直到没有所有的subset无法再split为止。


### thinking
其实在实现过程中对于DFA的构造和最小化，花费了很大的劲。不得不说，按照数学家的思维来写这个代码真的是比较痛苦。其实写到最后我都觉得，就算我不去构造DFA，直接是遍历parse生成的AST也能够做正则匹配。如果AST的性能不好的话，其实是可以转换成一个中间指令集，来执行字节码来进行做字符匹配。 到我实现regex之后才发现，这个想法在别人N早之前就已经尝试过了，有个叫 Thompson's VM 的东西。 而且，根据早期春哥写的[sregex](https://github.com/openresty/sregex)，其实用的也是这个，而且还使用dynsm添加JIT。

近期还花了一段时间读了Russ Cox写的关于[正则表达式的论文](http://swtch.com/~rsc/regexp/)，其中有详细描述NFA,DFA, backtracing 以及上面提到的 Thompson's VM这一些列的东西。从中科普受益了很多，;)

如果有时间的话，也想改成VM的，先加入到TODO list中吧~























