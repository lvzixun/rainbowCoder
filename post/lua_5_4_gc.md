## lua5.4 gc实现

近期因为lua5.4 更新了rc1，同时云风将其合并到了skynet的master上面，所以花时间了解了下新版本的gc实现。于是着手写一篇blog记录了下这两天对lua分代gc的了解。
相比于之前的5.3的分步gc实现，在5.4多了新的分代gc。而且这两种gc工作模式可以通过`lua_gc`api来进行相互切换。
在之前的[这篇blog](https://rainbowcoder.com/lua_5_3_5_gc.html)中有详细记录之前5.3分步gc的实现，在此不再多说，主要记录下新增的分代gc的实现。

-----

原来在`GCObject`中的用来标记当前颜色和状态的`marked`的低3个`bit`用来存储对象的`age`值。在分代gc模式下，所有的对象都会对应一个`age`值，来表示当前对象已经存活的时间和状态。
对于分代gc来说，回收分为`minor collection`(次收集回收)和`major collection`(主收集回收)两种方式。分代gc是基于如下假设来运行的：对于一个正常的系统中的对象，随着
运行时间的增加，总是会趋于一个稳定的大小，被回收的对象多数在新生对象中产生。所以对于分代gc来说，主要去对新生对象集合做gc收集，同时在必要的时候对系统中的所有对象做个主收集回收
。这样的好处是临时对象能够尽快的被释放，同时减少了mark和sweep的数目。这样相比于增量gc，内存可以及时的被释放，同时减少因为gc触发而导致的内存波动。

### gen mode
gc工作的入口依然是`void luaC_step (lua_State *L)`函数，但是此函数的实现加了对当前gc工作模式的判断，来选择是进行`gen mode`(分代模式) 还是`inc mode`增量模式。
对于`gen mode`的入口是`static void genstep (lua_State *L, global_State *g)` 函数。`genstep`函数会根据当前的内存量，来选择是做次收集回收还是主收集回收。
~~~.lua
static void genstep (lua_State *L, global_State *g) {
  if (g->lastatomic != 0)  /* last collection was a bad one? */
    stepgenfull(L, g);  /* do a full step */
  else {
    lu_mem majorbase = g->GCestimate;  /* memory after last major collection */
    lu_mem majorinc = (majorbase / 100) * getgcparam(g->genmajormul);
    if (g->GCdebt > 0 && gettotalbytes(g) > majorbase + majorinc) {
      lu_mem numobjs = fullgen(L, g);  /* do a major collection */
      if (gettotalbytes(g) < majorbase + (majorinc / 2)) {
        /* collected at least half of memory growth since last major
           collection; keep doing minor collections */
        setminordebt(g);
      }
      else {  /* bad collection */
        g->lastatomic = numobjs;  /* signal that last collection was bad */
        setpause(g);  /* do a long wait for next (major) collection */
      }
    }
    else {  /* regular case; do a minor collection */
      youngcollection(L, g);
      setminordebt(g);
      g->GCestimate = majorbase;  /* preserve base value */
    }
  }
  lua_assert(isdecGCmodegen(g));
}
~~~
`genmajormul`字段是通过之前的`collectgarbage("generational", minormul, majormul)`函数设置的。这个值是个百分比，表示当前内存超过了上一次主收集回收时的内存的`genmajormul%`时
触发下一次的主收集回收。反之将会进入次级回收 `youngcollection`中；在分代gc的策略中`youngcollection`应该是经常被触发，`fullgen`被触发的时机应该是极少。多数的对象都会在 `youngcollection`中被回收掉了。
就算是触发了`fullgen`也应该会很快。 `genmajormul`这个值默认是100,  在lgc.h有如下定义:
~~~.c
/* Default Values for GC parameters */
#define LUAI_GENMAJORMUL         100
#define LUAI_GENMINORMUL         20
~~~
100代表的意思是内存相比于上一次主收集回收时的内存翻倍情况下再次触发主收集。 当第一次触发会尝试做一次`fullgen`主收集，主收集之后会再次判断新增的内存是否有降低到一半，如果降低到一半将会设置`setminordebt`
下次次级回收的时机，从而继续进行次级回收。如果`fullgen`执行之后仍然大于新增内存的一半，将会`setpause`下次gc启动将会进入主收集回收`stepfull`。 在`stepfull`中会进行判断新增的对象个数是否有超过上一次的`lastatomic`对象个数的
`1/8`，如果超过了认为是进入了`bad collection`直接切换到`inc mode`模式做`stop world`的sweep。对于`fullgen`主收集回收来说，全部都是切换到`inc mode`同时`stop world`的方式来做回收的。此时有个问题是，如果
当前vm中在不停的分配和持有`object`，将会导致`gen mode`模式不停的进入`bad collection`状态，然而这个状态会`stop world`的mark和sweep整个vm的`object`，在应用层看来会定时的卡顿。不过每次`bad collection`的回收完之后
会进行调用`setpause(g);`如果vm在不停的增长内存的话， 下次启动的间隔也会变长。所以并不会太频繁的触发`bad collection`，但是因为`stop world`的原因，所以一旦多次触发主收集回收的话，很大概率会导致vm的卡顿。

### youngcollection
对于一个正常的vm来说，次级回收应该是被多数情况下触发的。次级回收的入口是在`static void youngcollection (lua_State *L, global_State *g)` 函数。整个次级回收会根据`allgc`, `survival`, `old`, `reallyold`
这几个链表(同理对于带有`__gc`元方法的对象会放在`finobjsur`, `finobjold`, `finobjrold`链表中，在此只说明下不带元表的正常对象) 和 每个对象的`age`字段来进行做sweep。任意一个可回收的对象的`age`只会分为如下的状态:
~~~.c
/* object age in generational mode */
#define G_NEW       0   /* created in current cycle */
#define G_SURVIVAL  1   /* created in previous cycle */
#define G_OLD0      2   /* marked old by frw. barrier in this cycle */
#define G_OLD1      3   /* first full cycle as old */
#define G_OLD       4   /* really old object (not to be visited) */
#define G_TOUCHED1  5   /* old object touched this cycle */
#define G_TOUCHED2  6   /* old object touched in previous cycle */
~~~

各个状态之间的转换可以在这个[slide](https://www.lua.org/wshop18/Ierusalimschy.pdf) 里面能看到：
![image](https://user-images.githubusercontent.com/1283355/81497448-27291980-92f1-11ea-9242-f11bb3b822ac.png)

其中黑线表示的是经过每轮gc调用`sweepgen`之后状态的变更；蓝色的线条表示的是通过`luaC_barrier_` 的状态转换；红色则是经过`luaC_barrierback_`的状态变换。
对于一个正常被引用的对象，在经历了多次的gc循环之后会经过 如下状态的转换:
```
G_NEW -> G_SURVIVAL -> G_OLD1 -> G_OLD
```
一旦成为了`old`对象(大于`G_SURVIVAL`之后的状态)，就必然不会在`yongcollection`中被清理掉，只能等待`fullgen`主收集回收被清理。`yongcollection`清理的对象必然是属于`G_NEW`或者是`G_SURVIVAL`的状态。
同时对于一个`old`对象，其本身的颜色只能是`black`或`gray`。次级回收的工作量主要在那些最近1-2轮gc中产生的对象。能活过2轮的对象就默认为是`old`状态，不再进行sweep处理。

----

当一次次级回收进行时， 需要知道当前哪些新生对象被持有引用。最简单的方式是像之前mark-sweep工作的方式那样， 从根节点开始传播标记，之后就能知道哪些对象还在存活。但是如果这样做的话， 就会导致mark过程要遍历整个vm的对象，
因此会出现stop world。这显然工作量太大，所以在`gen mode`分代回收模式下面，次级回收主要是根据每轮gc触发`luaC_barrier_`和`luaC_barrierback_`以及`grayagain`链表中产生的对象来进行`propagate`。
之后整个sweep工作会在`sweepgen`函数中进行， 这个函数会做两件事情，清理那些颜色为`white`的对象，同时对非白对象的`age`进行下一状态更新。当清理完从`G_NEW`和`G_SURVIVAL`的对象之后，进行`survival`, `old`, `reallyold`
这三个链表的更新:
~~~.c
/* sweep nursery and get a pointer to its last live element */
  psurvival = sweepgen(L, g, &g->allgc, g->survival);
  /* sweep 'survival' and 'old' */
  sweepgen(L, g, psurvival, g->reallyold);
  g->reallyold = g->old;
  g->old = *psurvival;  /* 'survival' survivals are old now */
  g->survival = g->allgc;  /* all news are survivals */
~~~

从代码中可以看到, `allgc`链表管理着整个`gcobjects`；`survival`, `old`, `reallyold`这三个指针指示指向`allgc`链表的不同item而已，同时根据指向不同item所在链表中的位置是: `allgc` < `survival` < `old` < `reallyold`
的关系。每次次级收集将要开始时`allgc` -- `survival`之间的对象多数是`G_NEW`； `survival` -- `old`是`G_SURVIVAL`；`old` -- `reallyold`是`G_OLD1`；`reallyold` -- `end`多数是`G_OLD`的对象。
当sweep进行清理完成之后，会调用`correctgraylists`函数，这个函数主要是将那些在此轮gc中被`barrier`函数标记为touch的对象做更新。touch分为两种状态`G_TOUCHED1`和`G_TOUCHED2`。每次触发`luaC_barrierback_`将会把
对象标记为`G_TOUCHED1`表示在此轮中进行触碰了该对象，下一轮没有被触碰将会变为`G_OLD`，同时移除`gclist`链表。
上述情况只适用于`table`和`userdata`这两种对象类型， 对于`thread`对象，除了当前新生对象外，会在触发
主收集之前将永远的放在对应的`grayagain`链表中。我认为这样做的原因是在对一个coroutine做resume时，没有触发`barrier`行为将对应的co正确mark，导致无法知道对应的co中的调用栈是否有变化。为了保证正确性，
干脆直接就一直放在`grayagain`链表中，每次执行次级回收的时候`atomic`会标记到这些co，从而能够标记到当前轮中触发了resume的co中新产生的对象。

### inc mode
增量模式相对于5.3，对于工作量的衡量有些变化。之前在`GCSpropagate`阶段每个对象的大小是真是的内存`alloc size`，现在改为了对象个数。我觉得这样做跟之前的5.3相比，对于每步gc的回收会更多一些。
